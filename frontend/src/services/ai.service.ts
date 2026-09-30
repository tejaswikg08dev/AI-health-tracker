import api from "./api";
import type {
  ChatHistoryResponse,
  ChatRequest,
  ChatResponse,
  DocumentInfo,
  DocumentListResponse,
  InsightData,
  InsightListResponse,
} from "@/types/ai";
import type { SuccessResponse } from "@/types/common";

export const aiService = {
  async chat(data: ChatRequest): Promise<ChatResponse> {
    const res = await api.post<ChatResponse>("/ai/chat", data);
    return res.data;
  },

  // SSE streaming chat — returns an EventSource-like reader
  streamChat(message: string): EventSource {
    const token = localStorage.getItem("access_token");
    const baseUrl = import.meta.env.VITE_API_URL || "";
    const url = `${baseUrl}/api/v1/ai/chat/stream?message=${encodeURIComponent(message)}`;

    // EventSource doesn't support custom headers, so we pass token as query
    // In production, you'd use fetch() with ReadableStream instead
    return new EventSource(url);
  },

  async getChatHistory(): Promise<ChatHistoryResponse> {
    const res = await api.get<ChatHistoryResponse>("/ai/chat/history");
    return res.data;
  },

  async uploadDocument(file: File): Promise<DocumentInfo> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await api.post<DocumentInfo>("/ai/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000, // 2 min timeout for large files
    });
    return res.data;
  },

  async getDocuments(): Promise<DocumentListResponse> {
    const res = await api.get<DocumentListResponse>("/ai/documents");
    return res.data;
  },

  async deleteDocument(id: string): Promise<SuccessResponse> {
    const res = await api.delete<SuccessResponse>(`/ai/documents/${id}`);
    return res.data;
  },

  async generateInsight(): Promise<InsightData> {
    const res = await api.post<InsightData>("/ai/insights");
    return res.data;
  },

  async getInsights(): Promise<InsightListResponse> {
    const res = await api.get<InsightListResponse>("/ai/insights");
    return res.data;
  },

  async generateWeeklyReport(): Promise<InsightData> {
    const res = await api.post<InsightData>("/ai/weekly-report");
    return res.data;
  },
};
