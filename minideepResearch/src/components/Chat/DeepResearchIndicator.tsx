"use client"; // 👈 必须加在第一行

import { PlanItem } from "@/store/useChatStore";
import { CheckCircle2, Circle, Loader2, ListTodo } from "lucide-react";
import { useState } from "react";

export default function DeepResearchIndicator({ plan }: { plan: PlanItem[] }) {
  // 默认展开，但用户可以折叠
  const [isExpanded, setIsExpanded] = useState(true);

  if (!plan || plan.length === 0) return null;

  const completedCount = plan.filter((p) => p.status === "done").length;
  const totalCount = plan.length;
  const isAllDone = completedCount === totalCount;

  return (
    <div className="mb-4 rounded-xl border border-purple-100 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-900/20 overflow-hidden">
      {/* 标题栏 (可点击折叠) */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-purple-100/50 dark:hover:bg-purple-900/30 transition-colors"
      >
        <div className="flex items-center gap-2 text-purple-800 dark:text-purple-200">
          {isAllDone ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <Loader2 className="w-4 h-4 animate-spin" />
          )}
          <span className="text-sm font-medium">
            {isAllDone ? "深度研究已完成" : "深度研究进行中..."}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-purple-600 dark:text-purple-400">
            {completedCount} / {totalCount}
          </span>
          <ListTodo className="w-4 h-4 text-purple-400" />
        </div>
      </div>

      {/* 任务列表内容 */}
      {isExpanded && (
        <div className="px-4 pb-3 space-y-2">
          {plan.map((item) => (
            <div key={item.id} className="flex items-start gap-2.5 text-sm">
              <div className="mt-0.5 shrink-0">
                {item.status === "done" ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  // 如果是第一个 pending 的，显示转圈，后面的显示空圈
                  item.id === completedCount + 1 ? (
                    <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
                  ) : (
                    <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                  )
                )}
              </div>
              <span className={`${
                item.status === "done" 
                  ? "text-gray-500 dark:text-gray-400 line-through" 
                  : item.id === completedCount + 1
                    ? "text-purple-900 dark:text-purple-100 font-medium"
                    : "text-gray-500 dark:text-gray-500"
              }`}>
                {item.task}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}