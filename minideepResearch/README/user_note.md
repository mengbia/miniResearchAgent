# Prompt
> 当前辅助我进行从零开始DeepResarch代码阅读，询问的文件和问题顺序都是循序渐进的，需要进行循序渐进和回顾式的回答和分析，以帮助我快速理解当前的目的、引用的文件、以及下一步的执行。

# 问题

# LangGraph

## 构建图的函数

在 LangGraph 中构建图（Graph）就像是**铺设一条自动化流水线**。

你需要定义**工位（Nodes）**在哪里，以及工位之间的**传送带（Edges）**怎么连。

以下是构建图时的三大核心函数总结：

---

### 1. `addNode(name, action)` —— **定义工位**

这是图的基础。你必须先在地图上把所有的“地点”标记出来，才能开始连线。

* **作用**：注册一个节点。
* **参数**：
* `name` (string): 给这个节点起个名字（如 "planner", "worker"）。
* `action` (function): 这个节点具体干什么活（通常是一个接收 State 并返回 Partial State 的异步函数）。


* **比喻**：在工厂里放置一台机器，或者安排一个员工。
* **DeepResearch 例子**：
```typescript
// 安排三个员工：规划师、工人、作家
builder.addNode("planner", plannerNode);
builder.addNode("worker", workerNode);
builder.addNode("writer", writerNode);

```



---

### 2. `addEdge(source, target)` —— **铺设固定传送带**

这是最简单的连接方式。它是**确定性**的（Deterministic）。

* **作用**：告诉图，“只要从 A 出来，**必须**立刻去 B”。
* **参数**：
* `source` (string): 起点节点名。
* `target` (string): 终点节点名。


* **特殊常量**：
* `START` (或 `setEntryPoint`): 图的入口。
* `END`: 图的出口（流程结束）。


* **比喻**：一条单行道，或者一根直通管道。
* **DeepResearch 例子**：
```typescript
// 刚上班(START) -> 先去规划(planner)
builder.addEdge(START, "planner");

// 规划(planner)完 -> 必须交给工人(worker)去执行
builder.addEdge("planner", "worker");

// 作家(writer)写完 -> 下班(END)
builder.addEdge("writer", END);

```



---

### 3. `addConditionalEdges(source, routingFn, mapping)` —— **设置分岔路口**

这是 Agent 智能的核心。它是**动态**的（Dynamic）。

* **作用**：告诉图，“从 A 出来后，**根据情况**决定去 B 还是去 C”。
* **参数**：
* `source` (string): 起点。
* `routingFn` (function): **判官函数**。它读取当前 State，返回一个字符串（比如 "continue" 或 "stop"）。
* `mapping` (object): **路牌映射**。把判官的返回值映射到真实的节点名。


* **比喻**：通过红绿灯、环岛或者通过检测仪（合格品走左边，次品走右边）。
* **DeepResearch 例子**：
```typescript
builder.addConditionalEdges(
  "worker",          // 来源：工人干完活后
  (state) => {       // 判官：看看还有任务没？
     return state.hasMore ? "continue" : "finish";
  },
  {                  // 路牌：
     continue: "worker", // 返回 "continue" -> 回到 worker (循环)
     finish: "writer"    // 返回 "finish" -> 去 writer (写报告)
  }
);

```



---

### 一张表总结

| 函数名 | 核心逻辑 | 典型场景 | 形象比喻 |
| --- | --- | --- | --- |
| **addNode** | **“这里有人干活”** | 定义 Agent, Tool, Retriever 等执行单元 | **工位 / 部门** |
| **addEdge** | **“干完这就去那”** | 线性流程，无需判断（如：初始化 -> 第一步） | **直达管道 / 高速公路** |
| **addConditionalEdges** | **“看情况再去那”** | 循环（Loop）、分支（If-Else）、结束判断 | **红绿灯 / 调度中心** |

### 最终构建 (Compile)

当你把所有的点（Node）、线（Edge）、判断逻辑（Conditional Edge）都加好后，最后必须调用：

```typescript
const graph = builder.compile();

```

这相当于按下了工厂的**“启动电源”**，把它变成了一个可以实际运行的对象（Runnable）。

# 设计优化

