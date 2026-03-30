# 第五阶段：面试重难点攻关 (Interview Highlights)

本文档总结 `mini-deepresearch_replicate` 项目在面试中的核心价值，整理了可能的追问方向及标准回答范例。

## 1. 项目亮点总结 (Key Selling Points)

在面试中介绍此项目时，应重点突出以下三个维度：

1.  **全栈开发能力 (Full-Stack Capability)**:
    *   不仅是画 UI，还深入后端 API (`Next.js Route Handlers`)、数据库设计 (`Prisma + Postgres`) 和 AI 编排 (`LangGraph`)。
    *   能够处理复杂的前后端数据流同步问题 (SSE Streaming)。

2.  **复杂状态管理 (Complex State Management)**:
    *   展示了如何处理非线性的、碎片化的流式数据。
    *   解决了“如何将后端推送的 5 种不同类型的事件 (Text, Tool, Plan, Source, Error) 实时合并到一个连贯的 UI 中”这一难题。

3.  **AI Native 交互设计**:
    *   不是简单的 Chatbot，而是实现了“思考过程可视化” (Thinking Process) 和“深度研究” (Deep Research)。
    *   体现了对 AI 产品用户体验 (UX) 的深度思考：让用户知道 AI 在忙什么，而不是傻等。

## 2. 常见面试题与回答策略

### Q1: 为什么不使用 Vercel AI SDK 的 `useChat`？为什么要自己写 SSE 解析？
*   **回答**:
    *   `useChat` 非常棒，但它主要针对标准的“文本对话”场景。
    *   本项目的需求比较特殊：我们需要在一个流里混合传输“思考步骤”、“搜索来源”、“任务清单更新”以及“最终文本”。
    *   虽然 `useChat` 支持 Tool Call，但对于像 LangGraph 这种复杂的图结构，自定义 SSE 协议 (`type` + `content`) 更加灵活，能让我们精确控制 UI 的每一个微小状态更新 (比如任务列表的打钩动画)。

### Q2: 深度研究模式 (Deep Research) 是如何实现的？
*   **回答**:
    *   **后端**: 采用 LangGraph 构建了一个 Plan-and-Solve 的图结构。
        *   `Planner` 节点负责生成 JSON 格式的任务列表。
        *   `Worker` 节点循环执行搜索任务。
        *   `Writer` 节点在最后汇总信息写报告。
    *   **前端**: 并不只是等待最终结果。我们监听了 `plan_created` 和 `plan_update` 事件。
        *   当 Planner 完成时，前端立刻渲染出任务列表。
        *   当 Worker 完成一个任务时，前端实时更新该任务的状态为 `done`。
        *   这极大降低了用户的等待焦虑感。

### Q3: 这里面遇到的最大坑是什么？如何解决的？
*   **回答**: **JSON 嵌套与大模型幻觉问题**。
    *   **现象**: 模型有时候会返回 `{"input": "{\"query\": \"...\"}"}` (JSON 套 JSON)，有时候又直接返回文本，或者格式错乱。
    *   **解决**:
        1.  **Prompt 优化**: 在 System Prompt 中反复强调输出格式。
        2.  **防御性编程**: 在前端编写了一个 `extractCleanQuery` 递归函数，无论 JSON 套了多少层，或者混杂了什么 Key，都能暴力递归找到最深层的字符串作为搜索关键词。
        3.  **正则兜底**: 对于搜索结果的解析，不完全依赖 JSON，而是用正则表达式去提取 `标题:` 和 `来源:`，保证即使模型输出格式微崩，UI 依然能渲染出链接。

### Q4: 如何优化首屏加载性能？
*   **回答**:
    *   **SSR (服务端渲染)**: 首页虽然是 Client Component，但框架本身提供了静态壳。
    *   **组件懒加载**: 对于 Markdown 渲染器这种重型组件，其实可以考虑 `next/dynamic` (虽然目前代码可能没加，但这不仅是优化点，也是面试加分项)。
    *   **流式渲染**: 分享页 (`/share/[id]`) 采用了 React Server Component (RSC)，直接在服务端读库渲染 HTML，首屏速度极快且 SEO 友好。

## 3. 代码级的细节准备

面试前请务必重新熟悉以下代码片段：

*   **流式循环**: `src/app/page.tsx` 中的 `while (true) { const { done, value } = await reader.read(); ... }`。
*   **递归解析**: `extractCleanQuery` 函数的逻辑。
*   **Zustand Store**: `setSourcesForLastMessage` 中的去重逻辑 (`Map` 的使用)。
*   **Prisma Schema**: `Json` 类型的使用场景。

## 4. 总结

`mini-deepresearch_replicate` 是一个**小而美**的面试杀手级项目。它摒弃了繁杂的后台管理功能，直击当前最热门的 **AI Agent** 和 **Streaming UX** 领域，展现了候选人在新技术探索和复杂逻辑实现上的潜力。
