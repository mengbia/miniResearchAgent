import { NextRequest, NextResponse } from "next/server";
import { HumanMessage } from "@langchain/core/messages";
import { graph as normalGraph } from "@/agents/graph";  // 普通图
import { deepGraph } from "@/agents/deepGraph";  // 深度图
import { prisma } from "@/lib/prisma";  // 数据库客户端

export const runtime = "nodejs";

/**
 * POST 路由处理函数
 * @param req - Next.js 请求对象
 * @returns Next.js 响应对象
 */
export async function POST(req: NextRequest) {
  try {
    // 1. 解析请求参数
    /**
     * 请求参数
     * @typedef {Object} RequestParams
     * @property {string} message - 用户输入的消息
     * @property {string} [chatId] - 可选的聊天 ID
     * @property {boolean} [isRegenerate=false] - 是否重新生成
     * @property {"normal"|"deep"} [mode="normal"] - 模式选择
     */
    const { message, chatId, isRegenerate, mode = "normal" } = await req.json();

    // 获取中断信号 (支持停止生成)
    const { signal } = req;

    // 2. 数据库会话管理
    /**
     * 数据库中，chatId对应一个聊天会话，每个会话表对应多个消息表
     * 当前端不传入 chatId 时，则是新会话，则创建新会话，否则复用已有会话，实现上下文连贯
     */
    let currentChatId = chatId;
    if (!currentChatId) {
      const newChat = await prisma.chat.create({
        data: { title: message.slice(0, 30) },
      });
      currentChatId = newChat.id;
    }

    // 3. 处理重新生成逻辑 (防止数据重复)
    /**
     * 如果 isRegenerate 为 true，则删除当前会话中最后一条 AI 消息，防止重复消息、防止脏数据污染上下文
     */
    if (isRegenerate) {
      // 找到最后一条 AI 消息并删除
      const lastMsg = await prisma.message.findFirst({
        where: { chatId: currentChatId },
        orderBy: { createdAt: 'desc' }
      });

      if (lastMsg && lastMsg.role === 'ai') {
        await prisma.message.delete({ where: { id: lastMsg.id } });
      }
      // 注意：重新生成时不创建新的 User Message
    } else {
      // 普通发送：创建 User Message
      await prisma.message.create({
        data: { content: message, role: "user", chatId: currentChatId },
      });
    }

    // 4. 开启流式响应
    /**
     * 当前场景：后端持续输出、前端只读——创建 ReadableStream 用于服务器发送事件 (SSE)，这是实现“打字机”和“实时状态更新”效果的关键
     * 
     */
    const stream = new ReadableStream({
      async start(controller) {
        const encoder = new TextEncoder();

        // === 状态变量 (用于最终存库) ===
        let fullAiResponse = "";
        let collectedSources: any[] = [];
        let collectedPlan: any = null; // 🌟 修复: 暂存 Plan 数据

        const sendData = (type: string, content: any) => {
          const json = JSON.stringify({ type, content });
          controller.enqueue(encoder.encode(`data: ${json}\n\n`));
        };

        sendData("chat_id", currentChatId);

        try {
          // 🌟 核心分流逻辑: Deep vs Normal
          let eventStream;

          if (mode === "deep") {
            // 深度模式: 传入 user_query 和 signal
            eventStream = await deepGraph.streamEvents(
              { user_query: message },
              { version: "v2", signal }
            );
          } else {
            // 普通模式: 传入 messages 和 signal
            eventStream = await normalGraph.streamEvents(
              { messages: [new HumanMessage(message)] },
              { version: "v2", signal }
            );
          }

          // === 事件循环 ===
          for await (const event of eventStream) {

            // A. 工具开始
            if (event.event === "on_tool_start" && event.name === "search_web") {
              sendData("tool_start", { tool: event.name, input: event.data.input });
            }

            // B. 工具结束 & 来源解析
            if (event.event === "on_tool_end" && event.name === "search_web") {
              const rawOutput = event.data.output;
              sendData("tool_end", { tool: event.name, output: "搜索完成" });

              try {
                let cleanContent = "";

                // --- 1. 强力拆包 JSON (解决 LangChain 套壳问题) ---
                if (typeof rawOutput === 'string') {
                    try {
                        if (rawOutput.trim().startsWith('{') || rawOutput.trim().startsWith('[')) {
                            const parsed = JSON.parse(rawOutput);
                            if (parsed.kwargs && parsed.kwargs.content) cleanContent = parsed.kwargs.content;
                            else if (parsed.content) cleanContent = parsed.content;
                            else cleanContent = rawOutput;
                        } else {
                            cleanContent = rawOutput;
                        }
                    } catch (e) { cleanContent = rawOutput; }
                } else if (typeof rawOutput === 'object' && rawOutput !== null) {
                    if (rawOutput.kwargs && rawOutput.kwargs.content) cleanContent = rawOutput.kwargs.content;
                    else if (rawOutput.content) cleanContent = rawOutput.content;
                    else cleanContent = JSON.stringify(rawOutput);
                }

                // --- 2. 分块提取来源 URL ---
                const sources: { title: string; url: string }[] = [];
                const chunks = cleanContent.split(/\[结果\s*\d+\]/);

                for (const chunk of chunks) {
                    if (!chunk.trim()) continue;
                    // 兼容 \n 和 \\n
                    const titleMatch = chunk.match(/(?:标题|Title):\s*(.+?)(?:\n|\\n|$)/);
                    const urlMatch = chunk.match(/(?:来源|Source|Link):\s*(https?:\/\/[^\s\n\\]+)/);

                    if (titleMatch && urlMatch) {
                        const title = titleMatch[1].trim();
                        const url = urlMatch[1].trim();
                        if (title && url && !url.includes("内容摘要")) {
                            sources.push({ title, url });
                        }
                    }
                }

                if (sources.length > 0) {
                  collectedSources = [...collectedSources, ...sources];
                  sendData("sources", sources);
                }
              } catch (e) {
                console.error("❌ 解析来源失败:", e);
              }
            }

            // C. [深度模式] 计划生成 (Planner)
            if (event.event === "on_chain_end" && event.name === "planner") {
               if (event.data.output && event.data.output.plan) {
                 sendData("plan_created", event.data.output.plan);
                 collectedPlan = event.data.output.plan; // 🌟 抓取 Plan
               }
            }

            // D. [深度模式] 计划更新 (Worker)
            if (event.event === "on_chain_end" && event.name === "worker") {
               if (event.data.output && event.data.output.plan) {
                 sendData("plan_update", event.data.output.plan);
                 collectedPlan = event.data.output.plan; // 🌟 更新 Plan
               }
            }

            // E. 文本生成 (Writer / ChatModel)
            if (event.event === "on_chat_model_stream" && event.data.chunk.content) {
              // 🌟 核心修复: 过滤掉非 Writer 节点的输出
              // 防止 Planner 的 JSON 或 Worker 的中间思考泄露到正文中
              if (mode === "deep" && event.metadata?.langgraph_node !== "writer") {
                continue;
              }

              const text = event.data.chunk.content;
              fullAiResponse += text;
              sendData("text", text);
            }
          }

          // 5. 流程结束，保存数据到数据库
          if (fullAiResponse) {
             // 来源去重
             const uniqueSources = Array.from(new Map(collectedSources.map(item => [item.url, item])).values());

             await prisma.message.create({
               data: {
                 content: fullAiResponse,
                 role: "ai",
                 chatId: currentChatId,

                 // 🌟 存入来源 (JSON)
                 sources: uniqueSources.length > 0 ? uniqueSources : undefined,

                 // 🌟 存入 Plan (JSON) - 修复刷新后任务列表消失的问题
                 plan: collectedPlan ? collectedPlan : undefined,
               }
             });
          }

        } catch (e: any) {
          // 处理用户中断
          if (e.name === "AbortError" || signal.aborted) {
            console.log("🛑 请求已中断，停止生成。");
            return;
          }
          console.error("Graph Error:", e);
          sendData("error", "生成过程中出现错误");
        } finally {
          controller.close();
        }
      },
    });

    return new NextResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error: any) {
    console.error("API Error:", error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}