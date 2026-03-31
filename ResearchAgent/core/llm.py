from langchain_openai import ChatOpenAI
from core.config import LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME

def get_llm():
    """
    获取大语言模型实例。
    这里使用的是兼容 OpenAI 接口格式的调用方式。
    """
    return ChatOpenAI(
        model=LLM_MODEL_NAME,  # 如果你用的千问，可以换成 qwen-max 等；DeepSeek 就填 deepseek-chat
        api_key=LLM_API_KEY,
        base_url=LLM_API_BASE,
        temperature=0.7, # 稍微给一点创造力，适合写报告
        streaming=True   # 开启流式输出底层支持
    )

# 你可以在这下面直接测一下大脑通不通
if __name__ == "__main__":
    llm = get_llm()
    print("正在测试大模型...")
    response = llm.invoke("用一句话形容一下天空。")
    print("大模型回复:", response.content)