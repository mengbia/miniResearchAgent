import json
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import get_llm
from agents.tools import get_web_search_tool
from agents.state import AgentState
from rag.vector_store import local_kb

llm = get_llm()
search_tool = get_web_search_tool(max_results=3)

# 🌟 变化 1：函数前面加上了 async
async def planner_node(state: AgentState):
    query = state["user_query"]
    prompt = f"你是一个资深研究员。用户想研究：{query}。请给出最多3个相关的搜索关键词，以逗号分隔，不要说多余的废话。"
    
    # 🌟 变化 2：invoke 变成了 ainvoke (异步调用)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    keywords = response.content.split(",")
    
    plan_list = []
    for i, kw in enumerate(keywords):
        if kw.strip():
            plan_list.append({"id": str(i), "title": f"搜索: {kw.strip()}", "status": "pending"})
            
    return {"plan": plan_list}

async def worker_node(state: AgentState):
    """负责根据规划师的关键词，同时进行【外网搜索】和【本地检索】"""
    plans = state.get("plan", [])
    all_sources = []
    
    for p in plans:
        keyword = p["title"].replace("搜索: ", "")
        print(f"\n[Worker] 正在执行双擎检索: {keyword}")
        
        # ==========================================
        # 引擎 A：查外网 (Tavily)
        # ==========================================
        try:
            web_results = await search_tool.ainvoke({"query": keyword})
            for res in web_results:
                all_sources.append({
                    "id": res.get("url", ""),
                    "url": res.get("url", ""),
                    "title": f"[全网] {res.get('title', '网页来源')}",
                    "snippet": res.get("content", "")[:300]
                })
        except Exception as e:
            print(f"外网搜索出错: {e}")

        # ==========================================
        # 引擎 B：查内网 (本地 ChromaDB)
        # ==========================================
        try:
            local_results = local_kb.search_knowledge(keyword, top_k=2) # 每次取最相关的2段本地文本
            for i, doc in enumerate(local_results):
                # 从文档的 metadata 中获取原文件名，如果没有就写“本地知识库”
                source_name = doc.metadata.get("source", "本地知识库").split("\\")[-1].split("/")[-1]
                
                all_sources.append({
                    "id": f"local_{keyword}_{i}",
                    "url": f"本地文件://{source_name}", # 给前端展示用的伪装URL
                    "title": f"[内部私有库] {source_name}",
                    "snippet": doc.page_content[:300]
                })
        except Exception as e:
            print(f"本地检索出错: {e}")
            
    return {"sources": all_sources}

async def writer_node(state: AgentState):
    query = state["user_query"]
    sources = state.get("sources", [])
    
    context = "\n".join([f"- [{s['title']}]({s['url']}): {s['snippet']}" for s in sources])
    
    prompt = f"""你是一个专业报告撰写专家。
用户原始问题：{query}
以下是研究员刚从全网搜集到的最新参考资料：
{context}

请根据以上资料，写一份详细的 Markdown 深度研究报告。
要求：逻辑清晰，分点阐述；必须结合参考资料里的具体信息，可以在文中多用加粗和列表。
"""
    print("\n[Writer] 正在撰写深度报告并实时流式输出...")
    # 🌟 变化 4：异步调用大模型写报告
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return {"report": response.content}

# 组装图神经网络
workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("worker", worker_node)
workflow.add_node("writer", writer_node)

workflow.add_edge(START, "planner")
workflow.add_edge("planner", "worker")
workflow.add_edge("worker", "writer")
workflow.add_edge("writer", END)

deep_research_graph = workflow.compile()

# ========== 底部测试代码 ==========
if __name__ == "__main__":
    print("🚀 正在独立测试 LangGraph 智能体网络...")
    
    # 模拟用户提问
    test_state = {"user_query": "2026年固态电池的最新商业化进展", "messages": []}
    
    # 运行整个图网络
    result = deep_research_graph.invoke(test_state)
    
    print("\n" + "="*40)
    print("生成的计划:", result.get("plan"))
    print("搜到的资料数:", len(result.get("sources", [])))
    print("最终报告:\n", result.get("report"))