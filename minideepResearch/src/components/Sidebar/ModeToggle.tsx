"use client"; // 👈 必须加这行！

import { useChatStore } from "@/store/useChatStore";
import { Brain, Sparkles } from "lucide-react";

export default function ModeToggle() {
  const { researchMode, setResearchMode, isLoading } = useChatStore();

  return (
    <button
      onClick={() => setResearchMode(researchMode === "normal" ? "deep" : "normal")}
      disabled={isLoading}
      className={`
        flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all border
        ${researchMode === "deep" 
          ? "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800" 
          : "bg-gray-100 text-gray-600 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700 hover:bg-gray-200 dark:hover:bg-gray-700"
        }
      `}
    >
      {researchMode === "deep" ? (
        <>
          <Brain className="w-3.5 h-3.5" />
          深度研究模式
        </>
      ) : (
        <>
          <Sparkles className="w-3.5 h-3.5" />
          普通模式
        </>
      )}
    </button>
  );
}