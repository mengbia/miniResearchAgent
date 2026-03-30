import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const chats = await prisma.chat.findMany({
    orderBy: { createdAt: "desc" }, // 按时间倒序
  });
  return NextResponse.json(chats);
}