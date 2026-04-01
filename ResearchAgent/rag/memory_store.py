import os
import uuid
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from core.config import LLM_API_KEY
from langchain_core.messages import SystemMessage
from core.llm import get_llm
from core.prompt_manager import prompt_manager

# 🌟 为记忆库分配一个独立的持久化目录或 Collection
MEMORY_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data", "user_memory")

class UserMemoryStore:
    def __init__(self):
        # 初始化 Embedding 模型 (vector_store.py 里的一样)
        self.embeddings = DashScopeEmbeddings(
            model="text-embedding-v2",
            dashscope_api_key=LLM_API_KEY
        )
        # 创建一个专属的 Collection: "long_term_memory"
        self.vector_store = Chroma(
            collection_name="long_term_memory",
            embedding_function=self.embeddings,
            persist_directory=MEMORY_PERSIST_DIR
        )
        self.llm = get_llm()

    async def async_extract_and_save(self, user_input: str):
        """异步执行：分析用户输入，如果是重要偏好，则存入 Chroma"""
        # 1. 加载提取器提示词
        template = prompt_manager.get("memory", "extractor")
        prompt = template.format(user_input=user_input)
        
        try:
            # 2. 让大模型判断这句话值不值得记下来
            response = await self.llm.ainvoke([SystemMessage(content=prompt)])
            memory_fact = response.content.strip()
            
            # 3. 如果大模型判定是有用事实，则向量化入库
            if memory_fact and memory_fact.lower() != "none":
                print(f"🧠 [长期记忆捕获]: {memory_fact}")
                # 生成唯一 ID 防止重复
                doc_id = str(uuid.uuid4())
                self.vector_store.add_texts(
                    texts=[memory_fact], 
                    ids=[doc_id],
                    metadatas=[{"source": "user_chat"}]
                )
        except Exception as e:
            print(f"❌ 记忆提取失败: {e}")

    def retrieve_memory(self, query: str, top_k: int = 3) -> str:
        """提问前执行：根据当前问题，去向量库捞取相关的长期记忆"""
        try:
            results = self.vector_store.similarity_search(query, k=top_k)
            if not results:
                return "暂无相关历史记忆。"
            
            memories = [doc.page_content for doc in results]
            return "\n".join([f"- {m}" for m in memories])
        except Exception as e:
            print(f"❌ 记忆检索失败: {e}")
            return "记忆检索异常。"

# 全局单例
user_memory = UserMemoryStore()