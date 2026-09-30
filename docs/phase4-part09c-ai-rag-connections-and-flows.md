# 🔄 Phase 4 Part 09c: RAG — Connections & Flows

> **"Two pipelines, five files, one purpose: let the AI answer from YOUR documents. Ingestion turns PDFs into searchable vectors. Retrieval finds the right chunks for each question. Together, they make the AI personalized."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 09c (RAG Flows & Architecture) |
| **Sprint** | Sprint 3 — AI Module |
| **Previous** | [phase4-part09b-ai-rag-retrieval.md](./phase4-part09b-ai-rag-retrieval.md) |
| **Next** | [phase4-part10-ai-agents-overview.md](./phase4-part10-ai-agents-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only) |
| **Time to Read** | ~15 minutes |

---

## 1. RAG Module — Complete File Map

```
backend/app/modules/ai/rag/
├── document_processor.py ─── Part 09a ── Extract text from PDF/TXT
├── chunker.py            ─── Part 09a ── Split into overlapping chunks
├── embeddings.py         ─── Part 09a ── Convert text → 768-dim vectors
├── vector_store.py       ─── Part 09b ── Store/search in pgvector
├── retriever.py          ─── Part 09b ── Orchestrate: embed → search → format
└── __init__.py

Dependency chain:
  retriever.py → embeddings.py → LLM factory (Part 08b)
       │
       └── vector_store.py → PostgreSQL + pgvector
```

---

## 2. Flow 1: Document Ingestion (Upload Time)

```
STEP  COMPONENT                  ACTION
────  ─────────                  ──────
 1    User                       POST /ai/documents
                                 Uploads "Sleep Guide.pdf" (50 pages, 2MB)

 2    AI Service                 Receives file bytes + filename

 3    DocumentProcessor          .process(file_bytes, "Sleep Guide.pdf", "pdf")
      .process()                   → PyPDF2.PdfReader(io.BytesIO(bytes))
                                   → Extract text from each of 50 pages
                                   → ProcessedDocument(
                                       text="Chapter 1: Sleep Nutrition...",
                                       page_count=50,
                                       page_texts=["Page 1 text", "Page 2 text", ...]
                                     )

 4    TextChunker                .chunk_text(text, page_texts)
      .chunk_text()                → Recursive split: paragraphs → sentences → words
                                   → 100 TextChunk objects:
                                     Chunk 0: "Chapter 1: Nutrition... Magnesium helps..."
                                              page=1, tokens=487
                                     Chunk 1: "...magnesium include almonds, dark chocolate..."
                                              page=1, tokens=512
                                     Chunk 2: "Avoid caffeine after 2 PM..."
                                              page=3, tokens=445
                                     ... 97 more chunks

 5    EmbeddingGenerator         .embed_texts([chunk.text for chunk in chunks])
      .embed_texts()               → Batch 1: chunks[0:32] → LLM embed API → 32 vectors
                                   → Batch 2: chunks[32:64] → 32 vectors
                                   → Batch 3: chunks[64:96] → 32 vectors
                                   → Batch 4: chunks[96:100] → 4 vectors
                                   → 100 vectors, each 768 dimensions

 6    VectorStore                .store_chunk() × 100
      .store_chunk()               → INSERT INTO document_chunks
                                     (id, document_id, user_id, chunk_text,
                                      chunk_index, page_number, token_count,
                                      embedding)
                                   → Each embedding stored as pgvector vector type

 7    Database                   document_chunks table now has 100 new rows
                                 Each row: text + 768-dim vector + metadata

 8    Response                   HTTP 201: {"id": "doc-001", "filename": "Sleep Guide.pdf",
                                           "chunks": 100, "status": "processed"}

TIME: ~10-30 seconds (depending on PDF size and embedding speed)
  - Text extraction: ~1s
  - Chunking: ~0.1s
  - Embedding (100 chunks × 768 dims): ~5-20s (API calls)
  - Storage: ~0.5s
```

---

## 3. Flow 2: Question Retrieval (Chat Time)

