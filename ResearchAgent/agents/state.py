from typing import TypedDict, List, Dict, Any, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
import operator

'''
在 LangGraph 中，如果让两个节点（外网特工和内网特工）同时并行运行，它们会抢夺并覆盖同一个 sources 列表。
为了让它们查到的资料能合并在一起，我们必须使用 Python 的 operator.add
'''


# --- 定义基础数据结构（必须和前端的结构对应上） ---

class PlanItem(TypedDict):
    id: str
    title: str
    status: str # 状态：pending（待处理）, generating（研究中）, completed（已完成）

class Source(TypedDict):
    id: str
    url: str
    title: str
    snippet: str

# --- 定义核心档案袋（AgentState） ---
class AgentState(TypedDict):
    user_query: str
    # 🌟 核心：使用 Annotated 和 operator.add，实现状态合并
    # 当多个并行节点同时往这里塞数据时，LangGraph 会自动把它们加在一起，而不是互相覆盖！
    messages: Annotated[List[Any], operator.add]
    plan: List[Dict[str, str]]
    sources: Annotated[List[Dict[str, str]], operator.add]
    report: str
    loop_count: int