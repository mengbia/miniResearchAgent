"use client";

import { useRef, useEffect } from "react";
import { nanoid } from "nanoid";
import { useChatStore } from "@/store/useChatStore";
import ChatMessage from "@/components/Chat/ChatMessage";
import Sidebar from "@/components/Sidebar/Sidebar";
import ModeToggle from "@/components/Sidebar/ModeToggle";
import ShareBottomBar from "@/components/Chat/ShareBottomBar"; // 👈 M10 引入分享栏
import { StopCircle } from "lucide-react";



export default function Home() {
  const {
    messages,
    input,
    isLoading,
    currentChatId,
    researchMode,
    abortController,

    setInput,
    addMessage,
    setLoading,
    updateLastMessage,
    addStepToLastMessage,
    completeLastStep,
    setCurrentChatId,
    setChats,
    setSourcesForLastMessage,
    deleteLastMessage,

    setAbortController,
    updateLastMessagePlan
  } = useChatStore();

  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      const div = scrollRef.current;
      div.scrollTo({ top: div.scrollHeight, behavior: "smooth" });
    }
  }, [messages, messages.flatMap(m => m.steps), messages.flatMap(m => m.plan)]);

  // 🛑 停止生成
  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setLoading(false);
    }
  };

  // 🔄 重新生成
  const handleRegenerate = async () => {
    if (isLoading) return;
    const msgs = useChatStore.getState().messages;
    if (msgs.length < 2) return;

    const lastUserMsg = msgs[msgs.length - 2];
    if (lastUserMsg.role !== "user") return;

    deleteLastMessage();
    setTimeout(() => handleSend(lastUserMsg.content), 0);
  };

  // 🌟 新增：处理文件上传的逻辑
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    alert(`正在上传并解析 ${file.name}... 请稍候。`);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();

      if (data.status === "success") {
        alert("✅ " + data.message);
      } else {
        alert("❌ 上传失败: " + data.message);
      }
    } catch (error) {
      console.error("上传出错:", error);
      alert("网络错误，上传失败！");
    } finally {
      e.target.value = ''; // 清空 input
    }
  };


  // 🚀 发送消息
  const handleSend = async (manualContent?: string) => {
    const contentToSend = manualContent || input;
    if (!contentToSend.trim() || isLoading) return;

    const isRegenerate = !!manualContent;

    if (!isRegenerate) {
      setInput("");
      addMessage({ role: "user", content: contentToSend, id: nanoid() });
    }

    setLoading(true);
    addMessage({ role: "ai", content: "", id: nanoid() });

    const controller = new AbortController();
    setAbortController(controller);

    // Variables for streaming accumulation
    let accumulatedContent = "";
    let currentThinkingId: string | null = null;
    let accumulatedThinking = "";

    try {
      const currentMessages = useChatStore.getState().messages.filter(m => m.content !== "");

      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: currentMessages,
          mode: researchMode
        }),
        signal: controller.signal
      });

      if (!response.ok) throw new Error(response.statusText);
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonStr = line.slice(6);
              if (!jsonStr.trim()) continue;
              const data = JSON.parse(jsonStr);

              // === 1. Text Generation ===
              if (data.type === "text") {
                if (currentThinkingId) {
                  completeLastStep();
                  currentThinkingId = null;
                  accumulatedThinking = "";
                }
                accumulatedContent += data.content;
                updateLastMessage(accumulatedContent);
              }

              // === 2. Thinking Process (New) ===
              else if (data.type === "thinking") {
                if (!currentThinkingId) {
                  currentThinkingId = nanoid();
                  addStepToLastMessage({
                    id: currentThinkingId,
                    type: "reasoning",
                    content: "正在分析意图...",
                    status: "pending"
                  });
                }
                accumulatedThinking += data.content;
                // Update the step content with the thinking stream
                const msgs = useChatStore.getState().messages;
                const lastMsg = msgs[msgs.length - 1];
                if (lastMsg.steps) {
                  const step = lastMsg.steps.find(s => s.id === currentThinkingId);
                  if (step) {
                    step.content = accumulatedThinking;
                  }
                }
              }

              // === 3. Tool Start ===
              else if (data.type === "tool_start") {
                // If we were thinking, complete it
                if (currentThinkingId) {
                  completeLastStep();
                  currentThinkingId = null;
                  accumulatedThinking = "";
                }
                const inputPayload = data.content.input;

                // 🌟 定义递归解析函数 (解决 JSON 套娃问题)
                const extractCleanQuery = (payload: any): string => {
                  if (!payload) return "";

                  // 情况 A: 它是对象 (例如 { input: "..." })
                  if (typeof payload === 'object') {
                    // 优先找标准 Key，找到后递归处理
                    if (payload.query) return extractCleanQuery(payload.query);
                    if (payload.input) return extractCleanQuery(payload.input);
                    if (payload.q) return extractCleanQuery(payload.q);

                    // 如果都没有，尝试取第一个字符串类型的值
                    const values = Object.values(payload);
                    for (const val of values) {
                      if (typeof val === 'string') {
                        return extractCleanQuery(val);
                      }
                    }
                    // 实在没办法，转字符串兜底
                    return JSON.stringify(payload);
                  }

                  // 情况 B: 它是字符串 (例如 '{"query": "..."}')
                  if (typeof payload === 'string') {
                    // 关键：如果长得像 JSON，尝试 Parse 它！
                    if (payload.trim().startsWith('{') || payload.trim().startsWith('[')) {
                      try {
                        const parsed = JSON.parse(payload);
                        // Parse 成功后，递归调用自己去处理那个对象
                        return extractCleanQuery(parsed);
                      } catch (e) {
                        // Parse 失败，说明它就是纯文本
                        return payload;
                      }
                    }
                    return payload;
                  }
                  return String(payload);
                };

                // 执行提取
                let queryContent = extractCleanQuery(inputPayload);

                // 兜底与截断
                if (!queryContent || queryContent === "{}" || queryContent.includes("input")) {
                  queryContent = "相关信息";
                }

                const displayContent = queryContent.length > 30
                  ? queryContent.slice(0, 30) + "..."
                  : queryContent;

                addStepToLastMessage({
                  id: nanoid(),
                  type: "search",
                  content: `正在搜索: ${displayContent}`,
                  status: "pending"
                });
              }

              // === 3. 工具结束 ===
              else if (data.type === "tool_end") {
                completeLastStep();
              }

              // === 4. 来源列表 ===
              else if (data.type === "sources") {
                setSourcesForLastMessage(data.content);
              }

              // === 5. 深度计划事件 ===
              else if (data.type === "plan_created" || data.type === "plan_update") {
                updateLastMessagePlan(data.content);
              }

              // === 6. Chat ID 更新 ===
              else if (data.type === "chat_id") {
                const newId = data.content;
                if (newId !== currentChatId) {
                  setCurrentChatId(newId);
                  // 刷新左侧列表
                  fetch("/api/history").then(res => res.json()).then(chats => setChats(chats));
                }
              }

            } catch (e) { console.error("解析错误:", e); }
          }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        console.log("请求已中断");
      } else {
        console.error("请求失败:", error);
        updateLastMessage(accumulatedContent + "\n\n❌ 网络请求错误或已中断。"); // 保留已生成内容
      }
    } finally {
      setLoading(false);
      setAbortController(null);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-black text-gray-900 dark:text-gray-100 overflow-hidden">

      <div className="hidden md:flex h-full flex-col">
        <Sidebar />
      </div>

      <main className="flex-1 flex flex-col h-full relative min-w-0">
        <header className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm z-10 shrink-0">
          <h1 className="text-lg font-bold">Mini DeepResearch</h1>
          <div className="hidden md:block">
            <ModeToggle />
          </div>
        </header>

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-4 md:p-6 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-700"
        >
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="text-center mt-32 space-y-4">
                <h2 className="text-2xl font-bold text-gray-700 dark:text-gray-200">
                  你想研究什么？
                </h2>
                <div className="md:hidden flex justify-center">
                  <ModeToggle />
                </div>
                <p className="text-gray-500">
                  支持联网深度搜索、即时数据分析与整合。
                </p>
              </div>
            )}

            {messages.map((msg, index) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                onRegenerate={
                  (index === messages.length - 1 && msg.role === "ai")
                    ? handleRegenerate
                    : undefined
                }
              />
            ))}
            <div className="h-4" />
          </div>
        </div>

        {/* 👇 M10: 底部悬浮分享栏 */}
        <ShareBottomBar />

        <div className="p-4 bg-white dark:bg-gray-900 border-t dark:border-gray-800 shrink-0">
          <div className="max-w-3xl mx-auto flex gap-3">
            <input
              type="file"
              id="kb-upload"
              accept=".pdf,.txt,.md,.docx"
              className="hidden" // Tailwind 隐藏样式
              onChange={handleFileUpload}
            />
            <label
              htmlFor="kb-upload"
              className="flex items-center justify-center px-4 py-3.5 bg-gray-100 dark:bg-gray-800 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors cursor-pointer shadow-sm"
              title="上传本地知识库文档"
            >
              📎
            </label>
            <input
              type="text"
              className="flex-1 p-3.5 bg-gray-100 dark:bg-gray-800 border-0 rounded-xl focus:ring-2 focus:ring-purple-500 focus:outline-none transition-all"
              placeholder={researchMode === "deep" ? "开启深度研究..." : "输入问题..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              disabled={isLoading}
            />

            {isLoading ? (
              <button
                onClick={handleStop}
                className="px-6 py-3.5 bg-red-500 text-white rounded-xl hover:bg-red-600 font-medium transition-colors shadow-lg shadow-red-500/20 flex items-center gap-2"
              >
                <StopCircle className="w-5 h-5" />
                停止
              </button>
            ) : (
              <button
                onClick={() => handleSend()}
                disabled={!input.trim()}
                className={`px-6 py-3.5 text-white rounded-xl font-medium transition-colors shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${researchMode === "deep"
                  ? "bg-purple-600 hover:bg-purple-700 shadow-purple-600/20"
                  : "bg-blue-600 hover:bg-blue-700 shadow-blue-600/20"
                  }`}
              >
                {researchMode === "deep" ? "深度研究" : "发送"}
              </button>
            )}
          </div>
          <p className="text-center text-xs text-gray-400 mt-3">
            Powered by LangGraph & Tavily & Qwen
          </p>
        </div>
      </main>
    </div>
  );
}