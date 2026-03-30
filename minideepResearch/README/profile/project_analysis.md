# Mini-DeepResearch Replicate 项目分析报告

## 1. 项目结构分析 (Project Structure)

该项目采用标准的 **Next.js 16 (App Router)** 架构，遵循 Feature-based 的目录组织方式，结构清晰，职责分明。

*   **`src/agents/` (核心大脑)**: 存放基于 LangGraph 的智能体逻辑。
    *   `graph.ts`: 处理普通对话的 ReAct 代理。
    *   `deepGraph.ts`: 处理深度研究模式的 Plan-and-Solve 代理，包含 Planner, Worker, Writer 等节点。
    *   `tools.ts`: 定义外部工具（如 Tavily Search）。
*   **`src/app/` (路由层)**:
    *   `api/`: 后端 Route Handlers，负责处理 SSE 流式响应 (`/api/chat`) 和数据持久化。
    *   `page.tsx`: 主页面，承载核心聊天交互。
    *   `share/[id]/`: 静态化的分享页面，支持服务端渲染 (SSR)。
*   **`src/store/` (状态管理)**: 使用 Zustand (`useChatStore.ts`) 作为单一数据源，精细管理从 SSE 接收到的碎片化数据（文本、计划、来源、步骤）。
*   **`src/components/` (UI 组件)**: 
    *   `Chat/`: 包含聊天气泡、输入框、以及核心的 `ThinkingProcess` (思维链展示) 组件。
    *   `Sidebar/`: 历史记录管理。
*   **`prisma/` (数据层)**: 定义了 PostgreSQL 的 Schema，包含 `Chat`, `Message` (存储 JSON 格式的 sources 和 plan), `SharedChat` 等模型。

## 2. 技术栈分析 (Tech Stack)

*   **前端框架**: Next.js 16 (React 19), Tailwind CSS, Framer Motion (动画).
*   **AI 编排**: LangChain, LangGraph (实现复杂的图与状态机逻辑).
*   **大模型交互**: Vercel AI SDK (基础), 自定义 SSE 协议 (高级流式控制).
*   **状态管理**: Zustand (轻量级，适合频繁更新的流式数据).
*   **数据库**: PostgreSQL, Prisma ORM.
*   **外部服务**: Tavily AI (搜索能力), OpenAI (模型推理).

## 3. 项目功能总结 (Functional Summary)

这是一个模仿 "Deep Research" 深度研究能力的 AI 搜索客户端。它不仅仅是一个聊天机器人，而是一个能够"自主思考"的研究助手。

*   **双模式对话**: 支持"普通模式" (快速问答) 和 "深度模式" (复杂任务拆解与研究)。
*   **深度研究 (Deep Research)**: 用户提出复杂问题后，AI 会自动拆解任务 (Plan)，分步执行网络搜索 (Execute)，收集多源信息，最后撰写长篇报告。
*   **透明化思维过程**: 界面实时展示 AI 的"思考过程"，包括正在执行的计划、搜索的关键词、引用的来源等。
*   **流式交互**: 采用打字机效果实时输出内容，并同步更新任务列表的状态。
*   **历史与分享**: 支持查看历史对话记录，并生成静态链接分享研究成果。

## 4. 项目亮点 (Highlights)

### 🌟 亮点一：基于 LangGraph 的 Plan-and-Solve 架构
**技术实现**: 使用 LangGraph 构建了一个包含 `Planner` (规划)、`Worker` (执行)、`Writer` (撰写) 节点的有向循环图。
**实现效果**: 突破了传统 LLM 单次问答的限制。面对 "分析 2024 AI 行业趋势" 这样的大问题，系统能自动拆解为 "查找硬件进展"、"查找模型层进展" 等子任务，循环执行搜索，直到收集足够信息。
**核心目的**: 赋予 AI 解决复杂、长链路问题的能力，大幅提升回答的深度和准确性。

### 🌟 亮点二：自定义全链路 SSE 流式协议
**技术实现**: 摒弃标准的 SDK 黑盒流，设计了包含 `text`, `tool_start`, `plan_update`, `sources` 等多种事件类型的自定义 SSE 协议。
**实现效果**: 前端不仅能显示文字，还能实时根据后端推送的事件让 "复选框打钩" (计划完成)、"弹出气泡" (正在搜索)、"展示卡片" (获取来源)。
**核心目的**: 极大地提升了用户体验 (UX) 和系统的透明度，让用户不再枯燥等待，而是看着 AI "干活"。

