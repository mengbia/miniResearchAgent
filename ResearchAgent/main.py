import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from fastapi import FastAPI, BackgroundTasks
from rag.memory_store import user_memory

import os
import shutil
from fastapi import FastAPI, UploadFile, File
from rag.vector_store import local_kb

from agents.deep_graph import deep_research_graph, workflow, DB_PATH
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import uuid 

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from agents.chat_agent import normal_chat_agent
from agents.chat_agent import tools
from core.llm import get_llm
from core.prompt_manager import prompt_manager

import uuid
import re

from core.logger import logger, trace_agent_event, log_user_interaction

app = FastAPI(title="Deep Research Agent Backend")

@app.get("/")
async def root():
    return {"message": "Deep Research Agent backend service is running.", "docs": "/docs"}

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str
    id: str
    model_config = ConfigDict(extra='ignore') 

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: str = "normal"

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # Prevent path traversal vulnerabilities by filtering characters
        safe_original_name = re.sub(r'[^\w\.\-\u4e00-\u9fa5]', '', file.filename)
        if not safe_original_name:
            safe_original_name = "unnamed_document.txt"
            
        safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_original_name}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"\nNew file upload received: {file.filename} -> Saved as {safe_filename}")
        
        await asyncio.to_thread(local_kb.process_and_save_document, file_path)
        
        return {"status": "success", "message": f"File {file.filename} processed successfully. The agent can now reference it."}

    except Exception as e:
        logger.exception(f"File upload failed: {str(e)}")
        return {"status": "error", "message": "文件处理失败，请稍后重试。"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    user_query = request.messages[-1].content
    mode = request.mode
    print(f"\nReceived query: {user_query} | Mode: {mode}")

    history = []
    for msg in request.messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    background_tasks.add_task(user_memory.async_extract_and_save, user_query)

    # Sliding window mechanism to limit context size
    WINDOW_SIZE = 10 
    recent_messages = request.messages[-WINDOW_SIZE:] if len(request.messages) > WINDOW_SIZE else request.messages
    
    log_user_interaction("User", f"[{mode.upper()}] {user_query}")

    llm = get_llm()

    async def agent_stream():
        try:
            if mode == "deep":
                task_id = request.messages[-1].id if (request.messages and request.messages[-1].id) else str(uuid.uuid4())
                run_config = {"configurable": {"thread_id": task_id}}
                latest_report = ""
                writer_buffer = ""
                last_announced_node = ""
                final_values = {}
                stream_final_writer = False
                streamed_text_to_client = False

                async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory_saver:
                    persistent_graph = workflow.compile(checkpointer=memory_saver)
                    
                    current_state = await persistent_graph.aget_state(run_config)
                    
                    if not current_state.next:
                        payload = {"user_query": user_query, "messages": [], "plan": [], "sources": [], "report": "", "loop_count": 0}
                    else:
                        payload = None
                        
                        if user_query.strip().lower() in ['quit', '取消', '放弃', 'q']:
                            yield f"data: {json.dumps({'type': 'text', 'content': 'Task cancelled.'}, ensure_ascii=False)}\n\n"
                            return
                            
                        # 1. 先把字典和 JSON 序列化的部分在外部处理好
                        json_str = json.dumps({'type': 'text', 'content': 'Resuming execution of specialist agents.\n\n'}, ensure_ascii=False)

                        # 2. 然后再把生成的纯字符串塞进 f-string 里
                        yield f"data: {json_str}\n\n"

                    while True:
                        async for event in persistent_graph.astream_events(payload, config=run_config, version="v2"):
                            trace_agent_event(event)
                            kind = event["event"]
                            node_name = event.get("metadata", {}).get("langgraph_node", "")
                            
                            if kind == "on_chain_start" and node_name == "planner" and last_announced_node != "planner":
                                last_announced_node = "planner"
                                event_data = json.dumps({"type": "thinking", "content": "[planner] 正在制定研究计划...\n"}, ensure_ascii=False)
                                yield f"data: {event_data}\n\n"

                            elif kind == "on_chain_end" and node_name == "planner" and isinstance(event["data"].get("output"), dict):
                                plan_data = event["data"]["output"].get("plan", [])
                                if plan_data:
                                    yield f"data: {json.dumps({'type': 'plan_created', 'content': plan_data}, ensure_ascii=False)}\n\n"
                                
                            elif kind == "on_chain_start" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"] and last_announced_node != node_name:
                                last_announced_node = node_name
                                thinking_content = f"[{node_name}] 正在执行检索...\n"
                                event_data = json.dumps({"type": "thinking", "content": thinking_content}, ensure_ascii=False)
                                yield f"data: {event_data}\n\n"
                                
                            elif kind == "on_chain_end" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"] and isinstance(event["data"].get("output"), dict):
                                sources_data = event["data"]["output"].get("sources", [])
                                if sources_data:
                                    yield f"data: {json.dumps({'type': 'sources', 'content': sources_data}, ensure_ascii=False)}\n\n"

                            elif kind == "on_chain_start" and node_name == "filter" and last_announced_node != "filter":
                                last_announced_node = "filter"
                                event_data = json.dumps({"type": "thinking", "content": "[filter] 正在清洗和去重资料...\n"}, ensure_ascii=False)
                                yield f"data: {event_data}\n\n"

                            elif kind == "on_chain_start" and node_name == "writer" and last_announced_node != "writer":
                                last_announced_node = "writer"
                                writer_buffer = ""
                                event_input = event.get("data", {}).get("input")
                                current_loop_count = event_input.get("loop_count", 0) if isinstance(event_input, dict) else 0
                                stream_final_writer = current_loop_count >= 2
                                event_data = json.dumps({"type": "thinking", "content": "[writer] 正在撰写最终报告...\n"}, ensure_ascii=False)
                                yield f"data: {event_data}\n\n"
                                    
                            elif kind == "on_chat_model_stream" and node_name == "writer":
                                chunk = event["data"]["chunk"].content
                                if chunk:
                                    if stream_final_writer:
                                        streamed_text_to_client = True
                                        yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                                    else:
                                        writer_buffer += chunk

                            elif kind == "on_chain_end" and node_name == "writer":
                                output = event["data"].get("output")
                                if isinstance(output, dict):
                                    report = output.get("report", "")
                                    if report:
                                        latest_report = report
                                elif writer_buffer:
                                    latest_report = writer_buffer

                            elif kind == "on_chain_start" and node_name == "reviewer" and last_announced_node != "reviewer":
                                last_announced_node = "reviewer"
                                event_data = json.dumps({"type": "thinking", "content": "[reviewer] 正在评估报告质量...\n"}, ensure_ascii=False)
                                yield f"data: {event_data}\n\n"
                                    
                            elif kind == "on_chat_model_stream" and node_name == "reviewer":
                                chunk = event["data"]["chunk"].content
                                if chunk:
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': chunk}, ensure_ascii=False)}\n\n"

                        paused_state = await persistent_graph.aget_state(run_config)
                        final_values = paused_state.values or {}
                        
                        if not paused_state.next:
                            break
                            
                        loop_count = final_values.get("loop_count", 0)
                        
                        if loop_count > 0:
                            # Automatic continuation after reviewer round
                            notification_text = f'\n[System] 审查官要求第 {loop_count} 轮修改，正在补充检索...\n'
                            # 生成 JSON 字符串
                            json_str = json.dumps({'type': 'thinking', 'content': notification_text}, ensure_ascii=False)
                            # 最后通过 yield 输出，用纯粹的变量替换
                            yield f"data: {json_str}\n\n"
                            payload = None
                            continue
                        else:
                            # Wait for user approval of the initial plan
                            yield "data: " + json.dumps({'type': 'text', 'content': '\n\n---\n**Outline Approval Required**\nTask suspended. Please review the proposed research plan.\n- Reply "continue" or "agree" to proceed.\n- Reply "cancel" to terminate.'}, ensure_ascii=False) + "\n\n"
                            break

                    final_plan = final_values.get("plan", [])
                    if final_plan:
                        completed_plan = []
                        for index, item in enumerate(final_plan):
                            completed_item = dict(item) if isinstance(item, dict) else {"title": str(item)}
                            completed_item.setdefault("id", index + 1)
                            completed_item["status"] = "completed"
                            completed_plan.append(completed_item)
                        yield f"data: {json.dumps({'type': 'plan_update', 'content': completed_plan}, ensure_ascii=False)}\n\n"

                    final_report = final_values.get("report") or latest_report or writer_buffer
                    if final_report and not streamed_text_to_client:
                        for index in range(0, len(final_report), 32):
                            chunk = final_report[index:index + 32]
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                            await asyncio.sleep(0)
                            
            else:
                state = {
                    "messages": history, 
                    "current_route": "", 
                    "search_keywords": []
                }
                
                async for event in normal_chat_agent.astream_events(state, version="v2"):
                    trace_agent_event(event)
                    kind = event["event"]
                    
                    if kind == "on_tool_start":
                        tool_name = event.get("name", "Unknown Tool")
                        yield f"data: {json.dumps({'type': 'tool_start', 'content': {'input': f'Invoking tool: {tool_name}'}}, ensure_ascii=False)}\n\n"
                    
                    elif kind == "on_tool_end":
                        yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
                        
                    elif kind == "on_chat_model_stream":
                        node_name = event.get("metadata", {}).get("langgraph_node", "")
                        chunk = event["data"]["chunk"].content
                        if chunk and isinstance(chunk, str):
                            if node_name == "router":
                                # Stream routing reasoning to a dedicated thinking channel
                                yield f"data: {json.dumps({'type': 'thinking', 'content': chunk}, ensure_ascii=False)}\n\n"
                            else:
                                # Standard response stream
                                yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.exception(f"Web API runtime error: {str(e)}")
            error_data = json.dumps({"type": "text", "content": f"\n\n❌ 抱歉，系统处理时发生内部错误。"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(agent_stream(), media_type="text/event-stream")
