import { prisma } from "@/lib/prisma";
import ChatMessage from "@/components/Chat/ChatMessage";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Home } from "lucide-react";
import ModeToggle from "@/components/Sidebar/ModeToggle";

// Next.js 15: params 是 Promise
interface Props {
  params: Promise<{ id: string }>;
}

export default async function SharePage({ params }: Props) {
  // 1. 等待 params 解析
  const { id } = await params;

  // 2. 获取数据库记录
  const sharedChat = await prisma.sharedChat.findUnique({
    where: { id },
  });

  if (!sharedChat) {
    return notFound();
  }

  // 3. 🌟 修复 JSON 解析逻辑
  let messages: any = sharedChat.snapshot;

  // 如果 Prisma 返回的是字符串（因为我们存的时候 stringify 了），则手动解析
  if (typeof messages === "string") {
    try {
      messages = JSON.parse(messages);
    } catch (e) {
      console.error("JSON Parse Error:", e);
      messages = [];
    }
  }

  // 二次安全校验：确保最终拿到的是数组，防止 .map 崩溃
  if (!Array.isArray(messages)) {
    messages = [];
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-black text-gray-900 dark:text-gray-100 flex flex-col">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 border-b dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                <Home className="w-5 h-5" />
            </Link>
            <div className="flex flex-col">
                <h1 className="text-sm font-bold text-gray-900 dark:text-gray-100 max-w-[200px] md:max-w-md truncate">
                    {sharedChat.title}
                </h1>
                <span className="text-xs text-gray-500">
                    发布于 {new Date(sharedChat.createdAt).toLocaleDateString()}
                </span>
            </div>
        </div>
        <div className="flex items-center gap-2">
            <a href="/" className="hidden md:inline-flex px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-full transition-colors">
                试用 Mini DeepResearch
            </a>
            {/*<ModeToggle />*/}
        </div>
      </header>

      {/* 消息列表区域 */}
      <main className="flex-1 max-w-3xl w-full mx-auto p-4 md:p-8">
        {messages.map((msg: any) => (
          <ChatMessage
            key={msg.id}
            message={msg}
            isReadOnly={true}
          />
        ))}

        <div className="h-20" />
      </main>

      {/* 底部推广栏 (移动端) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 p-4 bg-white dark:bg-gray-900 border-t dark:border-gray-800">
         <a href="/" className="block w-full py-3 bg-blue-600 text-white text-center font-bold rounded-xl">
            我也要问 (Try Mini DeepResearch)
         </a>
      </div>
    </div>
  );
}