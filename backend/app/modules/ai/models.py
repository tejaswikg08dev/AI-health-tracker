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
    - Smaller chunks = more precise retrieval. If the answer is on page 15,
      we retrieve just that section, not the entire document.
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

    # Vector embedding — the numeric representation of this chunk's meaning
    # 768 dimensions for nomic-embed-text, 1536 for OpenAI text-embedding-3-small
    # The actual column is created in the migration with raw SQL (pgvector type)

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
