export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  model: string;
  language: string;
  updated_at: string;
}

export interface ChatMessage {
  id?: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceCitation[];
  confidence?: number | null;
  tokens_used?: number | null;
  latency_ms?: number | null;
  isStreaming?: boolean;
}

export interface SourceCitation {
  document_id: string;
  filename: string;
  chunk_text: string;
  page: number | null;
  relevance_score: number;
}

export interface StreamChunk {
  conversation_id: string;
  delta: string;
  done: boolean;
  sources?: SourceCitation[] | null;
  confidence?: number | null;
}

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: "processing" | "ready" | "error";
  chunk_count: number;
  language: string;
  created_at: string;
}

export interface ModelInfo {
  name: string;
  size: string | null;
  quantization: string | null;
  family: string | null;
  parameter_size: string | null;
  is_available: boolean;
}

export interface AgentStep {
  agent: string;
  action: string;
  output: string;
  duration_ms: number;
}

export interface WorkflowResult {
  workflow: string;
  steps: AgentStep[];
  final_output: string;
  total_duration_ms: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  services: { service: string; status: string; latency_ms: number | null }[];
}
