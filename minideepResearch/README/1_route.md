# 项目解读路线图 (Project Analysis Route)

本文档旨在为前端工程师面试准备提供一个结构化的项目解读计划。我们将按照“从宏观到微观”、“从架构到细节”的顺序，逐步拆解 `mini-deepresearch_replicate` 项目。

## 第一阶段：宏观概览与技术栈 (The "Big Picture")
**目标**：理解项目的核心价值、业务场景以及底层技术选型。

1.  **项目定位**：
    *   这是一个什么样的应用？(Deep Research AI Agent 客户端)
    *   解决了什么问题？(复杂问题的深度搜索与推理)
2.  **技术栈盘点 (Tech Stack Audit)**：
    *   **核心框架**：Next.js 16 (App Router) + React 19 (Bleeding Edge)
    *   **开发语言**：TypeScript
    *   **UI 系统**：Tailwind CSS v4, Ant Design, Framer Motion, Lucide React
    *   **状态管理**：Zustand (轻量级状态库)
    *   **AI/后端**：LangChain, LangGraph, Vercel AI SDK
    *   **数据存储**：PostgreSQL + Prisma ORM
3.  **核心配置分析**：
    *   `package.json` (依赖分析)
    *   `prisma/schema.prisma` (数据模型：Chat, Message, SharedChat)
    *   `next.config.ts` (构建配置)

## 第二阶段：架构与路由设计 (The "Skeleton")
**目标**：掌握应用的骨架结构、路由跳转及数据流向。

1.  **目录结构映射**：
    *   `src/app` (App Router 路由定义)
    *   `src/components` (UI 组件库)
    *   `src/lib` (工具函数与核心逻辑)
    *   `src/store` (全局状态)
    *   `src/agents` (AI 智能体逻辑)
2.  **路由与页面分析**：
    *   `src/app/page.tsx` (主页面/聊天界面)
    *   `src/app/share/[id]/page.tsx` (分享页面的静态化/动态渲染)
    *   `src/app/api/chat/route.ts` (核心流式对话接口)
3.  **数据流向 (Data Flow)**：
    *   Client -> Server Actions/API -> LangGraph Agent -> DB -> Client (Stream)

## 第三阶段：核心业务逻辑 (The "Brain")
**目标**：深入理解核心功能是如何实现的，特别是 AI 交互部分。

1.  **深度研究 (Deep Research) 机制**：
    *   如何触发研究模式？
    *   后端 `src/agents/` 下的 `graph.ts` 和 `deepGraph.ts` 是如何工作的？
    *   前端如何接收并渲染“思考过程” (`ThinkingProcess`)？
2.  **状态管理 (State Management)**：
    *   解析 `src/store/useChatStore.ts`。
    *   如何管理复杂的聊天历史、加载状态、流式消息更新？
3.  **持久化与历史记录**：
    *   Prisma 如何存取 `Chat` 和 `Message`。
    *   侧边栏 (`Sidebar`) 的历史记录加载逻辑。

## 第四阶段：组件与 UI 细节 (The "Skin")
**目标**：展示前端工程化能力，关注组件封装、交互细节与样式实现。

1.  **核心组件剖析**：
    *   `ChatInput.tsx`：输入框的高度自适应、附件处理、提交逻辑。
    *   `ChatMessage.tsx`：Markdown 渲染 (`react-markdown`)、代码高亮、数学公式 (`katex`)。
    *   `ThinkingProcess.tsx`：折叠/展开动画、实时状态更新。
    *   `SourceBubble.tsx`：引用源的展示与交互。
2.  **交互与动画**：
    *   使用 `framer-motion` 实现的过渡效果。
    *   流式输出时的打字机效果或自动滚动逻辑。
3.  **样式方案**：
    *   Tailwind v4 的新特性使用。
    *   响应式设计适配 (Mobile vs Desktop)。

## 第五阶段：面试重难点攻关 (The "Value")
**目标**：总结项目亮点，准备面试中可能遇到的技术追问。

1.  **React 19 & Next.js 16 新特性**：
    *   Server Actions 的使用。
    *   `use` hook 或其他 React 19 特性的体现。
2.  **性能优化**：
    *   首屏加载 (FCP/LCP)。
    *   流式渲染 (Streaming SSR) 的用户体验优势。
3.  **难点复盘**：
    *   如何处理复杂的 Markdown + Component 混合渲染？
    *   如何保证流式响应的稳定性与前后端状态同步？
    *   LangGraph 这一 AI 编排理念在前端的体现。

---

**后续行动建议**：
按照上述阶段，每天/每阶段深入阅读相关代码，并在 `README/` 目录下产出对应的详细分析文档 (如 `2_architecture.md`, `3_core_logic.md` 等)。
