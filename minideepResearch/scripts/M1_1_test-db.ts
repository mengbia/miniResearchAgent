// scripts/M1_1_test-db.ts
import { PrismaClient } from '@prisma/client';

// 初始化客户端
const prisma = new PrismaClient();

async function main() {
  console.log("🔄 开始测试数据库连接...");

  // 1. 创建一个新的聊天会话
  const newChat = await prisma.chat.create({
    data: {
      title: "Deep Research 测试会话",
      messages: {
        create: [
          { role: "user", content: "你好，请帮我分析英伟达财报。" },
          { role: "assistant", content: "正在规划任务，请稍候..." }
        ]
      }
    },
    include: {
      messages: true // 让返回值包含消息详情
    }
  });

  console.log("✅ 写入成功！创建的会话数据如下：");
  console.dir(newChat, { depth: null });

  // 2. 尝试读取
  const count = await prisma.chat.count();
  console.log(`📊 当前数据库中共有 ${count} 个会话。`);
}

main()
  .catch((e) => {
    console.error("❌ 数据库连接失败:", e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });