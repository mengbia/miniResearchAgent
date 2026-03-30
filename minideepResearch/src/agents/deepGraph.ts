import { Annotation, StateGraph, END, START } from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";
import { z } from "zod";
import { searchWebTool } from "./tools"; // 复用 M2 定义的搜索工具
import { createLLM } from "@/lib/llm"; // 👈 复用统一的 LLM 初始化逻辑

// ================ 1. 定义状态 (State) ================
// 这是整个研究过程的"共享内存"
export const DeepResearchState = Annotation.Root({
    /**
     * 总目标 (User Query)
     * @property query - 用户原始问题，作为研究的起点
     */
    user_query: Annotation<string>(),

    /**
     * 任务清单 (Task Plan)
     * @property plan - 包含所有研究步骤的清单，每个步骤都是一个对象，包含 id、任务描述和状态
     */
    plan: Annotation<Array<{ id: number; task: string; status: "pending" | "done" }>>(),

    /**
     * 收集到的碎片知识 (Gathered Information)
     * @property info - 包含所有 Worker 执行任务后返回的研究结果，每个元素是一个字符串
     */
    gathered_info: Annotation<string[]>(),

    /**
     * 最终报告 (Final Report)
     * @property report - 包含所有研究结果的综合报告，格式为 Markdown
     */
    final_report: Annotation<string>(),

    /**
     * 迭代计数器 (Iteration Count)
     * @property count - 记录当前执行的迭代次数，用于防止无限循环
     */
    iteration_count: Annotation<number>(),

    /**
     * 用于收集 Source 的数组 (Web Search Results)，用于前端展示引用
     * @property results - 包含所有从互联网搜索到的文档，每个元素是一个对象，包含标题和 URL
     */
    web_search_results: Annotation<Array<{ title: string; url: string }>>(),
});

// ================ 2. 初始化模型 ================
// 使用稍高的温度 (0.3) 以激发规划能力，同时保持一定的严谨性
const model = createLLM({ temperature: 0.3 });

// ================ 3. 定义各个节点 (Nodes) ================

/**
 * 🧠 Planner 节点: 生成任务清单
 */
/**
 * 计划节点 (Planner)
 * @param state - 当前状态，包含用户原始问题
 * @returns 更新后的状态，包含初始任务清单
 */
const plannerNode = async (state: typeof DeepResearchState.State) => {
    console.log("--- 🧠 Planner: 正在规划任务 ---");

    /**
     * 结构化的计划输出 Schema，基于Zod对AI的输出进行验证和解析
     * @property steps - 详细的研究步骤列表，每个步骤都是一个字符串
     */
    const planSchema = z.object({
        steps: z.array(z.string()).describe("List of detailed research steps"),  // 基于Zod对AI输出限制为JSON对象，内部包含steps数组，每个元素是一个字符串
    });

    const structuredModel = model.withStructuredOutput(planSchema);  // 传入计划输出的Schema，确保AI输出符合预期格式，得到结构化限制后的模型

    // prompt：数量约束、内容限制、逻辑顺序
    const prompt = `你是一个深度研究规划专家。
用户的目标是: "${state.user_query}"
请将这个大目标拆解为 3-5 个具体的、可执行的子任务（搜索关键词或分析方向）。
任务要层层递进，例如先了解定义，再分析现状，最后对比优劣。`;

    // 调用模型，传入 prompt 并获取结构化输出
    // [
    //     { "id": 1, "task": "搜索 Next.js 官方定义", "status": "pending" },
    //     { "id": 2, "task": "查找 Next.js 与 React 的区别", "status": "pending" },
    //     { "id": 3, "task": "搜索 Next.js 14 新特性", "status": "pending" }
    // ]
    const response = await structuredModel.invoke([new HumanMessage(prompt)]);

    // 转换成 State 需要的格式，遍历写入 plan 的任务清单
    const initialPlan = response.steps.map((step, index) => ({
        id: index + 1,  // 任务ID从1开始递增
        task: step,  // 任务描述直接从AI输出的步骤中获取
        status: "pending" as const,  // 初始状态设为 pending
    }));

    return {
        plan: initialPlan,  // planner节点有权限写入初始任务清单
        iteration_count: 0,  // 初始迭代次数设为0
        gathered_info: [],  // 初始时没有收集到任何信息
        web_search_results: []  // 初始时没有搜索到任何文档
    };
};

/**
 * 🕵️ Worker 节点: 执行当前的一个任务
 */
/**
 * 工作节点 (Worker)
 * @param state - 当前状态，包含任务清单、收集到的信息、迭代次数和搜索结果
 * @returns 更新后的状态，包含执行结果和更新后的任务清单
 */