## deepGraph的无记忆优化——主从架构

**是的，你的理解非常精准。**

在当前展示的代码逻辑下，如果在同一个对话窗口中执行两次 Deep Research（深度研究），**第二次研究确实会“完全遗忘”第一次研究的内容**。

这并不是设计缺陷，而是**“工作流（Workflow）”**与**“聊天流（Chat）”**在设计理念上的本质区别。

以下是详细的深度解析，解释为什么会这样，以及在实际产品中是如何解决这个问题的。

---

### 1. 为什么会“失忆”？（代码实证）

主要有两个原因导致了这种“一次性”行为：

#### A. State 的覆盖机制 (Overwrite)

如你所见，我们在定义 `DeepResearchState` 时没有使用 reducer：

```typescript
gathered_info: Annotation<string[]>(), // 没有 reducer

```

这意味着每次有节点返回这个字段的新值时，旧值会被**直接替换**，而不是追加。

#### B. Planner 节点的显式重置 (Explicit Reset)

即使 State 本身能通过 Checkpointer (持久化) 保存下来，**Planner 节点的代码逻辑也主动删除了记忆**。

请看 `plannerNode` 的返回值：

```typescript
const plannerNode = async (...) => {
    // ... 生成新计划 ...

    return {
        plan: initialPlan,      // 新计划覆盖旧计划
        iteration_count: 0,     // 计数器归零
        gathered_info: [],      // 👈 凶手在这里！显式清空了之前的笔记
        web_search_results: []  // 👈 显式清空了之前的引用
    };
};

```

无论上次研究存了多少资料，只要新的研究开始（触发 Planner），所有数据瞬间归零。这是为了防止上次关于“苹果”的资料污染了这次关于“香蕉”的研究。

---

### 2. 这种设计叫“无状态任务 (Stateless Job)”

在 LangGraph 的架构设计中，这个 `deepGraph` 被视为一个**“函数”**或**“任务执行器”**，而不是一个**“对话伙伴”**。

* **它的生命周期：** 接收任务 -> 执行 -> 输出报告 -> **死亡（结束）**。
* **它的角色：** 就像你电脑里的“计算器”应用。你算完 `1+1=2`，按归零键，再算 `2+2=4`。计算器不需要记得上次你算了什么，它只需要保证这次算对就行。

---

### 3. 实际产品中如何解决“记忆”问题？

如果在真实应用（如 Perplexity 或 DeepResearch）中，你希望 AI 记得上次的研究结果（比如：“基于刚才的研究，帮我写个摘要”），通常采用 **“主从架构 (Host & Sub-graph)”** 模式。

我们需要引入一个**“上级领导”**（Main ReAct Agent）来管理这个**“深度研究员”**。

#### 架构图解

1. **Main Agent (拥有记忆):**
* 这是一个标准的 Chat Agent，使用 `messages` + `reducer`。
* 它**只有它**直接面对用户。
* 它拥有**长久记忆**。


2. **Deep Research Sub-graph (一次性工具):**
* 这就是我们刚才写的代码。
* 它被包装成一个 **Tool**（工具）。



#### 交互流程

1. **用户:** “帮我深度研究一下 Next.js。”
2. **Main Agent:** (查看记忆，发现需要研究) -> **调用 DeepResearch Tool**。
3. **Deep Research:** (启动 -> 清空内部状态 -> 搜搜写写 -> 生成 Markdown 报告) -> **返回报告字符串**。
4. **Main Agent:** 收到报告。
* **关键点：** Main Agent 把这份报告存入了自己的 `messages` 历史记录里 (Memory)。


5. **用户:** “在这个基础上，总结三个亮点。”
6. **Main Agent:**
* 查看 `messages` 历史（里面包含了刚才 Deep Research 返回的报告）。
* 直接基于记忆回答用户，**不需要**再次启动 Deep Research。



### 4. 代码修改思路 (如果非要在一个图里实现记忆)

如果你不想搞复杂的“主从架构”，非要在当前的 `deepGraph` 里实现记忆，你需要修改 `DeepResearchState`：

