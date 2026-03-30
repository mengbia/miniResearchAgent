import { BaseMessage } from "@langchain/core/messages";
import { Annotation } from "@langchain/langgraph";

// 使用 LangGraph 的新版注解语法 (Annotation)
// 这比旧版的 TypedDict 更简洁
export const AgentState = Annotation.Root({
  // messages: 存储所有的对话历史（用户问题、AI回复、搜索结果）
  // reducer: (x, y) => x.concat(y) 表示新消息会追加到旧消息后面
  messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
  }),
});