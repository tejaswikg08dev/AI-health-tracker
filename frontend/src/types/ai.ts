// ============================================================================
// AI Types — chat, documents, insights
// ============================================================================

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tokens_used: number;
  created_at: string;
}

export interface ChatRequest {
  message: string;
  use_agent?: boolean;
}

export interface ChatResponse {
  response: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
}

export interface DocumentInfo {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number | null;
  status: "uploaded" | "processing" | "processed" | "failed";
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
}

export interface InsightData {
  id: string;
  insight_type: string;
  title: string;
  content: string;
  tokens_used: number;
  created_at: string;
}

export interface InsightListResponse {
  insights: InsightData[];
}
