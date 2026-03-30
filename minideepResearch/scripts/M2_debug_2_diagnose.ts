// scripts/M2_debug_2_diagnose.ts
import "dotenv/config";
import fs from 'fs';
import path from 'path';

console.log("🔍 === 深度诊断开始 ===\n");

// 1. 检查 .env 文件物理状态
const envPath = path.resolve(process.cwd(), '.env');
if (fs.existsSync(envPath)) {
    console.log("✅ .env 文件存在于:", envPath);
    const content = fs.readFileSync(envPath, 'utf-8'); // 尝试用 UTF-8 读取
    console.log("📄 文件内容预览 (前50字符):", JSON.stringify(content.substring(0, 50)));

    // 检查是否包含特殊字符
    if (content.includes('\uFFFD')) {
        console.error("❌ 警告：检测到乱码，文件编码可能不是 UTF-8！请另存为 UTF-8 格式。");
    }
} else {
    console.error("❌ 严重错误：找不到 .env 文件！当前目录是:", process.cwd());
}

console.log("\n--------------------------------\n");

// 2. 检查环境变量读取结果
const qwenKey = process.env.OPENAI_QWEN_API_KEY;
const standardKey = process.env.OPENAI_API_KEY;

console.log("🔑 OPENAI_QWEN_API_KEY:");
if (qwenKey) {
    console.log(`   状态: ✅ 已读取`);
    console.log(`   长度: ${qwenKey.length}`);
    console.log(`   前缀: ${qwenKey.substring(0, 3)}`);
    console.log(`   后缀: ${qwenKey.substring(qwenKey.length - 3)}`);
    if (qwenKey.startsWith('"') || qwenKey.trim() !== qwenKey) {
        console.log("   ⚠️ 警告：Key 包含引号或空格，请删除 .env 中的多余字符！");
    }
} else {
    console.log("   状态: ❌ 未定义 (Undefined)");
}

console.log("\n--------------------------------\n");

console.log("🌐 OPENAI_QWEN_BASE_URL:", process.env.OPENAI_QWEN_BASE_URL || "未定义");