```
STEP  COMPONENT                  ACTION
────  ─────────                  ──────
 1    User                       "What foods help me sleep?"
                                 (via AI chat or agent's search_docs tool)

 2    Retriever                  .retrieve("What foods help me sleep?", user_id)
      .retrieve()

 3    EmbeddingGenerator         .embed_query("What foods help me sleep?")
                                   → LLM embed API → [0.019, -0.148, 0.897, ..., 0.039]
                                   → Time: ~0.1s

 4    VectorStore                .similarity_search(user_id, query_embedding, top_k=5)
      .similarity_search()         → SQL:
                                     SELECT chunk_text, filename, page_number,
                                            1 - (embedding <=> query_vec) AS similarity
                                     FROM document_chunks dc
                                     JOIN documents d ON dc.document_id = d.id
                                     WHERE dc.user_id = ? AND similarity > 0.3
                                     ORDER BY embedding <=> query_vec
                                     LIMIT 5

                                   → Results:
                                     Chunk: "Magnesium helps sleep..."  sim: 0.92
                                     Chunk: "Tryptophan in turkey..."   sim: 0.87
                                     Chunk: "Melatonin production..."   sim: 0.84
                                     Chunk: "Avoid caffeine..."         sim: 0.71
                                     Chunk: "Sleep hygiene tips..."     sim: 0.65
                                   → Time: ~5ms (indexed search)

 5    Retriever                  Token budgeting:
      (budget check)               Chunk 1: 487 tokens → total: 487 (under 2000) ✅
                                   Chunk 2: 512 tokens → total: 999 (under 2000) ✅
                                   Chunk 3: 445 tokens → total: 1444 (under 2000) ✅
                                   Chunk 4: 510 tokens → total: 1954 (under 2000) ✅
                                   Chunk 5: 480 tokens → total: 2434 (OVER 2000) ❌ skip

 6    Retriever                  ._format_context(4 chunks)
      ._format_context()           → "RELEVANT INFORMATION FROM YOUR DOCUMENTS:
                                      [Source: Sleep Guide.pdf, Page 1]
                                      Magnesium-rich foods like almonds and dark chocolate
                                      help sleep quality. Studies show 400mg daily improves
                                      sleep onset by 17 minutes.
                                      ---
                                      [Source: Sleep Guide.pdf, Page 3]
                                      Tryptophan, found in turkey and warm milk...
                                      ---
                                      [Source: Sleep Guide.pdf, Page 5]
                                      Melatonin production peaks at night...
                                      ---
                                      [Source: Sleep Guide.pdf, Page 7]
                                      Avoid caffeine after 2 PM as it blocks adenosine...
                                      ---
                                      Use the above information to help answer."

 7    Return                     RetrievedContext(
                                   formatted_context="RELEVANT INFORMATION...",
                                   sources=[
                                     {"filename":"Sleep Guide.pdf","page_number":1,"similarity":0.92},
                                     {"filename":"Sleep Guide.pdf","page_number":3,"similarity":0.87},
                                     {"filename":"Sleep Guide.pdf","page_number":5,"similarity":0.84},
                                     {"filename":"Sleep Guide.pdf","page_number":7,"similarity":0.71},
                                   ],
                                   chunk_count=4,
                                   total_tokens=1954,
                                 )

TOTAL RETRIEVAL TIME: ~0.1s (embed) + ~5ms (search) + ~1ms (format) = ~110ms
```

---

## 4. Flow 3: RAG Integration with Agent

```
User: "Based on my documents, what should I eat for better sleep?"
  │
  ▼
Agent ReAct Loop (Part 10):
  [THINK] "User asks about food and sleep from their documents"
  [ACT]   tool: search_docs(query="foods for better sleep")
    │
    ▼ Retriever.retrieve("foods for better sleep", user_id)
    │   → embed query → search pgvector → 4 chunks (1954 tokens)
    │   → formatted context with citations
    │
  [OBSERVE] "From Sleep Guide.pdf: magnesium (almonds, chocolate),
             tryptophan (turkey, milk), avoid caffeine after 2 PM..."
  │
  [THINK] "I have document data. Let me also check their actual food habits."
  [ACT]   tool: query_logs(habit_name="Water", days=7)
    │
  [OBSERVE] "Water intake this week: avg 6.5 glasses"
  │
  [ANSWER] "Based on your Sleep Guide by Dr. Smith, foods that help sleep:
            1. Almonds and dark chocolate (magnesium — improves sleep onset
               by 17 minutes, according to Page 1 of your guide)
            2. Turkey and warm milk (tryptophan — precursor to melatonin)
            3. Avoid caffeine after 2 PM (blocks adenosine, Page 7)

            Also, your water intake is 6.5 glasses/day — staying hydrated
            helps sleep quality. Try reaching your 8-glass target."
```

---

## 5. Error Handling Across the Pipeline

| Scenario | What Happens | User Sees |
|----------|-------------|-----------|
| **PDF parsing fails** | DocumentProcessor raises ValueError | "Failed to process PDF" (422) |
| **No text extracted** | Empty text → chunker returns [] | "Document appears to be empty" |
| **Embedding API down** | EmbeddingGenerator returns zero vectors | Document stored but not searchable |
| **No matching chunks** | VectorStore returns [] | Agent answers from training data (no citations) |
| **All chunks below threshold** | Filtered out | Same as no matching chunks |
| **Token budget exhausted** | Only best 3-4 chunks included | Answer uses fewer sources (still accurate) |

---

## 6. RAG Module Summary

### What You Built (Parts 09a–09c)

| Part | Files | What It Does |
|------|-------|-------------|
| **09a** | document_processor, chunker, embeddings | Ingestion: PDF→text→chunks→vectors |
| **09b** | vector_store, retriever | Retrieval: question→vector→search→context |
| **09c** | (this doc) | Flows: ingestion + retrieval + agent integration |

### By the Numbers

| Metric | Value |
|--------|-------|
| Python files | 5 |
| Pipeline steps (ingestion) | 4 (extract → chunk → embed → store) |
| Pipeline steps (retrieval) | 4 (embed query → search → budget → format) |
| Chunk size | ~500 tokens (2000 chars) |
| Chunk overlap | ~50 tokens (200 chars) |
| Embedding dimensions | 768 (Ollama) or 1536 (OpenAI) |
| Top-K default | 5 chunks |
| Similarity threshold | 0.3 minimum |
| Token budget | 2000 tokens max context |
| Batch size | 32 texts per embed call |

---

## 7. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 09b: RAG Retrieval](./phase4-part09b-ai-rag-retrieval.md) |
| ➡️ Next | [Phase 4 Part 10: AI Agents Overview](./phase4-part10-ai-agents-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### RAG Module — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 09a | ✅ RAG Ingestion (Extract, Chunk, Embed) |
| 09b | ✅ RAG Retrieval (Vector Search, Context Format) |
| **09c** | ✅ **RAG Connections & Flows** |

---

**🎉 The RAG pipeline is COMPLETE.**

*Documents go in as PDFs, come out as searchable vector-indexed chunks. Questions go in as text, come out as citation-formatted context. The AI can now answer from YOUR documents. Next: the Agents layer — where the AI learns to THINK and ACT with tools.*
