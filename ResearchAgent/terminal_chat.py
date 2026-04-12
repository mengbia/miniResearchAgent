import asyncio
import sys
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver # 🌟 导入异步持久化组件

# 导入图谱与基础组件
from agents.deep_graph import deep_research_graph, workflow, DB_PATH # 🌟 导入 workflow 和 DB_PATH
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from agents.chat_agent import tools  # 🌟 导入工具箱

# 引入基建模块（日志、提示词、记忆库）
from core.logger import logger, trace_agent_event, log_user_interaction, log_filepath
from core.prompt_manager import prompt_manager
from rag.memory_store import user_memory  # 🌟 引入记忆引擎

async def main():
    print("="*60)
    print(" 🛠️  Deep Research Agent - 终端调试控制台 (混合记忆增强版)")
    print(" 指令：")
    print("   - 输入 'quit' 或 'exit' 结束对话并保存日志。")
    print("   - 输入 '/mode normal' 切换为闲聊(工具)模式。")
    print("   - 输入 '/mode deep' 切换为深度研究模式。")
    print(f" 📂 本次调试日志将实时保存在: {log_filepath}")
    print("="*60)
    
    logger.info("=== 终端调试会话开始 ===")
    
    mode = "normal"
    chat_history = []
    WINDOW_SIZE = 10  # 🌟 设定短期记忆滑动窗口大小 (保留最近10条消息 = 5轮对话)

    while True:
        try:
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

        log_user_interaction("User", user_input)
        
        # ==========================================
        # 🌟 1. 长期记忆 (LTM)：触发后台静默提取
        # ==========================================
        # 使用原生 asyncio 创建后台任务，不阻塞当前主线程的响应速度
        asyncio.create_task(user_memory.async_extract_and_save(user_input))

        # ==========================================
        # 🌟 2. 短期记忆 (STM)：压入历史记录并执行滑动窗口截断
        # ==========================================
        chat_history.append(HumanMessage(content=user_input))
        if len(chat_history) > WINDOW_SIZE:
            chat_history = chat_history[-WINDOW_SIZE:]

        print(f"[{mode.upper()}] 🤖 AI: ", end="", flush=True)
        final_answer = ""
        
        try:
            if mode == "normal":
                # ==========================================
                # 🌟 3. 动态注入长期记忆并构建 Agent
                # ==========================================
                relevant_memories = user_memory.retrieve_memory(user_input)
                base_system_prompt = prompt_manager.get("chat_agent", "system_prompt")
                
                # 确保 JSON 中的 prompts 里有 {long_term_memory} 占位符
                injected_prompt = base_system_prompt.format(long_term_memory=relevant_memories)

                # 实时组装拥有最新记忆的聊天智能体
                memory_aware_agent = create_react_agent(
                    get_llm(),
                    tools=tools,
                    prompt=injected_prompt
                )

                state = {"messages": chat_history}
                
                async for event in memory_aware_agent.astream_events(state, version="v2"):
                    trace_agent_event(event)
                    kind = event["event"]
                    if kind == "on_tool_start":
                        print(f"\n   [🛠️ 正在调用工具: {event['name']}]...", end="\n   ")
                    elif kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"].content
                        if isinstance(chunk, str):
                            print(chunk, end="", flush=True)
                            final_answer += chunk

            elif mode == "deep":
                # 设定固定的任务 ID，用于容灾和断点续传
                thread_id = "human_in_loop_test_01"
                run_config = {"configurable": {"thread_id": thread_id}}
                
                async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory_saver:
                    # 🌟 在图谱编译时，强制要求在 "planner" 节点执行完毕后【挂起】
                    persistent_graph = workflow.compile(
                        checkpointer=memory_saver,
                        interrupt_after=["planner"]
                    )
                    
                    # 获取当前数据库中该任务的状态
                    current_state = await persistent_graph.aget_state(run_config)
                    
                    # 判定启动方式：准备第一次抛给图谱的载荷 (payload)
                    if not current_state.next:
                        payload = {"user_query": user_input, "messages": chat_history, "plan": [], "sources": [], "report": "", "loop_count": 0}
                    else:
                        payload = None
                        print("\n[系统提示] 侦测到未完成的中断任务，正在恢复...")

                    # ==========================================
                    # 🌟 进阶优化：引入内层状态机监听循环
                    # ==========================================
                    while True:
                        # 🏃 执行图谱（不论是初次启动 payload，还是中断恢复 None，都在这里跑）
                        async for event in persistent_graph.astream_events(payload, config=run_config, version="v2"):
                            trace_agent_event(event)
                            kind = event["event"]
                            node_name = event.get("metadata", {}).get("langgraph_node", "")
                            
                            if kind == "on_chain_end" and node_name == "planner":
                                print("\n   [📋 计划已生成，等待处理]...", end="\n   ")
                            elif kind == "on_chain_start" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"]:
                                print(f"\n   [🌐 {node_name} 正在火速出动检索]...", end="\n   ")
                            elif kind == "on_chat_model_stream" and node_name == "writer":
                                chunk = event["data"]["chunk"].content
                                if isinstance(chunk, str):
                                    print(chunk, end="", flush=True)
                                    final_answer += chunk

                        # 当 async for 结束时，说明图谱要么彻底跑完了，要么撞到了 interrupt_after 断点
                        # 再次获取最新状态
                        paused_state = await persistent_graph.aget_state(run_config)
                        
                        # 1. 彻底结束判定
                        if not paused_state.next:
                            # 如果 next 为空，说明整个研究大一统跑完了（走到了 END）
                            break 
                            
                        # 2. 触发了断点拦截
                        loop_count = paused_state.values.get("loop_count", 0)
                        
                        # 🌟 进阶自动化：如果这不是第一轮，说明是审查员打回的，直接静默放行
                        if loop_count > 0:
                            print(f"\n🔄 审查员第 {loop_count} 次打回重做，系统已自动放行新计划！")
                            payload = None  # 告诉图谱下一轮是 resume
                            continue        # 💡 直接进入下一轮 while，连着跑！
                            
                        # 🌟 初次运行，乖乖请求人类大纲审批
                        print("\n\n" + "="*60)
                        print(" ✋ [大纲审批] 任务已强制暂停！规划师已提交以下检索方案：")
                        plans = paused_state.values.get("plan", [])
                        for i, p in enumerate(plans):
                            print(f"   {i+1}. {p.get('title')}")
                        print("="*60)
                        
                        approval = input("\n👉 审批意见 (直接按【回车键】批准执行，或输入 'quit' 放弃): ")
                        
                        if approval.lower() in ['quit', 'exit', 'q']:
                            print("\n🛑 任务已手动取消。")
                            break # 彻底跳出内部循环
                            
                        print("\n▶️ 收到最高指令：批准执行！正在唤醒特种部队...")
                        payload = None # 告诉图谱下一轮是 resume，进入下一轮 while 循环顶部
                            
        except Exception as e:
            print(f"\n❌ 终端执行报错: {str(e)}")
            logger.error(f"终端执行报错: {str(e)}")
            
        print() 
        
        # 🌟 4. 将 AI 的回复也存入短期记忆滑动窗口
        if final_answer:
            chat_history.append(AIMessage(content=final_answer))
            if len(chat_history) > WINDOW_SIZE:
                chat_history = chat_history[-WINDOW_SIZE:]
                
        log_user_interaction("AI", final_answer)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())