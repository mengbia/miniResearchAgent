import logging
import os
from datetime import datetime

# 1. 确保日志文件夹存在
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 2. 生成标准日志文件名 (例如: 2026-03-31_15-30-00_agent.log)
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_agent.log")
log_filepath = os.path.join(LOG_DIR, log_filename)

# 3. 配置全局 Logger
logger = logging.getLogger("DeepResearchTracker")
logger.setLevel(logging.DEBUG) # 记录所有级别的细节

# 配置文件处理器 (输出到文件，保存为 utf-8)
file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# 定义企业级标准日志格式
formatter = logging.Formatter('%(asctime)s | [%(levelname)s] | %(name)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def trace_agent_event(event: dict):
    """
    解耦的事件追踪器：专门负责解析 LangGraph 的底层事件并写入日志。
    业务代码只需要把 event 扔进来，不用管怎么存。
    """
    kind = event.get("event")
    name = event.get("name", "unknown")
    
    if kind == "on_chat_model_start":
        logger.info(f"🧠 [大模型被唤醒] 节点: {name}")
        
    elif kind == "on_tool_start":
        inputs = event.get("data", {}).get("input")
        logger.info(f"🛠️ [工具调用开始] 工具名: {name} | 参数: {inputs}")
        
    elif kind == "on_tool_end":
        output = event.get("data", {}).get("output")
        # 截断太长的输出以防日志文件过大
        safe_output = str(output)[:300] + "..." if len(str(output)) > 300 else str(output)
        logger.info(f"✅ [工具调用结束] 工具名: {name} | 结果: {safe_output}")
        
    elif kind == "on_chain_error" or kind == "on_tool_error":
        error = event.get("data", {}).get("error")
        logger.error(f"❌ [系统报错] 节点: {name} | 错误详情: {error}")

def log_user_interaction(role: str, content: str):
    """记录人类与AI的交互记录"""
    logger.info(f"💬 [{role.upper()}]: {content}")
