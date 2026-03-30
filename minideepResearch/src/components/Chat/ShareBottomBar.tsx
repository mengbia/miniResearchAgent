import { useState } from "react";
import { X, CheckSquare, Share, Loader2 } from "lucide-react";
import { useChatStore } from "@/store/useChatStore";
import { toast } from "sonner";

export default function ShareBottomBar() {
  const {
    isSelectionMode,
    setSelectionMode,
    selectedMessageIds,
    selectAllMessages,
    deselectAllMessages,
    currentChatId
  } = useChatStore();

  const [isPublishing, setIsPublishing] = useState(false);

  if (!isSelectionMode) return null;

  const handlePublish = async () => {
    if (selectedMessageIds.length === 0) {
        toast.error("请至少选择一条消息");
        return;
    }

    setIsPublishing(true);
    try {
      const res = await fetch("/api/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          originalChatId: currentChatId,
          selectedMessageIds
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error);

      // 成功：复制链接并退出模式
      await navigator.clipboard.writeText(data.shareUrl);
      toast.success("链接已生成并复制到剪贴板！");
      setSelectionMode(false);

    } catch (e: any) {
      toast.error("分享失败: " + e.message);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-white dark:bg-gray-800 border dark:border-gray-700 shadow-2xl rounded-full px-6 py-3 animate-in slide-in-from-bottom-10 fade-in duration-300">

      <div className="text-sm font-medium text-gray-600 dark:text-gray-300 border-r dark:border-gray-700 pr-4 mr-1">
        已选 {selectedMessageIds.length} 条
      </div>

      <button
        onClick={selectAllMessages}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
      >
        <CheckSquare className="w-4 h-4" />
        全选
      </button>

      <button
        onClick={() => setSelectionMode(false)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
      >
        <X className="w-4 h-4" />
        取消
      </button>

      <div className="w-px h-4 bg-gray-200 dark:bg-gray-700 mx-1" />

      <button
        onClick={handlePublish}
        disabled={isPublishing || selectedMessageIds.length === 0}
        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-bold rounded-full shadow-lg shadow-purple-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPublishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Share className="w-4 h-4" />}
        生成分享链接
      </button>

    </div>
  );
}