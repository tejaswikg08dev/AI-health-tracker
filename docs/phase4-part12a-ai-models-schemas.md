# 🤖 Phase 4 Part 12a: AI — Models & Schemas

> **"4 database models power the AI: Document tracks uploads, DocumentChunk stores text+embeddings for RAG, AiChatMessage keeps conversation history, AiInsight saves generated reports. The schemas define what goes in and out of 9 endpoints."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 12a (AI Models & Schemas) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.5 — AI Endpoints & SSE Streaming |
| **Previous** | [phase4-part12-ai-service-router-overview.md](./phase4-part12-ai-service-router-overview.md) |
| **Next** | [phase4-part12b-ai-service-router.md](./phase4-part12b-ai-service-router.md) |
| **Files in This Doc** | 2 files (models.py ~230 lines, schemas.py ~100 lines) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (pgvector column, status state machine, streaming chunk schema, try/except import) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: models.py — 4 AI Database Models](#models)
3. [File 2: schemas.py — 8 Request/Response Schemas](#schemas)
4. [How Models and Schemas Connect](#connections)
5. [Design Decisions](#design-decisions)
6. [How to Verify Your Work](#verify)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Two files that define the data layer for all AI features:

| File | Contains | Used By |
|------|----------|---------|
| `models.py` | 4 SQLAlchemy models (Document, DocumentChunk, AiChatMessage, AiInsight) | Service (DB operations) |
| `schemas.py` | 8 Pydantic schemas (ChatRequest, DocumentResponse, StreamChunk, etc.) | Router (request/response validation) |

### What's New in These Models (Not in Previous Modules)

| Concept | What It Is | Where |
|---------|-----------|-------|
| **pgvector `Vector` column** | Stores 768-dimension float array for similarity search | DocumentChunk |
| **Status state machine** | `uploaded → processing → processed / failed` | Document.status |
| **try/except import** | Graceful fallback if pgvector package isn't installed | Top of models.py |
| **`StreamChunk` schema** | SSE event types: token, done, error, tool_call | schemas.py |
| **`UploadFile` response** | Response for file upload (not just JSON create) | DocumentResponse |

---

<a name="models"></a>
## 2. File 1: `models.py` — 4 AI Database Models

### Type This Code: `backend/app/modules/ai/models.py`

```python
# ============================================================================
# AI Module — Database Models
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines tables for: uploaded documents, document chunks (with vector
#   embeddings for RAG), AI chat messages, and AI-generated insights.
#
# TABLES:
#   documents        → user-uploaded health PDFs/texts for RAG
#   document_chunks  → text chunks with vector embeddings (pgvector)
#   ai_chat_messages → conversation history (user + assistant messages)
#   ai_insights      → saved AI-generated insights (from weekly reports)
#
# KEY CONCEPT — pgvector:
#   pgvector adds a 'vector' column type to PostgreSQL.
#   Each chunk's text is converted to a 768-dimension float array (embedding).
#   Similarity search: find chunks whose embeddings are closest to the query.
#   This is HOW RAG retrieves relevant context — not keyword matching,
#   but MEANING matching via vector distance (cosine similarity).
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# pgvector column type — stores embedding vectors
# Import will fail if pgvector isn't installed, but the column definition
# uses a string-based type so SQLAlchemy doesn't need the import at define-time.
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback for environments without pgvector (e.g., running tests locally)
    Vector = None


class Document(Base):
    """
    User-uploaded document for RAG (Retrieval-Augmented Generation).

    Users upload health-related PDFs, text files, or markdown:
    - Blood test reports
    - Doctor's notes
    - Nutrition guides
    - Fitness plans

    After upload, the document is processed:
    1. Text extracted (PDF → plain text)
    2. Split into chunks (~500 tokens each)
    3. Each chunk embedded (text → vector)
    4. Chunks stored in document_chunks table

    STATUS FLOW:
        uploaded → processing → processed (ready for search)
                             → failed (extraction error)
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="File extension: pdf, txt, md",
    )
    file_size: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="File size in bytes",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Number of pages (PDF only)",
    )

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="uploaded", server_default="uploaded",
        nullable=False,
        comment="uploaded, processing, processed, failed",
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0",
        comment="Number of chunks created from this document",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Error message if processing failed",
    )

    # S3 storage key
    s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="S3/MinIO object key for the original file",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class DocumentChunk(Base):
    """
    A text chunk from a document, with its vector embedding.

    THIS IS THE CORE OF RAG:
    1. Document text is split into overlapping chunks (~500 tokens)
    2. Each chunk is converted to a vector embedding (768 or 1536 dimensions)
    3. When the user asks a question, the question is also embedded
    4. We find chunks whose embeddings are closest to the question embedding
    5. Those chunks become the "context" sent to the LLM along with the question

    WHY CHUNKS (not full documents):
    - LLMs have token limits (4K-128K). A 50-page PDF won't fit.
    - Smaller chunks = more precise retrieval.
    - Overlap ensures context isn't lost at chunk boundaries.

    VECTOR COLUMN:
    - Uses pgvector extension (CREATE EXTENSION vector)
    - Stores a float array of 768 dimensions (nomic-embed-text)
    - Indexed with IVFFlat for fast approximate nearest neighbor search
    - Cosine similarity: 1.0 = identical meaning, 0.0 = unrelated
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Chunk content
    chunk_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="The actual text content of this chunk",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Order of this chunk within the document (0-based)",
    )
    page_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Page number in the original document (PDF only)",
    )

    # Token count for this chunk
    token_count: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Number of tokens in this chunk (for context window management)",
    )

    # Vector embedding — the actual column is created in migration with raw SQL
    # 768 dimensions for nomic-embed-text, 1536 for OpenAI text-embedding-3-small

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id}, doc={self.document_id}, "
            f"index={self.chunk_index}, tokens={self.token_count})>"
        )


class AiChatMessage(Base):
    """
    AI chat conversation history.

    Stores both user messages and assistant responses.
    Used for: displaying chat history, providing conversation context to the LLM.

    ROLE VALUES:
    - "user"      → message from the user
    - "assistant"  → response from the AI
    - "system"     → system instructions (rarely stored, usually in-memory)

    WHY STORE CHAT HISTORY:
    1. Users can scroll back and see past conversations
    2. The LLM needs conversation history for context
    3. AI agents reference past interactions for long-term memory
    4. Analytics: how often is the AI used, what topics are discussed
    """

    __tablename__ = "ai_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Message role: user, assistant, system",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Message content (user question or AI response)",
    )

    # Token usage tracking (for cost monitoring)
    tokens_used: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Tokens consumed by this message (input + output for assistant)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<AiChatMessage(role={self.role}, preview='{preview}')>"


class AiInsight(Base):
    """
    AI-generated insight stored for later reference.

    Created by: weekly report workflow, on-demand insight generation.
    Stored so the user can review past insights without re-generating.

    INSIGHT TYPES:
    - "weekly_report" → generated by the weekly report agentic workflow
    - "on_demand"     → user clicked "Generate Insights" button
    - "correlation"   → AI explanation of a detected correlation
    """

    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    insight_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Type: weekly_report, on_demand, correlation",
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="Short title for the insight",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Full insight text (markdown formatted)",
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, default=0,
        comment="Total tokens consumed to generate this insight",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AiInsight(type={self.insight_type}, title='{self.title}')>"
```

### Line-by-Line Explanation: Key New Concepts

**try/except Import for pgvector**
```python
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None
```
- `pgvector.sqlalchemy` provides the `Vector(768)` column type for SQLAlchemy
- If the package isn't installed (e.g., running tests without Docker), the import fails gracefully
- `Vector = None` — the model still loads, but the embedding column is defined in the migration with raw SQL instead
- This is a **defensive import** — the app doesn't crash if one optional dependency is missing

**Document Status State Machine**
```python
status: Mapped[str] = mapped_column(
    String(20), default="uploaded", server_default="uploaded",
    comment="uploaded, processing, processed, failed",
)
```
- A document goes through states: `uploaded` → `processing` → `processed` or `failed`
- The service updates the status at each stage of the RAG ingestion pipeline
- The frontend shows different UI based on status:
  - `uploaded/processing` → spinner + "Processing your document..."
  - `processed` → "Ready for search" + chunk count
  - `failed` → error message

```
uploaded ──→ processing ──→ processed  (success: chunks created, searchable)
                        └──→ failed    (error: PDF parsing failed, text empty)
```

**Two Foreign Keys on DocumentChunk**
```python
document_id: UUID (FK → documents.id, CASCADE)
user_id: UUID (FK → users.id, CASCADE)
```
- `document_id` — which document this chunk came from. CASCADE: delete document → delete all its chunks
- `user_id` — who owns this chunk. Used in vector search: `WHERE user_id = ?` (row-level security)
- Why BOTH FKs? `document_id` is for document management. `user_id` is for search queries — avoids a JOIN

**The Embedding Column (Not in SQLAlchemy Model)**

Notice: there's NO `embedding` column in the `DocumentChunk` model. Why?

The embedding is a pgvector `vector(768)` type — created in the migration with raw SQL:
```sql
ALTER TABLE document_chunks ADD COLUMN embedding vector(768)
```

We interact with it via raw SQL in `VectorStore` (Part 09b), not through the ORM. This keeps the model portable (works without pgvector installed) while the migration and queries handle the vector operations.

**`Text` Column Type (Not `String`)**
```python
content: Mapped[str] = mapped_column(Text, nullable=False)
chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
```
- `String(255)` → PostgreSQL `VARCHAR(255)` — limited length
- `Text` → PostgreSQL `TEXT` — unlimited length
- Chat messages and chunk text can be thousands of characters — `Text` has no length limit

**Content Preview in `__repr__`**
```python
def __repr__(self) -> str:
    preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
    return f"<AiChatMessage(role={self.role}, preview='{preview}')>"
```
- Truncates content to 50 characters for readable debug output
- A 5000-character AI response would make `repr()` unreadable without truncation

---

<a name="schemas"></a>
## 3. File 2: `schemas.py` — 8 Request/Response Schemas

### Type This Code: `backend/app/modules/ai/schemas.py`

```python
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
```

### Key Schema Concepts

**`ChatRequest` — Two Chat Modes in One Endpoint**
```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    use_agent: bool = Field(default=True)
```
- `message` — the user's question, max 2000 characters (prevents abuse, fits in prompt)
- `use_agent=True` (default) — ReAct agent with tools. Slower but data-driven
- `use_agent=False` — direct LLM call. Faster for general knowledge questions
- One endpoint handles both modes — the service decides which path to take

**`ChatMessage` extends `BaseSchema` (has `from_attributes=True`)**
```python
class ChatMessage(BaseSchema):
    id: UUID
    role: str
    content: str
```
- Created from `AiChatMessage` ORM objects: `ChatMessage.model_validate(db_message)`
- `BaseSchema` provides `from_attributes=True` for ORM → Pydantic conversion

**`DocumentResponse` — Status for Frontend UI**
```python
class DocumentResponse(BaseSchema):
    id: UUID
    filename: str
    status: str       # "uploaded" | "processing" | "processed" | "failed"
    chunk_count: int   # 0 while processing, 100 after processed
```
- Frontend renders different UI per status:
  - `processing` → spinner + "Analyzing your document..."
  - `processed` → ✅ "Ready! 100 searchable chunks"
  - `failed` → ❌ error message

**`StreamChunk` — SSE Event Schema**
```python
class StreamChunk(BaseModel):
    chunk_type: str    # "token", "done", "error", "tool_call"
    content: str       # The actual text chunk
    tool_name: str | None  # Which tool the agent is calling
```
- `"token"` — a piece of the response text (most common)
- `"done"` — response complete, close the SSE connection
- `"error"` — something went wrong during generation
- `"tool_call"` — agent is calling a tool, frontend shows "Checking your data..."
- This schema defines the CONTRACT for SSE events — frontend knows exactly what to expect

---

<a name="connections"></a>
## 4. How Models and Schemas Connect

```
POST /ai/chat  Body: {"message": "How's my sleep?", "use_agent": true}
  │
  ├── ChatRequest schema validates the body
  │     ✅ message: 1-2000 chars
  │     ✅ use_agent: boolean (default true)
  │
  ├── Service creates AiChatMessage:
  │     INSERT INTO ai_chat_messages (user_id, role="user", content="How's my sleep?")
  │
  ├── Agent runs → generates response
  │
  ├── Service creates AiChatMessage:
  │     INSERT INTO ai_chat_messages (user_id, role="assistant", content="Your sleep averaged...")
  │
  └── Response: {"response": "Your sleep averaged 6.8 hours this week..."}


POST /ai/documents  Body: multipart form (file upload)
  │
  ├── UploadFile received (no Pydantic schema — FastAPI handles file upload natively)
  │
  ├── Service creates Document:
  │     INSERT INTO documents (user_id, filename, status="processing")
  │
  ├── RAG pipeline runs → creates DocumentChunks:
  │     INSERT INTO document_chunks (chunk_text, embedding, ...) × 100
  │
  ├── Service updates Document:
  │     UPDATE documents SET status="processed", chunk_count=100
  │
  └── Response: DocumentResponse(status="processed", chunk_count=100, ...)


GET /ai/insights
  │
  ├── Service queries: SELECT * FROM ai_insights WHERE user_id = ? ORDER BY created_at DESC
  │
  └── Response: InsightListResponse(insights=[InsightResponse.model_validate(i) for i in results])
```

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision: Embedding Column in Migration, Not Model

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: pgvector Embedding Column Strategy                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Define embedding column in migration (raw SQL), not model  │
│                                                                     │
│  WHY:                                                               │
│  • Model stays portable — works without pgvector package installed  │
│  • Migration uses raw SQL: ALTER TABLE ADD COLUMN embedding vector(768)│
│  • VectorStore uses raw SQL: SELECT ... ORDER BY embedding <=>      │
│  • try/except import prevents crash if pgvector.sqlalchemy missing  │
│                                                                     │
│  ALTERNATIVE: Define in model with Vector(768)                      │
│    ⚠️ Requires pgvector package at import time                     │
│    ⚠️ Some test environments don't have pgvector installed         │
│                                                                     │
│  INTERVIEW TIP: "We define the embedding column in the migration    │
│  with raw SQL to keep the model portable. The model loads without   │
│  pgvector installed — useful for tests and environments without     │
│  PostgreSQL. Vector operations happen in raw SQL via VectorStore."  │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 6. How to Verify Your Work

```bash
docker-compose exec backend python -c "
from app.modules.ai.models import Document, DocumentChunk, AiChatMessage, AiInsight
print(f'Document table: {Document.__tablename__}')
print(f'  Columns: {[c.name for c in Document.__table__.columns]}')
print(f'DocumentChunk table: {DocumentChunk.__tablename__}')
print(f'AiChatMessage table: {AiChatMessage.__tablename__}')
print(f'AiInsight table: {AiInsight.__tablename__}')

from app.modules.ai.schemas import ChatRequest, DocumentResponse, InsightResponse, StreamChunk
req = ChatRequest(message='How is my sleep?')
print(f'ChatRequest: message={req.message}, use_agent={req.use_agent}')

chunk = StreamChunk(chunk_type='token', content='Your ')
print(f'StreamChunk: type={chunk.chunk_type}, content={chunk.content}')

print('✅ All AI models and schemas import OK')
"
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **try/except import** | Graceful fallback if optional package missing | pgvector import |
| 2 | **Status state machine** | `uploaded → processing → processed / failed` | Document.status |
| 3 | **`Text` column type** | Unlimited string length (vs `String(255)`) | content, chunk_text |
| 4 | **Two FK on one table** | document_id (parent doc) + user_id (owner) | DocumentChunk |
| 5 | **CASCADE on both FKs** | Delete user/doc → auto-delete chunks | DocumentChunk FKs |
| 6 | **Embedding column via migration** | Not in model — created with raw SQL | Migration 004 |
| 7 | **Content preview in repr** | `content[:50] + "..."` for readable debug | AiChatMessage.__repr__ |
| 8 | **`BaseSchema` vs `BaseModel`** | BaseSchema for ORM objects, BaseModel for manual construction | ChatMessage vs StreamChunk |
| 9 | **StreamChunk schema** | SSE event contract: token/done/error/tool_call | schemas.py |
| 10 | **`use_agent` toggle** | One endpoint, two modes (agent vs direct) | ChatRequest |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: Why isn't the embedding column in the SQLAlchemy model?
**A:** "Portability. The pgvector `Vector(768)` type requires the `pgvector` Python package at import time. Not all environments have it — local tests without Docker, CI without PostgreSQL. By defining the column in the migration with raw SQL (`ALTER TABLE ADD COLUMN embedding vector(768)`), the model loads anywhere. Vector operations happen through raw SQL in the VectorStore class, not through the ORM. This is the same approach Supabase uses."

### Q2: What is the Document status state machine?
**A:** "A document goes through 4 states: `uploaded` (file received), `processing` (RAG pipeline running: extract → chunk → embed), `processed` (all chunks stored, searchable), or `failed` (any step errored — PDF corrupt, embedding API down). The service updates status at each stage. The frontend renders different UI per status — spinner for processing, checkmark for processed, error for failed. The status field is a string, not an enum, for the same reason as habit types: adding new states doesn't require a migration."

### Q3: Why store both user_id AND document_id on DocumentChunk?
**A:** "Performance. The most common query is `SELECT ... FROM document_chunks WHERE user_id = ? ORDER BY embedding <=>` — similarity search scoped to one user. If we only had `document_id`, we'd need a JOIN to `documents` to get `user_id` on every vector search. By denormalizing `user_id` onto chunks, the query is a single-table scan with the pgvector index. The trade-off is slight data duplication (~16 bytes per chunk for the UUID), which is negligible."

### Q4: What does the StreamChunk schema enable?
**A:** "It defines the SSE event contract. Each streamed chunk has a `chunk_type`: `token` (text to append), `done` (close connection), `error` (show error), `tool_call` (show 'Checking your data...'). The frontend switches behavior based on type. Without this contract, the frontend would have to guess what each SSE event means — fragile parsing. With it, the frontend just reads `chunk_type` and acts accordingly."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 12: AI Service Overview](./phase4-part12-ai-service-router-overview.md) |
| ➡️ Next | [Phase 4 Part 12b: AI Service & Router](./phase4-part12b-ai-service-router.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Part 12 Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **12a** | ✅ **You are here** | AI Models & Schemas |
| 12b | ⬜ Next | AI Service & Router |
| 12c | ⬜ | AI Migration & Architecture |

---

**End of Phase 4 Part 12a: AI Models & Schemas**

*4 database models and 8 schemas define the data layer for all AI features. The pgvector embedding column, status state machine, and SSE StreamChunk are new patterns not seen in previous modules. Next: the service that orchestrates everything, and the router with SSE streaming.*
