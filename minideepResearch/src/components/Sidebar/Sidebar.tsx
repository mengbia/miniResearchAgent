"use client";
import { useEffect } from "react";
import { useChatStore } from "@/store/useChatStore";
import { MessageSquare, Plus, Trash2 } from "lucide-react";

export default function Sidebar() {
  const {
    chats, currentChatId,
    setChats, setCurrentChatId, setMessages
  } = useChatStore();

  // 1. 初始化加载列表
  useEffect(() => {
    fetch("/api/history")
      .then(res => res.json())
      .then(data => setChats(data));
  }, []);

  // 2. 加载某个具体的会话
  const loadChat = async (id: string) => {
    setCurrentChatId(id);
    const res = await fetch(`/api/chat/${id}`);
    const msgs = await res.json();
    setMessages(msgs); // 这里加载的还是纯文本，没有 steps (这是数据库持久化的局限，暂且接受)
  };

  // 3. 新建对话
  const startNewChat = () => {
    setCurrentChatId(null);
    setMessages([]);
  };

  // 4. 删除对话
  const deleteChat = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // 防止触发 click 选中
    if (!confirm("确定删除吗？")) return;

    await fetch(`/api/chat/${id}`, { method: "DELETE" });
    setChats(chats.filter(c => c.id !== id));
    if (currentChatId === id) startNewChat();
  };

  return (
    <div className="w-64 h-full bg-gray-50 dark:bg-gray-900 border-r dark:border-gray-800 flex flex-col">
      <div className="p-4">
        <button
          onClick={startNewChat}
          className="w-full flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>新对话</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2">
        {chats.map(chat => (
          <div
            key={chat.id}
            onClick={() => loadChat(chat.id)}
            className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer text-sm mb-1 ${currentChatId === chat.id
                ? "bg-gray-200 dark:bg-gray-800 font-medium"
                : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400"
              }`}
          >
            <div className="flex items-center gap-2 truncate">
              <MessageSquare className="w-4 h-4 shrink-0" />
              <span className="truncate">{chat.title}</span>
            </div>

            <button
              onClick={(e) => deleteChat(e, chat.id)}
              className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-500 transition-opacity"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}