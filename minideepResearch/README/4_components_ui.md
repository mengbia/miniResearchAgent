# 第四阶段：组件与 UI 细节 (Components & UI)

本文档聚焦于前端工程化实现，解析项目如何构建一个高性能、交互流畅的 Chat UI。

## 1. 核心组件架构

### 1.1 消息气泡 (`ChatMessage.tsx`)
这是最复杂的展示组件，采用了“乐高积木”式的嵌套结构，根据 `message` 对象的状态按需渲染不同模块。

*   **结构层级**:
    *   `Wrapper`: 处理多选模式 (Selection Mode) 的点击与样式变灰逻辑。
    *   `Container`: 区分 User (蓝色) 和 AI (白色/黑灰) 的背景色。
    *   `ThinkingProcess`: (可选) 渲染“正在搜索...”的折叠面板。
    *   `DeepResearchIndicator`: (可选) 渲染深度研究的任务清单 (Pending/Done 状态)。
    *   `ReactMarkdown`: 核心正文渲染。
        *   集成 `remark-math` + `rehype-katex` 支持 LaTeX 公式。
        *   自定义 `code` 块样式。
        *   自定义 `table` 容器防止移动端溢出。
    *   `SourceBubble`: (可选) 底部来源引用胶囊。
    *   `MessageActions`: 底部操作栏 (复制、重试)。

### 1.2 思考过程 (`ThinkingProcess.tsx`)
*   **交互**: 默认展开，点击标题栏可折叠。
*   **状态**: 只要有一个步骤是 `pending`，标题栏就显示 Loading 动画；全部完成后显示绿色对钩。
*   **样式**: 使用淡色背景与主内容区分，字体偏小 (text-xs/sm)，营造“后台日志”的感觉。

### 1.3 来源气泡 (`SourceBubble.tsx`)
*   **设计**: 药丸状 (Pill-shaped) 按钮，包含序号、地球图标和截断的标题。
*   **交互**: 点击在新标签页打开原始链接。
*   **排版**: `flex-wrap` 布局，自动换行适应不同屏幕宽度。

## 2. 交互与动效 (Interaction & Animation)

虽然项目未大量使用复杂的 Framer Motion 动画，但在微交互上做了细腻处理：

1.  **打字机效果 (Streaming Typing)**:
    *   不依赖第三方库，而是直接由 React 的重渲染机制驱动。
    *   当 `message.content` 在 Store 中更新时，UI 自动重绘。

2.  **自动滚动 (Auto Scroll)**:
    *   在 `page.tsx` 中使用 `useEffect` 监听 `messages` 变化。
    *   `scrollRef.current.scrollTo({ top: scrollHeight, behavior: "smooth" })` 实现平滑滚动。

3.  **多选模式 (Selection Mode)**:
    *   **触发**: 点击底部的分享按钮进入。
    *   **视觉反馈**:
        *   未选中的消息：`opacity-40 grayscale blur-[0.5px]` (变灰、模糊)。
        *   选中的消息：`scale-110` (复选框放大)，高亮显示。
    *   **智能选择**: 代码中包含了 `toggleMessageSelection` 的智能逻辑，选中一条 User 消息会自动关联其后的 AI 回复，反之亦然。

## 3. 样式系统 (Styling) - Tailwind CSS

项目全面采用 **Tailwind CSS**，并结合 CSS Variables 实现深色模式 (Dark Mode)。

*   **响应式设计**:
    *   `md:max-w-[80%]`: 桌面端限制气泡最大宽度。
    *   `hidden md:flex`: 侧边栏在移动端隐藏，桌面端显示。
*   **深色模式**:
    *   `dark:bg-gray-900`, `dark:text-gray-100`: 大量使用 `dark:` 前缀。
    *   利用 `tailwind.config` 中的 `darkMode: 'class'` 配合 `next-themes` (或手动 `ModeToggle`) 切换 `html` 标签上的 `dark` 类名。
*   **排版细节**:
    *   `prose prose-sm dark:prose-invert`: 使用 `@tailwindcss/typography` 插件一键处理 Markdown 的富文本样式。

## 4. 前端工程化亮点

1.  **组件复用**: `ChatMessage` 同时服务于主聊天页 (Client) 和 分享页 (Server)，通过 `isReadOnly` 属性控制交互行为。
2.  **防错处理**:
    *   LaTeX 渲染失败时的 Error Boundary (虽然代码中未显式展示，但 `react-markdown` 内部有容错)。
    *   JSON 解析失败时的 `try-catch` 兜底。
3.  **性能考量**:
    *   `ThinkingProcess` 内部独立维护 `isExpanded` 状态，避免折叠操作触发父组件重渲染。
    *   大量使用 `memo` (虽然当前代码未显式包裹，但这是 React 组件优化的常规手段)。
