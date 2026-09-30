# 🤖 Phase 4 Part 12: AI — Service, Router & Models Overview

> **"This is where 39 AI files become 9 API endpoints. The AI service is the single orchestrator — it decides whether to use the agent (tool-calling) or direct LLM (fast), handles document upload through the full RAG pipeline, generates insights, and triggers the weekly report workflow. The router exposes it all, including SSE streaming for that ChatGPT-like word-by-word experience."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 12 (AI Module — Service, Router & Models Overview) |
| **Sprint** | Sprint 3 — AI Module |
| **Release** | Release 3.5 — AI Endpoints & SSE Streaming |
| **Previous** | [phase4-part11b-ai-workflow-connections-and-flows.md](./phase4-part11b-ai-workflow-connections-and-flows.md) |
| **Next** | [phase4-part12a-ai-models-schemas.md](./phase4-part12a-ai-models-schemas.md) |
| **Files** | models.py (~230 lines), schemas.py (~100 lines), service.py (~280 lines), router.py (~220 lines), 004_migration.py (~100 lines) |
| **Endpoints** | 9 |
| **Database Tables** | 4 (documents, document_chunks, ai_chat_messages, ai_insights) |
| **Sub-Parts** | 3 documents (12a models/schemas, 12b service/router, 12c migration + architecture) |
| **Difficulty** | Hard (SSE streaming, file upload, cross-layer orchestration, pgvector IVFFlat index) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [The 9 AI Endpoints](#endpoints)
3. [The 4 AI Database Tables](#tables)
4. [SSE Streaming — How It Works](#sse)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram — How Service Connects All AI Layers](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Design Decisions](#design-decisions)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

Parts 08–11 built the AI engine — LLM providers, RAG pipeline, ReAct agent, agentic workflows. Now we wire all of it into the web application:

| What | Files | Purpose |
|------|-------|---------|
| **models.py** | 4 SQLAlchemy models | Database tables for AI data |
| **schemas.py** | 8 Pydantic schemas | Request/response shapes for 9 endpoints |
| **service.py** | 7 public methods | Single orchestrator for ALL AI features |
| **router.py** | 9 endpoint handlers | HTTP layer with SSE streaming |
| **004_migration.py** | CREATE TABLE × 4 | Database migration with pgvector IVFFlat index |

### What Makes This Part Different from Previous Modules

| Feature | Auth/Habits/Logs/Analytics | AI (this part) |
|---------|--------------------------|----------------|
| CRUD pattern | Standard (create/read/update/delete) | Mixed (chat, upload, generate, stream) |
| File upload | None | `UploadFile` for documents |
| Streaming | None | SSE (`StreamingResponse`) |
| LLM calls | None | 2 modes: agent (multi-step) + direct (single) |
| Token tracking | None | Redis-based daily usage limits |
| Cross-module | 1-2 repos | Uses ALL modules (habits, logs, analytics, RAG, agents, workflows) |

---

<a name="endpoints"></a>
## 2. The 9 AI Endpoints

### Chat Endpoints (3)

| # | Method | Endpoint | Auth | Request | Response | What It Does |
|---|--------|----------|:----:|---------|----------|-------------|
| 1 | `POST` | `/ai/chat` | ✅ | `ChatRequest` (message + use_agent) | `{response: str}` | Chat with AI coach — agent or direct mode |
| 2 | `GET` | `/ai/chat/stream` | ✅ | `?message=...` (query param) | SSE stream | Word-by-word streaming response |
| 3 | `GET` | `/ai/chat/history` | ✅ | — | `ChatHistoryResponse` | Past conversation messages |

### Document Endpoints — RAG (3)

| # | Method | Endpoint | Auth | Request | Response | What It Does |
|---|--------|----------|:----:|---------|----------|-------------|
| 4 | `POST` | `/ai/documents` | ✅ | `UploadFile` (multipart) | `DocumentResponse` | Upload PDF/TXT for RAG |
| 5 | `GET` | `/ai/documents` | ✅ | — | `DocumentListResponse` | List user's documents |
| 6 | `DELETE` | `/ai/documents/{id}` | ✅ | — | `SuccessResponse` | Delete document + chunks |

### Insight Endpoints (3)

| # | Method | Endpoint | Auth | Request | Response | What It Does |
|---|--------|----------|:----:|---------|----------|-------------|
| 7 | `POST` | `/ai/insights` | ✅ | — | `InsightResponse` | Generate on-demand insight |
| 8 | `GET` | `/ai/insights` | ✅ | — | `InsightListResponse` | List past insights |
| 9 | `POST` | `/ai/weekly-report` | ✅ | — | `InsightResponse` | Generate weekly report (workflow) |

---

<a name="tables"></a>
## 3. The 4 AI Database Tables

```
┌─────────────────────────────────────────────────────────────────┐
│  documents                                                       │
│  ├── id (UUID PK)                                                │
│  ├── user_id (FK → users)                                        │
│  ├── filename ("Sleep Guide.pdf")                                │
│  ├── file_type ("pdf")                                           │
│  ├── file_size (2048000 bytes)                                   │
│  ├── page_count (50)                                             │
│  ├── status ("uploaded" → "processing" → "processed"/"failed")   │
│  ├── chunk_count (100)                                           │
│  ├── error_message (null or "PDF parsing failed")                │
│  └── created_at                                                  │
├─────────────────────────────────────────────────────────────────┤
│  document_chunks                                                 │
│  ├── id (UUID PK)                                                │
│  ├── document_id (FK → documents, CASCADE)                       │
│  ├── user_id (FK → users, CASCADE)                               │
│  ├── chunk_text ("Magnesium helps sleep quality...")              │
│  ├── chunk_index (0, 1, 2, ...)                                  │
│  ├── page_number (3)                                             │
│  ├── token_count (487)                                           │
│  ├── embedding (vector(768)) ← pgvector column! IVFFlat indexed  │
│  └── created_at                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ai_chat_messages                                                │
│  ├── id (UUID PK)                                                │
│  ├── user_id (FK → users)                                        │
│  ├── role ("user" / "assistant")                                 │
│  ├── content ("How's my sleep?" / "You averaged 6.8h...")        │
│  ├── tokens_used (256)                                           │
│  └── created_at                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ai_insights                                                     │
│  ├── id (UUID PK)                                                │
│  ├── user_id (FK → users)                                        │
│  ├── insight_type ("weekly_report" / "on_demand" / "correlation")│
│  ├── title ("Weekly Report — 2026-09-26")                        │
│  ├── content (full markdown report)                              │
│  ├── tokens_used (4100)                                          │
│  └── created_at                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Table Relationships

```
users (1) ──── (many) documents (1) ──── (many) document_chunks
users (1) ──── (many) ai_chat_messages
users (1) ──── (many) ai_insights
```

All tables have `user_id` FK with `CASCADE` delete — if a user is deleted, all their AI data is cleaned up.

---

<a name="sse"></a>
## 4. SSE Streaming — How It Works

### What Is SSE (Server-Sent Events)?

SSE is a one-way communication channel from server to client. The server pushes data as it becomes available — the client receives it in real-time.

```
NORMAL API CALL:
  Client → Request → Server (processes for 5 seconds) → Full Response → Client
  User waits 5 seconds, then sees the entire answer at once.

SSE STREAMING:
  Client → Request → Server starts generating...
    → data: "Your"           → Client shows: "Your"
    → data: " sleep"         → Client shows: "Your sleep"
    → data: " averaged"      → Client shows: "Your sleep averaged"
    → data: " 6.8 hours"     → Client shows: "Your sleep averaged 6.8 hours"
    → data: [DONE]           → Client knows response is complete
  User sees text appearing word by word — same UX as ChatGPT.
```

### How SSE Works in Our Stack

```
┌────────────────────────────────────────────────────────────────────────┐
│  FRONTEND (React)                                                       │
│                                                                         │
│  const eventSource = new EventSource(                                   │
│    "/api/v1/ai/chat/stream?message=How's my sleep?"                    │
│  );                                                                     │
│                                                                         │
│  eventSource.onmessage = (event) => {                                  │
│    if (event.data === "[DONE]") {                                      │
│      eventSource.close();                                               │
│      return;                                                            │
│    }                                                                    │
│    setResponse(prev => prev + event.data);  // Append each chunk       │
│  };                                                                     │
└───────────────────────────┬────────────────────────────────────────────┘
                            │ SSE connection (long-lived HTTP)
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│  NGINX (default.conf)                                                   │
│  location /api/v1/ai/ {                                                │
│    proxy_buffering off;        ← DON'T buffer — send chunks immediately │
│    proxy_cache off;            ← DON'T cache streaming responses        │
│    proxy_read_timeout 300s;    ← AI responses can take up to 5 minutes  │
│    chunked_transfer_encoding on;                                        │
│  }                                                                      │
└───────────────────────────┬────────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│  FASTAPI (router.py)                                                    │
│                                                                         │
│  return StreamingResponse(                                              │
│    event_generator(),              ← async generator yields chunks      │
│    media_type="text/event-stream", ← tells browser this is SSE         │
│    headers={"X-Accel-Buffering": "no"},  ← tells Nginx too             │
│  )                                                                      │
│                                                                         │
│  async def event_generator():                                           │
│    async for chunk in service.stream_chat(user_id, user_name, message):│
│      yield f"data: {chunk}\n\n"    ← SSE format: data: <text>\n\n     │
│    yield "data: [DONE]\n\n"        ← Signal: stream complete           │
└───────────────────────────┬────────────────────────────────────────────┘
                            │ calls
                            ▼
┌────────────────────────────────────────────────────────────────────────┐
│  LLM CLIENT (stream_chat method — Part 08b)                             │
│                                                                         │
│  async for chunk in self.llm.stream_chat(messages):                    │
│    yield chunk   ← Each chunk is a few tokens ("Your ", "sleep ", ...) │
│                                                                         │
│  Ollama: reads NDJSON lines from HTTP stream                           │
│  Groq/OpenAI: reads SSE data events from HTTP stream                   │
└────────────────────────────────────────────────────────────────────────┘
```

### SSE vs WebSocket — Why SSE for Chat?

| Feature | SSE | WebSocket |
|---------|-----|-----------|
| Direction | Server → Client only | Bidirectional |
| Complexity | Simple (just HTTP) | Complex (connection upgrade) |
| Reconnection | Automatic (browser handles) | Manual (you implement) |
| Our use case | AI generates, client displays | Would be overkill |
| Used by | ChatGPT, Claude, Gemini | Real-time collab (Google Docs) |

SSE is simpler and sufficient — the AI generates text, the client displays it. No bidirectional communication needed.

---

<a name="file-list"></a>
## 5. File List & Build Order

```
backend/app/modules/ai/
├── models.py       ← File 1: 4 SQLAlchemy models (Document, DocumentChunk, AiChatMessage, AiInsight)
├── schemas.py      ← File 2: 8 Pydantic schemas (ChatRequest, DocumentResponse, InsightResponse, ...)
├── service.py      ← File 3: AI orchestrator (7 public methods + 4 private helpers)
├── router.py       ← File 4: 9 endpoints including SSE streaming

backend/alembic/versions/
└── 004_create_ai_tables.py ← File 5: Migration with pgvector IVFFlat index
```

### Build Order

| # | File | Why This Order |
|---|------|---------------|
| 1 | `models.py` | Tables must exist before service queries them |
| 2 | `schemas.py` | Router uses these for request/response validation |
| 3 | `004_migration.py` | Creates the tables in PostgreSQL |
| 4 | `service.py` | Orchestrates ALL AI layers — depends on everything |
| 5 | `router.py` | HTTP layer — calls service, uses schemas |

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 12a: AI Models & Schemas

```
📄 phase4-part12a-ai-models-schemas.md
├── models.py   — 4 models: Document, DocumentChunk (pgvector), AiChatMessage, AiInsight
│                  Full source code with line-by-line explanation
│                  pgvector Vector column, status flow, try/except import
└── schemas.py  — 8 schemas: ChatRequest, ChatMessage, DocumentResponse, InsightResponse,
                   StreamChunk (for SSE), etc.

KEY CONCEPTS: pgvector column type, status state machine, streaming chunk schema
TIME: ~45 minutes
```

### Part 12b: AI Service & Router

```
📄 phase4-part12b-ai-service-router.md
├── service.py  — 7 public methods: chat (agent+direct), stream_chat, upload_document,
│                  delete_document, generate_insight, generate_weekly_report, get_chat_history
│                  + 4 private helpers (_agent_chat, _direct_chat, _save_chat_message, _get_recent_messages)
│                  Full source code with line-by-line explanation
└── router.py   — 9 endpoints with SSE StreamingResponse, UploadFile, dependency injection
                   Full source code with line-by-line explanation

KEY CONCEPTS: StreamingResponse, UploadFile, event_generator, async for, token tracking
TIME: ~60 minutes
```

### Part 12c: AI Migration & Complete Architecture

```
📄 phase4-part12c-ai-migration.md
├── 004_create_ai_tables.py — 4 tables + pgvector embedding column + IVFFlat index
└── Complete AI architecture diagram (all 39 files mapped)

KEY CONCEPTS: ALTER TABLE ADD COLUMN vector(768), IVFFlat index, vector_cosine_ops
TIME: ~30 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram — How Service Connects All AI Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AI SERVICE — THE ORCHESTRATOR                        │
│                                                                          │
│  router.py (9 endpoints)                                                 │
│    │                                                                     │
│    ▼                                                                     │
│  service.py                                                              │
│    │                                                                     │
│    ├── chat(use_agent=True)  → HealthCoachAgent.create() → agent.chat()  │
│    │                            ├── ReAct loop (Part 10c)                │
│    │                            ├── 5 tools (Part 10a)                   │
│    │                            ├── Short-term memory (Part 10b)         │
│    │                            └── Long-term memory (Part 10b)          │
│    │                                                                     │
│    ├── chat(use_agent=False) → direct LLM call                          │
│    │                            └── get_llm_client() → chat(messages)    │
│    │                                                                     │
│    ├── stream_chat()         → llm.stream_chat() → SSE                  │
│    │                            └── async for chunk → yield to client    │
│    │                                                                     │
│    ├── upload_document()     → DocumentProcessor → TextChunker           │
│    │                         → EmbeddingGenerator → VectorStore          │
│    │                            └── Full RAG ingestion (Part 09a)        │
│    │                                                                     │
│    ├── generate_insight()    → DataCollector → LLM (INSIGHT_PROMPT)      │
│    │                                                                     │
│    └── generate_weekly_report() → DataCollector → Analyzer → ReportWriter│
│                                   └── Workflow pipeline (Part 11a)        │
│                                                                          │
│  Dependencies:                                                           │
│    LLM Layer (Part 08):  get_llm_client(), TokenTracker                 │
│    RAG Layer (Part 09):  DocumentProcessor, TextChunker, Embeddings,    │
│                          VectorStore                                     │
│    Agent Layer (Part 10): HealthCoachAgent                              │
│    Workflow Layer (Part 11): DataCollector, Analyzer, ReportWriter       │
│    Other Modules: HabitRepository, LogRepository, AnalyticsRepository    │
│    Database: documents, document_chunks, ai_chat_messages, ai_insights   │
│    Redis: TokenTracker (daily limits), LongTermMemory (agent insights)   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **SSE (Server-Sent Events)** | One-way server-to-client streaming over HTTP | router.py stream endpoint |
| 2 | **`StreamingResponse`** | FastAPI response that yields chunks over time | router.py |
| 3 | **`async def event_generator()`** | Async generator that wraps LLM stream in SSE format | router.py |
| 4 | **`UploadFile`** | FastAPI file upload handling (multipart form data) | router.py documents |
| 5 | **`X-Accel-Buffering: no`** | Header telling Nginx not to buffer SSE | router.py headers |
| 6 | **pgvector `vector(768)`** | PostgreSQL column type for 768-dimensional embeddings | models.py, migration |
| 7 | **IVFFlat index** | Approximate nearest neighbor index for fast vector search | migration |
| 8 | **Status state machine** | `uploaded → processing → processed/failed` | Document model |
| 9 | **Token tracking** | Redis INCRBY daily per-user usage counting | service.py |
| 10 | **Dual chat mode** | Agent (tools, multi-step) vs Direct (single LLM call) | service.py |
| 11 | **Chat history persistence** | Save all messages to DB for context + display | service.py |
| 12 | **Cross-layer orchestration** | One service method calls LLM + RAG + Agent + Workflow | service.py |

---

<a name="design-decisions"></a>
## 9. Design Decisions

### Decision 1: Single AI Service (Not Separate Services per Feature)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: AI Service Architecture                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: One AiService class orchestrating ALL AI features          │
│                                                                     │
│  WHY:                                                               │
│  • Single entry point — router only knows about AiService           │
│  • Shared dependencies — session, redis, llm client, token tracker  │
│  • Consistent token tracking across all AI features                 │
│  • Easier to test — mock one service, not five                      │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. ChatService + DocumentService + InsightService + ReportService  │
│     ❌ Four services with overlapping dependencies                  │
│     ❌ Token tracking fragmented across services                    │
│  2. Router calls agents/RAG directly                                │
│     ❌ Router becomes fat — orchestration logic in HTTP layer       │
│                                                                     │
│  THE SERVICE DELEGATES:                                             │
│  chat → HealthCoachAgent or direct LLM                              │
│  upload → DocumentProcessor + Chunker + Embedder + VectorStore      │
│  report → DataCollector + Analyzer + ReportWriter                   │
│  The service orchestrates; the layers execute.                      │
│                                                                     │
│  INTERVIEW TIP: "One AiService orchestrates chat, RAG, insights,   │
│  and workflows. It delegates to specialized components — agent for  │
│  chat, RAG pipeline for documents, workflow for reports. Shared     │
│  token tracking ensures consistent usage limits."                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: SSE for Streaming (Not WebSocket)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Streaming Protocol                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Server-Sent Events (SSE) over plain HTTP                   │
│                                                                     │
│  WHY:                                                               │
│  • Simpler than WebSocket — no connection upgrade, no handshake     │
│  • Automatic browser reconnection on disconnect                     │
│  • Sufficient — AI chat is server→client only (no client→server     │
│    streaming needed)                                                │
│  • Same protocol ChatGPT, Claude, and Gemini use                    │
│  • Works through Nginx with `proxy_buffering off`                   │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. WebSocket                                                       │
│     ❌ Bidirectional — overkill for one-way AI streaming            │
│     ❌ More complex (connection state, heartbeat, reconnection)     │
│  2. Long polling (client repeatedly asks "anything new?")           │
│     ❌ High overhead, wasteful, poor UX                            │
│  3. Regular POST (wait for full response)                           │
│     ❌ User waits 5-30 seconds with no feedback                    │
│                                                                     │
│  INTERVIEW TIP: "We use SSE because AI chat is one-directional —   │
│  the server generates tokens, the client displays them. SSE is      │
│  simpler than WebSocket (no connection upgrade), has automatic      │
│  reconnection, and is the same protocol OpenAI and Anthropic use."  │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: Dual Chat Mode (Agent vs Direct)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Two Chat Modes                                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Agent mode (default) + Direct mode (opt-in)                │
│                                                                     │
│  AGENT MODE (use_agent=True — default):                             │
│  • ReAct loop with 5 tools + memory                                 │
│  • Can fetch real data (habits, logs, analytics, documents)         │
│  • 2-5 LLM calls per question (slower, more expensive)             │
│  • Best for: "How's my sleep?" → fetches actual sleep data         │
│                                                                     │
│  DIRECT MODE (use_agent=False):                                     │
│  • Single LLM call with conversation history                       │
│  • No tools, no data fetching — only pre-loaded context            │
│  • 1 LLM call per question (faster, cheaper)                       │
│  • Best for: "What is sleep hygiene?" → general knowledge Q&A      │
│                                                                     │
│  WHY BOTH: Different questions need different approaches.           │
│  Data questions → agent (needs tools). Knowledge questions → direct.│
│  The frontend can toggle: "🤖 Smart Mode" vs "⚡ Quick Mode"        │
│                                                                     │
│  STREAMING: Only direct mode supports SSE streaming because agent   │
│  tool calls happen BETWEEN tokens (can't stream mid-reasoning).     │
│                                                                     │
│  INTERVIEW TIP: "We offer agent mode (data-driven, multi-step) and │
│  direct mode (fast, single-call). The frontend defaults to agent    │
│  but can switch to direct for general questions. Only direct mode   │
│  supports SSE streaming because tool calls interrupt the token flow."│
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: How does SSE streaming work in your AI chat?
**A:** "The `stream_chat()` LLM method is an async generator that yields text chunks as the model generates them. The router wraps this in an `event_generator()` that formats each chunk as SSE: `data: <text>\\n\\n`. FastAPI's `StreamingResponse` sends these events over a long-lived HTTP connection with `media_type='text/event-stream'`. The browser's `EventSource` receives each event and appends the text to the chat display — word by word, like ChatGPT. Nginx is configured with `proxy_buffering off` to forward chunks immediately instead of collecting the full response."

### Q2: Walk me through what happens when a user uploads a document.
**A:** "The router receives the file via FastAPI's `UploadFile`. The service creates a `Document` record with status 'processing'. Then it runs the RAG ingestion pipeline: `DocumentProcessor` extracts text from the PDF page by page, `TextChunker` splits it into ~500-token overlapping chunks, `EmbeddingGenerator` converts each chunk to a 768-dimension vector via the LLM's embed API, and `VectorStore` inserts each chunk with its embedding into the `document_chunks` table in pgvector. The document status is updated to 'processed' with the chunk count. If any step fails, status becomes 'failed' with an error message. The document is now searchable via cosine similarity."

### Q3: Why two chat modes — agent and direct?
**A:** "Different questions need different approaches. 'How much water did I drink this week?' needs the agent — it calls `query_logs` to fetch real data. 'What is sleep hygiene?' doesn't need data — direct LLM is faster and cheaper. Agent mode makes 2-5 LLM calls with tool use (~3-10 seconds). Direct mode makes 1 LLM call (~1-3 seconds). The frontend defaults to agent mode but can toggle to direct for general knowledge questions. Only direct mode supports SSE streaming because agent tool calls interrupt the linear token flow."

### Q4: How does the AI service connect to all other modules?
**A:** "The `AiService` is the single orchestrator. For chat, it creates a `HealthCoachAgent` that uses 5 tools — each tool calls a repository from another module (HabitRepository, LogRepository, AnalyticsService). For document upload, it calls the RAG ingestion pipeline (DocumentProcessor → Chunker → Embeddings → VectorStore). For weekly reports, it calls the workflow steps (DataCollector → Analyzer → ReportWriter). All share the same database session and Redis client. Token tracking wraps every AI call to enforce daily limits."

### Q5: How do you handle the pgvector embedding column in SQLAlchemy?
**A:** "We use a try/except import for `pgvector.sqlalchemy.Vector`. In the migration, we create the column with raw SQL: `ALTER TABLE document_chunks ADD COLUMN embedding vector(768)`. We also create an IVFFlat index: `CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`. IVFFlat is an approximate nearest neighbor index — it clusters vectors and only searches nearby clusters, trading ~5% recall for 10-100x speed. For our scale (<100K chunks per user), this is more than sufficient."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 11b: Workflow Connections & Flows](./phase4-part11b-ai-workflow-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 12a: AI Models & Schemas](./phase4-part12a-ai-models-schemas.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Part 12 Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 12a | [AI Models & Schemas](./phase4-part12a-ai-models-schemas.md) | 4 models + 8 schemas (full source) |
| 12b | [AI Service & Router](./phase4-part12b-ai-service-router.md) | 7-method service + 9-endpoint router (full source + SSE) |
| 12c | [AI Migration & Architecture](./phase4-part12c-ai-migration.md) | 004 migration + complete 39-file architecture |

---

**End of Phase 4 Part 12: AI Service, Router & Models Overview**

*9 endpoints tie 39 AI files into a unified API. SSE streaming gives the ChatGPT experience. The service orchestrates LLM, RAG, agents, and workflows through one clean interface. Next: the models and schemas that define the data shapes.*
