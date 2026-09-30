# 🔍 Phase 4 Part 09b: RAG — Retrieval (Vector Search + Context)

> **"This is where the magic happens. The user asks 'What foods help sleep?' — we embed their question into a vector, search pgvector for the most similar document chunks, format them with source citations, and inject them into the LLM prompt. The AI answers from YOUR documents."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 09b (RAG Retrieval — Search + Format) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.2 — Document-Based AI |
| **Previous** | [phase4-part09a-ai-rag-ingestion.md](./phase4-part09a-ai-rag-ingestion.md) |
| **Next** | [phase4-part09c-ai-rag-connections-and-flows.md](./phase4-part09c-ai-rag-connections-and-flows.md) |
| **Files in This Doc** | 2 files (vector_store.py, retriever.py) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Hard (pgvector `<=>` operator, cosine distance, token budgeting, raw SQL) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: vector_store.py — pgvector Operations](#vector-store)
3. [File 2: retriever.py — Full Retrieval Pipeline](#retriever)
4. [How Cosine Similarity Search Works](#cosine)
5. [Design Decisions](#design-decisions)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Two files that handle storage and search:

| File | Role | When It Runs |
|------|------|-------------|
| `vector_store.py` | Store chunks + search by similarity | Ingestion (store) + Retrieval (search) |
| `retriever.py` | Orchestrate: embed query → search → format context | Every chat query that needs document context |

```
RETRIEVAL PIPELINE:
  User: "What foods help sleep?"
    │
    ▼ retriever.py
  embed_query("What foods help sleep?")
    → [0.019, -0.148, 0.897, ..., 0.039]
    │
    ▼ vector_store.py
  similarity_search(user_id, query_embedding, top_k=5)
    → SQL: SELECT ... ORDER BY embedding <=> query_vec LIMIT 5
    → [{chunk_text: "Magnesium helps...", similarity: 0.92}, ...]
    │
    ▼ retriever.py
  _format_context(chunks)
    → "RELEVANT DOCUMENTS:\n[Source: Sleep Guide.pdf, Page 3]\nMagnesium..."
    │
    ▼
  Return RetrievedContext(formatted_context, sources, chunk_count, total_tokens)
```

---

<a name="vector-store"></a>
## 2. File 1: `vector_store.py` — pgvector Operations

### Type This Code: `backend/app/modules/ai/rag/vector_store.py`

```python
# ============================================================================
# RAG — Vector Store (pgvector)
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores and searches document chunk embeddings using PostgreSQL + pgvector.
#
# HOW VECTOR SEARCH WORKS:
#   1. The user's question is embedded into a vector
#   2. pgvector calculates COSINE DISTANCE between query and all chunks
#   3. Returns the TOP K chunks with smallest distance (most similar)
#   4. The <=> operator is pgvector's cosine distance operator
# ============================================================================

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    pgvector operations for document chunks.
    Uses raw SQL because pgvector operators aren't in SQLAlchemy ORM.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def store_chunk(
        self,
        chunk_id: str,
        document_id: str,
        user_id: str,
        chunk_text: str,
        chunk_index: int,
        page_number: int | None,
        token_count: int,
        embedding: list[float],
    ) -> None:
        """
        Store a document chunk with its embedding vector.
        The embedding is cast to pgvector's vector type via ::vector.
        """
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        await self.session.execute(
            text("""
                INSERT INTO document_chunks
                (id, document_id, user_id, chunk_text, chunk_index,
                 page_number, token_count, embedding, created_at)
                VALUES
                (:id, :document_id, :user_id, :chunk_text, :chunk_index,
                 :page_number, :token_count, :embedding::vector, NOW())
            """),
            {
                "id": chunk_id,
                "document_id": document_id,
                "user_id": user_id,
                "chunk_text": chunk_text,
                "chunk_index": chunk_index,
                "page_number": page_number,
                "token_count": token_count,
                "embedding": embedding_str,
            },
        )

    async def similarity_search(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
        similarity_threshold: float = 0.3,
    ) -> list[dict]:
        """
        Find the most similar document chunks to a query embedding.

        Uses pgvector's <=> cosine distance operator.
        Similarity = 1 - distance (0=unrelated, 1=identical).
        """
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        result = await self.session.execute(
            text("""
                SELECT
                    dc.chunk_text,
                    dc.page_number,
                    dc.chunk_index,
                    d.filename,
                    d.id AS document_id,
                    1 - (dc.embedding <=> :query_embedding::vector) AS similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.user_id = :user_id
                  AND d.status = 'processed'
                  AND 1 - (dc.embedding <=> :query_embedding::vector) > :threshold
                ORDER BY dc.embedding <=> :query_embedding::vector
                LIMIT :top_k
            """),
            {
                "user_id": user_id,
                "query_embedding": embedding_str,
                "threshold": similarity_threshold,
                "top_k": top_k,
            },
        )

        rows = result.mappings().all()

        logger.info(
            "vector_search_completed",
            user_id=user_id,
            results=len(rows),
            top_similarity=round(float(rows[0]["similarity"]), 3) if rows else 0,
        )

        return [dict(row) for row in rows]

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document (when user removes it)."""
        result = await self.session.execute(
            text("DELETE FROM document_chunks WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        await self.session.flush()
        count = result.rowcount
        logger.info("chunks_deleted", document_id=document_id, count=count)
        return count

    async def get_chunk_count(self, user_id: str) -> int:
        """Count total chunks stored for a user."""
        result = await self.session.execute(
            text("SELECT COUNT(*) FROM document_chunks WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        return result.scalar_one()
```

### Key pgvector Concepts

**The `<=>` Operator — Cosine Distance**
```sql
SELECT 1 - (dc.embedding <=> :query_embedding::vector) AS similarity
FROM document_chunks dc
ORDER BY dc.embedding <=> :query_embedding::vector
LIMIT 5;
```

- `<=>` is pgvector's **cosine distance** operator
- Returns a distance between 0 (identical) and 2 (opposite)
- We convert to **similarity**: `1 - distance` → 0 (unrelated) to 1 (identical)
- `ORDER BY ... <=>` sorts by closest match first
- `::vector` casts the string to pgvector's vector type

**Similarity Threshold Filter**
```sql
AND 1 - (dc.embedding <=> :query_embedding::vector) > :threshold
```
- Only return chunks with similarity > 0.3 (30%)
- Prevents returning irrelevant chunks when no documents match the query
- Without this, you'd always get 5 results — even if none are relevant

**Embedding String Format**
```python
embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
```
- pgvector expects vectors as strings: `"[0.12,-0.45,0.78,...,0.33]"`
- Python list → string with brackets and commas
- `::vector` in SQL casts this string to the binary vector type

**User Scoping**
```sql
WHERE dc.user_id = :user_id
  AND d.status = 'processed'
```
- Only search THIS user's documents (same row-level security as habits/logs)
- Only search documents with `status = 'processed'` (ingestion might still be running)

---

<a name="retriever"></a>
## 3. File 2: `retriever.py` — Full Retrieval Pipeline

### Type This Code: `backend/app/modules/ai/rag/retriever.py`

```python
# ============================================================================
# RAG — Retriever
# ============================================================================
# WHAT THIS FILE DOES:
#   Orchestrates the full retrieval pipeline:
#   1. Embed the user's question
#   2. Search pgvector for similar chunks
#   3. Build a formatted context string with source citations
#   4. Return context ready to inject into the LLM prompt
# ============================================================================

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.rag.embeddings import EmbeddingGenerator
from app.modules.ai.rag.vector_store import VectorStore
from app.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedContext:
    """
    The result of a retrieval operation.

    formatted_context: Ready to inject into the LLM prompt
    sources: List of source references (for citation display in UI)
    chunk_count: How many chunks were retrieved
    total_tokens: Estimated tokens in the context
    """

    formatted_context: str
    sources: list[dict]
    chunk_count: int
    total_tokens: int


class Retriever:
    """
    Full RAG retrieval pipeline.

    Usage:
        retriever = Retriever(session)
        context = await retriever.retrieve("How much iron do I need?", user_id)
        # context.formatted_context → ready for LLM prompt
        # context.sources → for UI citation display
    """

    def __init__(self, session: AsyncSession):
        self.vector_store = VectorStore(session)
        self.embedding_generator = EmbeddingGenerator()

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        max_context_tokens: int = 2000,
    ) -> RetrievedContext:
        """
        Retrieve relevant document chunks for a query.

        PIPELINE:
        1. Embed the query text → vector
        2. Search pgvector for similar chunks
        3. Filter by token budget (don't exceed max_context_tokens)
        4. Format into a context string with citations
        5. Return context + source metadata
        """
        # Step 1: Embed the query
        query_embedding = await self.embedding_generator.embed_query(query)

        if not query_embedding:
            logger.warning("empty_query_embedding", query=query[:50])
            return RetrievedContext(formatted_context="", sources=[], chunk_count=0, total_tokens=0)

        # Step 2: Search for similar chunks
        results = await self.vector_store.similarity_search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not results:
            logger.info("no_relevant_chunks", query=query[:50])
            return RetrievedContext(formatted_context="", sources=[], chunk_count=0, total_tokens=0)

        # Step 3: Build context within token budget
        context_chunks = []
        sources = []
        total_tokens = 0

        for chunk in results:
            chunk_tokens = len(chunk["chunk_text"]) // 4

            if total_tokens + chunk_tokens > max_context_tokens:
                break

            context_chunks.append(chunk)
            total_tokens += chunk_tokens

            source = {
                "filename": chunk["filename"],
                "page_number": chunk["page_number"],
                "similarity": round(float(chunk["similarity"]), 3),
                "document_id": str(chunk["document_id"]),
            }
            if source not in sources:
                sources.append(source)

        # Step 4: Format context with citations
        formatted = self._format_context(context_chunks)

        logger.info(
            "retrieval_completed",
            query=query[:50],
            chunks_retrieved=len(context_chunks),
            total_tokens=total_tokens,
            sources=len(sources),
        )

        return RetrievedContext(
            formatted_context=formatted,
            sources=sources,
            chunk_count=len(context_chunks),
            total_tokens=total_tokens,
        )

    @staticmethod
    def _format_context(chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a readable context for the LLM prompt.
        Each chunk gets a source citation header.
        """
        if not chunks:
            return ""

        parts = ["RELEVANT INFORMATION FROM YOUR DOCUMENTS:\n"]

        for chunk in chunks:
            page_info = f", Page {chunk['page_number']}" if chunk["page_number"] else ""
            header = f"[Source: {chunk['filename']}{page_info}]"
            parts.append(f"{header}\n{chunk['chunk_text']}\n---")

        parts.append(
            "\nUse the above information to help answer the user's question. "
            "Cite sources when referencing document content."
        )

        return "\n".join(parts)
```

### The Retrieval Pipeline Step by Step

**Step 1: Embed the Query**
```python
query_embedding = await self.embedding_generator.embed_query(query)
```
- "What foods help sleep?" → `[0.019, -0.148, 0.897, ..., 0.039]`
- Uses the same embedding model as ingestion — vectors are comparable
- If embedding fails → return empty context (graceful degradation)

**Step 2: Search pgvector**
```python
results = await self.vector_store.similarity_search(
    user_id=user_id, query_embedding=query_embedding, top_k=5, similarity_threshold=0.3,
)
```
- Returns up to 5 chunks with similarity > 0.3
- Results are ordered by similarity (highest first)
- Each result: `{chunk_text, filename, page_number, similarity}`

**Step 3: Token Budget**
```python
for chunk in results:
    chunk_tokens = len(chunk["chunk_text"]) // 4
    if total_tokens + chunk_tokens > max_context_tokens:
        break
```
- LLMs have context limits — can't inject 10,000 tokens of context
- `max_context_tokens=2000` — we stop adding chunks when we'd exceed this
- Most relevant chunks are added first (sorted by similarity)
- This ensures the MOST relevant content fits, and less relevant is dropped

**Step 4: Format with Citations**
```python
RELEVANT INFORMATION FROM YOUR DOCUMENTS:

[Source: Sleep Guide.pdf, Page 3]
Magnesium-rich foods like almonds and dark chocolate help sleep quality.
Studies show 400mg daily improves sleep onset by 17 minutes.
---
[Source: Sleep Guide.pdf, Page 7]
Tryptophan, found in turkey and warm milk, is a precursor to melatonin.
---

Use the above information to help answer the user's question.
Cite sources when referencing document content.
```

This formatted string is injected into the LLM prompt. The instruction to "cite sources" ensures the AI response references the document: "According to your Sleep Guide (Page 3), magnesium-rich foods like almonds..."

---

<a name="cosine"></a>
## 4. How Cosine Similarity Search Works

```
STEP 1: Question embedding
  "What foods help sleep?" → [0.019, -0.148, 0.897, ..., 0.039]

STEP 2: Compare against ALL stored chunk embeddings

  Chunk: "Magnesium helps sleep quality..."
  Embedding: [0.023, -0.156, 0.892, ..., 0.041]
  Cosine distance: 0.08 → Similarity: 0.92 ← VERY SIMILAR ✅

  Chunk: "Avoid caffeine after 2 PM..."
  Embedding: [0.015, -0.121, 0.856, ..., 0.055]
  Cosine distance: 0.16 → Similarity: 0.84 ← SIMILAR ✅

  Chunk: "Chapter 5: Exercise Routines..."
  Embedding: [0.567, 0.234, -0.123, ..., 0.890]
  Cosine distance: 0.78 → Similarity: 0.22 ← NOT SIMILAR ❌ (below 0.3 threshold)

STEP 3: Return top K above threshold
  → Chunk 1 (similarity: 0.92)
  → Chunk 2 (similarity: 0.84)
  → (Chunk 3 filtered out — below 0.3 threshold)
```

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision: Token Budget in Retriever

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Context Window Management                         │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Token budget in the retriever (max_context_tokens=2000)    │
│                                                                     │
│  WHY:                                                               │
│  • LLMs have context limits (4K–128K tokens)                        │
│  • Our prompt has: system (~200 tokens) + context (?) + user (~50)  │
│    + response budget (~500) = 2000 tokens for context is safe       │
│  • Adding too much context = noise (irrelevant chunks dilute focus) │
│  • Adding too little = missing info (answer is incomplete)          │
│                                                                     │
│  HOW:                                                               │
│  Chunks are sorted by similarity (highest first). We add chunks     │
│  until we'd exceed the budget. Most relevant content always fits.   │
│                                                                     │
│  INTERVIEW TIP: "The retriever enforces a token budget — it adds    │
│  the most relevant chunks first and stops when the context window   │
│  would overflow. This ensures the LLM sees the best context without │
│  exceeding its limits or introducing noise from less relevant       │
│  chunks."                                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **pgvector `<=>`** | Cosine distance operator (0=same, 2=opposite) | `similarity_search` SQL |
| 2 | **`::vector` cast** | Convert string to pgvector's binary vector type | INSERT and SELECT |
| 3 | **`1 - distance = similarity`** | Convert distance (lower=better) to similarity (higher=better) | SQL SELECT |
| 4 | **Similarity threshold** | Filter out irrelevant chunks (similarity < 0.3) | WHERE clause |
| 5 | **Token budgeting** | Stop adding chunks when context window would overflow | Retriever loop |
| 6 | **Source citations** | `[Source: filename, Page N]` headers for each chunk | `_format_context` |
| 7 | **`RetrievedContext` dataclass** | Bundles formatted text + sources + metadata | Retriever return type |
| 8 | **Orchestration pattern** | Retriever composes embedding + vector_store + formatting | `retrieve()` method |
| 9 | **User-scoped search** | `WHERE user_id = ?` — only search this user's docs | `similarity_search` |
| 10 | **Graceful empty results** | Return empty context if no docs match (not error) | Multiple checkpoints |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: How does pgvector similarity search work?
**A:** "The user's question is embedded into a 768-dimensional vector. pgvector's `<=>` operator calculates cosine distance between this query vector and every stored chunk vector. We convert distance to similarity (`1 - distance`), filter by a threshold (0.3), sort by similarity descending, and return the top 5. An IVFFlat index makes this fast by clustering vectors and only searching nearby clusters — approximate nearest neighbor instead of brute force."

### Q2: What is the token budget and why does it matter?
**A:** "LLMs have context limits. Our prompt includes: system message (~200 tokens), retrieved context (?), user question (~50 tokens), and response budget (~500 tokens). We allocate 2000 tokens for context. The retriever adds the most relevant chunks first (sorted by similarity) and stops when the budget would be exceeded. This ensures the best content fits, prevents context overflow, and avoids diluting relevance with too many mediocre chunks."

### Q3: How do you format context for the LLM?
**A:** "Each retrieved chunk gets a header with source citation: `[Source: Sleep Guide.pdf, Page 3]`. The chunks are joined with `---` separators. A final instruction tells the LLM: 'Use the above information. Cite sources when referencing document content.' This structure helps the LLM distinguish between document facts and its own knowledge, and produces responses like 'According to your Sleep Guide (p.3), magnesium helps sleep.'"

### Q4: What happens when no documents are relevant?
**A:** "Graceful degradation. If `similarity_search` returns no results (all chunks below the 0.3 threshold), the retriever returns an empty `RetrievedContext`. The caller (agent or service) proceeds without document context — the LLM answers from its training data instead. The user experience doesn't break; they just get a generic answer instead of a document-grounded one."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 09a: RAG Ingestion](./phase4-part09a-ai-rag-ingestion.md) |
| ➡️ Next | [Phase 4 Part 09c: RAG Connections & Flows](./phase4-part09c-ai-rag-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### RAG Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 09a | ✅ Done | RAG Ingestion (Extract, Chunk, Embed) |
| **09b** | ✅ **You are here** | RAG Retrieval (Vector Search, Context Format) |
| 09c | ⬜ Next | RAG Connections & Flows |

---

**End of Phase 4 Part 09b: RAG Retrieval**

*The search pipeline is complete — embed the question, search pgvector, budget tokens, format with citations. Next: flow diagrams connecting ingestion and retrieval into the full RAG pipeline.*
