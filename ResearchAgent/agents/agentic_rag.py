from typing import TypedDict, List
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
import asyncio

from core.llm import get_llm
from core.logger import logger
from rag.vector_store import local_kb

class AgenticRAGState(TypedDict):
    original_query: str
    chat_history: List[BaseMessage]
    current_search_query: str
    documents: List[Document]
    iteration_count: int
    final_answer: str

class GradeResult(BaseModel):
    is_relevant: bool = Field(description="Boolean indicating if the document answers the query.")

async def grade_single_doc(doc: Document, query: str) -> bool:
    """Evaluate a single document for relevance using LLM structured output."""
    llm = get_llm()
    grader = llm.with_structured_output(GradeResult)
    prompt = f"Assess if the following document is relevant to the user query.\n\nQuery: {query}\n\nDocument: {doc.page_content}"
    try:
        res = await grader.ainvoke([HumanMessage(content=prompt)])
        return res.is_relevant
    except Exception as e:
        logger.warning(f"Document grader encountered an error, defaulting to True: {e}")
        return True

async def retrieve_node(state: AgenticRAGState):
    """Retrieve documents from local vector store."""
    query = state["current_search_query"]
    iteration = state.get("iteration_count", 0)
    logger.info(f"Retrieving documents for query: {query}")
    docs = await asyncio.to_thread(local_kb.search_knowledge, query, top_k=5)
    return {"documents": docs, "iteration_count": iteration + 1}

async def grade_documents_node(state: AgenticRAGState):
    """Concurrently evaluate all retrieved documents."""
    docs = state.get("documents", [])
    query = state["original_query"]
    logger.info(f"Evaluating relevance of {len(docs)} documents.")
    
    if not docs:
        return {"documents": []}
        
    results = await asyncio.gather(*[grade_single_doc(doc, query) for doc in docs])
    filtered_docs = [doc for doc, is_relevant in zip(docs, results) if is_relevant]
    logger.info(f"Retained {len(filtered_docs)} relevant documents.")
    
    return {"documents": filtered_docs}

def decide_to_generate_or_rewrite(state: AgenticRAGState) -> str:
    """Route to generate, rewrite, or fallback based on grading results."""
    docs = state.get("documents", [])
    iteration = state.get("iteration_count", 0)
    
    if not docs:
        if iteration >= 3:
            logger.warning("Max retrieval iterations reached. Routing to fallback.")
            return "fallback"
        logger.info("No relevant documents found. Routing to rewrite.")
        return "rewrite"
    
    logger.info("Relevant documents found. Routing to generate.")
    return "generate"

async def rewrite_query_node(state: AgenticRAGState):
    """Rewrite the search query to improve retrieval."""
    query = state["original_query"]
    llm = get_llm()
    prompt = f"The previous search for '{query}' failed to yield relevant results. Rewrite the query to capture the core intent effectively for a vector database search. Output ONLY the new query string."
    
    res = await llm.ainvoke([HumanMessage(content=prompt)])
    new_query = res.content.strip().strip('"').strip("'")
    logger.info(f"Query rewritten to: {new_query}")
    return {"current_search_query": new_query}

async def generate_answer_node(state: AgenticRAGState):
    """Generate final answer using relevant documents and chat history."""
    query = state["original_query"]
    docs = state.get("documents", [])
    context = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}" for doc in docs])
    
    prompt = (
        f"Answer the user's question based strictly on the provided context. "
        f"If the context does not contain sufficient information, state clearly that you cannot answer based on available data. Do not fabricate information.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}"
    )
    
    messages = state.get("chat_history", []) + [HumanMessage(content=prompt)]
    llm = get_llm()
    res = await llm.ainvoke(messages)
    logger.info("Answer generated successfully.")
    return {"final_answer": res.content}

async def fallback_node(state: AgenticRAGState):
    """Fallback handler when no relevant documents are found after max retries."""
    logger.info("Executing fallback strategy.")
    fallback_msg = "After multiple retrieval attempts, I could not find relevant information in the local knowledge base to answer your question accurately."
    return {"final_answer": fallback_msg}

# StateGraph construction
workflow = StateGraph(AgenticRAGState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_documents_node)
workflow.add_node("rewrite", rewrite_query_node)
workflow.add_node("generate", generate_answer_node)
workflow.add_node("fallback", fallback_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "grade")
workflow.add_conditional_edges("grade", decide_to_generate_or_rewrite, {
    "rewrite": "rewrite",
    "generate": "generate",
    "fallback": "fallback"
})
workflow.add_edge("rewrite", "retrieve")
workflow.add_edge("generate", END)
workflow.add_edge("fallback", END)

agentic_rag_graph = workflow.compile()
