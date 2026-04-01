# 🚀 Mini Deep Research Agent
This project is a **Hybrid RAG Dual-State Agent**. It combines a local private knowledge base (ChromaDB) with a global web search engine (Tavily), powered by Qwen3-max and LangGraph. It supports two independent workflows: lightweight daily chat and heavy-duty deep research.

## ✨ Core Features

- 🎨 **Modern Geek-style Interaction (Modern UI/UX)**: Responsive minimal interface built with Next.js and Tailwind CSS, supporting seamless light/dark theme switching for an immersive experience comparable to premium native applications.
- 🌊 **Full-Link Streaming Visualization**: Deeply parses the backend SSE protocol, delivering smooth typewriter-style text output while dynamically rendering the Agent’s underlying reasoning trajectory (including task breakdown progress bars and loading animations for local tool calls).
- 🏷️ **Dual-Source Precise Citation & Source Display**: Unique citation bubble component that clearly isolates hybrid retrieval results, accurately marking `[Web]` external webpage links and `[Internal Private Library]` local document sources to eliminate LLM hallucinations.
- 📦 **Robust Global State Management**: Lightweight state management with Zustand, perfectly supporting smooth scrolling for long conversations, on-demand generation interruption (Stop button), one-click regeneration, and seamless hot switching between dual modes (Chat / Deep Research).
- 📎 **One-Click Knowledge Base Mounting**: Highly customized hidden file upload component supporting one-click seamless upload of `.pdf`, `.txt`, `.md`, and `.docx` files, with real-time feedback on asynchronous parsing and vectorized storage status.
- 🧠 **Dual-State Intelligent Routing**: Backend allocates computing power on demand. Normal mode autonomously selects local tools via the Tool-Calling mechanism for second-level response; Deep Research mode handles complex topics via a LangGraph multi-node pipeline (Planner -> Worker -> Writer).
- 🔍 **Hybrid Dual-Engine Concurrent Search**: Seamlessly integrates Tavily real-time web search and ChromaDB local private data retrieval, with true concurrent queries implemented via an `asyncio.gather` coroutine pool at the Worker node to eliminate thread blocking.
- ⚡ **MD5 High-Speed Deduplication Engine**: Content-addressable MD5 hash duplicate checking prior to vector database storage, accurately blocking duplicate files, reducing token consumption, preventing data redundancy, and enabling "second upload" for large files.
- 🛠️ **Observability & Evals**: Built-in non-intrusive, decoupled underlying log tracking system (generating standard `.log` persistent files), plus an Anthropic-standard automated end-to-end LLM-as-a-Judge evaluation script (`evaluate.py`).

---

## 📦 Environment Setup & Dependency Installation
Ensure **Python 3.10+** and **Node.js 18+** are installed on your machine.

### 1. Backend Dependencies (Python)
Navigate to the backend directory `ResearchAgent` and install core packages:
```bash
pip install -r requirement.txt
```
*(Note: This project uses `dashscope` to access Alibaba Cloud's Qwen model and the `text-embedding-v2` embedding model)*

### 2. Frontend Dependencies (Node.js)
Navigate to the frontend directory `minideepResearch` and install dependencies:
```bash
npm install
```

---

## ⚙️ Environment Configuration
Create a `.env` file in the `ResearchAgent` root directory and fill in your API Keys:

```env
# LLM Configuration (Qwen, etc.)
OPENAI_API_KEY="sk-your-llm-api-key"
OPENAI_API_BASE="https://dashscope.aliyuncs.com/compatible-mode/v1" # Example for Qwen

# Web Search Configuration
TAVILY_API_KEY="tvly-your-tavily-api-key"
```

---

## 🚀 Startup & Deployment
This project uses a front-end and back-end separation architecture, requiring two services to be started separately.

### Start Backend API Service
1. Open a terminal and enter the backend directory: `cd ResearchAgent`
2. Start the FastAPI service:
```bash
uvicorn main:app --reload
```
*Service runs at `http://localhost:8000`*

### Start Frontend Web Interface
1. Open a new terminal and enter the frontend directory: `cd minideepResearch`
2. Start the Next.js development server:
```bash
npm run dev
```
*Access `http://localhost:3000` in your browser to start using!*

---

## 🛠️ Developer Debugging Tool
The backend provides a pure terminal debugging tool independent of the frontend UI, with built-in automatic log persistence.
Run in the backend directory:
```bash
python terminal_chat.py
```
*Supports switching the Agent’s operating mode at any time by entering `/mode normal` and `/mode deep`.*

## 🧪 Automated Evaluation (LLM-as-a-Judge)
Run the built-in Anthropic-standard evaluation script to automatically test the Agent’s tool call accuracy and hallucination rate:
```bash
python evaluate.py
```