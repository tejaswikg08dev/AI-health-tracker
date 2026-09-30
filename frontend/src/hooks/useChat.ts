// ============================================================================
// useChat — Custom hook for AI chat with streaming support
// ============================================================================
// This is a CUSTOM HOOK — not a TanStack Query hook.
// Chat is stateful (message list) and involves streaming (SSE),
// which doesn't fit the simple query/mutation pattern.
// ============================================================================

import { useState, useCallback } from "react";
import { aiService } from "@/services/ai.service";
import type { ChatMessage } from "@/types/ai";

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (message: string, useAgent?: boolean) => Promise<void>;
  loadHistory: () => Promise<void>;
  clearMessages: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = useCallback(async () => {
    try {
      const data = await aiService.getChatHistory();
      setMessages(data.messages);
    } catch {
      // Chat history load failure is not critical
    }
  }, []);

  const sendMessage = useCallback(
    async (message: string, useAgent = true) => {
      setIsLoading(true);
      setError(null);

      // Add user message to UI immediately (optimistic)
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        tokens_used: 0,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        // Call the AI chat endpoint
        const response = await aiService.chat({
          message,
          use_agent: useAgent,
        });

        // Add assistant response
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.response,
          tokens_used: 0,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to get response";
        setError(errorMsg);

        // Add error message to chat
        const errorChat: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Sorry, I encountered an error: ${errorMsg}. Please try again.`,
          tokens_used: 0,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorChat]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    loadHistory,
    clearMessages,
  };
}