### 🌟 亮点三：鲁棒的客户端状态重组 (Rehydration)
**技术实现**: 利用 Zustand 在客户端通过 `addMessage`, `updateStep`, `updatePlan` 等 Actions，将后端碎片化的流式事件实时"缝合"成完整的 UI 状态树。
**实现效果**: 即使网络波动或流式传输中断，客户端也能尽可能保留当前的上下文。配合 Prisma 的 JSON 存储，保证了刷新页面后，之前的 "研究计划" 和 "引用来源" 依然完整可见。
**核心目的**: 解决流式应用中状态难以同步和持久化的痛点，保证复杂交互下的数据一致性。

### 🌟 亮点四：智能多模态剪贴板 (Smart Clipboard)
**技术实现**: 利用 `ClipboardItem` API 构建双重数据流。
    1. **Text Stream**: 纯 Markdown 文本。
    2. **HTML Stream**: 定制的 Word 兼容 HTML 模板（包含 `xmlns:w` 等命名空间），并利用 `KaTeX` 预先将 LaTeX 公式转换为 MathML，用 `<table>` 模拟代码块背景。
**实现效果**: 用户点击复制按钮后，若粘贴到代码编辑器，得到的是纯 Markdown；若粘贴到 Word、Outlook 或 Notion，得到的是完美保留格式（表格、标题、高亮代码、可编辑公式）的富文本。
**核心目的**: 打通 "AI 研究" 到 "文档撰写" 的最后一公里，无需手动调整格式。

### 🌟 亮点五：全息流式 UI (Holographic Streaming UI)
**技术实现**: 采用**组件化流式渲染**策略。将单一的 Message 数据流拆解为四个独立的 UI 维度：
    1. `ThinkingProcess`: 折叠式思维链，展示 AI 的隐式推理。
    2. `DeepResearchIndicator`: 动态 Todo List，根据 SSE 事件实时打钩 (Check)。
    3. `SourceBubble`: 搜索结果气泡，随搜随出，点击可溯源。
    4. `ReactMarkdown`: 主文本内容的打字机输出。
**实现效果**: 界面如同一个繁忙的仪表盘。用户能同时看到 AI "正在思考什么"、"计划执行到了哪一步"、"找到了哪些证据" 以及 "正在写什么结论"，彻底告别了传统 Chatbot "转圈圈 -> 吐结果" 的黑盒体验。
**核心目的**: 通过极致的信息透明度建立用户对 AI 智能体的信任感 (Cognitive Trust)。

### 🌟 亮点六：快照式多选分享 (Snapshot Sharing)
**技术实现**: 结合 `useChatStore` 的多选状态机与 Prisma 的快照存储。
    *   **前端**: 进入 "选择模式" (Selection Mode)，用户点选特定的对话气泡。
    *   **后端**: `/api/share` 接收 ID 列表，从 DB 拉取完整数据，进行 `JSON.stringify` 序列化，存入 `SharedChat` 表并生成 10 位 Nanoid 短链。
**实现效果**: 生成的分享链接是**静态快照** (Snapshot)。原对话后续的更新不会影响已分享的页面；同时，分享页面支持服务端渲染 (SSR)，秒开且 SEO 友好。
**核心目的**: 实现精准的知识分发，既保护了用户隐私（不分享无关的历史记录），又保证了分享内容的稳定性。

### 🌟 亮点七：交互式 LaTeX 公式 (Interactive LaTeX)
**技术实现**: 基于 DOM 事件代理的深度交互。
    在 `ChatMessage` 组件中监听点击事件，利用 `e.target.closest(".katex")` 捕获点击区域。一旦检测到用户点击了渲染后的数学公式，立即从 KaTeX生成的 `<annotation>` 标签中提取原始 TeX 代码。
**实现效果**: 用户在阅读复杂的数学推导时，只需点击公式 $E=mc^2$，剪贴板中即刻获得 `E=mc^2` 源码。
**核心目的**: 专为科研人员与开发者设计，极大降低了引用公式和二次编辑的成本。
