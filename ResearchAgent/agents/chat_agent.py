from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent

from core.llm import get_llm
from agents.tools import get_web_search_tool
from rag.local_tools import list_local_files, search_local_content, read_full_document

# 1. 初始化大模型
llm = get_llm()

# 2. 组装全能工具箱 (把外网搜索和本地私有库工具全塞进去)
# 注意：get_web_search_tool() 需要实例化调用
tools = [
    get_web_search_tool(max_results=3), 
    list_local_files, 
    search_local_content, 
    read_full_document
]

# 3. 设定“全能聊天助手”的灵魂 (System Prompt)
# 这里的准则极其重要，它决定了大模型何时聊天，何时动用工具
system_prompt = """你是一个全能型的高级智能助手，就像用户日常交流的伙伴。
你配备了强大的工具箱，可以随时查阅全网最新资讯和用户的本地私有文档。

【核心准则】：
1. 实事求是，绝不捏造事实（严禁AI幻觉）。对于你不确定的客观知识，必须调用工具查询，查不到就坦白承认不懂，不要乱回答。
2. 灵活判断：如果是日常打招呼或闲聊（如“你好”、“你是谁”），直接自然回复，无需调用工具。
3. 外网优先：当用户询问最新新闻、技术进展、天气或常识时，主动调用外网搜索工具。
4. 本地优先：当用户明确提到“本地文件”、“我的资料”、“刚上传的文档”，或者问及一些明显属于私有背景的问题时，主动调用本地知识库工具。

请保持对话的自然、友好和专业。"""

# 4. 使用 LangGraph 预置的 ReAct 架构，一键生成拥有无限循环对话能力的 Agent
normal_chat_agent = create_react_agent(
    llm,
    tools=tools,
    state_modifier=SystemMessage(content=system_prompt)
)