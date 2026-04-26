from typing import TypedDict, List, Literal, Annotated
import operator
from pydantic import BaseModel, Field

from langchain_core.messages import HumanMessage, SystemMessage, AnyMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

# 引入基础大脑
from core.llm import get_llm
# 引入提示词管理器
from core.prompt_manager import prompt_manager
# 引入长期记忆引擎
from rag.memory_store import user_memory
# 引入日志 (遵循审查建议：替换 print)
from core.logger import logger

# 引入工具
from agents.tools import get_web_search_tool, arxiv_search_tool, read_excel_csv_tool
from rag.local_tools import list_local_files, search_local_content, read_full_document

# ==========================================
# 1. 定义图的状态 (Agent State)
# ==========================================
class AgentState(TypedDict):
    """
    定义贯穿整个 LangGraph 生命周期的状态对象。
    """
    messages: Annotated[List[AnyMessage], operator.add]
    current_route: str          
    search_keywords: List[str]  
    context_memory: str  # 新增：解耦记忆检索与下游节点

# ==========================================
# 2. 定义严格的 Pydantic Schema (强制约束模型输出)
# ==========================================
class RouteDecision(BaseModel):
    next_node: Literal["direct_chat", "web_search_agent", "local_rag_agent"] = Field(
        description=(
            "路由决策，必须从以下三个选项中严格选择其一："
            "1. 'direct_chat': 简单的日常问候、通用常识、闲聊，无需查资料即可直接回答。"
            "2. 'web_search_agent': 询问实时新闻、最新事件、未知事实或需要联网的公众知识。"
            "3. 'local_rag_agent': 询问明确涉及'我们的系统'、'内部文档'、'私有库'或用户上传文件的问题。"
        )
    )
    
    search_keywords: List[str] = Field(
        description="如果决策是 web_search_agent 或 local_rag_agent，请提取 1 到 3 个核心检索关键词。如果无需检索，则返回空列表 []。",
        default_factory=list
    )

# ==========================================
# 3. 实例化小模型并绑定结构化输出
# ==========================================
router_llm = get_llm()
structured_router = router_llm.with_structured_output(RouteDecision)

# ==========================================
# 4. 编写处理节点逻辑
# ==========================================

async def retrieve_memory_node(state: AgentState):
    """前置节点：统一捞取长期记忆，实现与下游业务节点的解耦"""
    user_query = state["messages"][-1].content
    relevant_memories = user_memory.retrieve_memory(user_query)
    logger.info("[Memory] 🧠 长期记忆检索完成，已注入上下文。")
    return {"context_memory": relevant_memories}

async def router_node(state: AgentState):
    """图谱的入口节点：负责意图识别与路由分发。"""
    user_query = state["messages"][-1].content
    sys_prompt = (
        "你是一个智能且高效的流量分发网关。请仔细分析用户的最新请求，并选择最佳的处理节点。\n"
        "请返回 JSON 格式。返回的 JSON 必须且仅能包含以下两个字段：\n"
        "1. \"next_node\": 必须严格从这三个值中选择一个：\n"
        "   - \"direct_chat\": 简单的日常问候、闲聊等直接回复的问题\n"
        "   - \"web_search_agent\": 需要联网查询最新信息或公众知识的问题\n"
        "   - \"local_rag_agent\": 涉及内部文档或系统的具体问题\n"
        "2. \"search_keywords\": 核心搜索关键词字符串列表（如果没有则为空列表 []）。"
    )
    
    logger.info("[Router] 🧭 正在分析用户意图并决定路由流向...")
    
    try:
        decision: RouteDecision = await structured_router.ainvoke([
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_query)
        ])
        logger.info(f"[Router] 🎯 决策完毕 | 目标节点: {decision.next_node} | 提取关键词: {decision.search_keywords}")
        return {
            "current_route": decision.next_node,
            "search_keywords": decision.search_keywords
        }
    except Exception as e:
        logger.warning(f"[Router] ⚠️ 解析失败或模型异常，触发降级路由(direct_chat): {e}")
        return {
            "current_route": "direct_chat",
            "search_keywords": []
        }

def route_condition(state: AgentState) -> str:
    # 经过 try-except 兜底后，此处的 current_route 必定是合法的 Literal
    return state["current_route"]

async def direct_chat_node(state: AgentState, config: RunnableConfig):
    logger.info("[Direct Chat] 💬 走闲聊/常识通道，无需检索...")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_msg = SystemMessage(content=base_sys.format(long_term_memory=state.get("context_memory", "")) + "\n\n(当前为直答模式，无需调用工具，请直接回复。)")
    
    llm = get_llm()
    response = await llm.ainvoke([sys_msg] + state["messages"], config=config)
    return {"messages": [response]}

async def web_search_node(state: AgentState, config: RunnableConfig):
    logger.info(f"[Web Search] 🌐 走联网检索通道，使用关键词: {state.get('search_keywords')}")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_prompt = base_sys.format(long_term_memory=state.get("context_memory", "")) + f"\n\n(提示: 刚才路由网关为您提取的推荐检索关键词是: {state.get('search_keywords')})"
    
    web_tools = [get_web_search_tool(max_results=3), arxiv_search_tool]
    agent = create_react_agent(get_llm(), tools=web_tools, prompt=sys_prompt)
    
    res = await agent.ainvoke({"messages": state["messages"]}, config=config)
    new_messages = res["messages"][len(state["messages"]):]
    return {"messages": new_messages}

async def local_rag_node(state: AgentState, config: RunnableConfig):
    logger.info(f"[Local RAG] 📁 走本地知识库通道，使用关键词: {state.get('search_keywords')}")
    
    base_sys = prompt_manager.get("chat_agent", "system_prompt")
    sys_prompt = base_sys.format(long_term_memory=state.get("context_memory", "")) + f"\n\n(提示: 刚才路由网关为您提取的推荐检索关键词是: {state.get('search_keywords')})"
    
    local_tools = [list_local_files, search_local_content, read_full_document, read_excel_csv_tool]
    agent = create_react_agent(get_llm(), tools=local_tools, prompt=sys_prompt)
    
    res = await agent.ainvoke({"messages": state["messages"]}, config=config)
    new_messages = res["messages"][len(state["messages"]):]
    return {"messages": new_messages}

# ==========================================
# 6. 构建并连线状态机 (StateGraph)
# ==========================================
workflow = StateGraph(AgentState)

# 注册所有节点
workflow.add_node("retrieve_memory", retrieve_memory_node)
workflow.add_node("router", router_node)
workflow.add_node("direct_chat", direct_chat_node)
workflow.add_node("web_search_agent", web_search_node)
workflow.add_node("local_rag_agent", local_rag_node)

# 串联边
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

# 导出最终的编译图谱
normal_chat_agent = workflow.compile()
tools = [] # 标记为空，旧接口不再直接拿 tools 去生成 agent 了