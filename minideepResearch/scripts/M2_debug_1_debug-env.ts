// scripts/M2_debug_1_debug-env.ts
import "dotenv/config";

console.log("当前目录:", process.cwd());
console.log("环境变量检查:");
console.log("OPENAI_QWEN_API_KEY:", process.env.OPENAI_QWEN_API_KEY ? "✅ 存在 (长度: " + process.env.OPENAI_QWEN_API_KEY.length + ")" : "❌ 未找到");
console.log("TAVILY_API_KEY:", process.env.TAVILY_API_KEY ? "✅ 存在" : "❌ 未找到");