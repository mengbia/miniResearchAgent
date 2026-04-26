"use client"; // 👈 必须加在第一行

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { toast } from "sonner";

import ThinkingProcess from "./ThinkingProcess";
import SourceBubble from "./SourceBubble";
import MessageActions from "./MessageActions";
import DeepResearchIndicator from "./DeepResearchIndicator";

// 👇 引入 Store 用于多选状态管理
import { useChatStore } from "@/store/useChatStore";

// 定义消息结构 (需与数据库/API返回保持一致)
interface MessageType {
  id: string;
  role: string;
  content: string;
  // 深度研究相关字段
  steps?: any[];
  sources?: any[];
  plan?: any[];
}

interface Props {
  message: MessageType;
  onRegenerate?: () => void;
  isReadOnly?: boolean; // ✨ 新增：只读模式标记 (用于分享页面)
}

export default function ChatMessage({ message, onRegenerate, isReadOnly = false }: Props) {
  const isUser = message.role === "user";

  // 👇 从 Store 获取多选状态
  const { isSelectionMode, selectedMessageIds, toggleMessageSelection } = useChatStore();
  const isSelected = selectedMessageIds.includes(message.id);

  // 处理点击交互
  const handleContentClick = (e: React.MouseEvent) => {
    // 1. 如果处于多选模式，点击内容区域直接触发选择
    if (isSelectionMode) {
        e.preventDefault();
        toggleMessageSelection(message.id);
        return;
    }

    // 2. 普通模式下，保留 LaTeX 公式的点击复制功能
    const target = e.target as HTMLElement;
    const katexNode = target.closest(".katex");

    if (katexNode) {
      const texSource = katexNode.querySelector("annotation")?.textContent;
      if (texSource) {
        navigator.clipboard.writeText(texSource);
        toast.success("LaTeX 公式已复制");
        e.stopPropagation();
      }
    }
  };

  return (
    <div
      className={`group flex w-full mb-6 relative transition-all duration-200 
        ${isUser ? "justify-end" : "justify-start"}
        ${/* 多选模式下的容器样式调整 */ isSelectionMode ? "cursor-pointer hover:bg-black/5 dark:hover:bg-white/5 rounded-xl -mx-2 px-2 py-2" : ""}
      `}
      // 在多选模式下，点击整行都会触发选择
      onClick={isSelectionMode ? () => toggleMessageSelection(message.id) : undefined}
    >
      {/* ✨ 1. 多选模式下的复选框 (Checkbox) */}
      {isSelectionMode && (
        <div className={`absolute top-4 ${isUser ? "-left-10" : "-left-10 md:-left-12"} flex items-center justify-center z-20`}>
          <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all duration-200 ${
             isSelected 
                ? "bg-purple-600 border-purple-600 shadow-md scale-110" 
                : "border-gray-400 bg-white dark:bg-black hover:border-purple-400"
          }`}>
             {isSelected && (
                 <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                 </svg>
             )}
          </div>
        </div>
      )}

      {/* 消息主体容器 */}
      <div className={`max-w-[90%] md:max-w-[80%] flex flex-col ${isUser ? "items-end" : "items-start"} 
        ${/* 未选中时变暗，突出选中项 */ isSelectionMode && !isSelected ? "opacity-40 grayscale blur-[0.5px]" : "opacity-100"}
        transition-all duration-300
      `}>

        <div
          className={`p-4 rounded-xl overflow-hidden shadow-sm w-full relative ${
            isUser 
              ? "bg-blue-600 text-white rounded-br-none" 
              : "bg-white dark:bg-gray-900 border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-100 rounded-bl-none"
          }`}
        >
            {/* A. 思考过程 (仅 AI) */}
            {!isUser && message.steps && message.steps.length > 0 && (
                <ThinkingProcess steps={message.steps} />
            )}

            {/* B. 深度研究任务清单 (仅 AI + M8功能) */}
            {!isUser && message.plan && message.plan.length > 0 && (
                <DeepResearchIndicator plan={message.plan} />
            )}

            {/* C. 正文内容 */}
            {message.content && (
                <div
                  onClick={handleContentClick}
                  className={`prose prose-sm break-words max-w-none ${
                      isUser ? "prose-invert text-white" : "dark:prose-invert text-gray-800 dark:text-gray-100"
                  } ${
                      // 如果上面有思考过程或任务，正文上方加分割线
                      (!isUser && (message.steps?.length || message.plan?.length)) ? "mt-4 pt-4 border-t dark:border-gray-800" : ""
                  }`}
                >
                <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                        // 链接新窗口打开
                        a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline break-all" />,
                        // 代码块美化
                        code: ({ node, ...props }) => <code {...props} className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm font-mono text-pink-500" />,
                        // 表格容器 (防止溢出)
                        table: ({node, ...props}) => <div className="overflow-x-auto my-4"><table {...props} className="min-w-full divide-y divide-gray-300 dark:divide-gray-700 border dark:border-gray-700 rounded-lg" /></div>,
                        // 表头
                        th: ({node, ...props}) => <th {...props} className="px-3 py-2 bg-gray-50 dark:bg-gray-800 font-semibold text-left text-xs uppercase text-gray-700 dark:text-gray-300" />,
                        // 单元格
                        td: ({node, ...props}) => <td {...props} className="px-3 py-2 text-sm border-t dark:border-gray-700" />
                    }}
                >
                    {message.content}
                </ReactMarkdown>
                </div>
            )}

            {/* D. 来源气泡 (仅 AI) */}
            {!isUser && message.sources && message.sources.length > 0 && (
                <SourceBubble sources={message.sources} />
            )}
        </div>

        {/* ✨ Action Bar */}
        {/* 1. 多选模式下：完全隐藏操作栏，避免干扰 */}
        {/* 2. 普通模式/只读模式下：显示，但在 Actions 内部会根据 isReadOnly 禁用某些按钮 */}
        {!isSelectionMode && (
             <MessageActions
                content={message.content}
                isUser={isUser}
                onRegenerate={!isReadOnly && !isUser ? onRegenerate : undefined}
                isReadOnly={isReadOnly}
             />
        )}

      </div>
    </div>
  );
}