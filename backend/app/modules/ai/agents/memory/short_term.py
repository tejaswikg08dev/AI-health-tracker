# ============================================================================
# Agent Memory — Short-Term (Conversation Buffer)
# ============================================================================
# WHAT THIS FILE DOES:
#   Maintains the current conversation history (last N messages).
#   This is the agent's "working memory" — what was said in THIS conversation.
#
# WHY SHORT-TERM MEMORY:
#   User: "How much water did I drink this week?"
#   Agent: "You averaged 7 glasses per day this week."
#   User: "How about last week?"  ← agent needs to remember the topic is water!
#
#   Without conversation history, the agent treats each message independently.
#   With it, the agent understands context and follow-up questions.
#
# HOW IT WORKS:
#   - Stores the last N messages (default: 20)
#   - Older messages are dropped (sliding window)
#   - Messages are stored as LLMMessage objects (role + content)
#   - In-memory only — cleared when the session ends
#   - The DB stores full history (AiChatMessage), this is just the active window
#
# TOKEN BUDGET:
#   Conversation history uses tokens from the context window.
#   20 messages × ~100 tokens each = ~2000 tokens for history.
#   We cap it to leave room for: system prompt + tool results + response.
# ============================================================================

from app.modules.ai.llm.base_client import LLMMessage


class ShortTermMemory:
    """
    Sliding window conversation buffer.

    Keeps the last `max_messages` messages in memory.
    When the buffer is full, the oldest message is dropped.

    Usage:
        memory = ShortTermMemory(max_messages=20)
        memory.add_user_message("How much water did I drink?")
        memory.add_assistant_message("You averaged 7 glasses.")
        messages = memory.get_messages()  # → list of LLMMessage
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: list[LLMMessage] = []

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self._add(LLMMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to the conversation."""
        self._add(LLMMessage(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """
        Add a tool execution result to the conversation.

        Formatted so the LLM knows this is data from a tool, not a human.
        The LLM uses this data to formulate its response.
        """
        self._add(LLMMessage(
            role="tool",
            content=f"[Tool: {tool_name}]\n{result}",
        ))

    def get_messages(self) -> list[LLMMessage]:
        """Get the current conversation history."""
        return list(self._messages)

    def get_message_count(self) -> int:
        """Get the number of messages in the buffer."""
        return len(self._messages)

    def clear(self) -> None:
        """Clear all messages (start fresh conversation)."""
        self._messages.clear()

    def _add(self, message: LLMMessage) -> None:
        """Add a message, dropping the oldest if at capacity."""
        self._messages.append(message)
        # Sliding window — drop oldest messages when buffer is full
        while len(self._messages) > self.max_messages:
            self._messages.pop(0)
