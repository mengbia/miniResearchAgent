import {create} from "zustand";

// === 1. 导出所有子接口 (修复 import 报错) ===

export interface Source {
    id: string;
    url: string;
    title: string;
    snippet?: string;
    favicon?: string;
}

export interface PlanItem {
    id: string;
    title: string;
    status: "pending" | "completed" | "generating";
}

export interface Step {
    id: string;
    type: string; // e.g., 'search', 'process', 'reasoning'
    content: string;
    status: "pending" | "completed";
}

// === 2. 核心 Message 接口 (使用严格类型) ===

export interface Message {
    id: string;
    role: "user" | "ai";
    content: string;

    // 深度研究专用字段 (使用上面定义的接口)
    sources?: Source[];
    plan?: PlanItem[];
    steps?: Step[];

    createdAt?: string | Date;
}

export interface Chat {
    id: string;
    title: string;
    createdAt: string | Date;
}

// === 3. Store 状态定义 ===

interface ChatState {
    // --- 基础状态 ---
    messages: Message[];
    input: string;
    isLoading: boolean;
    chats: Chat[];
    currentChatId: string | null;
    researchMode: "normal" | "deep";
    abortController: AbortController | null;

    // --- M10 新增状态 (多选分享) ---
    isSelectionMode: boolean;
    selectedMessageIds: string[];

    // --- 基础 Actions ---
    setMessages: (messages: Message[]) => void;
    setInput: (input: string) => void;
    setLoading: (isLoading: boolean) => void;
    setChats: (chats: Chat[]) => void;
    setCurrentChatId: (id: string | null) => void;
    setResearchMode: (mode: "normal" | "deep") => void;
    setAbortController: (controller: AbortController | null) => void;

    addMessage: (message: Message) => void;
    deleteLastMessage: () => void;
    updateLastMessage: (content: string) => void;

    // --- 深度研究相关 Actions (使用严格类型) ---
    setSourcesForLastMessage: (sources: Source[]) => void;
    updateLastMessagePlan: (plan: PlanItem[]) => void;
    addStepToLastMessage: (step: Step) => void;
    completeLastStep: () => void;

    // --- M10 多选分享 Actions ---
    setSelectionMode: (mode: boolean) => void;
    toggleMessageSelection: (messageId: string) => void;
    selectAllMessages: () => void;
    deselectAllMessages: () => void;
}

// === 4. Store 实现 ===

export const useChatStore = create<ChatState>((set, get) => ({
    // --- 初始化 ---
    messages: [],
    input: "",
    isLoading: false,
    chats: [],
    currentChatId: null,
    researchMode: "normal",
    abortController: null,
    isSelectionMode: false,
    selectedMessageIds: [],

    // --- 基础 Setter ---
    setMessages: (messages) => set({messages}),
    setInput: (input) => set({input}),
    setLoading: (isLoading) => set({isLoading}),
    setChats: (chats) => set({chats}),
    setCurrentChatId: (currentChatId) => set({currentChatId}),
    setResearchMode: (researchMode) => set({researchMode}),
    setAbortController: (abortController) => set({abortController}),

    // --- 消息操作 ---
    addMessage: (message) => set((state) => ({
        messages: [...state.messages, message]
    })),

    deleteLastMessage: () => set((state) => ({
        messages: state.messages.slice(0, -1)
    })),

    updateLastMessage: (content) => set((state) => {
        const msgs = [...state.messages];
        if (msgs.length > 0) {
            const lastMsg = msgs[msgs.length - 1];
            lastMsg.content = content;
        }
        return {messages: msgs};
    }),

    // --- 深度研究操作 (强类型支持) ---
    // setSourcesForLastMessage: (sources) => set((state) => {
    //   const msgs = [...state.messages];
    //   if (msgs.length > 0) {
    //     msgs[msgs.length - 1].sources = sources;
    //   }
    //   return { messages: msgs };
    // }),
    setSourcesForLastMessage: (newSources) => set((state) => {
        const msgs = [...state.messages];
        const lastMsg = msgs[msgs.length - 1];

        if (lastMsg && lastMsg.role === "ai") {
            // 1. 获取已有的 sources
            const existingSources = lastMsg.sources || [];

            // 2. 合并新旧 sources
            const combinedSources = [...existingSources, ...newSources];

            // 3. 去重 (根据 URL)
            // 使用 Map，键是 url，值是 source 对象。这样相同的 url 会被覆盖（保留一个）
            const uniqueSources = Array.from(
                new Map(combinedSources.map((item) => [item.url, item])).values()
            );

            // 4. 赋值回去
            lastMsg.sources = uniqueSources;
        }
        return {messages: msgs};
    }),

    updateLastMessagePlan: (plan) => set((state) => {
        const msgs = [...state.messages];
        if (msgs.length > 0) {
            msgs[msgs.length - 1].plan = plan;
        }
        return {messages: msgs};
    }),

    addStepToLastMessage: (step) => set((state) => {
        const msgs = [...state.messages];
        if (msgs.length > 0) {
            const lastMsg = msgs[msgs.length - 1];
            const steps = lastMsg.steps || [];
            lastMsg.steps = [...steps, step];
        }
        return {messages: msgs};
    }),

    completeLastStep: () => set((state) => {
        const msgs = [...state.messages];
        if (msgs.length > 0) {
            const lastMsg = msgs[msgs.length - 1];
            if (lastMsg.steps && lastMsg.steps.length > 0) {
                const lastStep = lastMsg.steps[lastMsg.steps.length - 1];
                lastStep.status = "completed";
            }
        }
        return {messages: msgs};
    }),

    // --- M10 多选分享操作 ---

    setSelectionMode: (mode) => set({
        isSelectionMode: mode,
        selectedMessageIds: []
    }),

    toggleMessageSelection: (messageId) => {
        const {selectedMessageIds, messages} = get();
        const isSelected = selectedMessageIds.includes(messageId);
        let newSelectedIds = [...selectedMessageIds];

        const currentIndex = messages.findIndex(m => m.id === messageId);
        if (currentIndex === -1) return;

        const currentMsg = messages[currentIndex];

        // 智能绑定 User + AI
        const idsToToggle = [messageId];

        if (currentMsg.role === 'user') {
            const nextMsg = messages[currentIndex + 1];
            if (nextMsg && nextMsg.role === 'ai') {
                idsToToggle.push(nextMsg.id);
            }
        } else if (currentMsg.role === 'ai') {
            const prevMsg = messages[currentIndex - 1];
            if (prevMsg && prevMsg.role === 'user') {
                idsToToggle.push(prevMsg.id);
            }
        }

        if (isSelected) {
            newSelectedIds = newSelectedIds.filter(id => !idsToToggle.includes(id));
        } else {
            newSelectedIds = Array.from(new Set([...newSelectedIds, ...idsToToggle]));
        }

        set({selectedMessageIds: newSelectedIds});
    },

    selectAllMessages: () => {
        const allIds = get().messages.map(m => m.id);
        set({selectedMessageIds: allIds});
    },

    deselectAllMessages: () => {
        set({selectedMessageIds: []});
    }
}));