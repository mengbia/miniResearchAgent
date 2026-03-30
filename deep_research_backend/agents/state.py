from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

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
# 这个 State 会在 Planner -> Worker -> Writer 之间不断传递和累加

class AgentState(TypedDict):
    # 1. 聊天记录 (Annotated + add_messages 表示新消息会追加到列表末尾，而不是覆盖)
    messages: Annotated[list[AnyMessage], add_messages]
    
    # 2. 用户当前要研究的核心问题
    user_query: str
    
    # 3. 规划师 (Planner) 拆解出来的研究计划列表
    plan: List[PlanItem]
    
    # 4. 研究员 (Worker) 从全网搜集回来的网页资料
    sources: List[Source]
    
    # 5. 撰稿人 (Writer) 最终写出的长篇报告
    report: str
    
    # 6. 当前执行到了计划的哪一步（用于 Worker 循环时的指针）
    current_step_index: int