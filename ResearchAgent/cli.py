import asyncio
import sys
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.deep_graph import deep_research_graph, workflow, DB_PATH
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from agents.chat_agent import tools, normal_chat_agent

from core.logger import logger, trace_agent_event, log_user_interaction, log_filepath
from core.prompt_manager import prompt_manager
from rag.memory_store import user_memory

async def main():
    print("-" * 60)
    print("Deep Research Agent - Terminal Debug Console")
    print("Commands:")
    print("   - Type 'quit' or 'exit' to end session and save logs.")
    print("   - Type '/mode normal' for chat mode.")
    print("   - Type '/mode deep' for deep research mode.")
    print(f"Logs will be saved at: {log_filepath}")
    print("-" * 60)
    
    logger.info("Terminal debug session started")
    
    mode = "normal"
    chat_history = []
    # Set sliding window size for short-term memory (10 messages = 5 turns)
    WINDOW_SIZE = 10

    while True:
        try:
            user_input = input(f"\n[{mode.upper()}] User: ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if user_input.strip().lower() in ['quit', 'exit', 'q']:
            print("\nSession ended.")
            logger.info("Terminal debug session ended normally")
            break
            
        if user_input.startswith("/mode"):
            parts = user_input.split()
            if len(parts) > 1 and parts[1] in ["normal", "deep"]:
                mode = parts[1]
                print(f"Mode switched to: {mode}")
                logger.info(f"Mode switch: {mode}")
            else:
                print("Invalid mode. Use '/mode normal' or '/mode deep'")
            continue
            
        if not user_input.strip():
            continue

        log_user_interaction("User", user_input)
        
        # Trigger background memory extraction
        asyncio.create_task(user_memory.async_extract_and_save(user_input))

        # Update short-term memory with sliding window
        chat_history.append(HumanMessage(content=user_input))
        if len(chat_history) > WINDOW_SIZE:
            chat_history = chat_history[-WINDOW_SIZE:]

        print(f"[{mode.upper()}] AI: ", end="", flush=True)
        final_answer = ""
        
        try:
            if mode == "normal":
                # Intent-based routing for normal chat mode
                state = {
                    "messages": chat_history, 
                    "current_route": "", 
                    "search_keywords": []
                }
                
                async for event in normal_chat_agent.astream_events(state, version="v2"):
                    trace_agent_event(event)
                    kind = event["event"]
                    if kind == "on_tool_start":
                        print(f"\n   [Tool call: {event['name']}]...", end="\n   ")
                    elif kind == "on_chat_model_stream":
                        node_name = event.get("metadata", {}).get("langgraph_node", "")
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and isinstance(chunk.content, str):
                            if node_name == "router":
                                # Stream thinking in grey
                                print(f"\033[90m{chunk.content}\033[0m", end="", flush=True)
                            else:
                                print(chunk.content, end="", flush=True)
                                final_answer += chunk.content

            elif mode == "deep":
                thread_id = "human_in_loop_test_01"
                run_config = {"configurable": {"thread_id": thread_id}}
                
                async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory_saver:
                    # Compile graph with persistence and interrupt point after planning
                    persistent_graph = workflow.compile(
                        checkpointer=memory_saver,
                        interrupt_after=["planner"]
                    )
                    
                    current_state = await persistent_graph.aget_state(run_config)
                    
                    if not current_state.next:
                        payload = {"user_query": user_input, "messages": chat_history, "plan": [], "sources": [], "report": "", "loop_count": 0}
                    else:
                        payload = None
                        print("\nRestoring incomplete task...")

                    while True:
                        async for event in persistent_graph.astream_events(payload, config=run_config, version="v2"):
                            trace_agent_event(event)
                            kind = event["event"]
                            node_name = event.get("metadata", {}).get("langgraph_node", "")
                            
                            if kind == "on_chain_end" and node_name == "planner":
                                print("\n   [Plan generated, awaiting approval]...", end="\n   ")
                            elif kind == "on_chain_start" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"]:
                                print(f"\n   [{node_name} executing retrieval]...", end="\n   ")
                            elif kind == "on_chat_model_stream" and node_name == "writer":
                                chunk = event["data"]["chunk"].content
                                if isinstance(chunk, str):
                                    print(chunk, end="", flush=True)
                                    final_answer += chunk

                        paused_state = await persistent_graph.aget_state(run_config)
                        
                        if not paused_state.next:
                            break 
                            
                        loop_count = paused_state.values.get("loop_count", 0)
                        
                        # Automation: skip manual approval for subsequent research iterations
                        if loop_count > 0:
                            print(f"\nReviewer iteration {loop_count}: resume execution.")
                            payload = None
                            continue
                            
                        # Request manual approval for the initial plan
                        print("\n" + "-" * 60)
                        print("Outline Approval Required. Proposed plan:")
                        plans = paused_state.values.get("plan", [])
                        for i, p in enumerate(plans):
                            print(f"   {i+1}. {p.get('title')}")
                        print("-" * 60)
                        
                        approval = input("\nAction (Press Enter to approve, or type 'quit' to cancel): ")
                        
                        if approval.lower() in ['quit', 'exit', 'q']:
                            print("\nTask cancelled.")
                            break
                            
                        print("\nApproval received. Resuming specialist nodes...")
                        payload = None
                            
        except Exception as e:
            print(f"\nExecution error: {str(e)}")
            logger.error(f"Execution error: {str(e)}")
            
        print() 
        
        # Store AI response in sliding window
        if final_answer:
            chat_history.append(AIMessage(content=final_answer))
            if len(chat_history) > WINDOW_SIZE:
                chat_history = chat_history[-WINDOW_SIZE:]
                
        log_user_interaction("AI", final_answer)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())