export type ApiStatus =
  | "checking"
  | "online"
  | "offline";

export type QueryMode = "stream" | "standard";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ReadinessResponse {
  ready: boolean;
  database: boolean;
  redis: boolean;
  details: Record<string, string>;
}

export interface SessionResponse {
  session_id: string;
  thread_id: string;
  user_id: string;
  status: string;
}

export interface UploadResponse {
  filename: string;
  source: string;
  indexed_chunks: number;
  status: string;
}

export interface Citation {
  citation_id: string;
  source: string;
  page: number;
}

export interface AskResponse {
  run_id: string;
  thread_id: string;
  status: string;
  answer: string;
  citations: Citation[];
  context_tokens_est: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cache_read_tokens: number;
  latency_ms: number;
  replayed: boolean;
}

export interface TaskStatusResponse {
  run_id: string;
  thread_id: string;
  status: string;
  current_node: string;
  step_count: number;
  max_steps: number;
  error: string;
}

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface StreamPayload {
  question: string;
  thread_id: string;
  request_id: string;
  stream: true;
}

export interface StandardAskPayload {
  question: string;
  thread_id: string;
  request_id: string;
  stream: false;
}
