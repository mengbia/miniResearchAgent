import logging
import os
from datetime import datetime

# Ensure log directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Generate standard log filename (e.g., 2026-03-31_15-30-00_agent.log)
log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_agent.log")
log_filepath = os.path.join(LOG_DIR, log_filename)

# Configure global logger
logger = logging.getLogger("DeepResearchTracker")
logger.setLevel(logging.DEBUG)

# File handler configuration with UTF-8 encoding
file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# Standardized log format
formatter = logging.Formatter('%(asctime)s | [%(levelname)s] | %(name)s | %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def trace_agent_event(event: dict):
    """
    Parses LangGraph low-level events and writes them to the log.
    Decouples event processing from logging implementation.
    """
    kind = event.get("event")
    name = event.get("name", "unknown")
    
    if kind == "on_chat_model_start":
        logger.info(f"[Model Start] Node: {name}")
        
    elif kind == "on_tool_start":
        inputs = event.get("data", {}).get("input")
        logger.info(f"[Tool Start] Tool: {name} | Parameters: {inputs}")
        
    elif kind == "on_tool_end":
        output = event.get("data", {}).get("output")
        # Truncate long output to manage log file size
        safe_output = str(output)[:300] + "..." if len(str(output)) > 300 else str(output)
        logger.info(f"[Tool End] Tool: {name} | Result: {safe_output}")
        
    elif kind == "on_chain_error" or kind == "on_tool_error":
        error = event.get("data", {}).get("error")
        logger.error(f"[System Error] Node: {name} | Details: {error}")

def log_user_interaction(role: str, content: str):
    """Logs interactions between the user and the AI."""
    logger.info(f"[{role.upper()}]: {content}")
