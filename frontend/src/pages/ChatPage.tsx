// AI Chat page — conversation with the health coach agent

import { useEffect } from "react";
import { useChat } from "@/hooks/useChat";
import ChatWindow from "@/components/ai/ChatWindow";
import ChatInput from "@/components/ai/ChatInput";
import { MessageSquare, Sparkles } from "lucide-react";

export default function ChatPage() {
  const { messages, isLoading, sendMessage, loadHistory } = useChat();

  // Load chat history on mount
  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return (
    <div className="flex flex-col h-[calc(100vh-130px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-brand-500" />
          AI Health Coach
        </h2>
        <div className="flex items-center gap-1 text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
          <Sparkles className="w-3 h-3" />
          Agent mode — can access your data
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 bg-white rounded-xl border overflow-hidden flex flex-col">
        <ChatWindow messages={messages} isLoading={isLoading} />
        <ChatInput onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}
