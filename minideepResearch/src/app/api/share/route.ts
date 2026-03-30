import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { nanoid } from "nanoid";

export async function POST(req: NextRequest) {
  try {
    const { originalChatId, selectedMessageIds } = await req.json();

    if (!selectedMessageIds || selectedMessageIds.length === 0) {
      return NextResponse.json({ error: "未选择任何消息" }, { status: 400 });
    }

    // 1. 查询完整的消息数据 (确保包含 plan, sources 等)
    // 我们从数据库重新查一遍，以防前端数据不完整
    const messages = await prisma.message.findMany({
      where: {
        id: { in: selectedMessageIds },
        chatId: originalChatId // 安全校验：确保消息属于该会话
      },
      orderBy: { createdAt: 'asc' } // 保持时间顺序
    });

    if (messages.length === 0) {
      return NextResponse.json({ error: "消息不存在" }, { status: 404 });
    }

    // 2. 生成标题 (取第一条 User 消息的前 30 字)
    const firstUserMsg = messages.find(m => m.role === 'user');
    const title = firstUserMsg ? firstUserMsg.content.slice(0, 30) : "未命名对话";

    // 3. 生成短码 ID
    const shareId = nanoid(10); // 例如: V1StGXR8_Z

    // 4. 存入快照表
    await prisma.sharedChat.create({
      data: {
        id: shareId,
        title,
        snapshot: JSON.stringify(messages), // 序列化存入
        originalChatId
      }
    });

    // 5. 返回链接
    const origin = req.headers.get("origin") || "";
    const shareUrl = `${origin}/share/${shareId}`;

    return NextResponse.json({ shareUrl, shareId });

  } catch (error: any) {
    console.error("Share Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}