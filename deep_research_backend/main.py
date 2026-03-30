'''
uvicorn main:app --reload 启动
'''

import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

import os
import shutil
from fastapi import FastAPI, UploadFile, File
from rag.vector_store import local_kb

# 引入 LangGraph 和 基础消息类型
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from agents.deep_graph import deep_research_graph
from agents.chat_agent import normal_chat_agent
from core.llm import get_llm  # 🌟 引入基础大脑用于闲聊

app = FastAPI(title="Deep Research Agent Backend")

# 新增根接口，解决无限加载
@app.get("/")
async def root():
    return {"message": "Deep Research Agent 后端服务运行成功！", "docs": "/docs"}

# 🌟 确保上传目录存在
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
 
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
        # 1. 保存用户上传的文件到本地 uploads 文件夹
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"\n📥 收到新文件上传: {file.filename}")
        
        # 2. 调用我们在 rag/vector_store.py 里写好的入库逻辑
        local_kb.process_and_save_document(file_path)
        
        return {"status": "success", "message": f"文件 {file.filename} 解析并入库成功！Agent现在可以参考它了。"}
        
    except Exception as e:
        print(f"❌ 上传解析失败: {e}")
        return {"status": "error", "message": f"处理失败: {str(e)}"}


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_query = request.messages[-1].content
    mode = request.mode  # 🌟 获取前端当前的模式
    print(f"\n🚀 接收到提问: {user_query} | 当前模式: {mode}")

    # 初始化大模型（用于闲聊）
    llm = get_llm()

    async def agent_stream():
        try:
            # ==========================================
            # 分支 1：深度研究模式 (跑复杂的 LangGraph 图)
            # ==========================================
            if mode == "deep":
                state = {"user_query": user_query, "messages": [], "plan": [], "sources": [], "report": ""}
                async for event in deep_research_graph.astream_events(state, version="v2"):
                    kind = event["event"]
                    node_name = event.get("metadata", {}).get("langgraph_node", "")
                    
                    if kind == "on_chain_end" and node_name == "planner":
                        plan_data = event["data"]["output"].get("plan", [])
                        yield f"data: {json.dumps({'type': 'plan_created', 'content': plan_data}, ensure_ascii=False)}\n\n"
                        
                    elif kind == "on_chain_start" and node_name == "worker":
                        yield f"data: {json.dumps({'type': 'tool_start', 'content': {'input': '正在全网深度检索中...'}}, ensure_ascii=False)}\n\n"
                        
                    elif kind == "on_chain_end" and node_name == "worker":
                        yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
                        sources_data = event["data"]["output"].get("sources", [])
                        yield f"data: {json.dumps({'type': 'sources', 'content': sources_data}, ensure_ascii=False)}\n\n"
                        
                    elif kind == "on_chat_model_stream" and node_name == "writer":
                        chunk = event["data"]["chunk"].content
                        if chunk:
                            yield f"data: {json.dumps({'type': 'text', 'content': chunk}, ensure_ascii=False)}\n\n"
                            
            # ==========================================
            # 分支 2：普通闲聊模式 (企业级 Agentic RAG 版)
            # ==========================================
            else:
                # 1. 组装前端传来的历史聊天记录
                history = []
                for msg in request.messages:
                    if msg.role == "user":
                        history.append(HumanMessage(content=msg.content))
                    else:
                        history.append(AIMessage(content=msg.content))
                
                # 2. 包装成 LangGraph 需要的 state
                state = {"messages": history}
                
                # 3. 🌟 启动监听器，实时把 Agent 思考和调用工具的过程发给前端
                async for event in normal_chat_agent.astream_events(state, version="v2"):
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
            error_data = json.dumps({"type": "text", "content": f"\n\n后端报错: {str(e)}"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(agent_stream(), media_type="text/event-stream")