"use client"; // 👈 必须加在第一行

import { useState } from "react";
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, Search, BrainCircuit } from "lucide-react";
import { Step } from "@/store/useChatStore";

export default function ThinkingProcess({ steps }: { steps: Step[] }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!steps || steps.length === 0) return null;

  // 判断整个过程是否还在进行中
  const isThinking = steps.some(s => s.status === "pending");

  return (
    <div className="mb-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* 标题栏 (点击折叠) */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300">
          {isThinking ? (
             <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          ) : (
             <CheckCircle2 className="w-4 h-4 text-green-500" />
          )}
          <span>思考过程 ({steps.length} 步)</span>
        </div>
        {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
      </div>

      {/* 步骤列表 */}
      {isExpanded && (
        <div className="p-3 pt-0 space-y-3 border-t border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-900/50">
          {steps.map((step) => (
            <div key={step.id} className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400 pl-1">
              {/* 图标状态 */}
              <div className="mt-0.5 shrink-0">
                {step.status === "pending" ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />
                ) : (
                  step.type === "reasoning" ? (
                    <BrainCircuit className="w-3.5 h-3.5 text-purple-400" />
                  ) : (
                    <Search className="w-3.5 h-3.5 text-gray-400" />
                  )
                )}
              </div>
              {/* 内容 */}
              <span className="break-all font-mono text-xs md:text-sm opacity-80">
                {step.content}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}