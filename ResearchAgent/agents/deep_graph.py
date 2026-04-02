import sys
sys.path.append(".")

import json
import asyncio
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from core.llm import get_llm
from agents.tools import get_web_search_tool
from agents.state import AgentState
from rag.vector_store import local_kb

from core.prompt_manager import prompt_manager

llm = get_llm()
search_tool = get_web_search_tool(max_results=3)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def safe_web_search(keyword: str):
    return await search_tool.ainvoke({"query": keyword})

# ==========================================
# 1. 初始化与规划层 (Init & Planner)
# ==========================================
async def init_system_node(state: AgentState):
    """全局系统起点：注入系统提示词与人设"""
    print("\n[System] 🌟 正在初始化深度研究网络...")
    # 🌟 动态获取
    prompt_text = prompt_manager.get("deep_graph", "init_system")
    sys_msg = SystemMessage(content=prompt_text)
    return {"messages": [sys_msg], "loop_count": 0, "sources": []}

async def planner_node(state: AgentState):
    """规划师：不仅生成关键词，还给任务打上【路由标签】"""
    query = state["user_query"]
    history_context = "\n".join([m.content for m in state.get("messages", []) if isinstance(m, AIMessage)])
    
    # 🌟 动态获取并注入变量
    template = prompt_manager.get("deep_graph", "planner")
    prompt = template.format(query=query, history_context=history_context)

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    keywords = response.content.split(",")
    
    plan_list = []
    for kw in keywords:
        if kw.strip():
            plan_list.append({"title": kw.strip()})
            
    print(f"\n[Planner] 📋 制定了 {len(plan_list)} 条定向检索计划。")
    # 覆盖之前的 plan
    return {"plan": plan_list}

# ==========================================
# 2. 并行路由 (Dynamic Router)
# ==========================================
def route_specialists(state: AgentState):
    """交通警察：决定图谱下一步激活哪些节点。如果返回列表，图谱就会并发执行！"""
    plans = state.get("plan", [])
    routes = set()
    
    for p in plans:
        title = p["title"].upper()
        if "[WEB]" in title: routes.add("web_specialist")
        elif "[LOCAL]" in title: routes.add("local_specialist")
        else: # 默认为 ALL
            routes.add("web_specialist")
            routes.add("local_specialist")
            
    print(f"\n[Router] 🚦 侦测到任务属性，即将并发唤醒特种部队: {list(routes)}")
    # LangGraph 魔法：返回包含多个节点名的列表，就会开启真实的多线程并行！
    return list(routes) 

# ==========================================
# 3. 特种部队节点 (Specialist Agents)
# ==========================================
async def web_specialist_node(state: AgentState):
    """只负责查外网"""
    print("[Web Specialist] 🌐 外网特工出动...")
    plans = state.get("plan", [])
    sources = []
    for p in plans:
        if "[LOCAL]" in p["title"].upper(): continue # 不归我管
        keyword = p["title"].replace("[WEB]", "").replace("[ALL]", "").strip()
        
        try:
            web_results = await safe_web_search(keyword)
            for res in web_results:
                sources.append({
                    "title": f"[全网] {res.get('title', '')}",
                    "url": res.get("url", ""),
                    "snippet": res.get("content", "")[:300]
                })
        except Exception as e:
            print(f"外网检索异常: {e}")
            
    # 由于我们在 state.py 用了 operator.add，这里的 return 会把 sources 追加进去，而不是覆盖！
    return {"sources": sources}

async def local_specialist_node(state: AgentState):
    """只负责查本地向量库"""
    print("[Local Specialist] 📁 内网特工出动...")
    plans = state.get("plan", [])
    sources = []
    for p in plans:
        if "[WEB]" in p["title"].upper(): continue
        keyword = p["title"].replace("[LOCAL]", "").replace("[ALL]", "").strip()
        
        try:
            local_results = await asyncio.to_thread(local_kb.search_knowledge, keyword, top_k=2)
            for doc in local_results:
                source_name = doc.metadata.get("source", "未知").split("/")[-1]
                sources.append({
                    "title": f"[内部库] {source_name}",
                    "url": f"本地文件://{source_name}",
                    "snippet": doc.page_content[:300]
                })
        except Exception as e:
            print(f"内网检索异常: {e}")
            
    return {"sources": sources}

# ==========================================
# 4. 汇聚与生成层 (Merge & Write)
# ==========================================
async def filter_node(state: AgentState):
    """情报局长：等所有特工回来后，对情报进行去重和质检"""
    raw_sources = state.get("sources", [])
    print(f"\n[Filter] 🕵️ 收到 {len(raw_sources)} 份原始情报，准备执行强制清洗...")
    
    # 1. 模拟数据清洗逻辑 (例如：剔除内容太少的废渣数据)
    filtered_sources = [s for s in raw_sources if len(s.get("snippet", "")) > 10]
    
    # 如果你想做更复杂的 LLM 过滤，也可以在这里写
    
    print(f"[Filter] ✨ 清洗完毕，保留 {len(filtered_sources)} 条有效数据。")
    
    # 🌟 核心破局点：使用特殊的字典格式，触发 Reducer 的【强制覆盖模式】
    # 这样就能彻底斩断 operator.add 造成的无限膨胀死循环！
    return {"sources": {"action": "overwrite", "data": filtered_sources}}

