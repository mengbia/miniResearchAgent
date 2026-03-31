from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from core.llm import get_llm
from rag.local_tools import list_local_files, search_local_content, read_full_document

# 1. 实例化你的大脑 (Qwen3-max)
llm = get_llm()

# 2. 组装工具箱
tools = [list_local_files, search_local_content, read_full_document]

# 3. 设定企业级路由规则（人设）
system_prompt = """你是一个专业的企业级智能助手。
你有三个关于本地知识库的专属工具可用：
1. 若用户询问上传了什么文件，请调用 list_local_files。
2. 若用户询问某个知识点，请调用 search_local_content。
3. 若用户要求总结某个文件，请调用 read_full_document。
如果是普通的日常闲聊，你可以直接友好回答，无需调用工具。
请根据用户的意图，自主决定是否使用工具，以及使用哪个工具。"""

# 4. 创建具备 ReAct (推理与行动) 能力的智能体
normal_chat_agent = create_react_agent(
    llm, 
    tools=tools, 
    prompt=system_prompt
)