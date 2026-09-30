# 🤖 Phase 4 Part 12c: AI — Migration & Complete Architecture

> **"Migration 004 creates 4 tables and the pgvector IVFFlat index — the key that makes vector similarity search fast. Then: the complete 39-file AI architecture mapped, every file, every connection."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 12c (AI Migration + Architecture) |
| **Sprint** | Sprint 3 — AI Module |
| **Previous** | [phase4-part12b-ai-service-router.md](./phase4-part12b-ai-service-router.md) |
| **Next** | [phase4-part13-notifications-module-overview.md](./phase4-part13-notifications-module-overview.md) |
| **Files in This Doc** | 1 file (004_create_ai_tables.py) + architecture diagram |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (raw SQL for vector column, IVFFlat index, vector_cosine_ops) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File: 004_create_ai_tables.py — Full Source Code](#migration)
3. [The pgvector Embedding Column — Deep Dive](#pgvector)
4. [The IVFFlat Index — Why and How](#ivfflat)
5. [Complete AI Module Architecture (39 Files)](#architecture)
6. [AI Module — Complete Summary](#summary)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

One migration that creates 4 tables + 1 vector index:

| Table | Columns | Key Feature |
|-------|---------|------------|
| `documents` | 10 columns | Status state machine (uploaded → processing → processed) |
| `document_chunks` | 8 columns + **embedding vector(768)** | pgvector column for RAG similarity search |
| `ai_chat_messages` | 6 columns | Composite index on (user_id, created_at) |
| `ai_insights` | 7 columns | Stores weekly reports + on-demand insights |

Plus the **IVFFlat index** on the embedding column — this is what makes vector search fast.

---

<a name="migration"></a>
## 2. File: `004_create_ai_tables.py` — Full Source Code

### Type This Code: `backend/alembic/versions/004_create_ai_tables.py`

```python
"""create AI tables (documents, chunks with pgvector, chat messages, insights)

Revision ID: 004
Revises: 003
Create Date: 2026-09-26

WHAT THIS MIGRATION DOES:
    Creates 4 tables for the AI module:
    1. documents        — uploaded files (PDF, TXT) for RAG
    2. document_chunks  — text chunks with vector embeddings (pgvector)
    3. ai_chat_messages — conversation history
    4. ai_insights      — saved AI-generated reports and insights

    Also creates the IVFFlat index on the embedding column for fast
    approximate nearest neighbor search.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Table 1: documents ──
    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    # ── Table 2: document_chunks (with pgvector embedding) ──
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Add the vector embedding column using raw SQL (pgvector type)
    # 768 dimensions for nomic-embed-text (Ollama default)
    # Change to 1536 if using OpenAI text-embedding-3-small
    op.execute("""
        ALTER TABLE document_chunks
        ADD COLUMN embedding vector(768)
    """)

    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_user_id", "document_chunks", ["user_id"])

    # IVFFlat index for fast approximate nearest neighbor search
    # lists=100 is good for up to ~100K vectors
    # Use cosine distance operator class (vector_cosine_ops)
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)

    # ── Table 3: ai_chat_messages ──
    op.create_table(
        "ai_chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_chat_messages_user_id", "ai_chat_messages", ["user_id"])
    op.create_index("ix_ai_chat_messages_user_created", "ai_chat_messages", ["user_id", "created_at"])

    # ── Table 4: ai_insights ──
    op.create_table(
        "ai_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_insights_user_id", "ai_insights", ["user_id"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.drop_table("ai_insights")
    op.drop_table("ai_chat_messages")
    op.drop_table("document_chunks")
    op.drop_table("documents")
```

### Line-by-Line: Key New Concepts

**The pgvector Embedding Column (Raw SQL)**
```python
op.execute("""
    ALTER TABLE document_chunks
    ADD COLUMN embedding vector(768)
""")
```
- `vector(768)` is pgvector's data type — stores 768 floating-point numbers as a binary vector
- We use `op.execute()` (raw SQL) instead of `sa.Column()` because SQLAlchemy doesn't natively support the `vector` type
- **768 dimensions** = nomic-embed-text model (Ollama). If using OpenAI's text-embedding-3-small, change to `vector(1536)`
- This column stores the MEANING of each text chunk as numbers. Similar text → similar vectors → found by cosine search

**The IVFFlat Index (Raw SQL)**
```python
op.execute("""
    CREATE INDEX ix_document_chunks_embedding
    ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
""")
```
This is the most important line in the migration. Let me explain every part:

- `USING ivfflat` — the index type. IVFFlat = Inverted File Flat. An approximate nearest neighbor (ANN) algorithm
- `(embedding vector_cosine_ops)` — index the `embedding` column using cosine distance as the metric
- `WITH (lists = 100)` — divide vectors into 100 clusters. The search only scans nearby clusters, not all vectors

**Composite Index on Chat Messages**
```python
op.create_index("ix_ai_chat_messages_user_created", "ai_chat_messages", ["user_id", "created_at"])
```
- Most common query: "Get the 10 most recent messages for user X, ordered by date"
- `WHERE user_id = ? ORDER BY created_at DESC LIMIT 10`
- The composite index on `(user_id, created_at)` satisfies both the filter AND the ordering

**Downgrade — Drop in Reverse Order**
```python
def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.drop_table("ai_insights")
    op.drop_table("ai_chat_messages")
    op.drop_table("document_chunks")
    op.drop_table("documents")
```
- Drop the pgvector index FIRST (it's on the document_chunks table)
- Then drop tables in reverse dependency order: insights → messages → chunks → documents
- `document_chunks` has FK to `documents`, so chunks must go first

---

<a name="pgvector"></a>
## 3. The pgvector Embedding Column — Deep Dive

### What `vector(768)` Stores

```
Each row in document_chunks:
  chunk_text: "Magnesium-rich foods like almonds help sleep quality..."
  embedding:  [0.023, -0.156, 0.892, 0.041, -0.334, ..., 0.067]
              ← ─────────── 768 float numbers ─────────────── →

  This vector captures the MEANING of the text.
  Similar text produces similar vectors.
  The <=> operator measures how close two vectors are.
```

### How pgvector Was Enabled

In Migration 001 (Part 04e), we ran:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
This added the `vector` data type and operators (`<=>`, `<->`, `<#>`) to PostgreSQL. Migration 004 uses this type.

### Storage Cost

Each 768-dim vector = 768 × 4 bytes = ~3KB per chunk.
100 chunks per document × 3KB = ~300KB per document.
100 documents per user × 300KB = ~30MB per user.
PostgreSQL handles this comfortably — it's smaller than the text content itself.

---

<a name="ivfflat"></a>
## 4. The IVFFlat Index — Why and How

### Without Index (Brute Force)

```
Query: "What foods help sleep?"  → embedding: [0.019, -0.148, ...]

Scan ALL 10,000 chunks:
  Chunk 1:  distance = 0.45 (not close)
  Chunk 2:  distance = 0.78 (far)
  Chunk 3:  distance = 0.08 (very close!)  ←
  ...
  Chunk 10000: distance = 0.92 (far)

Sort by distance, return top 5.
Time: ~50ms for 10K chunks. ~500ms for 100K chunks.
```

### With IVFFlat Index (Approximate)

```
Index divides 10,000 chunks into 100 clusters.
Each cluster: ~100 chunks that are similar to each other.

Query: "What foods help sleep?"  → embedding: [0.019, -0.148, ...]

Step 1: Find the 5 closest CLUSTERS to the query vector  (~0.1ms)
Step 2: Scan only those 5 clusters (~500 chunks, not 10,000)  (~5ms)
Step 3: Return top 5 from those 500 chunks

Time: ~5ms (vs 50ms brute force) = 10× faster
Recall: ~95% (might miss 5% of exact matches — acceptable trade-off)
```

### When to Use Which Index

| Chunks | Index | Speed | Recall |
|--------|-------|-------|--------|
| <1,000 | None (brute force) | ~5ms | 100% |
| 1K–100K | IVFFlat (lists=100) | ~5ms | ~95% |
| 100K–1M | IVFFlat (lists=1000) | ~10ms | ~95% |
| >1M | HNSW (more accurate ANN) | ~2ms | ~99% |

Our scale: ~100-10K chunks per user. IVFFlat with 100 lists is perfect.

---

<a name="architecture"></a>
## 5. Complete AI Module Architecture (39 Files)

```
backend/app/modules/ai/                              PART
├── models.py              ← 4 SQLAlchemy models       12a
├── schemas.py             ← 8 Pydantic schemas        12a
├── service.py             ← 7-method orchestrator     12b
├── router.py              ← 9 endpoints + SSE         12b
│
├── llm/                   ← LLM LAYER (8 files)       08
│   ├── base_client.py           Strategy pattern       08a
│   ├── ollama_client.py         Ollama (free, local)   08b
│   ├── groq_client.py           Groq (free, cloud)     08b
│   ├── openai_client.py         OpenAI (paid, prod)    08b
│   ├── factory.py               get_llm_client()       08b
│   ├── prompt_templates.py      6 Jinja2 templates     08c
│   └── token_tracker.py         Redis daily limits     08c
│
├── rag/                   ← RAG LAYER (5 files)        09
│   ├── document_processor.py    PDF/TXT extraction     09a
│   ├── chunker.py               Recursive splitting    09a
│   ├── embeddings.py            Text → vectors         09a
│   ├── vector_store.py          pgvector CRUD          09b
│   └── retriever.py             Search + format        09b
│
├── agents/                ← AGENTS LAYER (10 files)    10
│   ├── base_agent.py            ★★★ ReAct loop        10c
│   ├── health_coach.py          Pre-configured agent   10c
│   ├── tools/
│   │   ├── base_tool.py         Abstract tool          10a
│   │   ├── query_logs.py        Fetch habit data       10a
│   │   ├── get_analytics.py     Get analytics          10a
│   │   ├── correlate.py         Find correlations      10a
│   │   ├── search_docs.py       RAG search             10a
│   │   └── create_plan.py       Generate plan          10a
│   └── memory/
│       ├── short_term.py        Conversation buffer    10b
│       └── long_term.py         Redis insights         10b
│
└── workflows/             ← WORKFLOWS LAYER (5 files)  11
    ├── base_workflow.py         Abstract + dataclasses  11a
    ├── orchestrator.py          Run + retry + log       11a
    └── weekly_report/
        ├── data_collector.py    Step 1: DB queries      11a
        ├── analyzer.py          Step 2: LLM analysis    11a
        └── report_writer.py     Step 3: LLM writing     11a

+ alembic/versions/004_create_ai_tables.py              12c (this file)

TOTAL: 39 Python files across 4 layers
```

---

<a name="summary"></a>
## 6. AI Module — Complete Summary

### By the Numbers

| Metric | Value |
|--------|-------|
| **Total files** | 39 |
| **Database tables** | 4 (documents, chunks, messages, insights) |
| **Endpoints** | 9 (chat × 3, documents × 3, insights × 2, report × 1) |
| **LLM providers** | 3 (Ollama, Groq, OpenAI) via Strategy pattern |
| **Agent tools** | 5 (query_logs, get_analytics, correlate, search_docs, create_plan) |
| **Memory types** | 2 (short-term: conversation, long-term: Redis insights) |
| **RAG pipeline steps** | 4 (extract → chunk → embed → store) |
| **Workflow steps** | 3 (collect → analyze → write) |
| **Design patterns** | Strategy, Factory, Abstract Base, ReAct, Pipeline |
| **Prompt templates** | 6 (Jinja2) |
| **Migrations** | 1 (004 — creates 4 tables + IVFFlat index) |

### 🎉 THE AI MODULE IS COMPLETE

| Layer | Parts | Docs | Status |
|-------|-------|------|--------|
| LLM | 08a-08c | 4 docs | ✅ Strategy pattern, 3 providers, prompts, tokens |
| RAG | 09a-09c | 4 docs | ✅ Ingestion, pgvector search, retrieval |
| Agents | 10a-10d | 5 docs | ✅ 5 tools, memory, ReAct loop ★★★ |
| Workflows | 11-11b | 3 docs | ✅ Pipeline, orchestrator, weekly report |
| Service/Router | 12-12c | 4 docs | ✅ 9 endpoints, SSE, models, migration |
| **Total** | | **20 docs** | ✅ |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: How does the IVFFlat index speed up vector search?
**A:** "IVFFlat divides all vectors into clusters (we use 100 lists). When searching, instead of comparing the query against ALL vectors (brute force), it first finds the closest clusters, then only scans those clusters' vectors. For 10,000 chunks, brute force scans 10,000 vectors (~50ms). IVFFlat scans ~500 vectors across 5 closest clusters (~5ms). The trade-off is ~95% recall — it might miss 5% of exact matches. For RAG, this is fine because we retrieve 5 chunks and only need 3-4 relevant ones."

### Q2: Why raw SQL for the embedding column instead of SQLAlchemy?
**A:** "SQLAlchemy doesn't natively support pgvector's `vector` type. We use `op.execute('ALTER TABLE ... ADD COLUMN embedding vector(768)')` in the migration and `text('SELECT ... ORDER BY embedding <=> ...')` in the VectorStore. This keeps the migration and queries explicit. The model (`DocumentChunk`) doesn't define the embedding column — it's only accessed through raw SQL in the VectorStore class."

### Q3: Walk me through the complete AI module architecture.
**A:** "39 files across 4 layers. The LLM layer provides a Strategy-pattern interface to 3 providers. The RAG layer handles document ingestion (extract → chunk → embed → store in pgvector) and retrieval (embed query → cosine search → format context). The Agents layer implements a ReAct loop with 5 tools and dual memory. The Workflows layer orchestrates multi-step AI tasks with retry logic. The service ties all 4 layers into 9 endpoints including SSE streaming and file upload. Migration 004 creates 4 database tables with a pgvector IVFFlat index for fast similarity search."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 12b: AI Service & Router](./phase4-part12b-ai-service-router.md) |
| ➡️ Next | [Phase 4 Part 13: Notifications Module Overview](./phase4-part13-notifications-module-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Part 12 — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 12a | ✅ AI Models & Schemas (4 models, 8 schemas) |
| 12b | ✅ AI Service & Router (7 methods, 9 endpoints, SSE) |
| **12c** | ✅ **AI Migration & Architecture (4 tables, IVFFlat, 39-file map)** |

---

**🎉 THE ENTIRE AI MODULE IS COMPLETE — 20 docs across Parts 08-12.**

*39 files, 4 layers, 9 endpoints, built from scratch. Next: Notifications module — daily reminders, streak milestones, email templates, and the Strategy pattern again for email providers.*
