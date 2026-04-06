import sys
sys.path.append(".")

import os
import hashlib
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 为阿里云官方嵌入模型
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_chroma import Chroma
from core.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME, BACKUP_LLM_MODEL_EMBEDDING

# 知识库保存在本地的路径
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")

class LocalVectorStore:
    def __init__(self):
        # 1. 初始化【阿里云通义千问专属】词向量模型
        self.embeddings = DashScopeEmbeddings(
            model=BACKUP_LLM_MODEL_EMBEDDING,
            dashscope_api_key=LLM_API_KEY
        )
        
        # 2. 连接或创建 ChromaDB 向量数据库
        self.vector_store = Chroma(
            collection_name="deep_research_kb",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        # 3. 初始化文本切片机
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )

    # 🌟 计算文件内容的 MD5 值
    def _calculate_file_md5(self, file_path: str) -> str:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            # 分块读取，防止超大文件把内存撑爆
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process_and_save_document(self, file_path: str):
        """核心功能：识别文件 -> 计算MD5查重 -> 读取 -> 切片 -> 分配唯一ID存入数据库"""
        ext = os.path.splitext(file_path)[-1].lower()
        print(f"📁 正在处理文件: {file_path}")
        
        # 🌟 1. 计算全文 MD5
        file_md5 = self._calculate_file_md5(file_path)
        print(f"   [MD5指纹]: {file_md5}")

        # 🌟 2. 利用 MD5 进行去重校验 (检查数据库里是否已经有这个文件的切片了)
        # Chroma 允许我们通过 where 过滤 metadata 来查询
        existing_docs = self.vector_store.get(where={"file_md5": file_md5})
        if existing_docs and len(existing_docs["ids"]) > 0:
            print("   ⏩ 检测到文件内容完全一致，已跳过向量化，直接秒传！")
            return True

        # 3. 文件解析 (这里保持原来的 Loader 逻辑)
        if ext == ".pdf": loader = PyPDFLoader(file_path)
        elif ext == ".txt": loader = TextLoader(file_path, encoding='utf-8')
        elif ext == ".docx": loader = Docx2txtLoader(file_path)
        elif ext == ".md": loader = UnstructuredMarkdownLoader(file_path)
        else: raise ValueError(f"不支持的文件格式: {ext}")

        docs = loader.load()
        split_docs = self.text_splitter.split_documents(docs)
        print(f"✂️ 文件已被切分为 {len(split_docs)} 个片段。")

        # 🌟 4. 为每个切片打上 MD5 烙印，并生成全局唯一 ID
        chunk_ids = []
        for i, doc in enumerate(split_docs):
            # 将 MD5 存入元数据，方便以后查重或精准删除
            doc.metadata["file_md5"] = file_md5
            # 生成形如 "d41d8cd98f00b204e9800998ecf8427e_chunk_0" 的绝对唯一 ID
            chunk_ids.append(f"{file_md5}_chunk_{i}")

        # 🌟 5. 带 ID 入库 (如果 ID 重复，Chroma 会自动更新而不是新增，杜绝冗余)
        self.vector_store.add_documents(documents=split_docs, ids=chunk_ids)
        print("✅ 成功存入向量数据库！")
        return True

    def search_knowledge(self, query: str, top_k: int = 3):
        """核心功能：从数据库中检索最相关的片段"""
        print(f"🔍 正在本地知识库检索: {query}")
        results = self.vector_store.similarity_search(query, k=top_k)
        return results
    
    '''
    
    '''
    # def get_all_filenames(self):
    #     """ 获取当前数据库里所有的文件名清单"""
    #     try:
    #         results = self.vector_store.get()
    #         metadatas = results.get("metadatas", [])
    #         filenames = set()
    #         for meta in metadatas:
    #             if meta and "source" in meta:
    #                 # 兼容 Windows 和 Linux 的路径斜杠
    #                 name = meta["source"].replace("\\", "/").split("/")[-1]
    #                 filenames.add(name)
    #         return list(filenames)
    #     except Exception as e:
    #         print(f"获取文件名失败: {e}")
    #         return []

    # def get_full_document_by_keyword(self, keyword: str, max_chars: int = 6000):
    #     """绕过向量检索，直接按文件名关键词把内容硬拽出来！"""
    #     try:
    #         results = self.vector_store.get()
    #         metadatas = results.get("metadatas", [])
    #         documents = results.get("documents", [])
            
    #         content = ""
    #         for i, meta in enumerate(metadatas):
    #             if meta and "source" in meta:
    #                 name = meta["source"].replace("\\", "/").split("/")[-1]
    #                 # 如果文件名包含这个关键词，就把切片内容无脑拼起来
    #                 if keyword.lower() in name.lower():
    #                     content += documents[i] + "\n"
    #                     # 防止文件太大把大模型撑爆，截断一下
    #                     if len(content) > max_chars:
    #                         break
    #         return content[:max_chars]
    #     except Exception as e:
    #         print(f"强制提取文件失败: {e}")
    #         return ""

# 实例化一个单例供全局使用
local_kb = LocalVectorStore()

#=========测试向量存储============
if __name__ == "__main__":
    test_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "test.txt")
    
    if os.path.exists(test_file):
        local_kb.process_and_save_document(test_file)
    else:
        print("找不到测试文件，请在 uploads 文件夹下随便建一个文件。")
        
    print("\n--- 开始检索测试 ---")
    query = "总结一下文章的内容"
    docs = local_kb.search_knowledge(query)
    
    for i, doc in enumerate(docs):
        print(f"\n片段 {i+1}:\n{doc.page_content[:150]}...")