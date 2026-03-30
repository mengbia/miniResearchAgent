import "dotenv/config";

async function verify() {
  const apiKey = process.env.OPENAI_QWEN_API_KEY;
  console.log("正在测试 Key:", apiKey?.slice(0, 5) + "..." + apiKey?.slice(-3));

  try {
    const response = await fetch("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "qwen-plus",
        messages: [{ role: "user", content: "如果你能看到这句话，请回复OK" }]
      })
    });

    const data = await response.json();

    if (!response.ok) {
      console.error("\n❌ 阿里云拒绝了请求！");
      console.error("状态码:", response.status);
      console.error("错误信息:", JSON.stringify(data, null, 2));
      console.log("\n💡 建议：请登录阿里云百炼控制台，创建一个新的 API Key 并替换到 .env 文件中。");
    } else {
      console.log("\n✅ Key 有效！阿里云回复:", data.choices[0].message.content);
      console.log("既然这里能通，说明是项目代码里的配置有细微差别，请告诉我，我来调整代码。");
    }
  } catch (e) {
    console.error("网络请求失败:", e);
  }
}

verify();