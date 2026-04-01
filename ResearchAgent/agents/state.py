from typing import TypedDict, List, Dict, Any, Annotated, Union
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
import operator

'''
在 LangGraph 中，如果让两个节点（外网特工和内网特工）同时并行运行，它们会抢夺并覆盖同一个 sources 列表。
为了让它们查到的资料能合并在一起，我们必须使用 Python 的 operator.add
'''


# ==========================================
# 🌟 状态合并器 (Custom Reducer)
# =========================================
def reduce_sources(left: List[Dict[str, str]], right: Union[List[Dict[str, str]], Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    智能合并器：解决并发追加与强制清洗的冲突。
    - left: 图谱中原本就有的历史数据
    - right: 当前节点刚计算完，准备塞进图谱的新数据
    """
    if left is None: left = []
    
    # 💥 模式 A：强制覆盖模式 (用于 Filter 节点)
    # 侦测到特殊指令，直接丢弃老数据，用新数据覆盖
    if isinstance(right, dict) and right.get("action") == "overwrite":
        return right.get("data", [])
        
    # 🤝 模式 B：并发合并模式 (用于 Worker 节点)
    if not isinstance(right, list): right = []
    
    # 使用字典按 URL 去重合并
    merged = {}
    for s in left:
        merged[s.get("url", "")] = s
    for s in right:
        merged[s.get("url", "")] = s
        
    return list(merged.values())

# ==========================================
# 图谱全局状态字典
# ==========================================
class AgentState(TypedDict):
    user_query: str
    messages: Annotated[List[Any], operator.add]
    plan: List[Dict[str, str]]
    # 🌟 将 operator.add 替换为我们自己写的 reduce_sources
    sources: Annotated[List[Dict[str, str]], reduce_sources]
    report: str
    loop_count: int