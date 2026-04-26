from typing import TypedDict, List, Literal, Annotated
import operator
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

from core.llm import get_llm
from core.prompt_manager import prompt_manager
from rag.memory_store import user_memory
from core.logger import logger

from agents.tools import get_web_search_tool, arxiv_search_tool, read_excel_csv_tool
from rag.local_tools import list_local_files, search_local_content, read_full_document

# Agent State definition
class AgentState(TypedDict):
    """
    Represents the state object throughout the LangGraph lifecycle.
    """
    messages: Annotated[List[AnyMessage], operator.add]
    current_route: str          
    search_keywords: List[str]  
    context_memory: str  # Decoupled memory retrieval for downstream nodes

# Pydantic Schema for structured routing decisions
class RouteDecision(BaseModel):
    next_node: Literal["direct_chat", "web_search_agent", "local_rag_agent"] = Field(
        description=(
            "Routing decision. Choose one of the following:"
            "1. 'direct_chat': For simple greetings, general knowledge, or casual chat."
            "2. 'web_search_agent': For real-time news, latest events, or public knowledge requiring web access."
            "3. 'local_rag_agent': For queries about internal systems, private documents, or uploaded files."
        )
    )
    
    search_keywords: List[str] = Field(
        description="Search keywords for retrieval (1-3 keywords). Return empty list [] if not applicable.",
        default_factory=list
    )

# Instantiate router with structured output support
router_llm = get_llm()
structured_router = router_llm.with_structured_output(RouteDecision)

# Processing Nodes

async def retrieve_memory_node(state: AgentState):
    """Retrieves long-term memory to decouple retrieval from business logic nodes."""
    user_query = state["messages"][-1].content
    relevant_memories = user_memory.retrieve_memory(user_query)
    logger.info("[Memory] Long-term memory retrieval complete.")
    return {"context_memory": relevant_memories}

async def router_node(state: AgentState):
    """Entry point node responsible for intent recognition and routing."""
    user_query = state["messages"][-1].content
    sys_prompt = (
        "You are an efficient traffic distribution gateway. Analyze the user request and select the best processing node.\n"
        "Return the response in JSON format. The JSON must contain the following fields:\n"
        "1. \"next_node\": Must be one of: \"direct_chat\", \"web_search_agent\", \"local_rag_agent\".\n"
        "2. \"search_keywords\": A list of core search keyword strings."
    )
    
    logger.info("[Router] Analyzing user intent for routing...")
    
    try:
        decision: RouteDecision = await structured_router.ainvoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_query)
        ])
        logger.info(f"[Router] Decision: {decision.next_node} | Keywords: {decision.search_keywords}")
        return {
            "current_route": decision.next_node,
            "search_keywords": decision.search_keywords
        }
    except Exception as e:
        logger.warning(f"[Router] Parsing failure or model error. Falling back to direct_chat: {e}")
        return {
            "current_route": "direct_chat",
            "search_keywords": []
        }

def route_condition(state: AgentState) -> str:
    """Helper for conditional edge mapping."""
    return state["current_route"]

async def direct_chat_node(state: AgentState, config: RunnableConfig):
    """Handles general knowledge and casual conversation without retrieval."""
    logger.info("[Direct Chat] Executing direct response mode...")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_msg = SystemMessage(content=base_sys.format(long_term_memory=state.get("context_memory", "")) + "\n\n(Direct response mode: reply directly without calling tools.)")
    
    llm = get_llm()
    response = await llm.ainvoke([sys_msg] + state["messages"], config=config)
    return {"messages": [response]}

async def web_search_node(state: AgentState, config: RunnableConfig):
    """Handles queries requiring external web search."""
    logger.info(f"[Web Search] Executing web search agent with keywords: {state.get('search_keywords')}")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_prompt = base_sys.format(long_term_memory=state.get("context_memory", "")) + f"\n\n(Note: Recommended search keywords: {state.get('search_keywords')})"
    
    web_tools = [get_web_search_tool(max_results=3), arxiv_search_tool]
    agent = create_react_agent(get_llm(), tools=web_tools, prompt=sys_prompt)
    
    res = await agent.ainvoke({"messages": state["messages"]}, config=config)
    new_messages = res["messages"][len(state["messages"]):]
    return {"messages": new_messages}

async def local_rag_node(state: AgentState, config: RunnableConfig):
    """Handles queries requiring internal knowledge base retrieval."""
    logger.info(f"[Local RAG] Executing local retrieval agent with keywords: {state.get('search_keywords')}")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_prompt = base_sys.format(long_term_memory=state.get("context_memory", "")) + f"\n\n(Note: Recommended search keywords: {state.get('search_keywords')})"
    
    local_tools = [list_local_files, search_local_content, read_full_document, read_excel_csv_tool]
    agent = create_react_agent(get_llm(), tools=local_tools, prompt=sys_prompt)
    
    res = await agent.ainvoke({"messages": state["messages"]}, config=config)
    new_messages = res["messages"][len(state["messages"]):]
    return {"messages": new_messages}

# StateGraph construction
workflow = StateGraph(AgentState)

workflow.add_node("retrieve_memory", retrieve_memory_node)
workflow.add_node("router", router_node)
workflow.add_node("direct_chat", direct_chat_node)
workflow.add_node("web_search_agent", web_search_node)
workflow.add_node("local_rag_agent", local_rag_node)

workflow.add_edge(START, "retrieve_memory")
workflow.add_edge("retrieve_memory", "router")

workflow.add_conditional_edges(
    "router",
    route_condition,
    {
        "direct_chat": "direct_chat",
        "web_search_agent": "web_search_agent",
        "local_rag_agent": "local_rag_agent"
    }
)

workflow.add_edge("direct_chat", END)
workflow.add_edge("web_search_agent", END)
workflow.add_edge("local_rag_agent", END)

# Compiled graph for normal chat operations
normal_chat_agent = workflow.compile()
tools = []
