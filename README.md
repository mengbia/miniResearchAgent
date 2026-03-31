# 🚀 Mini Deep Research Agent

本项目是一个**双态混合检索智能体 (Hybrid RAG Dual-State Agent)**。它结合了本地私有知识库（ChromaDB）与全网搜索引擎（Tavily），由通义千问 (Qwen3-max) 和 LangGraph 驱动。支持轻量级日常闲聊与重度深度研究两种独立工作流。

## ✨ 核心特性

- 🎨 **现代化极客交互 (Modern UI/UX)**：基于 Next.js 与 Tailwind CSS 构建响应式极简界面，支持浅色/深色双主题无缝切换，提供媲美原生高级应用的沉浸式体验。
- 🌊 **全链路流式可视化 (Streaming Visualization)**：深度解析后端 SSE 协议，不仅实现丝滑的文字“打字机”输出，更能动态渲染 Agent 的底层思考轨迹（包括任务拆解进度条、本地工具调用加载动画）。
- 🏷️ **双源精准溯源展示 (Citation & Sources)**：独创的引用气泡组件，清晰隔离混合检索结果，精准标注 `[全网]` 外部网页链接与 `[内部私有库]` 本地文档出处，拒绝大模型幻觉。
- 📦 **稳健的全局状态托管 (State Management)**：采用 Zustand 进行轻量级状态管理，完美支持长对话平滑滚动、随时中断生成（Stop按钮）、一键重新生成，以及双态模式（闲聊/深度研究）的无缝热切换。
- 📎 **一键式知识库挂载 (Upload Interaction)**：高度定制的隐藏式文件上传组件，支持 `.pdf`, `.txt`, `.md`, `.docx` 格式一键无感上传，实时向用户反馈异步解析与向量化入库的状态。
- 🧠 **双态智能路由 (Dual-State Routing)**：后端按需分配算力。普通模式基于 Tool-Calling 机制自主挑选本地工具实现秒级响应；深度模式基于 LangGraph 多节点流水线 (Planner -> Worker -> Writer) 处理复杂课题。
- 🔍 **混合双擎并发检索 (Concurrent Hybrid Search)**：无缝融合 Tavily 全网实时搜索与 ChromaDB 本地私有数据检索，并在 Worker 节点采用 `asyncio.gather` 协程池实现真并发查询，彻底告别线程阻塞。
- ⚡ **MD5 极速去重引擎 (Content Deduplication)**：向量库入库前置基于内容寻址的 MD5 哈希查重机制，精准拦截重复文件，节省 Token 消耗，防止库内数据冗余并实现大文件“秒传”。
- 🛠️ **可观测性 (Observability & Evals)**：内置无侵入式、解耦的底层日志追踪系统（生成标准 `.log` 持久化文件），以及基于 Anthropic 标准的自动化端到端裁判评测脚本 (`evaluate.py`)。
---

## 📦 环境准备与依赖安装

确保你的机器上已安装 **Python 3.10+** 和 **Node.js 18+**。

### 1. 后端依赖 (Python)
进入后端目录 `deep_research_backend`，安装以下核心包：
```bash
pip install -r requirement.txt
```
*(注：本项目使用 `dashscope` 接入阿里云通义千问模型及 `text-embedding-v2` 向量模型)*

### 2. 前端依赖 (Node.js)
进入前端目录 `minideepResearch`，安装依赖：
```bash
npm install
```

---

## ⚙️ 环境配置

在 `deep_research_backend` 根目录下创建一个 `.env` 文件，填入你的 API Keys：

```env
# 大语言模型配置 (Qwen 等)
OPENAI_API_KEY="sk-你的大模型API_KEY"
OPENAI_API_BASE="[https://dashscope.aliyuncs.com/compatible-mode/v1](https://dashscope.aliyuncs.com/compatible-mode/v1)" # 以通义千问为例

# 联网搜索配置
TAVILY_API_KEY="tvly-你的Tavily_API_KEY"
```

---

## 🚀 启动与部署

本项目采用前后端分离架构，需要分别启动两个服务。

### 启动后端 API 服务
1. 打开终端，进入后端目录：`cd deep_research_backend`
2. 启动 FastAPI 服务：
```bash
uvicorn main:app --reload
```
*服务将运行在 `http://localhost:8000`*

### 启动前端 Web 界面
1. 打开新终端，进入前端目录：`cd minideepResearch`
2. 启动 Next.js 开发服务器：
```bash
npm run dev
```
*在浏览器中访问 `http://localhost:3000` 即可开始使用！*

---

## 🛠️ 开发者调试工具

后端提供了一个脱离前端 UI 的纯终端调试工具，内置自动日志落盘功能。
在后端目录下运行：
```bash
python terminal_chat.py
```
*支持通过输入 `/mode normal` 和 `/mode deep` 随时切换 Agent 的运行形态。*

## 🧪 自动化评测 (LLM-as-a-Judge)

运行内置的 Anthropic 标准评测脚本，自动测试 Agent 的工具调用准确率与幻觉率：
```bash
python evaluate.py
```
