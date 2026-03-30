import { graph } from "../src/agents/graph";
import { HumanMessage } from "@langchain/core/messages";
import * as dotenv from "dotenv";

// 加载环境变量
dotenv.config();

async function main() {
  console.log("🤖 Agent 启动中...");

  // 测试问题：必须是一个需要联网才能回答的问题，以验证 Search 功能
  const query = "OpenAI 在 2024 年 12 月发布了什么新模型？或者是 Sora 的最新进展？";
  console.log(`User: ${query}\n`);

  const inputs = {
    messages: [new HumanMessage(query)],
  };

  // 运行图
  // streamMode="values" 表示每当状态更新时，就把最新的消息吐出来
  const stream = await graph.stream(inputs, {
    streamMode: "values",
  });

  for await (const chunk of stream) {
    const lastMessage = chunk.messages[chunk.messages.length - 1];

    console.log("--------------------------------------------------");
    console.log(`[节点角色]: ${lastMessage.getType()}`); // user | ai | tool

    // 如果是 AI 的回复
    if (lastMessage.content) {
      console.log(`[内容]: ${lastMessage.content}`);
    }

    // 如果是工具调用请求
    if ("tool_calls" in lastMessage && lastMessage.tool_calls?.length > 0) {
      console.log(`[正在调用工具]: ${JSON.stringify(lastMessage.tool_calls, null, 2)}`);
    }
  }

  console.log("\n✅ 测试结束");
}

main().catch(console.error);