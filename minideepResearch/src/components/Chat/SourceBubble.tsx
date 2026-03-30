"use client"; // 👈 必须加在第一行

import { Source } from "@/store/useChatStore";
import { Globe } from "lucide-react";

export default function SourceBubble({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {sources.map((source, idx) => (
        <a
          key={idx}
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-300 transition-colors border border-gray-200 dark:border-gray-700 max-w-full"
          title={source.title}
        >
          <Globe className="w-3 h-3 shrink-0" />
          <span className="truncate max-w-[150px]">{idx + 1}. {source.title}</span>
        </a>
      ))}
    </div>
  );
}