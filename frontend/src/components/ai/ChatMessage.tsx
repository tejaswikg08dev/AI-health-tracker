// Single chat message bubble — user (right) or assistant (left)

import type { ChatMessage } from "@/types/ai";
import { User, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
          isUser ? "bg-brand-100 text-brand-600" : "bg-gray-100 text-gray-600"
        )}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message bubble */}
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-brand-600 text-white rounded-tr-md"
            : "bg-gray-100 text-gray-800 rounded-tl-md"
        )}
      >
        {/* Render message content — preserving line breaks */}
        {message.content.split("\n").map((line, i) => (
          <p key={i} className={cn(i > 0 && "mt-2")}>
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}
