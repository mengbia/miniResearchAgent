import { StateGraph, END, START } from "@langchain/langgraph";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { createLLM } from "../lib/llm";  // 从 lib 目录导入 LLM 工厂函数
import { tools } from "./tools";  // 从当前目录导入工具函数
import { AgentState } from "./state";  // 从当前目录导入状态定义

// ================ 1. 初始化模型并绑定工具 ================
const llm = createLLM();
const llmWithTools = llm.bindTools(tools);

// ================ 2. 定义节点 (Nodes) ================

// 节点 A: 思考节点 (Agent)
// 它的任务是调用 LLM，LLM 会返回一段文本，或者一个“工具调用请求”
/**
 * 思考节点 (Agent)
 * @param state - 当前状态，包含所有对话历史
 * @returns 更新后的状态，包含新的 LLM 回复
 */
async function agentNode(state: typeof AgentState.State) {
  const { messages } = state;  // 从状态中提取所有对话历史
  const result = await llmWithTools.invoke(messages);  // 调用 LLM 并绑定工具
  return { messages: [result] };  // 返回新的状态，包含 LLM 的回复，可能包含工具调用请求
}

// 节点 B: 工具执行节点 (Tools)
// LangGraph 自带的预构建节点，它会自动执行 agentNode 发出的工具调用请求
/**
 * 工具执行节点 (Tools)
 * @param state - 当前状态，包含所有对话历史，同时可能包含工具调用请求
 * @returns 更新后的状态，包含工具执行结果
 */
const toolNode = new ToolNode(tools);

// ================ 3. 定义条件边 (Conditional Logic) ================

// 判断 LLM 是想继续搜索，还是想结束说话
/**
 * 判断 LLM 是否想继续搜索或结束说话
 * @param state - 当前状态，包含所有对话历史
 * @returns 如果想继续搜索，返回 "tools"；如果想结束说话，返回 END
 */
function shouldContinue(state: typeof AgentState.State) {
  const messages = state.messages;
  const lastMessage = messages[messages.length - 1];

  // 如果 LLM 返回的消息里包含 tool_calls，说明它想用工具 -> 去 tools 节点
  if (
    lastMessage &&
    "tool_calls" in lastMessage &&
    Array.isArray(lastMessage.tool_calls) &&
    lastMessage.tool_calls.length > 0
  ) {
    return "tools";
  }

  // 否则 -> 结束
  return END;
}

// ================ 4. 组装图 (Graph) ================
/**
 * 组装图 (Graph)
 * @description 定义节点和边，构建完整的状态流转图，为一个循环执行结构
 */
const workflow = new StateGraph(AgentState)
  .addNode("agent", agentNode)       // 放置节点：agent（思考节点）
  .addNode("tools", toolNode)        // 放置节点：tools（工具节点）
  .addEdge(START, "agent")           // 设置起点：agent（思考节点）
  .addConditionalEdges(              // 设置分叉：根据 agent 节点的输出，选择下一步
    "agent",         // 从 agent 节点出来后
    shouldContinue,  // 运行这个判断函数
    {                // 映射关系
      tools: "tools",  // 如果返回工具调用请求，去 tools 节点
      [END]: END       // 如果返回 END，说明想结束说话，直接结束
    }
  )
  .addEdge("tools", "agent");        // 工具用完后 -> 回到 agent 继续思考（实现ReAct循环，通过思考再次决定是否继续调用工具）

// 5. 编译成可运行的应用
export const graph = workflow.compile();