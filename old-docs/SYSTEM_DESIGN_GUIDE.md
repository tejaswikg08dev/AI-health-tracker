# 🏗️ System Design Guide — Health Tracker

## How to Do System Design (Step by Step)

This guide teaches you the PROCESS of system design — the same process used in interviews and at companies. We'll design the Health Tracker from scratch so you learn the thinking, not just the answer.

---

## The 7-Step System Design Process

Every system design — interview or real project — follows these steps:

```
Step 1: REQUIREMENTS       → What does it do? For whom?
Step 2: CAPACITY ESTIMATES  → How much data? How many users?
Step 3: API DESIGN          → What endpoints? What goes in/out?
Step 4: DATA MODEL          → What tables? What relationships?
Step 5: HIGH-LEVEL DESIGN   → What components? How do they talk?
Step 6: DEEP DIVES          → Caching? AI pipeline? Real-time?
Step 7: TRADE-OFFS          → What did you choose and WHY?
```

Let's walk through each for the Health Tracker.

---

## Step 1: Requirements

### How to think about requirements:

Always split into **functional** (what the system does) and **non-functional** (how well it does it).

### Functional Requirements (What)

```
CORE:
├── User registration and authentication
├── Create and manage trackable habits (numeric, boolean, scale types)
├── Log daily habit values (single + bulk)
├── View analytics: streaks, weekly comparison, monthly trends, correlations
├── AI chat: ask questions about your health data
├── Upload health documents (PDF) for AI to reference (RAG)
├── AI agent that fetches real data using tools
├── Weekly AI-generated health report
├── Email notifications (daily reminders, streak milestones)
└── Export data as CSV

DERIVED (from core):
├── One log per habit per day (no duplicates)
├── Soft delete for habits (preserve historical data)
├── Habit reordering (user's preferred display order)
├── Real-time streaming for AI responses (SSE)
└── Document processing pipeline (extract → chunk → embed → store)
```

### Non-Functional Requirements (How Well)

```
PERFORMANCE:
├── Dashboard loads in < 500ms (cached analytics)
├── AI chat responds in < 10 seconds (agent mode)
├── API latency < 200ms for CRUD operations
└── Support 1,000 concurrent users

SECURITY:
├── Passwords hashed with bcrypt (never plain text)
├── JWT with short-lived access tokens (30 min)
├── Rate limiting (prevent brute force, AI spam)
└── Row-level security (users can only see their own data)

RELIABILITY:
├── Data never lost (PostgreSQL with backups)
├── Graceful degradation (AI fails → app still works)
└── Background tasks don't block API responses

SCALABILITY:
├── Modular monolith → can extract modules into microservices
├── Stateless API → horizontal scaling
└── Cache-aside for expensive analytics
```

### Interview tip:
Always ASK clarifying questions before designing:
- "How many users? 100? 1 million?"
- "Is real-time needed or near-real-time?"
- "What's more important — consistency or availability?"
- "What's the read/write ratio?"

For our app: ~1,000 users, reads >> writes, consistency matters (correct streak counts), near-real-time for AI chat.

---

## Step 2: Capacity Estimates

### Why this matters:
Capacity estimates tell you whether you need 1 server or 100, whether to use SQL or NoSQL, whether to cache or not.

### Back-of-the-envelope for Health Tracker:

```
USERS:
├── 1,000 registered users
├── 200 daily active users (DAU)
└── 50 concurrent users at peak

DATA PER USER PER DAY:
├── Habit logs: 5-10 entries × ~200 bytes each = 1-2 KB
├── AI chat messages: 2-5 messages × ~500 bytes each = 1-2.5 KB
├── Document chunks: occasional, ~50 KB per document
└── Total: ~5 KB per user per day

DATA PER YEAR:
├── 1,000 users × 5 KB/day × 365 days = ~1.8 GB/year
├── This fits in a single PostgreSQL instance easily
└── No need for sharding, partitioning, or NoSQL at this scale

REQUESTS PER SECOND:
├── Dashboard load: 4 API calls × 200 DAU = 800 calls/day ≈ 0.01 RPS
├── Daily check-in: 1 bulk call × 200 DAU = 200 calls/day
├── AI chat: 5 messages × 50 users = 250 calls/day
├── Peak: ~10 RPS (all users at morning check-in time)
└── One FastAPI server handles 1,000+ RPS → single server is enough

STORAGE:
├── PostgreSQL: 1.8 GB/year + indexes → 5 GB sufficient for years
├── Redis: <100 MB (cache + rate limiting + token blacklist)
├── S3: document uploads + exports → <1 GB
└── Total: well within free tier limits
```

### Interview tip:
Always show the math, even if approximate. Interviewers want to see you THINK about scale, not just guess.

---

## Step 3: API Design

### How to design APIs:

```
1. Group endpoints by RESOURCE (not by page)
   ✅ /habits, /logs, /analytics
   ❌ /dashboard-data, /check-in-page, /settings-page

2. Use HTTP methods correctly
   GET = read, POST = create, PUT = update, DELETE = remove

3. Use plural nouns
   ✅ /habits, /logs
   ❌ /habit, /log

4. Version your API
   /api/v1/habits (not /habits)

5. Consistent error format
   {"error_code": "HABIT_NOT_FOUND", "message": "...", "detail": null}
```

### Our API design:

```
/api/v1/auth/        → 6 endpoints (signup, login, refresh, logout, profile)
/api/v1/habits/      → 6 endpoints (CRUD + reorder)
/api/v1/logs/        → 5 endpoints (single, bulk, query, update, delete)
/api/v1/analytics/   → 6 endpoints (dashboard, streaks, weekly, monthly, completion, correlations)
/api/v1/ai/          → 9 endpoints (chat, stream, history, documents, insights, report)
/api/v1/notifications/ → 3 endpoints (settings, test email)
/api/v1/export/      → 2 endpoints (CSV, S3)
/health              → 1 endpoint (load balancer health check)
TOTAL: 38 endpoints
```

