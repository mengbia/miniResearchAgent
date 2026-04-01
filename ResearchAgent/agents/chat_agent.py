from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from agents.tools import get_web_search_tool
from rag.local_tools import list_local_files, search_local_content, read_full_document

# 🌟 引入提示词管理器
from core.prompt_manager import prompt_manager

llm = get_llm()

tools = [
    get_web_search_tool(max_results=3), 
    list_local_files, 
    search_local_content, 
    read_full_document
]

# 🌟 动态加载提示词
system_prompt = prompt_manager.get("chat_agent", "system_prompt")

normal_chat_agent = create_react_agent(
    llm,
    tools=tools,
    state_modifier=SystemMessage(content=system_prompt)
)