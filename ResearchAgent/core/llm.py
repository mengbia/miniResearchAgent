import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from core.config import (LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME, LLM_MODEL_EMBEDDING,
                    BACKUP_API_KEY, BACKUP_API_BASE, BACKUP_MODEL_NAME, BACKUP_MODEL_EMBEDDING)

from langchain_core.embeddings import Embeddings

load_dotenv()

def get_llm():
    """
    Initialize the global large language model with high availability support.
    Falls back to a backup model if the primary model fails or is rate-limited.
    """
    main_llm = ChatOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        model=LLM_MODEL_NAME, 
        temperature=0.7,
        max_retries=1,      # Quick fallback to minimize latency
        request_timeout=30  # Timeout to prevent hanging API requests
    )

    backup_api_key = BACKUP_API_KEY
    backup_api_base = BACKUP_API_BASE
    backup_model_name = BACKUP_MODEL_NAME

    if backup_api_key and backup_api_base:
        backup_llm = ChatOpenAI(
            api_key=backup_api_key,
            base_url=backup_api_base,
            model=backup_model_name,
            temperature=0.7, 
            max_retries=3,  # Higher retry count for backup model
            request_timeout=30
        )
        
        fallback_llm = main_llm.with_fallbacks(
            [backup_llm],
            exceptions_to_handle=(Exception, BaseException)
        )
        
        return fallback_llm
    else:
        print("\n[System Warning] No valid BACKUP_API_KEY detected. High availability mechanism disabled.\n")

    return main_llm

class FallbackEmbeddings(Embeddings):
    """
    Custom wrapper for embeddings to handle failures by switching to a backup provider.
    """
    def __init__(self):
        self.main_emb = OpenAIEmbeddings(
            api_key=LLM_API_KEY,
            base_url=LLM_API_BASE,
            model=LLM_MODEL_EMBEDDING,
            check_embedding_ctx_length=False
        )
        
        backup_api_key = BACKUP_API_KEY
        backup_api_base = BACKUP_API_BASE
        self.backup_emb = None
        
        if backup_api_key and backup_api_base:
            self.backup_emb = OpenAIEmbeddings(
                api_key=backup_api_key,
                base_url=backup_api_base,
                # Ensure main and backup models are compatible to avoid dimension mismatch
                model=BACKUP_MODEL_EMBEDDING,
                check_embedding_ctx_length=False
            )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.main_emb.embed_documents(texts)
        except Exception as e:
            if self.backup_emb:
                print(f"[Fallback] Main embedding node exception ({e}), switching to backup node.")
                return self.backup_emb.embed_documents(texts)
            raise e

    def embed_query(self, text: str) -> list[float]:
        try:
            return self.main_emb.embed_query(text)
        except Exception as e:
            if self.backup_emb:
                print(f"[Fallback] Main embedding node exception ({e}), switching to backup node.")
                return self.backup_emb.embed_query(text)
            raise e

def get_embeddings():
    """Get the global high-availability embedding model."""
    return FallbackEmbeddings()


if __name__ == "__main__":
    llm = get_llm()
    print("Testing large language model...")
    response = llm.invoke("Describe the sky in one sentence.")
    print("Model response:", response.content)
