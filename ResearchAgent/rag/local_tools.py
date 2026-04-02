import os
from langchain_core.tools import tool
from rag.vector_store import local_kb
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredMarkdownLoader

# 🌟 将 uploads 文件夹作为我们的轻量级 "OSS/S3" 和 "MySQL"
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

@tool
def list_local_files() -> str:
    """获取当前本地知识库中已上传的所有文件列表（文件名）。当用户问“有什么文件”、“上传了哪些文件”时调用此工具。"""
    # 🌟 直接读取操作系统目录，O(1) 复杂度，告别 Chroma 全表扫描！
    if not os.path.exists(UPLOAD_DIR):
        return "当前本地知识库没有任何文件。"
        
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return "当前本地知识库没有任何文件。"
    return "当前已上传的文件有：" + "、".join(files)

@tool
def search_local_content(query: str) -> str:
    """在本地知识库中进行语义片段检索。当用户询问具体知识点、概念、或普通问题时调用此工具。"""
    # 语义检索（Similarity Search），在向量数据库检索
    results = local_kb.search_knowledge(query, top_k=5)
    if not results:
        return "本地知识库中没有找到相关内容。"
    context = ""
    for doc in results:
        source = doc.metadata.get("source", "未知").replace("\\", "/").split("/")[-1]
        context += f"-[{source}]: {doc.page_content[:400]}\n"
    return context

@tool
def read_full_document(filename: str) -> str:
    """读取指定文件的完整内容。当且仅当用户明确要求“总结某个文件”或指名道姓要看某个文件全貌时调用。"""
    # 🌟 绕过 Chroma 数据库，直接从磁盘读取原文件！
    if not os.path.exists(UPLOAD_DIR):
        return "本地无任何文件。"
        
    files = os.listdir(UPLOAD_DIR)
    # 模糊匹配文件名
    matched_file = next((f for f in files if filename.lower() in f.lower()), None)
    
    if not matched_file:
        return f"未能找到包含 '{filename}' 的文件。"
        
    file_path = os.path.join(UPLOAD_DIR, matched_file)
    ext = os.path.splitext(file_path)[-1].lower()
    
    try:
        # 使用对应的解析器直接硬读原文件
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding='utf-8')
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
        else:
            return f"不支持直接读取全文的格式: {ext}"
            
        docs = loader.load()
        content = "\n".join([doc.page_content for doc in docs])
        
        # 依然做一个简单的截断，防止单文件十几万字把大模型的 Token 撑爆
        return f"文件 {matched_file} 的内容如下：\n{content[:8000]}"
        
    except Exception as e:
        return f"读取物理文件失败: {e}"