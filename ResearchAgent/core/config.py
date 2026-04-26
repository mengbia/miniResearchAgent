import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 获取大模型配置
LLM_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_API_BASE = os.getenv("OPENAI_API_BASE")
LLM_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME")
LLM_MODEL_EMBEDDING = os.getenv("OPENAI_MODEL_EMBEDDING")

# 备用大模型
BACKUP_API_KEY = os.getenv("BACKUP_API_KEY")
BACKUP_API_BASE = os.getenv("BACKUP_API_BASE")
BACKUP_MODEL_NAME = os.getenv("BACKUP_MODEL_NAME")
BACKUP_MODEL_EMBEDDING = os.getenv("BACKUP_MODEL_EMBEDDING")
BACKUP_DASHSCOPE_API_KEY = os.getenv("BACKUP_DASHSCOPE_MODEL_EMBEDDING")

# 获取 Tavily 搜索配置
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not LLM_API_KEY or not TAVILY_API_KEY:
    print("⚠️ 警告: 请检查 .env 文件，API Key 未正确加载！")