import { tool } from "@langchain/core/tools";
import { TavilySearchAPIRetriever } from "@langchain/community/retrievers/tavily_search_api";  // 用于从 Tavily 搜索 API 中检索文档
import { z } from "zod";  // 用于定义工具的输入参数的验证模式

// 自定义一个搜索工具
export const searchWebTool = tool(
  async ({ query }: { query: string }) => {
    // 1. 初始化检索器
    const retriever = new TavilySearchAPIRetriever({
      // 这里的 apiKey 会自动读取 process.env.TAVILY_API_KEY
      k: 3,  // k: 3 表示搜索 3 条结果
    });

    console.log(`🔍 正在执行搜索: "${query}" ...`);

    // 2. 执行搜索
    const docs = await retriever.invoke(query);  // 等待异步检索完成

    // 3. 格式化结果 (这是参考项目的精髓)
    // 预处理：把原始的 Document 对象转换成 LLM 易读的字符串。每个文档用 [结果 x] 开头，包含标题、来源、内容摘要，用 --- 分隔
    const formattedResult = docs
      .map((doc, index) => {
        return `[结果 ${index + 1}]
标题: ${doc.metadata.title || "未知标题"}
来源: ${doc.metadata.source || "未知链接"}
内容摘要: ${doc.pageContent}
---`;
      })
      .join("\n");

    return formattedResult;
  },
  {
    name: "search_web", // 给工具起个名字，LLM 会看到
    description: "当需要从互联网获取实时信息、新闻或验证事实时使用此工具。",  // prompt：搜索互联网以获取实时信息、新闻或验证事实
    schema: z.object({
      query: z.string().describe("需要搜索的关键词或问题"),  // 基于Zod对AI的输出进行验证和解析，确保 query 是一个非空字符串，且内容是`需要搜索的关键词或问题`
    }),  // 定义接口，验证返回的 query 参数是否符合要求
  }
);

// 导出工具列表
export const tools = [searchWebTool];