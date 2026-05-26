import { create } from "zustand";
import type { ChatMessage, Conversation, Document, ModelInfo, User } from "@/types";

interface AppState {
  // Auth
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  logout: () => void;

  // Chat
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  setConversations: (c: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  setMessages: (m: ChatMessage[]) => void;
  addMessage: (m: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (v: boolean) => void;

  // Model
  models: ModelInfo[];
  selectedModel: string;
  setModels: (m: ModelInfo[]) => void;
  setSelectedModel: (m: string) => void;

  // Documents
  documents: Document[];
  selectedDocIds: string[];
  useRag: boolean;
  setDocuments: (d: Document[]) => void;
  toggleDocSelection: (id: string) => void;
  setUseRag: (v: boolean) => void;

  // UI
  sidebarOpen: boolean;
  language: string;
  toggleSidebar: () => void;
  setLanguage: (l: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Auth
  user: null,
  token: null,
  setAuth: (user, token) => {
    if (typeof window !== "undefined") localStorage.setItem("token", token);
    set({ user, token });
  },
  logout: () => {
    if (typeof window !== "undefined") localStorage.removeItem("token");
    set({ user: null, token: null });
  },

  // Chat
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId, messages: [] }),
  setMessages: (messages) => set({ messages }),
  addMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  updateLastMessage: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0) {
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content };
      }
      return { messages: msgs };
    }),
  setStreaming: (isStreaming) => set({ isStreaming }),

  // Model
  models: [],
  selectedModel: "llama3:8b",
  setModels: (models) => set({ models }),
  setSelectedModel: (selectedModel) => set({ selectedModel }),

  // Documents
  documents: [],
  selectedDocIds: [],
  useRag: false,
  setDocuments: (documents) => set({ documents }),
  toggleDocSelection: (id) =>
    set((s) => ({
      selectedDocIds: s.selectedDocIds.includes(id)
        ? s.selectedDocIds.filter((d) => d !== id)
        : [...s.selectedDocIds, id],
    })),
  setUseRag: (useRag) => set({ useRag }),

  // UI
  sidebarOpen: true,
  language: "en",
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setLanguage: (language) => set({ language }),
}));