1. **增加一个“历史存档”字段：**
```typescript
export const DeepResearchState = Annotation.Root({
    // ... 原有字段 ...

    // 新增：存档区 (追加模式)
    archived_reports: Annotation<string[]>({
        reducer: (x, y) => x.concat(y)
    })
});

```


2. **修改 Writer 节点：**
当 Writer 写完报告后，不仅更新 `final_report`（覆盖），还要把报告追加到 `archived_reports`（存档）。
3. **修改 Planner 节点：**
Planner 在生成新计划时，Prompt 需要读取 `archived_reports`，这样它才知道“哦，虽然这次是新任务，但用户之前研究过这个，我可以参考一下”。

### 总结

你的判断完全正确：**当前的 Deep Research 模式是“阅后即焚”的。**

在专业开发中，我们通常**不希望** Deep Research 本身有记忆（因为它太重了，Token 消耗巨大），我们更倾向于把它的**产出物（Final Report）**交给外层的轻量级 Chat Agent 去记忆。



# 需求分析

## 询问每个组件的优化/改进

## 重型组件懒加载 (next/dynamic)
1. markdown 渲染器


# 代码解读——`src/agents/state.ts`构建图

## LangGraph节点流转数据结构
> `src/agents/state.ts`这段代码定义了 DeepResearch 智能体的**全局共享状态（内存结构）**，核心是一个**“只增不减”的消息列表**，通过 `reducer` 逻辑确保后续每一步产生的新数据（无论是用户指令、AI 思考还是搜索结果）都会被**追加**到历史记录中，从而形成完整的上下文记忆链。
>
> 每个节点的输入和输出都是 `AgentState` 类型，如`src/agents/graph.ts`/`src/langgraph/deepGraph.ts`

`src/agents/state.ts`代码
```js
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
```
## graph图设计
> `src/agents/graph.ts`这段代码使用 **LangGraph** 构建了一个经典的 **ReAct 循环工作流**，通过定义“思考节点”（Agent）和“工具节点”（Tools）之间的**条件循环**（Conditional Edge），让 AI 能够自主执行“**思考 -> 决定用工具 -> 执行工具 -> 带着结果再思考**”的闭环过程，直到 AI 认为任务完成并输出最终答案。

## LangGraph搜索工具封装
> `src/agents/tools.ts`这段代码将 **Tavily 搜索 API** 封装成了一个标准的 **LangChain 工具**（`search_web`），既实现了**“怎么搜”**的逻辑（获取前 3 条结果并将复杂的元数据格式化为 AI 易读的纯文本摘要），又通过 Zod 定义了**“怎么用”**的接口规范（Schema），从而赋予 AI 智能体**实时联网获取最新信息**的能力。

## deepGraph深度研究图设计
> `src/agents/deepGraph.ts`这段代码构建了一个基于 **Plan-and-Execute（计划与执行）模式**的深度研究智能体，通过 **Planner**（将大问题拆解为子任务列表）、**Worker**（循环执行联网搜索并解析数据）、**Writer**（基于收集到的所有信息撰写最终 Markdown 报告）三个节点的有序协作，实现了对复杂用户问题的自动化深度调研闭环。

1. Plan-and-Solve 架构
这就是大名鼎鼎的 Agentic Workflow（智能体工作流）。
   * 普通模式：想一步走一步，容易跑偏。
   * 深度模式：先画地图 (Planner)，再照着地图走 (Worker)，最后写游记 (Writer)。
   * 这种架构特别适合处理复杂问题，因为它把“规划能力”和“执行能力”解耦了。

2. 状态驱动的循环
Worker 节点是一个自循环的节点。它不需要 LLM 来决定是否继续，而是通过硬逻辑（state.plan 里还有没有 pending
的项）来驱动。这比让 LLM 自己决定何时停止要稳定得多。

3. 信息的汇聚 (Gathered Info)
gathered_info 是一个关键的累加器。Worker
每次跑完，不仅仅是完成了一个任务，更重要的是往这个“素材库”里丢进了一块拼图。Writer 最后拿着这一筐拼图，才能拼出全景图。

## `graph.ts`和`deepGraph.ts`的设计理念区别

这是一个非常深刻的问题！这触及了 **LangGraph** 设计哲学中“两种不同的状态管理模式”的核心区别。

