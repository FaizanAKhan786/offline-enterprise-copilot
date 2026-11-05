const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> || {}),
  };

  // Remove Content-Type for FormData
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  const res = await fetch(`${API_V1}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API Error: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; role: string; expires_in: number }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    ),

  getMe: () => request<any>("/auth/me"),

  // Chat
  sendMessage: async function* (params: {
    message: string;
    conversation_id?: string | null;
    model?: string;
    use_rag?: boolean;
    document_ids?: string[];
    temperature?: number;
    language?: string;
  }) {
    const token = getToken();
    const res = await fetch(`${API_V1}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ ...params, stream: true }),
    });

    if (!res.ok) throw new Error(`Chat error: ${res.status}`);
    if (!res.body) throw new Error("No response body");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const chunk = JSON.parse(line.slice(6));
            yield chunk;
          } catch {}
        }
      }
    }
  },

  getConversations: () =>
    request<any[]>("/chat/conversations"),

  // Documents
  uploadDocument: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<any>("/documents/upload", {
      method: "POST",
      body: form,
    });
  },

  getDocuments: () =>
    request<{ documents: any[]; total: number }>("/documents"),

  deleteDocument: (id: string) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  // Agents
  executeWorkflow: (params: {
    workflow: string;
    input_text: string;
    document_ids?: string[];
    target_language?: string;
    model?: string;
  }) =>
    request<any>("/agents/execute", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  getWorkflows: () => request<any>("/agents/workflows"),

  // Models
  getModels: () =>
    request<{ models: any[]; default: string }>("/models"),

  // Voice
  transcribe: async (audio: Blob) => {
    const form = new FormData();
    form.append("file", audio, "recording.wav");
    return request<{ text: string; language: string }>("/voice/transcribe", {
      method: "POST",
      body: form,
    });
  },

  // Health
  getHealth: () => request<any>("/health"),
};

/** Compatibility adapter used by the chat and document panels. */
export const apiClient = {
  async *chatStream(message: string, model: string, useRag: boolean, conversationId?: string, language = "en", _token?: string) {
    for await (const chunk of api.sendMessage({
      message,
      model,
      use_rag: useRag,
      conversation_id: conversationId,
      language,
    })) {
      if (chunk.done) {
        if (chunk.sources?.length) yield { type: "citations" as const, citations: chunk.sources };
        if (chunk.confidence != null) yield { type: "metadata" as const, confidence: chunk.confidence };
      } else if (typeof chunk.delta === "string") {
        yield { type: "token" as const, content: chunk.delta };
      }
    }
  },
  async transcribe(blob: Blob, _language?: string, _token?: string): Promise<string> {
    const result = await api.transcribe(blob);
    return result.text;
  },
  uploadDocument(file: File, _token?: string) {
    return api.uploadDocument(file);
  },
  deleteDocument(id: string, _token?: string) {
    return api.deleteDocument(id);
  },
};
