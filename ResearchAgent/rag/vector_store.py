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
from langchain_chroma import Chroma
from core.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME, BACKUP_MODEL_EMBEDDING
from core.llm import get_embeddings

# Path for local Chroma persistence
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data")

class LocalVectorStore:
    def __init__(self):
        # Use high-availability embedding model
        self.embeddings = get_embeddings()
        
        try:
            model_name = getattr(self.embeddings, 'model', 'default_emb').replace("-", "_")
        except:
            model_name = "backup_emb"

        # Dynamically set collection name based on the embedding model
        dynamic_collection_name = f"deep_research_kb_{model_name}"
        
        self.vector_store = Chroma(
            collection_name=dynamic_collection_name, 
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )

    def _calculate_file_md5(self, file_path: str) -> str:
        """Calculates MD5 hash of file content for deduplication."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def process_and_save_document(self, file_path: str):
        """Processes a document, checks for duplicates via MD5, and saves to the vector store."""
        ext = os.path.splitext(file_path)[-1].lower()
        print(f"Processing file: {file_path}")
        
        file_md5 = self._calculate_file_md5(file_path)
        print(f"MD5 Fingerprint: {file_md5}")

        # Check for existing documents with the same MD5 hash
        existing_docs = self.vector_store.get(where={"file_md5": file_md5})
        if existing_docs and len(existing_docs["ids"]) > 0:
            print("File content identical to existing records. Skipping vectorization.")
            return True

        if ext == ".pdf": loader = PyPDFLoader(file_path)
        elif ext == ".txt": loader = TextLoader(file_path, encoding='utf-8')
        elif ext == ".docx": loader = Docx2txtLoader(file_path)
        elif ext == ".md": loader = UnstructuredMarkdownLoader(file_path)
        else: raise ValueError(f"Unsupported file format: {ext}")

        docs = loader.load()
        split_docs = self.text_splitter.split_documents(docs)
        print(f"File split into {len(split_docs)} chunks.")

        chunk_ids = []
        for i, doc in enumerate(split_docs):
            doc.metadata["file_md5"] = file_md5
            chunk_ids.append(f"{file_md5}_chunk_{i}")

        # Add documents with unique IDs to prevent redundancy
        self.vector_store.add_documents(documents=split_docs, ids=chunk_ids)
        print("Successfully saved to vector store.")
        return True

    def search_knowledge(self, query: str, top_k: int = 3):
        """Retrieves the most relevant document chunks from the store."""
        print(f"Searching local knowledge base: {query}")
        results = self.vector_store.similarity_search(query, k=top_k)
        return results
    
local_kb = LocalVectorStore()

if __name__ == "__main__":
    test_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "test.txt")
    
    if os.path.exists(test_file):
        local_kb.process_and_save_document(test_file)
    else:
        print("Test file not found.")
        
    print("\nStarting retrieval test...")
    query = "Summarize the content"
    docs = local_kb.search_knowledge(query)
    
    for i, doc in enumerate(docs):
        print(f"\nChunk {i+1}:\n{doc.page_content[:150]}...")
