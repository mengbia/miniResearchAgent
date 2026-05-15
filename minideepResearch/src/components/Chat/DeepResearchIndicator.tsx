"use client";

import { PlanItem } from "@/store/useChatStore";
import { CheckCircle2, Circle, Loader2, ListTodo } from "lucide-react";
import { useState } from "react";

const isCompleted = (item: PlanItem) => item.status === "done" || item.status === "completed";

export default function DeepResearchIndicator({ plan }: { plan: PlanItem[] }) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (!plan || plan.length === 0) return null;

  const completedCount = plan.filter(isCompleted).length;
  const totalCount = plan.length;
  const isAllDone = completedCount === totalCount;

  return (
    <div className="mb-4 rounded-xl border border-purple-100 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-900/20 overflow-hidden">
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

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2">
          {plan.map((item, index) => {
            const itemId = item.id ?? index + 1;
            const done = isCompleted(item);
            const current = itemId === completedCount + 1;
            const label = item.task || item.title || "";

            return (
              <div key={itemId} className="flex items-start gap-2.5 text-sm">
                <div className="mt-0.5 shrink-0">
                  {done ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : current ? (
                    <Loader2 className="w-4 h-4 text-purple-600 animate-spin" />
                  ) : (
                    <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" />
                  )}
                </div>
                <span
                  className={
                    done
                      ? "text-gray-500 dark:text-gray-400 line-through"
                      : current
                        ? "text-purple-900 dark:text-purple-100 font-medium"
                        : "text-gray-500 dark:text-gray-500"
                  }
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