const workerNode = async (state: typeof DeepResearchState.State) => {
    // 1. 找到第一个 pending 的任务的索引
    const currentTaskIndex = state.plan.findIndex(p => p.status === "pending");
    if (currentTaskIndex === -1) {
        return {}; // 没有任务了，理论上逻辑会流转到 writer 节点，则结束循环
    }

    // 根据索引获取当前任务
    const currentTask = state.plan[currentTaskIndex];
    console.log(`--- 🕵️ Worker: 正在执行任务 ${currentTask.id}: ${currentTask.task} ---`);

    // 2. 调用搜索工具
    // 注意：searchWebTool 返回的是格式化后的字符串 (包含 "标题:", "来源:", "内容摘要:")
    const searchResult = await searchWebTool.invoke({ query: currentTask.task });

    // 3. 硬编码解析搜索结果（提供给前端展示标题和URL）
    // 正则逻辑，确保前端能在深度模式下也看到引用气泡，后续可以考虑优化
    const newSources: { title: string; url: string }[] = [];
    const lines = searchResult.split("\n");

    // 临时解析逻辑 (对应 searchWebTool 的输出格式)
    // 如果 searchWebTool 输出格式有变，这里也要微调
    const chunks = searchResult.split(/\[结果\s*\d+\]/);
    for (const chunk of chunks) {
        const titleMatch = chunk.match(/(?:标题|Title):\s*(.+?)(?:\n|\\n|$)/);
        const urlMatch = chunk.match(/(?:来源|Source|Link):\s*(https?:\/\/[^\s\n\\]+)/);

        if (titleMatch && urlMatch) {
            const title = titleMatch[1].trim();
            const url = urlMatch[1].trim();
            if (title && url && !url.includes("内容摘要")) {
                newSources.push({ title, url });
            }
        }
    }

    // 4. 更新 State，更新当前任务状态为 done
    const newPlan = [...state.plan];
    newPlan[currentTaskIndex] = { ...currentTask, status: "done" };

    return {
        plan: newPlan,  // 更新后的任务清单
        gathered_info: [...state.gathered_info, `### 任务: ${currentTask.task}\n${searchResult}`],  // 收集当前任务的搜索结果
        web_search_results: [...(state.web_search_results || []), ...newSources],  // 更新解析后的引文列表
        iteration_count: state.iteration_count + 1,  // 迭代次数加1
    };
};

/**
 * ✍️ Writer 节点: 撰写最终报告
 */
/**
 * 编写节点 (Writer)
 * @param state - 当前状态，包含用户查询、收集到的信息、迭代次数和搜索结果
 * @returns 更新后的状态，包含最终报告
 */
const writerNode = async (state: typeof DeepResearchState.State) => {
    console.log("--- ✍️ Writer: 正在撰写报告 ---");

    // prompt
    const prompt = `基于以下收集到的信息，为用户撰写一份详尽的深度研究报告。
用户问题: "${state.user_query}"

--- 收集到的信息 ---
${state.gathered_info.join("\n\n")}
------------------

要求:
1. 使用 Markdown 格式。
2. 结构清晰：包含标题、目录、正文（分章节）、总结。
3. 内容要深度整合收集到的信息，不要只是简单的罗列。
4. **必须**在文中适当位置标注引用来源，格式为 [1], [2] 等。
   (注意：前端会根据你提供的链接列表进行渲染，请尽量保证引用标记的逻辑合理性)。
`;

    // 调用模型生成报告
    const response = await model.invoke([new HumanMessage(prompt)]);

    return {
        final_report: response.content as string,  // 最终生成的报告
    };
};

// === 4. 构建图 (Graph Construction) ===
/**
 * 构建图 (DeepResearch Graph)
 * @description 定义研究流程的节点和边，包括规划、工作、写作节点
 */
const builder = new StateGraph(DeepResearchState)
    .addNode("planner", plannerNode)  // 放置节点：规划节点
    .addNode("worker", workerNode)  // 放置节点：工作节点
    .addNode("writer", writerNode);  // 放置节点：写作节点


/**
 * 定义图的边 (Edges)
 * @description 描述节点之间的流转关系，包括规划到工作、工作到循环或写作
 */
builder.addEdge(START, "planner");  // 设置起点：规划节点
builder.addEdge("planner", "worker");  // 设置边：规划节点 -> 工作节点


/**
 * 定义条件边 (Worker -> Loop or Writer)
 * @description 根据任务状态判断是否继续循环或去写作节点
 */
builder.addConditionalEdges(
    "worker",
    (state) => {
        // 安全阀: 如果迭代超过 6 次，强制结束去写作
        if (state.iteration_count >= 6) {
            console.log("⚠️ 达到最大迭代次数，强制结束研究");
            return "writer";
        }

        // 检查是否还有未完成的任务
        const hasPending = state.plan.some(p => p.status === "pending");

        // 如果有任务没做完，继续回 worker；否则去 writer
        return hasPending ? "worker" : "writer";
    },
    {
        worker: "worker", // 继续循环
        writer: "writer", // 去写作
    }
);

builder.addEdge("writer", END);

// 编译图
export const deepGraph = builder.compile();