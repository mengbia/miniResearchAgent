import os
import uuid
import datetime
from langchain_chroma import Chroma
from core.config import LLM_API_KEY
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm, get_embeddings
from core.prompt_manager import prompt_manager

# Persistent directory for user memory
MEMORY_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_data", "user_memory")

class UserMemoryStore:
    def __init__(self):
        self.embeddings = get_embeddings()
        
        try:
            model_name = getattr(self.embeddings, 'model', 'default_emb').replace("-", "_")
        except:
            model_name = "backup_emb"

        # Isolate long-term memory collections based on embedding model
        dynamic_collection_name = f"long_term_memory_{model_name}"

        self.vector_store = Chroma(
            collection_name=dynamic_collection_name,
            embedding_function=self.embeddings,
            persist_directory=MEMORY_PERSIST_DIR
        )
        self.llm = get_llm()

    async def async_extract_and_save(self, user_input: str):
        """Analyzes user input for important preferences and saves them to the vector store."""
        sys_template = prompt_manager.get("memory", "extractor")
        
        try:
            # Extract memory fact using LLM with fallback support
            messages = [
                SystemMessage(content=sys_template),
                HumanMessage(content=f"用户的话：\n<user_input>\n{user_input}\n</user_input>")
            ]
            response = await self.llm.ainvoke(messages)
            memory_fact = response.content.strip()
            
            if memory_fact and memory_fact.lower() != "none":
                print(f"[Memory Captured]: {memory_fact}")
                doc_id = str(uuid.uuid4())
                now = datetime.datetime.now()
                
                try:
                    # Save to vector store with temporal metadata
                    self.vector_store.add_texts(
                        texts=[memory_fact], 
                        ids=[doc_id],
                        metadatas=[{
                            "source": "user_chat",
                            "timestamp": now.timestamp(),
                            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
                        }]
                    )
                except Exception as emb_e:
                    print(f"[Warning] Memory extracted but vector storage failed: {emb_e}")
                    
        except Exception as e:
            print(f"[Error] Memory extraction failed: {e}")

    def retrieve_memory(self, query: str, top_k: int = 5) -> str:
        """Retrieves relevant long-term memories based on the current query."""
        try:
            # Retrieve candidates
            results = self.vector_store.similarity_search(query, k=top_k)
            if not results:
                return "No relevant historical memory found."
            
            # Dynamic timestamp injection: only inject if there are multiple memories to compare
            # Sort results by timestamp (newest first) to prioritize recent facts
            results.sort(key=lambda x: x.metadata.get("timestamp", 0.0), reverse=True)
            
            memories = []
            for doc in results:
                if len(results) > 1 and "timestamp" in doc.metadata:
                    # Use a shorter timestamp format (YY-MM-DD HH:MM) to save tokens but prevent cross-year conflicts
                    dt_obj = datetime.datetime.fromtimestamp(doc.metadata["timestamp"])
                    short_time = dt_obj.strftime("%y-%m-%d %H:%M")
                    memories.append(f"[{short_time}] {doc.page_content}")
                else:
                    # No timestamp overhead if it's a single, unambiguous memory
                    memories.append(doc.page_content)
            
            return "\n".join([f"- {m}" for m in memories])
        except Exception as e:
            print(f"[Error] Memory retrieval failed: {e}")
            return "Memory retrieval error."

user_memory = UserMemoryStore()
