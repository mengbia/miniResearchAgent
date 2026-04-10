'''
uvicorn main:app --reload 启动
'''

import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from fastapi import FastAPI, BackgroundTasks # 🌟 引入 BackgroundTasks
from rag.memory_store import user_memory # 🌟 引入记忆库

import os
import shutil
from fastapi import FastAPI, UploadFile, File
from rag.vector_store import local_kb

# 进程断点保护
from agents.deep_graph import deep_research_graph, workflow, DB_PATH # 🌟 导入 workflow 和 DB_PATH
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver # 🌟 导入异步持久化组件
import uuid 

# 引入 LangGraph 和 基础消息类型
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from agents.chat_agent import normal_chat_agent
from agents.chat_agent import tools
from core.llm import get_llm  # 🌟 引入基础大脑用于闲聊
from core.prompt_manager import prompt_manager

# 防目录遍历漏洞
import uuid # 引入uuid
import re   # 引入正则

#日志
from core.logger import logger, trace_agent_event, log_user_interaction

app = FastAPI(title="Deep Research Agent Backend")

# 🌟 根接口，解决无限加载
@app.get("/")
async def root():
    return {"message": "Deep Research Agent 后端服务运行成功！", "docs": "/docs"}

# 🌟 确保上传目录存在
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
 
