# 🔍 Phase 4 Part 09: AI — RAG Pipeline Overview

> **"RAG lets the AI answer questions from YOUR documents. Upload a nutrition guide, and the AI can say 'Based on your uploaded guide, magnesium-rich foods like almonds help sleep quality.' Without RAG, the AI only knows generic internet knowledge. With RAG, it becomes personalized."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 09 (AI Module — RAG Pipeline Overview) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.2 — Document-Based AI |
| **Previous** | [phase4-part08c-ai-llm-prompts-tokens.md](./phase4-part08c-ai-llm-prompts-tokens.md) |
| **Next** | [phase4-part09a-ai-rag-ingestion.md](./phase4-part09a-ai-rag-ingestion.md) |
| **Files** | 5 files (document_processor.py, chunker.py, embeddings.py, vector_store.py, retriever.py) |
| **Sub-Parts** | 3 documents (09a–09c) |
| **Difficulty** | ★★ Hard (embeddings, vector math, pgvector, chunking strategies) |

---

## 📖 Table of Contents

1. [What Is RAG?](#what-is-rag)
2. [The Two RAG Pipelines — Ingestion & Retrieval](#pipelines)
3. [Key Concepts Explained](#concepts)
4. [File List & Sub-Part Roadmap](#file-list)
5. [Architecture Diagram](#architecture)
6. [Design Decisions](#design-decisions)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="what-is-rag"></a>
## 1. What Is RAG?

**RAG = Retrieval-Augmented Generation**

Without RAG, the AI only knows what it was trained on (generic knowledge up to its training cutoff). With RAG, the AI can answer from YOUR specific documents.

```
WITHOUT RAG:
  User: "What foods help me sleep?"
  AI: "Warm milk, chamomile tea, kiwi..." (generic internet knowledge)

WITH RAG:
  User uploads: "Dr. Smith's Sleep Nutrition Guide.pdf"
  User: "What foods help me sleep?"
  AI: "Based on your uploaded guide by Dr. Smith, magnesium-rich foods
       like almonds and dark chocolate help sleep quality. The guide
       specifically recommends eating them 2 hours before bed."
       (personalized, from YOUR document)
```

### Real-World Analogy

Think of RAG as a **student taking an open-book exam**:
- **Without RAG** = closed-book exam. The student can only answer from memory (training data)
- **With RAG** = open-book exam. The student quickly finds the right page in the textbook (retrieval) and uses it to write a better answer (generation)

The "book" is your uploaded documents. The "finding the right page" is vector similarity search. The "writing the answer" is the LLM.

---

<a name="pipelines"></a>
## 2. The Two RAG Pipelines — Ingestion & Retrieval

### Pipeline 1: INGESTION (one-time, when document is uploaded)

```
User uploads "Sleep Guide.pdf" (50 pages)
  │
  ▼
┌─── document_processor.py ──────────────────────────────────────┐
│  Extract text from PDF/TXT                                      │
│  "Chapter 1: Nutrition and Sleep. Magnesium helps..."           │
│  (raw text, possibly thousands of characters)                    │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── chunker.py ─────────────────────────────────────────────────┐
│  Split into overlapping chunks (~500 chars each)                │
│                                                                  │
│  Chunk 1: "Chapter 1: Nutrition and Sleep. Magnesium helps      │
│            regulate melatonin. Foods rich in magnesium..."      │
│  Chunk 2: "...magnesium include almonds, dark chocolate,        │
│            and spinach. Studies show 400mg daily improves..."    │
│  Chunk 3: "...improves sleep onset by 17 minutes. Avoid        │
│            caffeine after 2 PM as it blocks adenosine..."       │
│  ... 100 chunks total                                            │
│                                                                  │
│  WHY OVERLAP: so "magnesium" context isn't lost at boundaries   │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── embeddings.py ──────────────────────────────────────────────┐
│  Convert each chunk to a vector (list of numbers)               │
│                                                                  │
│  Chunk 1 → [0.023, -0.156, 0.892, ..., 0.041] (768 dimensions) │
│  Chunk 2 → [0.018, -0.142, 0.901, ..., 0.038]                  │
│  Chunk 3 → [-0.045, 0.231, 0.543, ..., 0.112]                  │
│                                                                  │
│  Similar meaning → similar vectors (close in 768-D space)       │
│  Uses LLM provider's embedding API (nomic-embed or OpenAI)      │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── vector_store.py (pgvector) ─────────────────────────────────┐
│  Store in PostgreSQL document_chunks table:                      │
│                                                                  │
│  id | document_id | chunk_text           | embedding             │
│  1  | sleep-guide | "Chapter 1: Nutri..."| [0.023, -0.156, ...]  │
│  2  | sleep-guide | "...magnesium inc..." | [0.018, -0.142, ...]  │
│  3  | sleep-guide | "...improves sleep..."| [-0.045, 0.231, ...]  │
│                                                                  │
│  pgvector enables: SELECT ... ORDER BY embedding <=> query_vec   │
└────────────────────────────────────────────────────────────────┘
```

### Pipeline 2: RETRIEVAL (every chat query that needs document context)

```
User asks: "What foods help me sleep?"
  │
  ▼
┌─── embeddings.py ──────────────────────────────────────────────┐
│  Convert question to vector:                                     │
│  "What foods help me sleep?"                                     │
│  → [0.019, -0.148, 0.897, ..., 0.039] (768 dimensions)          │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── vector_store.py ────────────────────────────────────────────┐
│  Cosine similarity search in pgvector:                           │
│                                                                  │
│  SELECT chunk_text, 1 - (embedding <=> query_vec) AS similarity  │
│  FROM document_chunks                                            │
│  WHERE user_id = ?                                               │
│  ORDER BY embedding <=> query_vec                                │
│  LIMIT 5;                                                        │
│                                                                  │
│  Results (most similar first):                                   │
│  Chunk 2: "magnesium include almonds..." similarity: 0.92        │
│  Chunk 1: "Nutrition and Sleep..."        similarity: 0.87       │
│  Chunk 7: "tryptophan in turkey..."       similarity: 0.84       │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── retriever.py ───────────────────────────────────────────────┐
│  Format chunks into LLM context:                                 │
│                                                                  │
│  "RELEVANT CONTEXT FROM USER'S DOCUMENTS:                        │
│   [Source: Sleep Guide.pdf]                                      │
│   Magnesium-rich foods include almonds, dark chocolate,          │
│   and spinach. Studies show 400mg daily improves sleep           │
│   onset by 17 minutes.                                           │
│                                                                  │
│   [Source: Sleep Guide.pdf]                                      │
│   Tryptophan, found in turkey and warm milk, is a precursor     │
│   to melatonin production..."                                    │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌─── LLM (via agent or direct) ──────────────────────────────────┐
│  System: "You are a health coach. Use the provided context."     │
│  Context: [retrieved chunks above]                               │
│  User: "What foods help me sleep?"                               │
│                                                                  │
│  AI: "Based on your Sleep Guide by Dr. Smith, here are foods    │
│       that help sleep:                                           │
│       1. Almonds and dark chocolate (magnesium — improves sleep  │
│          onset by 17 minutes)                                    │
│       2. Turkey and warm milk (tryptophan — precursor to         │
│          melatonin)                                              │
│       The guide recommends eating these 2 hours before bed."     │
└────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 3. Key Concepts Explained

### What Is an Embedding?

An **embedding** is a list of numbers (a vector) that represents the MEANING of text:

```
"I love cats" → [0.21, -0.15, 0.89, 0.03, ..., 0.42]  (768 numbers)
"I adore kittens" → [0.20, -0.14, 0.88, 0.04, ..., 0.41]  (similar vectors!)
"The stock market crashed" → [-0.67, 0.45, -0.12, ..., -0.31]  (very different!)
```

- **Similar meaning → similar vectors** (close in 768-dimensional space)
- **Different meaning → different vectors** (far apart)
- This is how the AI "understands" that your question about "foods for sleep" is related to a chunk about "magnesium and sleep quality"

### What Is Cosine Similarity?

Measures the angle between two vectors (not the distance):

```
Cosine Similarity:
  1.0 = identical meaning (parallel vectors)
  0.0 = unrelated (perpendicular vectors)
 -1.0 = opposite meaning (anti-parallel)

"magnesium helps sleep" vs "foods for better sleep" → ~0.92 (very similar)
"magnesium helps sleep" vs "stock market returns"   → ~0.05 (unrelated)
```

pgvector uses the `<=>` operator for cosine distance (1 - similarity). Lower distance = more similar.

### What Is Chunking?

Splitting a large document into smaller pieces:

```
50-page PDF (~25,000 words)
  → Too big for LLM context window (4K-128K tokens)
  → Embedding on full doc is too coarse (loses detail)

Split into ~100 chunks of ~500 chars each:
  → Each chunk fits easily in the context window
  → Embedding is precise ("this chunk is about magnesium")
  → Retrieval finds THE specific section that answers the question
```

**Overlap** prevents losing context at chunk boundaries:

```
WITHOUT overlap:
  Chunk 1: "...the patient's iron level is"
  Chunk 2: "10.5 µg/dL which is below normal"
  ← Neither chunk has the full sentence!

WITH 50-char overlap:
  Chunk 1: "...the patient's iron level is 10.5 µg/dL which is"
  Chunk 2: "iron level is 10.5 µg/dL which is below normal"
  ← Both chunks preserve the complete information
```

### What Is pgvector?

A PostgreSQL extension that adds vector operations:

```sql
-- Enable the extension (done in migration 001)
CREATE EXTENSION vector;

-- Store embeddings
ALTER TABLE document_chunks ADD COLUMN embedding vector(768);

-- Search by similarity (cosine distance)
SELECT chunk_text
FROM document_chunks
ORDER BY embedding <=> '[0.019, -0.148, ...]'::vector
LIMIT 5;
```

**Why pgvector (not Pinecone)?** Same database, same transactions, $0 cost. For our scale (<1M vectors), performance is excellent.

---

<a name="file-list"></a>
## 4. File List & Sub-Part Roadmap

### RAG Layer File Structure

```
backend/app/modules/ai/rag/
├── __init__.py
├── document_processor.py  ← Extract text from PDF/TXT uploads
├── chunker.py             ← Split text into overlapping chunks
├── embeddings.py          ← Convert text → vectors (via LLM embed())
├── vector_store.py        ← Store/search vectors in pgvector
└── retriever.py           ← Orchestrate: embed question → search → format context
```

### Sub-Part Roadmap

| Part | Document | Files | Key Concepts |
|------|----------|-------|-------------|
| **09a** | [RAG Ingestion](./phase4-part09a-ai-rag-ingestion.md) | document_processor.py + chunker.py + embeddings.py | PDF extraction, recursive splitting, batch embedding |
| **09b** | [RAG Retrieval](./phase4-part09b-ai-rag-retrieval.md) | vector_store.py + retriever.py | pgvector `<=>`, top-K search, context formatting |
| **09c** | [RAG Connections & Flows](./phase4-part09c-ai-rag-connections-and-flows.md) | Full pipeline flow diagrams | Ingestion + retrieval end-to-end |

---

<a name="architecture"></a>
## 5. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE                                │
│                                                                   │
│  INGESTION (upload time):                                         │
│  ┌─────────────┐ ┌──────────┐ ┌───────────┐ ┌───────────────┐  │
│  │ document_    │→│ chunker  │→│ embeddings│→│ vector_store  │  │
│  │ processor    │ │          │ │           │ │ (pgvector)    │  │
│  │              │ │ 500-char │ │ text→vec  │ │ INSERT chunks │  │
│  │ PDF → text   │ │ overlap  │ │ via LLM   │ │ + vectors     │  │
│  └─────────────┘ └──────────┘ └───────────┘ └───────────────┘  │
│                                                                   │
│  RETRIEVAL (query time):                                          │
│  ┌─────────────┐ ┌───────────┐ ┌───────────────┐ ┌──────────┐  │
│  │ retriever   │→│ embeddings│→│ vector_store   │→│ format   │  │
│  │             │ │           │ │                 │ │ context  │  │
│  │ orchestrate │ │ query→vec │ │ <=> similarity  │ │ + cite   │  │
│  │             │ │           │ │ TOP K chunks    │ │ sources  │  │
│  └─────────────┘ └───────────┘ └───────────────┘ └──────────┘  │
│                                                    │             │
│                                                    ▼             │
│                                              ┌──────────┐       │
│                                              │   LLM    │       │
│                                              │ (Part 08)│       │
│                                              └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
        │                                            │
        ▼                                            ▼
┌───────────────┐                          ┌───────────────────┐
│  PostgreSQL    │                          │  External API     │
│  + pgvector    │                          │  (embedding model)│
│  documents     │                          │  Ollama/OpenAI    │
│  document_     │                          └───────────────────┘
│  chunks        │
└───────────────┘
```

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Decision 1: pgvector vs Pinecone

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Vector Database                                   │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: PostgreSQL + pgvector (in our existing database)           │
│                                                                     │
│  WHY:                                                               │
│  • Free — no additional service cost ($0 vs $70+/month Pinecone)    │
│  • One database — vectors in same DB as habits/logs/users           │
│  • Transactional — document + chunks stored in one transaction      │
│  • Simple — no separate infrastructure to manage or monitor         │
│  • Good enough — handles millions of vectors with IVFFlat index     │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Pinecone (dedicated vector DB)                                  │
│     ❌ $70+/month minimum, separate service, network latency        │
│  2. Weaviate / Qdrant (self-hosted)                                 │
│     ❌ Another container, more infrastructure complexity            │
│  3. ChromaDB (in-memory)                                            │
│     ❌ Data lost on restart, not production-ready                   │
│  4. FAISS (Facebook's in-memory vector search)                      │
│     ❌ No persistence, single-machine only                         │
│                                                                     │
│  AT SCALE: If vector search exceeds 100ms for millions of vectors,  │
│  migrate to a dedicated vector DB. For our scale (per-user docs,    │
│  ~1000 chunks max), pgvector is perfect.                            │
│                                                                     │
│  INTERVIEW TIP: "We chose pgvector because it eliminates a separate │
│  service. Vectors live in the same PostgreSQL instance as our other  │
│  data — one transaction, one backup, one connection pool. We enabled│
│  the extension in our very first migration."                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Recursive Character Splitting

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Chunking Strategy                                 │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Recursive character text splitting with overlap            │
│                                                                     │
│  STRATEGY:                                                          │
│  1. Try to split on paragraph boundaries (\n\n)                     │
│  2. If paragraphs too long → split on sentences (. ! ?)             │
│  3. If sentences too long → split on words (spaces)                 │
│  4. Last resort → split on character count                          │
│                                                                     │
│  PARAMETERS: chunk_size=500 chars, overlap=50 chars                 │
│                                                                     │
│  WHY:                                                               │
│  • Preserves semantic boundaries (complete thoughts per chunk)      │
│  • Overlap prevents information loss at boundaries                  │
│  • 500 chars is optimal for embedding precision + context fitting   │
│  • Same algorithm as LangChain's RecursiveCharacterTextSplitter     │
│                                                                     │
│  ALTERNATIVES: Fixed-size (loses context), sentence-based (uneven   │
│  sizes), token-based (slower, provider-dependent).                  │
│                                                                     │
│  INTERVIEW TIP: "We use recursive character splitting — it tries    │
│  paragraph boundaries first, then sentences, then words. This       │
│  preserves semantic coherence. 500-char chunks with 50-char overlap │
│  give optimal embedding precision while fitting in context windows."│
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: What is RAG and why did you implement it?
**A:** "RAG stands for Retrieval-Augmented Generation. It lets the AI answer questions using the user's own documents — not just generic training data. When a user uploads a nutrition guide, we split it into ~500-character chunks, convert each chunk to a 768-dimensional vector embedding, and store them in PostgreSQL with pgvector. When the user asks a question, we embed their question, find the most similar chunks via cosine distance search, and inject those chunks into the LLM prompt as context. The AI generates an answer grounded in the user's specific document."

### Q2: How does vector similarity search work?
**A:** "Text is converted to a vector (list of numbers) using an embedding model. Similar text produces similar vectors — 'foods for sleep' and 'magnesium and sleep quality' have vectors pointing in nearly the same direction. pgvector's `<=>` operator computes cosine distance between the query vector and all stored chunk vectors. We return the top 5 chunks with the smallest distance. An IVFFlat index makes this fast even with thousands of chunks — it groups vectors into clusters and only searches nearby clusters."

### Q3: Why pgvector instead of a dedicated vector database like Pinecone?
**A:** "Cost and simplicity. pgvector is free — it's a PostgreSQL extension we enabled in our first migration. Vectors live in the same database as habits, logs, and user data — one connection pool, one backup, one transaction. Pinecone costs $70+/month minimum and adds network latency. For our scale (personal documents, ~1000 chunks per user), pgvector performance is excellent. If we needed to scale to millions of vectors across millions of users, we'd evaluate a dedicated vector DB."

### Q4: Why chunk documents instead of embedding the whole thing?
**A:** "Three reasons. First, LLMs have context limits — a 50-page PDF won't fit in a 4K-token window. Second, embedding precision degrades on large texts — a 500-char chunk about 'magnesium and sleep' produces a much more precise vector than a 50-page document. Third, retrieval accuracy — we fetch THE specific paragraph that answers the question, not the entire document. The overlap between chunks ensures information at boundaries isn't lost."

### Q5: How does RAG integrate with the Agent?
**A:** "The agent has a `search_docs` tool. When the user asks a question that might be answered by their uploaded documents, the agent calls this tool. The tool invokes the retriever, which embeds the query, searches pgvector, and returns formatted context with source citations. The agent then includes this context in its next LLM call to generate a grounded answer. The agent decides WHEN to use RAG — if the question is about the user's habits, it uses the query_logs tool instead."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 08c: AI LLM Prompts & Tokens](./phase4-part08c-ai-llm-prompts-tokens.md) |
| ➡️ Next | [Phase 4 Part 09a: RAG Ingestion](./phase4-part09a-ai-rag-ingestion.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### RAG Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 09a | [RAG Ingestion](./phase4-part09a-ai-rag-ingestion.md) | document_processor + chunker + embeddings |
| 09b | [RAG Retrieval](./phase4-part09b-ai-rag-retrieval.md) | vector_store (pgvector) + retriever |
| 09c | [RAG Connections & Flows](./phase4-part09c-ai-rag-connections-and-flows.md) | Full pipeline diagrams |

---

**End of Phase 4 Part 09: RAG Pipeline Overview**

*RAG turns a generic AI into a personalized one. Your documents become the AI's knowledge base — chunked, embedded, and searchable. Next: the Agents layer — where the AI learns to THINK and ACT.*