---

## Step 4: Data Model

### How to design database tables:

```
1. Identify ENTITIES (nouns): User, Habit, HabitLog, Document, ChatMessage
2. Identify RELATIONSHIPS: User has many Habits, Habit has many Logs
3. Choose PRIMARY KEYS: UUID (safe to expose) vs auto-increment (leaks info)
4. Add INDEXES based on query patterns (not guessing)
5. Add CONSTRAINTS: UNIQUE, NOT NULL, CHECK, FK with ON DELETE
6. Think about SOFT DELETE vs HARD DELETE per entity
```

### Our 8 tables:

```
users ──┬── habits ──── habit_logs
        ├── documents ── document_chunks (+ vector embedding)
        ├── ai_chat_messages
        ├── ai_insights
        └── notification_settings

Key design decisions:
├── UUID PKs (not auto-increment) — safe in URLs, supports sharding
├── Soft delete for habits (is_archived) — preserves analytics
├── Hard delete for logs — user correcting mistakes
├── UNIQUE(user_id, habit_id, log_date) — one log per habit per day
├── 3 value columns (numeric, boolean, scale) — type safety > flexibility
└── pgvector for embeddings — same database, no separate vector DB
```

---

## Step 5: High-Level Design

### How to draw architecture:

```
1. Start with the USER
2. Add the FRONTEND (what they interact with)
3. Add the API GATEWAY / REVERSE PROXY (entry point)
4. Add the BACKEND (processes requests)
5. Add DATABASES (stores data)
6. Add CACHE (speeds up reads)
7. Add BACKGROUND WORKERS (async tasks)
8. Add EXTERNAL SERVICES (AI, email, storage)
```

### Our HLD:

```
     User
      │
  React App ──── Vite dev server (localhost:3000)
      │
    Nginx ─────── Rate limiting, SSL, static files
      │
  FastAPI ─────── 7 modules, 38 endpoints
   │  │  │
   │  │  └── Celery Workers ── background tasks
   │  │         │
   │  │      Redis ──── cache, rate limit, token blacklist, task broker
   │  │
   │  └── Ollama ──── local LLM (free)
   │      Groq ────── cloud LLM (free)
   │
   └── PostgreSQL + pgvector ── 8 tables, vector search
       MinIO/S3 ──── file storage
```

---

## Step 6: Deep Dives

### For each non-trivial feature, explain HOW it works internally:

```
DEEP DIVE 1: Authentication (JWT flow)
DEEP DIVE 2: Streak Calculation (gaps-and-islands SQL)
DEEP DIVE 3: Caching Strategy (cache-aside with Redis)
DEEP DIVE 4: Rate Limiting (sliding window algorithm)
DEEP DIVE 5: RAG Pipeline (chunk → embed → search → generate)
DEEP DIVE 6: ReAct Agent (think → act → observe loop)
DEEP DIVE 7: Agentic Workflow (3-step pipeline with retry)
```

---

## Step 7: Trade-offs

### Every design decision has trade-offs. Interviewers love hearing these:

| Decision | We Chose | Alternative | Why |
|----------|----------|-------------|-----|
| Architecture | Modular monolith | Microservices | Single team, shared DB, clear module boundaries |
| Database | PostgreSQL + pgvector | Postgres + Pinecone | One DB to manage, free, transactional |
| Cache | Redis cache-aside | Read-through cache | Simpler, explicit control, easy invalidation |
| LLM | Multi-provider (Strategy) | Hardcoded OpenAI | Free dev (Ollama), free staging (Groq), paid prod (OpenAI) |
| Auth | JWT (stateless) | Session (stateful) | Scalable, no session store, works with mobile |
| Soft delete | is_archived flag | Hard delete | Preserves analytics, reversible |
| 3 value columns | Type-specific columns | Single JSONB column | Type safety at DB level |
| File storage | MinIO (dev) / S3 (prod) | Local filesystem | Same API (boto3), scales to production |
| Background tasks | Celery + Lambda | Just Celery or just Lambda | Celery for dev, Lambda for production (auto-scale) |
| Frontend state | Zustand | Redux | 1KB vs 10KB, less boilerplate, good enough for this scale |

---

## How This Maps to Phases 1-3

| Step | Phase | Document |
|------|-------|----------|
| Step 1: Requirements | Phase 1 | `phase1-part01-system-design-overview.md` |
| Step 2: Capacity | Phase 1 | (included in Phase 1) |
| Step 3: API Design | Phase 2 | `phase2-part01-high-level-design.md` |
| Step 4: Data Model | Phase 3 | `phase3-part02-database-design.md` |
| Step 5: HLD | Phase 2 | `phase2-part01-high-level-design.md` |
| Step 6: Deep Dives | Phase 3 | `phase3-part01-low-level-design.md` |
| Step 7: Trade-offs | All phases | (woven into every design doc) |

---

## Interview Practice

When asked "Design a habit tracker," follow this order:

1. **2 min:** Clarify requirements (ask 3-4 questions)
2. **3 min:** Estimate capacity (users, data, RPS)
3. **5 min:** API design (list main endpoints)
4. **5 min:** Data model (draw tables, relationships)
5. **10 min:** HLD (draw architecture diagram)
6. **10 min:** Deep dive into 2-3 interesting areas
7. **5 min:** Discuss trade-offs and scaling

Total: 40 min — matches a standard system design interview.