简单来说：**之前的 `AgentState` 是“聊天记录模式”，而这里的 `DeepResearchState` 是“黑板/数据库模式”。**

以下是详细的原因分析：

### 1. 根本区别：流式对话 vs. 结构化工作流

#### A. ReAct Agent (之前的代码) -> **“聊天流”**

* **模式**：整个过程是一场连贯的对话。
* **逻辑**：用户说 -> AI 思考 -> 工具返回 -> AI 再思考。
* **为什么需要 Reducer**：
* 因为对话是**线性增长**的。
* LangGraph 默认的节点返回行为是“覆盖”。如果我们不加 `reducer: concat`，当工具节点返回结果时，它可能会覆盖掉之前的用户问题，导致 AI 忘了用户问了啥。
* 我们需要 `reducer` 像胶水一样，把新产生的 Message 自动粘到旧列表的屁股后面。



#### B. DeepResearch (现在的代码) -> **“状态机”**

* **模式**：这是一个精密管理的工程项目。
* **逻辑**：Planner 制定计划表 -> Worker 领取任务 -> Worker 更新任务状态 -> Writer 汇总。
* **为什么不需要 Reducer**：
* 我们需要**精准控制**每一个字段的值，而不是无脑追加。
* **Plan (计划表)**：我们需要修改特定任务的状态（从 `pending` 改为 `done`）。如果是 `concat`，你会得到两个重复的任务，一个 pending 一个 done，而不是状态更新。
* **Gathered Info (笔记)**：虽然它是增长的，但我们在 `workerNode` 里**手动**写了追加逻辑（`[...state.gathered_info, newInfo]`）。



### 2. 代码层面的对比

#### 场景一：自动追加 (ReAct Agent)

```typescript
// 定义：只要有新东西，就往后堆
messages: Annotation<BaseMessage[]>({
    reducer: (x, y) => x.concat(y),
}),

// 节点里：我只管返回新的，Graph 帮我合并
async function node() {
    return { messages: [newMessage] }; 
    // 结果状态: [Old1, Old2, newMessage]
}

```

#### 场景二：手动全量更新 (Deep Research)

这是 DeepResearch 采用的模式。

```typescript
// 定义：默认覆盖模式 (Last Write Wins)
plan: Annotation<Array<Task>>(), 

// 节点里：我自己计算好完整的最终状态，再返回
async function workerNode(state) {
    // 1. 拿出旧计划
    const newPlan = [...state.plan]; 
    // 2. 修改指定的那一行 (精准手术)
    newPlan[0].status = "done"; 
    
    // 3. 返回完整的、修改后的计划
    return { plan: newPlan }; 
    // 结果状态: newPlan (覆盖了旧的 state.plan)
}

```

### 3. 为什么要在这里用“手动覆盖”而不是“自动追加”？

在 DeepResearch 中，如果不使用默认的覆盖模式，会有两个大问题：

1. **状态管理的复杂性**：
如果 `plan` 字段使用了 `concat` reducer，每次 Worker 更新任务状态时，你实际上是在往数组里塞一个新的 Task 对象。最后你的 Plan 数组会变成：
`[Task1(Pending), Task2(Pending), Task1(Done)]`
Planner 还需要去处理去重逻辑，这非常混乱。直接覆盖是最干净的。
2. **Context (上下文) 控制**：
DeepResearch 涉及大量的网页搜索内容（HTML 文本很大）。
* 在 Chat 模式下，所有历史记录默认都塞给 LLM。
* 在 DeepResearch 模式下，**Planner 节点可能不需要看到冗长的搜索结果**，它只需要看任务清单。
* 通过将 State 拆分成 `plan`、`gathered_info` 等独立字段，我们可以精确控制传给 LLM 的 Prompt 包含哪些字段，避免 Token 爆炸。



### 总结

* **`messages` + `reducer**` 适用于：**“请记住我们聊过的每一句话。”** (ChatBot)
* **无 reducer (默认覆盖)** 适用于：**“请更新这个表格里的这一行数据。”** (Agent Workflow / CRUD)

DeepResearch 本质上是在维护一个**动态的任务表格**，所以使用默认的覆盖模式更合适。


# 代码解读——`src/app/api/chat/route.ts`构建图