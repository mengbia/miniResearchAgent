from langchain_core.tools import tool
from rag.vector_store import local_kb

@tool
def list_local_files() -> str:
    """获取当前本地知识库中已上传的所有文件列表（文件名）。当用户问“有什么文件”、“上传了哪些文件”时调用此工具。"""
    files = local_kb.get_all_filenames()
    if not files:
        return "当前本地知识库没有任何文件。"
    return "当前已上传的文件有：" + "、".join(files)

@tool
def search_local_content(query: str) -> str:
    """在本地知识库中进行语义片段检索。当用户询问具体知识点、概念、或普通问题时调用此工具。"""
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
    content = local_kb.get_full_document_by_keyword(filename)
    if not content:
        return f"未能找到包含 {filename} 的文件内容。"
    return f"文件 {filename} 的内容如下：\n{content}"