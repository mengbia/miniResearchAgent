import os
from dotenv import load_dotenv

load_dotenv()

# Primary LLM configuration
LLM_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_API_BASE = os.getenv("OPENAI_API_BASE")
LLM_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
LLM_MODEL_EMBEDDING = os.getenv("OPENAI_MODEL_EMBEDDING")

# Backup LLM configuration
BACKUP_API_KEY = os.getenv("BACKUP_API_KEY")
BACKUP_API_BASE = os.getenv("BACKUP_API_BASE")
BACKUP_MODEL_NAME = os.getenv("BACKUP_MODEL_NAME")
BACKUP_MODEL_EMBEDDING = os.getenv("BACKUP_MODEL_EMBEDDING")
BACKUP_DASHSCOPE_API_KEY = os.getenv("BACKUP_DASHSCOPE_MODEL_EMBEDDING")

# Tavily search configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not LLM_API_KEY or not TAVILY_API_KEY:
    print("Warning: API keys not found in .env file.")
