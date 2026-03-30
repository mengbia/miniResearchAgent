// src/lib/llm.ts
import { ChatOpenAI } from "@langchain/openai";

interface LLMOptions {
  temperature?: number;
  modelName?: string;
}

export const createLLM = (options: LLMOptions = {}) => {
  // 1. 获取配置 (优先级：参数 > 环境变量 > 默认值)

  // 兼容多种 Key 的命名方式 (Qwen 专用 Key -> OpenAI 兼容 Key)
  const apiKey =
    process.env.DASHSCOPE_API_KEY ||
    process.env.OPENAI_QWEN_API_KEY ||
    process.env.OPENAI_API_KEY;

  const baseURL =
    process.env.OPENAI_QWEN_BASE_URL ||
    process.env.OPENAI_API_BASE ||
    "https://dashscope.aliyuncs.com/compatible-mode/v1"; // 默认 Qwen 地址

  const modelName =
    options.modelName ||
    process.env.OPENAI_MODEL_NAME ||
    "qwen-plus";

  const temperature = options.temperature ?? 0; // 默认为 0

  if (!apiKey) {
    throw new Error("❌ 未找到 API Key，请检查 .env 文件 (需配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY)");
  }

  // 🔍 调试日志 (只在开发环境或第一次调用时有用，避免刷屏)
  // console.log(`🔧 初始化 LLM [${modelName}] Temp: ${temperature}`);

  // 2. 初始化 ChatOpenAI
  return new ChatOpenAI({
    modelName: modelName,
    temperature: temperature,
    streaming: true,

    // 关键：强制配置底层 Client
    configuration: {
      apiKey: apiKey,
      baseURL: baseURL,
    },
    // 双重保险
    openAIApiKey: apiKey,
  });
};