async def writer_node(state: AgentState):
    """撰稿人"""
    query = state["user_query"]
    sources = state.get("sources", [])[-10:]
    context = "\n".join([f"- [{s['title']}]({s['url']}): {s['snippet']}" for s in sources])
    
    # 🌟 动态获取并注入变量
    template = prompt_manager.get("deep_graph", "writer")
    prompt = template.format(query=query, context=context)
    
    print("\n[Writer] ✍️ 正在奋笔疾书...")
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    return {"report": response.content}

# ==========================================
# 5. 审查与闭环 (Review & Loop)
# ==========================================
async def reviewer_node(state: AgentState):
    """审查员"""
    loop_count = state.get("loop_count", 0)
    if loop_count >= 2: return {"loop_count": loop_count + 1}
        
    print(f"\n[Reviewer] 🧐 严厉审查第 {loop_count + 1} 版报告...")
    report = state.get("report", "")
    
    # 🌟 动态获取并注入变量
    template = prompt_manager.get("deep_graph", "reviewer")
    prompt = template.format(report=report[:2000])
    
    response = await llm.ainvoke([SystemMessage(content=prompt)])
    
    if "FAIL" in response.content.upper():
        print("[Reviewer] ❌ 发现信息断层，打回重做！")
        return {
            "loop_count": loop_count + 1,
            "messages": [AIMessage(content=f"打回理由：{response.content}")] # 追加消息
        }
    print("[Reviewer] ✅ 审查通过！")
    return {"loop_count": loop_count + 1}

def review_router(state: AgentState) -> str:
    loop_count = state.get("loop_count", 0)
    last_msg = state.get("messages", [])[-1].content if state.get("messages") else ""
    if "打回理由" in last_msg and loop_count <= 2:
        return "planner"
    return "end"

# ==========================================
# 🌟 构建网状拓扑图 (The Graph Topology)
# ==========================================
workflow = StateGraph(AgentState)

# 注册所有节点
workflow.add_node("init", init_system_node)
workflow.add_node("planner", planner_node)
workflow.add_node("web_specialist", web_specialist_node)
workflow.add_node("local_specialist", local_specialist_node)
workflow.add_node("filter", filter_node)
workflow.add_node("writer", writer_node)
workflow.add_node("reviewer", reviewer_node)

# 连线：起跑线
workflow.add_edge(START, "init")
workflow.add_edge("init", "planner")

# 连线：动态并行分发 (Planner 查完后，由 Router 决定走哪条路，或者两条路同时走)
workflow.add_conditional_edges("planner", route_specialists, ["web_specialist", "local_specialist"])

# 连线：海纳百川 (所有特工无论谁先跑完，最终都在 Filter 处汇聚)
workflow.add_edge("web_specialist", "filter")
workflow.add_edge("local_specialist", "filter")

# 连线：后半段直线流程
workflow.add_edge("filter", "writer")
workflow.add_edge("writer", "reviewer")

# 连线：审查员的“回头草”条件分支
workflow.add_conditional_edges("reviewer", review_router, {"planner": "planner", "end": END})


import os

# 在根目录创建一个独立的 SQLite 数据库文件来保存所有任务的状态
if not os.path.exists("checkpoints"):
    os.makedirs("checkpoints")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "checkpoints", "research_checkpoints.db")

# 编译时注入 checkpointer！从现在起，图谱走的每一步都会实时自动落盘。
deep_research_graph = workflow.compile()



# ========== 底部测试代码 ==========
if __name__ == "__main__":
    import asyncio
    import sys
    import uuid # 引入 UUID

    async def main():
        print("🚀 正在独立测试多智能体 LangGraph 网络(带容灾持久化)...")
        
        test_state = {
            "user_query": "2026年固态电池的最新商业化进展", 
            "messages": [], "plan": [], "sources": [], "report": "", "loop_count": 0
        }
        
        # 🌟 核心：使用 checkpointer 后，必须传入 thread_id！
        # 这样系统才知道当前是在跑哪个任务，重启后只要 thread_id 相同就能无缝接上
        test_thread_id = str(uuid.uuid4())
        run_config = {"configurable": {"thread_id": test_thread_id}}
        
        result = await deep_research_graph.ainvoke(test_state, config=run_config)
        
        print("\n" + "="*50)
        print("🏁 测试运行结束！")
        print("="*50)
        print(f"📋 最终生成的计划: {[p.get('title', '') for p in result.get('plan', [])]}")
        print(f"📚 汇聚并清洗后的资料数: {len(result.get('sources', []))} 条")
        print(f"🔄 深度审查循环次数: {result.get('loop_count', 0)} 次")
        print("-" * 50)
        print("✅ 最终深度报告:\n")
        print(result.get("report", "无报告生成"))

    # 解决 Windows 系统下 Asyncio 可能会报错的问题
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())