#  中间件 连接前后端数据通路 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  
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
    mode: str = "normal"  # 前端传来的模式开关

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # ==========================================
        # 🌟 安全改造：防目录遍历漏洞 (Path Traversal)
        # ==========================================
        # 1. 过滤危险字符，仅保留中英文字母、数字、点、下划线和连字符
        safe_original_name = re.sub(r'[^\w\.\-\u4e00-\u9fa5]', '', file.filename)
        if not safe_original_name:
            safe_original_name = "unnamed_document.txt"
            
        # 2. 拼接短 UUID 作为前缀，既防攻击，又防同名文件覆盖
        safe_filename = f"{uuid.uuid4().hex[:8]}_{safe_original_name}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 3. 安全保存落盘
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"\n📥 收到新文件上传: [原名] {file.filename} -> [安全落盘] {safe_filename}")
        
        # 4. 调用入库逻辑 (此时传入的是绝对安全的物理路径)
        await asyncio.to_thread(local_kb.process_and_save_document, file_path)
        
        # 返回给前端的依然是原始名，保证用户体验
        return {"status": "success", "message": f"文件 {file.filename} 解析并入库成功！Agent现在可以参考它了。"}

    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        return {"status": "error", "message": f"上传失败：{str(e)}"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, background_tasks: BackgroundTasks):
    user_query = request.messages[-1].content
    mode = request.mode  # 🌟 获取前端当前的模式
    print(f"\n🚀 接收到提问: {user_query} | 当前模式: {mode}")

    #组装前端传来的历史聊天记录
    history = []
    for msg in request.messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))

    # ==========================================
    # 🌟 长期记忆 (LTM)：触发后台静默提取
    # ==========================================
    # 用户发完消息，后台立刻去分析这句话有没有价值存入 Chroma，不阻塞当前响应
    background_tasks.add_task(user_memory.async_extract_and_save, user_query)

    # ==========================================
    # 🌟 短期记忆 (STM)：滑动窗口机制
    # ==========================================
    # 规则：只取最近的 10 条消息（即最近 5 轮对话），防止 Token 撑爆和上下文干扰
    WINDOW_SIZE = 10 
    recent_messages = request.messages[-WINDOW_SIZE:] if len(request.messages) > WINDOW_SIZE else request.messages
    
    # 🌟 将用户的操作落盘到日志文件
    log_user_interaction("User", f"[{mode.upper()}] {user_query}")

    # 初始化大模型（用于闲聊）
    llm = get_llm()

    async def agent_stream():
        try:
           # ==========================================
            # 分支 1：深度研究模式 (跑复杂的 LangGraph 图)
            # ==========================================
            if mode == "deep":
                # 🌟 核心：为了让两次分开的 HTTP 请求能接上头，必须使用固定的 thread_id。
                # 在真实生产中，这里应该用前端传来的对话框 ID (conversation_id)。
                # 为了你目前方便测试，我们取第一条消息的 ID，或者给个默认值。
                task_id = request.messages[0].id if (request.messages and request.messages[0].id) else "web_deep_task_01"
                run_config = {"configurable": {"thread_id": task_id}}

                async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory_saver:
                    # 🌟 在图谱编译时，打上 Planner 断点
                    persistent_graph = workflow.compile(
                        checkpointer=memory_saver,
                        interrupt_after=["planner"]
                    )
                    
                    # 获取当前状态，看看这个任务是不是被挂起在一半了
                    current_state = await persistent_graph.aget_state(run_config)
                    
                    if not current_state.next:
                        # ==========================================
                        # 🏃 第一阶段：全新任务，跑到大纲生成后挂起
                        # ==========================================
                        input_data = {"user_query": user_query, "messages": [], "plan": [], "sources": [], "report": "", "loop_count": 0}
                        
                        async for event in persistent_graph.astream_events(input_data, config=run_config, version="v2"):
                            trace_agent_event(event)
                            kind = event["event"]
                            node_name = event.get("metadata", {}).get("langgraph_node", "")
                            
                            if kind == "on_chain_end" and node_name == "planner":
                                plan_data = event["data"]["output"].get("plan", [])
                                yield f"data: {json.dumps({'type': 'plan_created', 'content': plan_data}, ensure_ascii=False)}\n\n"
                                
                        # 检查是否成功挂起，如果挂起了，给前端发一段提示文字
                        paused_state = await persistent_graph.aget_state(run_config)
                        if paused_state.next:
                            yield f"data: {json.dumps({'type': 'text', 'content': '\n\n---\n**✋ [大纲审批]** 任务已挂起！请查看上方的检索方案。\n- 若同意：请直接回复“继续”或“同意”。\n- 若放弃：请回复“取消”。'}, ensure_ascii=False)}\n\n"
                            
                    else:
                        # ==========================================
                        # 🏃 第二阶段：任务苏醒！用户的提问就是“审批指令”
                        # ==========================================
                        if user_query.strip().lower() in ['quit', '取消', '放弃', 'q']:
                            yield f"data: {json.dumps({'type': 'text', 'content': '🛑 任务已取消。您可以开启新的深度研究。'}, ensure_ascii=False)}\n\n"
                            return
                            
                        yield f"data: {json.dumps({'type': 'text', 'content': '▶️ **收到审批指令！** 正在唤醒特种部队继续执行...\n\n'}, ensure_ascii=False)}\n\n"
                        
                        # (🔥 终极玩法预留：你甚至可以用 persistent_graph.aupdate_state 把前端用户修改后的大纲强行塞进状态里，替代原来的大纲)
                        
                        # 传入 None 恢复执行
                        async for event in persistent_graph.astream_events(None, config=run_config, version="v2"):
                            trace_agent_event(event)
                            kind = event["event"]
                            node_name = event.get("metadata", {}).get("langgraph_node", "")
                            
                            if kind == "on_chain_start" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"]:
                                yield f"data: {json.dumps({'type': 'tool_start', 'content': {'input': f'特工 {node_name} 正在全网检索...'}}, ensure_ascii=False)}\n\n"
                                
                            elif kind == "on_chain_end" and node_name in ["web_specialist", "arxiv_specialist", "data_specialist", "local_specialist"]:
                                yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
                                sources_data = event["data"]["output"].get("sources", [])
                                # 防止空数据导致前端报错
                                if sources_data:
                                    yield f"data: {json.dumps({'type': 'sources', 'content': sources_data}, ensure_ascii=False)}\n\n"
                                
                            elif kind == "on_chat_model_stream" and node_name == "writer":
                                chunk = event["data"]["chunk"].content
                                if chunk:
                                    yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                            
            # ==========================================
            # 分支 2：普通闲聊模式 (企业级 Agentic RAG 版)
            # ==========================================
            else:
                # ==========================================
                # 🌟 长期记忆 (LTM)：动态检索与注入
                # ==========================================
                # 提问前，先从 Chroma 捞出跟当前问题相关的长期偏好
                relevant_memories = user_memory.retrieve_memory(user_query)
                print(f"🔮 [提取到的相关长期记忆]:\n{relevant_memories}")
                
                # 读取基础 prompt 模板
                base_system_prompt = prompt_manager.get("chat_agent", "system_prompt")
                # 将捞出来的记忆动态注入进去
                injected_prompt = base_system_prompt.format(long_term_memory=relevant_memories)

                # 重新初始化带有最新记忆的 Agent (注意：这在生产中最好缓存，但目前每次重新实例化也没问题)
                memory_aware_agent = create_react_agent(
                    get_llm(),
                    tools=tools, 
                    prompt=injected_prompt
                )

                state = {"messages": history} # 这里的 history 已经是滑动窗口截断过的了
                
                # 3. 🌟 启动监听器，实时把 Agent 思考和调用工具的过程发给前端
                async for event in memory_aware_agent.astream_events(state, version="v2"):
                   
                    # 🌟 无侵入式解耦追踪！
                    trace_agent_event(event)

                    kind = event["event"]
                    
                    # 监听动作 A：大模型决定拿工具了！给前端发一个优雅的加载动画
                    if kind == "on_tool_start":
                        tool_name = event.get("name", "未知工具")
                        yield f"data: {json.dumps({'type': 'tool_start', 'content': {'input': f'正在调用本地工具查阅: {tool_name}'}}, ensure_ascii=False)}\n\n"
                    
                    # 监听动作 B：工具查完了，告诉前端关闭动画
                    elif kind == "on_tool_end":
                        yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
                        
                    # 监听动作 C：大模型开始根据工具查到的资料写回复了（流式打字机）
                    elif kind == "on_chat_model_stream":
                        chunk = event["data"]["chunk"].content
                        # 过滤掉由于工具调用逻辑产生的空字符
                        if chunk and isinstance(chunk, str):
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"

        except Exception as e:
            print(f"❌ 报错: {e}")

            # 🌟 记录系统崩溃日志
            logger.error(f"Web API 运行崩溃: {str(e)}")

            error_data = json.dumps({"type": "text", "content": f"\n\n后端报错: {str(e)}"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(agent_stream(), media_type="text/event-stream")