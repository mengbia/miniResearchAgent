import asyncio
import sys
from langchain_core.messages import HumanMessage

# 导入业务大模型
from agents.chat_agent import normal_chat_agent
from agents.deep_graph import deep_research_graph

# 🌟 引入刚刚写好的独立日志模块
from core.logger import logger, trace_agent_event, log_user_interaction, log_filepath

async def main():
    print("="*60)
    print(" 🛠️  Deep Research Agent - 终端调试控制台")
    print(" 指令：")
    print("   - 输入 'quit' 或 'exit' 结束对话并保存日志。")
    print("   - 输入 '/mode normal' 切换为闲聊(工具)模式。")
    print("   - 输入 '/mode deep' 切换为深度研究模式。")
    print(f" 📂 本次调试日志将实时保存在: {log_filepath}")
    print("="*60)
    
    logger.info("=== 终端调试会话开始 ===")
    
    mode = "normal"
    chat_history = []

    while True:
        try:
            # 1. 获取终端输入
            user_input = input(f"\n[{mode.upper()}] 👤 你: ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if user_input.strip().lower() in ['quit', 'exit', 'q']:
            print("\n👋 调试结束，日志已落盘！")
            logger.info("=== 终端调试会话正常结束 ===")
            break
            
        if user_input.startswith("/mode"):
            parts = user_input.split()
            if len(parts) > 1 and parts[1] in ["normal", "deep"]:
                mode = parts[1]
                print(f"🔄 模式已切换至: {mode}")
                logger.info(f"系统操作: 切换模式至 {mode}")
            else:
                print("⚠️ 无效模式，请使用 '/mode normal' 或 '/mode deep'")
            continue
            
        if not user_input.strip():
            continue

        # 记录用户输入
        log_user_interaction("User", user_input)
        chat_history.append(HumanMessage(content=user_input))
        
        print(f"[{mode.upper()}] 🤖 AI: ", end="", flush=True)
        
        final_answer = ""
        try:
            # ==========================================
            # 分支 A：普通闲聊模式 (调用 normal_chat_agent)
            # ==========================================
            if mode == "normal":
                state = {"messages": chat_history}
                async for event in normal_chat_agent.astream_events(state, version="v2"):
                    # 🌟 将事件丢给解耦的 logger 进行追踪
                    trace_agent_event(event)
                    
                    kind = event["event"]
                    if kind == "on_tool_start":
                        print(f"\n   [🛠️ 正在调用工具: {event['name']}]...", end="\n   ")
                    elif kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"].content
                        if isinstance(chunk, str):
                            print(chunk, end="", flush=True)
                            final_answer += chunk

            # ==========================================
            # 分支 B：深度研究模式 (调用 deep_research_graph)
            # ==========================================
            elif mode == "deep":
                state = {"user_query": user_input, "messages": [], "plan": [], "sources": [], "report": ""}
                async for event in deep_research_graph.astream_events(state, version="v2"):
                    # 🌟 同样丢给解耦的 logger 进行追踪
                    trace_agent_event(event)
                    
                    kind = event["event"]
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    
                    if kind == "on_chain_end" and node_name == "planner":
                        print("\n   [📋 计划已生成，开始执行]...", end="\n   ")
                    elif kind == "on_chain_start" and node_name == "worker":
                        print("\n   [🌐 正在全网与知识库混合检索]...", end="\n   ")
                    elif kind == "on_chat_model_stream" and node_name == "writer":
                        chunk = event["data"]["chunk"].content
                        if isinstance(chunk, str):
                            print(chunk, end="", flush=True)
                            final_answer += chunk
                            
        except Exception as e:
            print(f"\n❌ 终端执行报错: {str(e)}")
            logger.error(f"终端执行报错: {str(e)}")
            
        print() # 换行
        
        # 记录 AI 的最终完整回复
        log_user_interaction("AI", final_answer)

if __name__ == "__main__":
    # 解决 Windows 下 Asyncio 可能会报错的问题
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())