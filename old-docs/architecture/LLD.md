# Low-Level Design (LLD) — Health Tracker

## 1. Module Layer Architecture

Every module follows this layered pattern:

```
Router (HTTP layer)
  ↓ Parses request, calls service, formats response
Service (Business logic)
  ↓ Validates rules, orchestrates repos, raises domain errors
Repository (Data access)
  ↓ Executes SQL queries, returns model objects
Models (Database schema)
  ↓ SQLAlchemy table definitions
Schemas (Pydantic validation)
  ↓ Request/response data shapes
Exceptions (Domain errors)
  → Mapped to HTTP status codes by error_handler middleware
```

## 2. Authentication Flow (Sequence Diagram)

```
Client          FastAPI            AuthService       UserRepo        Redis
  │ POST /login    │                   │               │              │
  │ {email, pass}  │                   │               │              │
  │───────────────>│                   │               │              │
  │                │ authenticate()    │               │              │
  │                │──────────────────>│               │              │
  │                │                   │ get_by_email() │              │
  │                │                   │──────────────>│              │
  │                │                   │    User       │              │
  │                │                   │<──────────────│              │
  │                │                   │               │              │
  │                │                   │ verify_password(plain, hash) │
  │                │                   │ create_access_token(user.id)  │
  │                │                   │ create_refresh_token(user.id) │
  │                │                   │               │              │
  │                │  TokenResponse    │               │              │
  │                │<──────────────────│               │              │
  │ {access_token,  │                   │               │              │
  │  refresh_token} │                   │               │              │
  │<───────────────│                   │               │              │
  │                │                   │               │              │
  │ GET /habits    │                   │               │              │
  │ Auth: Bearer x │                   │               │              │
  │───────────────>│                   │               │              │
  │                │ decode_token(x)   │               │              │
  │                │ check blacklist   │               │              │
  │                │─────────────────────────────────────────────────>│
  │                │                   │               │   not found  │
  │                │<─────────────────────────────────────────────────│
  │                │ → user_id extracted, proceed to handler          │
```

## 3. Streak Calculation Algorithm

**Problem:** Given a list of dates a habit was logged, find consecutive day sequences.

**Algorithm:** Gaps and Islands (SQL window function)

```sql
-- Step 1: Number each date
log_date    | row_num
2026-09-20  | 1
2026-09-21  | 2
2026-09-22  | 3
2026-09-24  | 4    ← gap on Sep 23
2026-09-25  | 5
2026-09-26  | 6

-- Step 2: Subtract row_number from date → group identifier
log_date - row_num = group
2026-09-20 - 1 = Sep 19
2026-09-21 - 2 = Sep 19   ← same group (consecutive)
2026-09-22 - 3 = Sep 19   ← same group
2026-09-24 - 4 = Sep 20   ← different group (gap detected!)
2026-09-25 - 5 = Sep 20
2026-09-26 - 6 = Sep 20

-- Step 3: GROUP BY group → count = streak length
Group Sep 19: 3 days (Sep 20-22)
Group Sep 20: 3 days (Sep 24-26) ← current streak (includes today)
```

**Time complexity:** O(n log n) — one SQL query with window function.

## 4. Rate Limiter Design

**Algorithm:** Fixed window counter (Redis)

```
Key format:  rl:{client_ip}:{path}:{window_start}
Value:       counter (incremented per request)
TTL:         window_seconds (auto-cleanup)

Request arrives:
1. window_start = time() // window_seconds
2. key = f"rl:{ip}:{path}:{window_start}"
3. count = INCR key
4. if count == 1: EXPIRE key window_seconds
5. if count > limit: return 429 Too Many Requests
6. else: proceed
```

**Limits:** `/api/v1/ai/*` = 2r/s, `/api/v1/auth/login` = 5r/min, general = 30r/s

## 5. Cache-Aside Pattern (Analytics)

```
GET /analytics/dashboard
    ↓
Check Redis: analytics:{user_id}:dashboard
    ↓
  HIT → return cached JSON (< 1ms)
  MISS → query PostgreSQL (50-200ms)
       → transform to response schema
       → SET Redis with TTL (5 min for dashboard)
       → return fresh data

POST /logs (new log created)
    ↓
DELETE analytics:{user_id}:* from Redis (invalidate all analytics)
    ↓
Next dashboard load recalculates fresh data
```

## 6. ReAct Agent Loop

```
INIT: system_prompt + tools + memory

LOOP (max 5 iterations):
  1. Build messages = [system, ...history, user_message, ...tool_results]
  2. LLM.chat(messages, tools=tool_schemas)
  3. IF response has tool_calls:
       FOR each tool_call:
         result = tools[name].execute(**arguments)
         messages.append(tool_result)
       CONTINUE loop
     ELSE:
       RETURN response.content as final answer

TIMEOUT: Ask LLM for best answer without tools
```

## 7. RAG Pipeline

```
INGESTION:
  PDF → PyPDF2 extract → page_texts[]
  → RecursiveCharacterTextSplitter(2000 chars, 200 overlap)
  → TextChunks[] with page_number tracking
  → EmbeddingGenerator.embed_texts(chunk_texts) → vectors[]
  → VectorStore.store_chunk(chunk, embedding) → pgvector INSERT

RETRIEVAL:
  User query → EmbeddingGenerator.embed_query(query) → query_vector
  → VectorStore.similarity_search(query_vector, top_k=5, threshold=0.3)
  → PostgreSQL: ORDER BY embedding <=> query_vector LIMIT 5
  → Filter by token budget (max 2000 tokens context)
  → Format with source citations: "[Source: report.pdf, Page 3]"
  → Return to LLM as context in the prompt
```

## 8. Database Schema (ER Diagram)

```
users (PK: id)
  │
  ├── habits (FK: user_id) ── habit_logs (FK: habit_id, user_id)
  │
  ├── documents (FK: user_id) ── document_chunks (FK: document_id)
  │                                 └── embedding vector(768)
  │
  ├── ai_chat_messages (FK: user_id)
  ├── ai_insights (FK: user_id)
  └── notification_settings (FK: user_id, UNIQUE)

Key indexes:
  habits:         (user_id, is_archived)
  habit_logs:     (user_id, log_date), (habit_id, log_date)
  habit_logs:     UNIQUE(user_id, habit_id, log_date)
  document_chunks: IVFFlat(embedding vector_cosine_ops)
  ai_chat_messages: (user_id, created_at)
```
