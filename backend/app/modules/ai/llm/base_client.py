# ============================================================================
# LLM — Abstract Base Client
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the INTERFACE that all LLM providers must implement.
#   Ollama, Groq, and OpenAI all look the same to the rest of the app.
#
# WHY AN ABSTRACT CLASS:
#   This is the STRATEGY PATTERN — a core design pattern.
#
#   Without it:
#     if provider == "ollama": call_ollama(...)
#     elif provider == "groq": call_groq(...)
#     elif provider == "openai": call_openai(...)
#     # Every function that uses AI has these if/elif chains — nightmare
#
#   With it:
#     client = get_llm_client()   # Returns the right one based on config
#     response = await client.chat(messages)  # Works with ANY provider
#     # Adding a new provider = one new class, zero changes elsewhere
#
# THIS IS EXACTLY HOW COMPANIES DO IT:
#   - Same interface for OpenAI, Anthropic, AWS Bedrock, Azure OpenAI
#   - Swap providers via config, not code changes
#   - Test with a mock client (no API calls, deterministic responses)
#
# INTERVIEW NOTE:
#   "How would you design an AI system that works with multiple LLM providers?"
#   Answer: "Strategy pattern with an abstract base class. Each provider
#   implements the same interface. A factory function returns the right
#   implementation based on configuration."
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class LLMMessage:
    """
    A single message in a conversation.

    Mirrors the OpenAI/Anthropic message format — the industry standard.
    Every LLM API uses role + content, so this works universally.

    Roles:
        system    → instructions for the AI (persona, rules, context)
        user      → the human's message
        assistant → the AI's response
        tool      → result of a tool call (for agents)
    """

    role: str       # "system", "user", "assistant", "tool"
    content: str    # The message text


@dataclass
class ToolCall:
    """
    A tool call requested by the LLM (for agent mode).

    When the LLM decides to use a tool, it returns a ToolCall
    instead of a text response. The agent executes the tool
    and feeds the result back to the LLM.
    """

    name: str                       # Tool name (e.g., "query_logs")
    arguments: dict = field(default_factory=dict)  # Tool arguments as key-value pairs


@dataclass
class LLMResponse:
    """
    Response from an LLM API call.

    Either:
    - content is filled (text response) and tool_calls is empty
    - tool_calls is filled (agent wants to use tools) and content may be empty

    Never both — the LLM either responds with text OR requests tool calls.
    """

    content: str = ""                                # Text response
    tool_calls: list[ToolCall] = field(default_factory=list)  # Requested tool calls
    input_tokens: int = 0                            # Tokens in the prompt
    output_tokens: int = 0                           # Tokens in the response
    model: str = ""                                  # Model name used

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMClient(ABC):
    """
    Abstract LLM client — all providers implement this interface.

    Methods:
        chat()         → single request/response (for simple queries)
        stream_chat()  → streaming response (for real-time chat UI)
        embed()        → generate vector embeddings (for RAG)

    Each provider translates these calls to their specific API format.
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Send messages to the LLM and get a complete response.

        Args:
            messages: Conversation history (system + user + assistant messages)
            tools: Tool definitions for agent mode (None for simple chat)
            temperature: Randomness (0.0=deterministic, 1.0=creative)
            max_tokens: Maximum response length

        Returns:
            LLMResponse with either content (text) or tool_calls (agent action)
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens one at a time.

        Used by the chat UI — shows the response appearing word by word.
        Each yielded string is a small piece of the response (a few tokens).

        Yields:
            Text chunks as they're generated by the LLM
        """
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate vector embeddings for a list of texts.

        Used by RAG:
        - During ingestion: embed document chunks → store in pgvector
        - During query: embed the user's question → search pgvector

        Args:
            texts: List of strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)
            Dimensions: 768 (nomic-embed-text) or 1536 (OpenAI)
        """
        ...
