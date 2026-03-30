import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

// 定义 params 的类型为 Promise
type Props = {
  params: Promise<{ id: string }>;
};

export async function GET(req: NextRequest, { params }: Props) {
  // 🌟 修复关键点：先 await params，再解构获取 id
  const { id } = await params;

  const messages = await prisma.message.findMany({
    where: { chatId: id },
    orderBy: { createdAt: "asc" },
  });

  return NextResponse.json(messages);
}

export async function DELETE(req: NextRequest, { params }: Props) {
  // 🌟 修复关键点：先 await params
  const { id } = await params;

  await prisma.chat.delete({ where: { id } });
  return NextResponse.json({ success: true });
}