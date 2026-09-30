# ============================================================================
# AI Module — Pydantic Schemas
# ============================================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.base_schemas import BaseSchema


# ── Chat ──

class ChatRequest(BaseModel):
    """
    User message to the AI health coach.

    use_agent: If true, uses the ReAct agent (tool-calling, multi-step).
               If false, uses direct LLM chat (faster, simpler).
               Default: true (agent mode gives better answers).
    """

    message: str = Field(
        ..., min_length=1, max_length=2000,
        description="User's question or message",
        examples=["How much did I sleep this week?", "Why am I feeling tired?"],
    )
    use_agent: bool = Field(
        default=True,
        description="Use AI agent (tool-calling) vs direct chat",
    )


class ChatMessage(BaseSchema):
    """Single chat message in the conversation history."""

    id: UUID
    role: str       # "user" or "assistant"
    content: str
    tokens_used: int
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """List of past chat messages."""

    messages: list[ChatMessage]


# ── Documents (RAG) ──

class DocumentResponse(BaseSchema):
    """Uploaded document metadata."""

    id: UUID
    filename: str
    file_type: str
    file_size: int
    page_count: int | None
    status: str
    chunk_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    """List of user's uploaded documents."""

    documents: list[DocumentResponse]


# ── Insights ──

class InsightResponse(BaseSchema):
    """AI-generated insight."""

    id: UUID
    insight_type: str
    title: str
    content: str
    tokens_used: int
    created_at: datetime


class InsightListResponse(BaseModel):
    """List of AI insights."""

    insights: list[InsightResponse]


# ── Streaming ──

class StreamChunk(BaseModel):
    """
    A single chunk of a streaming AI response.

    Used with Server-Sent Events (SSE) — the AI response appears
    word-by-word in the chat UI, just like ChatGPT.

    chunk_type:
    - "token"   → a piece of the response text
    - "done"    → response is complete
    - "error"   → an error occurred during generation
    - "tool_call" → agent is calling a tool (shown as "Checking your data...")
    """

    chunk_type: str = Field(description="token, done, error, or tool_call")
    content: str = Field(default="", description="Text content of this chunk")
    tool_name: str | None = Field(default=None, description="Tool being called (for tool_call type)")
