// Chat window — scrollable message list with loading indicator

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/types/ai";
import ChatMessageBubble from "./ChatMessage";
import LoadingSpinner from "@/components/layout/LoadingSpinner";
import { MessageSquare } from "lucide-react";

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export default function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Empty state */}
      {messages.length === 0 && !isLoading && (
        <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 py-16">
          <MessageSquare className="w-12 h-12 mb-4" />
          <p className="text-lg font-medium">Ask your AI Health Coach</p>
          <p className="text-sm mt-1 max-w-md">
            I can check your habit data, find patterns, search your documents,
            and help you build better habits.
          </p>
          <div className="flex flex-wrap gap-2 mt-6 justify-center">
            {[
              "How's my sleep this week?",
              "Am I drinking enough water?",
              "What correlates with my mood?",
              "Help me improve my exercise habit",
            ].map((q) => (
              <span
                key={q}
                className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-full"
              >
                {q}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      {messages.map((msg) => (
        <ChatMessageBubble key={msg.id} message={msg} />
      ))}

      {/* Loading indicator */}
      {isLoading && (
        <div className="flex items-center gap-2 text-gray-400 py-2">
          <LoadingSpinner size="sm" />
          <span className="text-sm">Thinking...</span>
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} />
    </div>
  );
}
