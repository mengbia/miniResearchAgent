import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

def get_llm():
    """
    获取全局大语言模型。
    自带高可用机制：当主模型崩溃或限流时，无缝切换至备用模型。
    """
    # 1. 实例化主模型
    main_llm = ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
        model=os.getenv("MAIN_MODEL_NAME", "qwen-max"), 
        temperature=0.7,
        max_retries=1,      # 主模型最多重试 1 次，不行就赶紧切备胎，避免用户等太久
        request_timeout=30  # 设置合理的超时时间，防止 API 死锁
    )

    # 2. 读取备用模型配置
    backup_api_key = os.getenv("BACKUP_API_KEY")
    backup_api_base = os.getenv("BACKUP_API_BASE")
    backup_model_name = os.getenv("BACKUP_MODEL_NAME", "deepseek-chat")

    # 3. 组装高可用大模型底座
    if backup_api_key and backup_api_base:
        backup_llm = ChatOpenAI(
            api_key=backup_api_key,
            base_url=backup_api_base,
            model=backup_model_name,
            temperature=0.7, # 调节大模型生成答案是更具创造性还是更保守，数值越低越保守
            max_retries=2, # 备用模型可以多重试几次
            request_timeout=30
        )
        
        # 🌟 核心魔法：把备用模型绑定到主模型上
        # 一旦 main_llm 报错（如 500 服务器错误、429 并发超限、超时），
        # LangChain 会立刻静默启动 backup_llm 接管任务。
        fallback_llm = main_llm.with_fallbacks([backup_llm])
        
        return fallback_llm
    
    # 如果没配备用密钥，就直接返回主模型
    return main_llm


#===============测试大模型是否连通===============
if __name__ == "__main__":
    llm = get_llm()
    print("正在测试大模型...")
    response = llm.invoke("用一句话形容一下天空。")
    print("大模型回复:", response.content)