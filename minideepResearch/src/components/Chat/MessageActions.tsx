"use client"; // 👈 必须加在第一行

import { Copy, Check, Download, RotateCw, Share2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { copyDualFormat } from "@/lib/clipboardUtils"; // M9: 智能复制工具
import { useChatStore } from "@/store/useChatStore";   // M10: 状态管理

interface Props {
  content: string;
  isUser: boolean;
  onRegenerate?: () => void;
  isReadOnly?: boolean; // M10: 只读模式标记
}

export default function MessageActions({ content, isUser, onRegenerate, isReadOnly = false }: Props) {
  const [copied, setCopied] = useState(false);
  const { setSelectionMode } = useChatStore(); // 获取开启多选模式的方法

  // 1. 处理复制 (智能双模：文本 + Word HTML)
  const handleCopy = async () => {
    try {
      const success = await copyDualFormat(content);

      setCopied(true);
      if (success) {
        toast.success("已复制 (Word格式已优化)");
      } else {
        toast.warning("已复制纯文本");
      }
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Copy failed", e);
      toast.error("复制失败");
    }
  };

  // 2. 处理下载 (保存为 Markdown 文件)
  const handleDownload = () => {
    try {
      const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `deep-research-report-${Date.now()}.md`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("报告已下载");
    } catch (e) {
      toast.error("下载失败");
    }
  };

  return (
    <div className={`flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? "justify-end text-blue-100" : "justify-start text-gray-400"}`}>

      {/* A. 复制按钮 (所有模式下均可用) */}
      <button
        onClick={handleCopy}
        className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
        title="智能复制 (支持 Word/Markdown)"
      >
        {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
      </button>

      {/* B. 下载按钮 (仅 AI 消息可用) */}
      {!isUser && (
        <button
            onClick={handleDownload}
            className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
            title="下载 Markdown 文件"
        >
            <Download className="w-3.5 h-3.5" />
        </button>
      )}

      {/* C. 分享按钮 (仅 AI 消息 && 非只读模式可用) */}
      {!isReadOnly && !isUser && (
        <button
          onClick={() => setSelectionMode(true)} // 触发 M10 多选模式
          className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
          title="分享对话快照"
        >
          <Share2 className="w-3.5 h-3.5" />
        </button>
      )}

      {/* D. 重新生成按钮 (仅 AI 消息 && 非只读模式可用) */}
      {!isReadOnly && !isUser && onRegenerate && (
        <button
          onClick={onRegenerate}
          className="p-1 hover:bg-black/10 dark:hover:bg-white/10 rounded transition-colors"
          title="重新生成"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}