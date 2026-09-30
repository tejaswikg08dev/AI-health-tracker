// Chat input — text area with send button, Enter to send

import { useState } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => Promise<void>;
  isLoading: boolean;
}

export default function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isLoading) return;

    setMessage("");
    await onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Enter sends, Shift+Enter adds a new line
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-gray-200 p-4 flex gap-3 items-end"
    >
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your health habits..."
        rows={1}
        disabled={isLoading}
        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none disabled:opacity-50 text-sm"
        style={{ maxHeight: "120px" }}
      />
      <button
        type="submit"
        disabled={isLoading || !message.trim()}
        className="bg-brand-600 text-white p-2.5 rounded-xl hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
        aria-label="Send message"
      >
        <Send className="w-5 h-5" />
      </button>
    </form>
  );
}
