import os
from langchain_core.tools import tool
from rag.vector_store import local_kb
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader, UnstructuredMarkdownLoader

# Directory for storing uploaded files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

@tool
def list_local_files() -> str:
    """
    Retrieves a list of all files in the local knowledge base.
    Called when the user asks about available files.
    """
    if not os.path.exists(UPLOAD_DIR):
        return "The local knowledge base is empty."
        
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return "The local knowledge base is empty."
    return "Currently uploaded files: " + ", ".join(files)

@tool
def search_local_content(query: str) -> str:
    """
    Performs semantic retrieval within the local knowledge base.
    Called for specific knowledge points, concepts, or general questions.
    """
    results = local_kb.search_knowledge(query, top_k=5)
    if not results:
        return "No relevant content found in the local knowledge base."
    context = ""
    for doc in results:
        source = doc.metadata.get("source", "unknown").replace("\\", "/").split("/")[-1]
        context += f"-[{source}]: {doc.page_content[:400]}\n"
    return context

@tool
def read_full_document(filename: str) -> str:
    """
    Reads the full content of a specified file.
    Called when the user explicitly requests a summary or the full content of a file.
    """
    if not os.path.exists(UPLOAD_DIR):
        return "No local files found."
        
    files = os.listdir(UPLOAD_DIR)
    matched_file = next((f for f in files if filename.lower() in f.lower()), None)
    
    if not matched_file:
        return f"Could not find a file matching '{filename}'."
        
    file_path = os.path.join(UPLOAD_DIR, matched_file)
    ext = os.path.splitext(file_path)[-1].lower()
    
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding='utf-8')
        elif ext == ".docx":
            loader = Docx2txtLoader(file_path)
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
        else:
            return f"Unsupported file format for full text reading: {ext}"
            
        docs = loader.load()
        content = "\n".join([doc.page_content for doc in docs])
        
        # Truncate to manage context window limits
        return f"Content of {matched_file}:\n{content[:8000]}"
        
    except Exception as e:
        return f"Failed to read file: {e}"

if __name__ == "__main__" :
    print("Tool: list_local_files")
    print("Name:", list_local_files.name)
    print("Description:", list_local_files.description)
    print("Args:", list_local_files.args)

    print("\nTool: search_local_content")
    print(search_local_content.name)
    print(search_local_content.description)
