import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from core.config import (LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME, LLM_MODEL_EMBEDDING,
                    BACKUP_API_KEY, BACKUP_API_BASE, BACKUP_MODEL_NAME, BACKUP_MODEL_EMBEDDING)

from langchain_core.embeddings import Embeddings
# 加载环境变量
load_dotenv()

def get_llm():
    """
    获取全局大语言模型。
    自带高可用机制：当主模型崩溃或限流时，无缝切换至备用模型。
    """
    # 1. 实例化主模型
    main_llm = ChatOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        model=LLM_MODEL_NAME, 
        temperature=0.7,
        max_retries=1,      # 主模型最多重试 1 次，不行就赶紧切备胎，避免用户等太久
        request_timeout=30  # 设置合理的超时时间，防止 API 死锁
    )

    # 2. 读取备用模型配置
    backup_api_key = BACKUP_API_KEY
    backup_api_base = BACKUP_API_BASE
    backup_model_name = BACKUP_MODEL_NAME

    # 3. 组装高可用大模型底座
    if backup_api_key and backup_api_base:
        backup_llm = ChatOpenAI(
            api_key=backup_api_key,
            base_url=backup_api_base,
            model=backup_model_name,
            temperature=0.7, # 调节大模型生成答案是更具创造性还是更保守，数值越低越保守
            max_retries=3, # 备用模型可以多重试几次
            request_timeout=30
        )
        
        # 🌟 把备用模型绑定到主模型上
        # 一旦 main_llm 报错（如 500 服务器错误、429 并发超限、超时），
        # LangChain 会立刻静默启动 backup_llm 接管任务。
        fallback_llm = main_llm.with_fallbacks(
            [backup_llm],
            exceptions_to_handle=(Exception, BaseException)
        )
        
        return fallback_llm
    else:
        # 🌟 增加自检提醒：如果没读到备用 Key，在控制台大声警告！
        print("\n⚠️ [系统警告] 未检测到有效的 BACKUP_API_KEY，大模型高可用容灾机制未启动！\n")

    # 如果没配备用密钥，就直接返回主模型
    return main_llm

# ==========================================
# 🌟 词向量高可用容灾器 (Custom Fallback Embeddings)
# ==========================================
class FallbackEmbeddings(Embeddings):
    """
    自定义的词向量高可用包装器。
    当主节点崩溃、限流或欠费时，静默拦截报错，并无缝使用备用节点重新计算向量。
    """
    def __init__(self):
        # 1. 实例化主节点词向量
        self.main_emb = OpenAIEmbeddings(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE,
            model=LLM_MODEL_EMBEDDING
        )
        
        # 2. 检查并实例化备用节点词向量
        backup_api_key = BACKUP_API_KEY
        backup_api_base = BACKUP_API_BASE
        self.backup_emb = None
        
        if backup_api_key and backup_api_base:
            self.backup_emb = OpenAIEmbeddings(
                api_key=backup_api_key,
                base_url=backup_api_base,
                # ⚠️ 注意：这里必须保证主备使用的是同款模型，否则向量维度不匹配会导致 ChromaDB 崩溃！
                model=BACKUP_MODEL_EMBEDDING
            )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.main_emb.embed_documents(texts)
        except Exception as e:
            if self.backup_emb:
                print(f"⚠️ [容灾] 主 Embedding 节点异常 ({e})，立刻切换备用节点！")
                return self.backup_emb.embed_documents(texts)
            raise e

    def embed_query(self, text: str) -> list[float]:
        try:
            return self.main_emb.embed_query(text)
        except Exception as e:
            if self.backup_emb:
                print(f"⚠️ [容灾] 主 Embedding 节点异常 ({e})，立刻切换备用节点！")
                return self.backup_emb.embed_query(text)
            raise e

def get_embeddings():
    """获取全局高可用词向量模型"""
    return FallbackEmbeddings()


#===============测试大模型是否连通===============
if __name__ == "__main__":
    llm = get_llm()
    print("正在测试大模型...")
    response = llm.invoke("用一句话形容一下天空。")
    print("大模型回复:", response.content)