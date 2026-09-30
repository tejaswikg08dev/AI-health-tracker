# 🏗️ Phase 1: System Design

> **"A health tracker is not just CRUD — it's a data pipeline that feeds an AI agent which reasons about your life."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 1 — System Design |
| **Previous** | [phase0-part2-environment-setup.md](./phase0-part2-environment-setup.md) |
| **Next** | [phase2-high-level-design.md](./phase2-high-level-design.md) |
| **Author** | Shreya |
| **Created** | 2026 |
| **Status** | Living Document |
| **Audience** | System Design Learners, Full-Stack Engineers, AI Engineers |

---

## 📖 Table of Contents

1. [Introduction — Why System Design Matters](#introduction)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [Design Decisions (10 Decisions in Boxed Format)](#design-decisions)
5. [API Design (38 Endpoints)](#api-design)
6. [Database Design (8 Tables with SQL)](#database-design)
7. [AI Pipeline Design](#ai-pipeline-design)
8. [Security Design](#security-design)
9. [Capacity Planning](#capacity-planning)
10. [Caching Strategy](#caching-strategy)
11. [What You Learned](#what-you-learned)
12. [Document Index](#document-index)

---

## 🎯 Introduction

### Why System Design Matters for This Project

This project looks simple on the surface — "track habits and show charts." But under the hood, it solves problems that most tutorial apps never touch:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HEALTH TRACKER COMPLEXITY                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  1. AI AGENT WITH TOOLS   → LLM decides which DB queries to run     │
│  2. RAG PIPELINE          → PDF → chunks → embeddings → vector search│
│  3. VECTOR SEARCH         → Cosine similarity in PostgreSQL (pgvector)│
│  4. CACHE INVALIDATION    → Stale analytics when new logs arrive     │
│  5. RATE LIMITING         → Different limits per endpoint type       │
│  6. TOKEN LIFECYCLE       → Access + refresh + blacklist in Redis    │
│  7. STREAK ALGORITHM      → Gaps-and-islands SQL (window functions)  │
│  8. STREAMING RESPONSES   → SSE for word-by-word AI chat             │
│  9. BULK OPERATIONS       → Atomic save-all in daily check-in        │
│  10. MULTI-STEP WORKFLOW  → 3 agents in pipeline with retry/fallback │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### What Makes a Health Tracker Different from CRUD?

Unlike a typical to-do app:

| Aspect | Typical CRUD App | Our Health Tracker |
|--------|-----------------|-------------------|
| Data model | Flat (one table, simple fields) | Multi-type values (numeric, boolean, scale) per entity |
| Analytics | None or basic counts | Window functions, correlations, time-series trends |
| AI | None | ReAct agent with 5 tools, RAG pipeline, agentic workflow |
| Caching | None | Cache-aside with Redis, TTL per query type, invalidation on writes |
| Auth | Simple token | JWT access + refresh, Redis blacklist, token rotation |
| Background | None | Celery tasks, Lambda functions, scheduled emails |
| Deployment | `python app.py` | Docker Compose (7 services), Nginx, CI/CD, Lambda |

This document walks through every design decision with full reasoning, alternatives, and trade-offs.

---

## 📝 Functional Requirements

### FR Table — What the System Must DO

| ID | Requirement | Description | Priority | Module |
|----|-------------|-------------|----------|--------|
| FR-01 | **User Authentication** | Register with email/password, login with JWT tokens (access 30min + refresh 7d), logout with token blacklist, profile management | P0 — Critical | Auth |
| FR-02 | **Habit Management** | Create trackable habits (3 types: numeric, boolean, scale), edit properties, archive (soft delete), drag-and-drop reorder, max 20 active habits | P0 — Critical | Habits |
| FR-03 | **Daily Logging** | Log habit values for today (or past dates, not future), bulk "Save All" for daily check-in, one log per habit per day (enforced by DB constraint), type-specific validation | P0 — Critical | Logs |
| FR-04 | **Analytics Dashboard** | Today's progress (X of Y habits), current best streak, weekly completion %, streaks for all habits, weekly comparison (this vs last), monthly trend charts, completion rates | P0 — Critical | Analytics |
| FR-05 | **Habit Correlations** | Pearson correlation between any two habits (e.g., sleep vs mood r=0.72), strength rating (weak/moderate/strong), human-readable insights | P1 — High | Analytics |
| FR-06 | **AI Chat** | Conversational health coaching with two modes: direct LLM (fast, simple) and ReAct agent (slower, data-driven with tool calling) | P0 — Critical | AI |
| FR-07 | **RAG Document Q&A** | Upload health PDFs (blood reports, nutrition guides), chunk + embed + store in pgvector, retrieve and cite relevant passages when answering questions | P1 — High | AI |
| FR-08 | **AI Agent Tools** | 5 tools: query habit logs, get analytics, search documents (RAG), calculate correlations, generate improvement plans | P1 — High | AI |
| FR-09 | **Agent Memory** | Short-term (conversation buffer, last 20 messages) + long-term (persistent insights in Redis across sessions, e.g., "user is vegetarian") | P2 — Medium | AI |
| FR-10 | **Weekly Report** | Automated 3-step agentic workflow: collect data → analyze patterns (LLM) → write personalized report (LLM). Orchestrator handles retry and fallback. | P1 — High | AI |
| FR-11 | **Streaming Responses** | AI chat responses appear word-by-word via Server-Sent Events (SSE), like ChatGPT | P1 — High | AI |
| FR-12 | **Email Notifications** | Daily reminder ("time to log!"), weekly report email, streak milestone celebrations (7, 30, 100 days) | P2 — Medium | Notifications |
| FR-13 | **Data Export** | Export habit logs as CSV (direct download or async via S3 presigned URL) | P2 — Medium | Export |
| FR-14 | **Serverless Functions** | 6 Lambda functions: daily reminder (cron), weekly report (cron), CSV export (SQS), streak milestone (SQS), data cleanup (cron), document processor (S3 event) | P2 — Medium | Lambda |

### Habit Type System

Understanding the 3 habit types is critical for data model and validation design:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    3 HABIT TYPES                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  TYPE 1: NUMERIC                                                     │
│  ├── Value: a floating-point number                                  │
│  ├── Unit: "glasses", "hours", "steps", "minutes"                   │
│  ├── Target: daily goal (e.g., 8 glasses)                           │
│  ├── Examples: Water (8 glasses), Sleep (7.5 hours), Steps (10000) │
│  ├── Stored in: habit_logs.value_numeric (FLOAT)                    │
│  └── Analytics: AVG, SUM, trend lines                               │
│                                                                       │
│  TYPE 2: BOOLEAN                                                     │
│  ├── Value: true or false (yes/no)                                  │
│  ├── Unit: N/A                                                       │
│  ├── Target: "did it" = true                                        │
│  ├── Examples: Exercise (did/didn't), Meditated (yes/no)           │
│  ├── Stored in: habit_logs.value_boolean (BOOLEAN)                  │
│  └── Analytics: count of true days, streak of consecutive true     │
│                                                                       │
│  TYPE 3: SCALE                                                       │
│  ├── Value: integer 1-10                                            │
│  ├── Unit: N/A                                                       │
│  ├── Target: N/A (subjective rating)                                │
│  ├── Examples: Mood (1-10), Energy (1-10), Pain (1-10)             │
│  ├── Stored in: habit_logs.value_scale (INTEGER, CHECK 1-10)       │
│  └── Analytics: AVG, trend lines, correlation with other habits    │
│                                                                       │
│  WHY 3 SEPARATE COLUMNS (not one JSONB)?                            │
│  ├── Type safety at database level (FLOAT vs BOOLEAN vs INT)       │
│  ├── Direct SQL aggregation: AVG(value_numeric) works              │
│  ├── CHECK constraints: value_scale BETWEEN 1 AND 10              │
│  └── Clear semantics: each column stores only its type             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Streak Rules

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAK BUSINESS RULES                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  WHAT COUNTS AS "LOGGED":                                            │
│  ├── Numeric habit: value_numeric IS NOT NULL (even 0 counts)       │
│  ├── Boolean habit: value_boolean = TRUE only (false = not done)    │
│  └── Scale habit: value_scale IS NOT NULL (any 1-10 counts)        │
│                                                                       │
│  CURRENT STREAK:                                                     │
│  ├── Consecutive days ending today OR yesterday                     │
│  ├── "Yesterday" tolerance: user might not have logged today yet    │
│  └── Resets to 0 if a day is missed (gap in dates)                 │
│                                                                       │
│  LONGEST STREAK:                                                     │
│  └── All-time maximum consecutive days (historical best)            │
│                                                                       │
│  EXAMPLE:                                                            │
│  Dates logged: Sep 20, 21, 22, 24, 25, 26 (today)                 │
│  ├── Gap on Sep 23!                                                  │
│  ├── Streak 1: Sep 20-22 (3 days)                                  │
│  ├── Streak 2: Sep 24-26 (3 days) ← CURRENT (includes today)     │
│  ├── Current streak: 3                                               │
│  └── Longest streak: 3 (tied)                                        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Non-Functional Requirements

### NFR Table — How Well the System Must Perform

| ID | Category | Requirement | Target | How We Achieve It |
|----|----------|-------------|--------|-------------------|
| NFR-01 | **Latency** | Dashboard API response time | < 500ms (cached), < 2s (uncached) | Redis cache-aside (5 min TTL) |
| NFR-02 | **Latency** | CRUD operations (habits, logs) | < 200ms | PostgreSQL with proper indexes |
| NFR-03 | **Latency** | AI chat (agent mode) | < 15 seconds | Max 5 tool calls, LLM timeout 30s |
| NFR-04 | **Latency** | AI chat (direct mode) | < 5 seconds | Single LLM call, no tools |
| NFR-05 | **Throughput** | Concurrent users at peak | 50 users | Single FastAPI server (handles 1000+ RPS) |
| NFR-06 | **Availability** | System uptime | 99% (3.65 days downtime/year) | Docker restart policies, health checks |
| NFR-07 | **Durability** | Zero data loss for habit logs | RPO = 0 | PostgreSQL WAL, Docker volumes |
| NFR-08 | **Security** | Password storage | bcrypt cost 12 (~100ms/hash) | passlib[bcrypt] |
| NFR-09 | **Security** | Token lifecycle | Access 30min, refresh 7d, blacklist on logout | JWT + Redis SETEX with TTL |
| NFR-10 | **Security** | Rate limiting | 30r/s API, 2r/s AI, 5r/min login | Redis sliding window + Nginx limit_req |
| NFR-11 | **Security** | Row-level access | User can ONLY see their own data | WHERE user_id = :current_user in every query |
| NFR-12 | **Scalability** | Growth path | 10x without re-architecture | Stateless JWT, modular monolith, Redis cache |
| NFR-13 | **Cost** | Development cost | $0/month | Ollama (free LLM), Docker (free), MinIO (free S3) |
| NFR-14 | **Cost** | Production cost | < $200/month | Render free + AWS free tier + Groq free |
| NFR-15 | **Observability** | Request tracing | Every request has a unique ID | X-Request-ID header, structlog JSON |

---

## 🧠 Design Decisions

### Decision 1: Architecture Style

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Architecture Style — Modular Monolith       │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Modular Monolith (7 modules in ONE deployable app)      │
│ WHY: Single developer, shared database, clear module boundaries │
│      that allow future extraction into microservices if needed. │
│ ALTERNATIVES:                                                    │
│   ├── Pure Monolith — Rejected: No module boundaries. All code │
│   │   in one folder. Becomes spaghetti at 100+ files. Can't    │
│   │   reason about what depends on what.                        │
│   └── Microservices — Rejected: Need service discovery, API     │
│       gateway, distributed tracing, separate CI/CD per service, │
│       distributed transactions. 3 months of infrastructure      │
│       before writing any business logic. Overkill for 1 dev.    │
│ TRADE-OFFS:                                                      │
│   ✅ Simple deployment (one Docker container)                    │
│   ✅ Simple debugging (one process, one log stream)              │
│   ✅ Shared database (no distributed transactions)               │
│   ✅ Module boundaries for future extraction                     │
│   ❌ Can't scale modules independently (all scale together)     │
│   ❌ One module's bug can crash the whole app                    │
│   ❌ Single database becomes bottleneck at very high scale      │
│ AT SCALE: Extract the AI module first (most expensive). It      │
│   becomes a separate FastAPI service with its own scaling.      │
│   Replace service.method() with HTTP call. Zero business logic  │
│   changes because modules communicate through interfaces.        │
│ REAL-WORLD: Shopify (10M+ merchants) runs a modular monolith.  │
│   GitHub ran a monolith until 2020. Basecamp deliberately chose │
│   monolith over microservices. Most successful startups start   │
│   monolith and extract services only when scale demands it.     │
│ 🎤 INTERVIEW TIP: "I chose a modular monolith because it gives │
│    me microservice-like boundaries (Router→Service→Repository)  │
│    without the operational overhead. Each module communicates    │
│    through service interfaces, so extracting any module into a  │
│    separate service requires changing one line: the service     │
│    call becomes an HTTP call."                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 2: Primary Database

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Primary Database — PostgreSQL + pgvector    │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: PostgreSQL 16 with pgvector extension                    │
│ WHY: Need ACID transactions for habit data AND vector search    │
│      for RAG. PostgreSQL + pgvector gives BOTH in ONE database. │
│ ALTERNATIVES:                                                    │
│   ├── PostgreSQL + Pinecone (separate vector DB) — Rejected:    │
│   │   $70/month for Pinecone. Two databases to manage, backup,  │
│   │   and scale. Document + chunks can't be in same transaction │
│   │   (if doc insert succeeds but chunks fail → orphaned doc).  │
│   ├── MongoDB — Rejected: No ACID across collections. No window│
│   │   functions for streak calculation. No native vector search │
│   │   (Atlas Vector Search is add-on). Eventual consistency is  │
│   │   unacceptable for streak counts that must be accurate.     │
│   └── SQLite — Rejected: No concurrent writes (WAL mode helps  │
│       but limited). No pgvector. No connection pooling. Fine    │
│       for prototypes, not for production with async FastAPI.    │
│ TRADE-OFFS:                                                      │
│   ✅ ACID transactions — streak counts are always accurate      │
│   ✅ pgvector — vector search without separate database          │
│   ✅ Window functions — streak calculation in one SQL query      │
│   ✅ JSONB — flexible metadata without schema migrations         │
│   ✅ Mature ecosystem (pgAdmin, DBeaver, Alembic, SQLAlchemy)   │
│   ❌ Vertical scaling limits (solved by read replicas)           │
│   ❌ pgvector IVFFlat is approximate (~95% recall, not 100%)    │
│   ❌ More complex than SQLite for simple prototypes              │
│ AT SCALE: Read replicas for analytics queries. RDS Multi-AZ     │
│   for high availability. Citus extension for horizontal sharding│
│   by user_id if needed.                                          │
│ REAL-WORLD: Supabase uses PostgreSQL + pgvector. Notion uses    │
│   PostgreSQL for their AI features. Instagram used PostgreSQL   │
│   at massive scale before sharding.                              │
│ 🎤 INTERVIEW TIP: "I chose PostgreSQL with pgvector because I  │
│    need ACID compliance for accurate streak counts AND vector   │
│    similarity search for RAG — all in one database. The         │
│    alternative was PostgreSQL + Pinecone at $70/month, with no  │
│    transactional guarantee between document and chunk inserts." │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 3: LLM Provider Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: LLM Providers — Strategy Pattern (3 impls) │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Abstract BaseLLMClient with 3 implementations:          │
│         OllamaClient (free local), GroqClient (free cloud),    │
│         OpenAIClient (paid production). Factory function reads  │
│         LLM_PROVIDER env var and returns the right one.         │
│ WHY: Development must be free ($0). Production needs the best  │
│      quality (OpenAI). Switching should be a config change,     │
│      not a code change.                                         │
│ ALTERNATIVES:                                                    │
│   ├── Hardcode OpenAI — Rejected: Costs $30-50/month during    │
│   │   development. Requires internet. Vendor lock-in.           │
│   ├── Use LangChain — Rejected: Heavy abstraction over simple  │
│   │   HTTP calls. We only need chat() + stream_chat() + embed()│
│   │   LangChain adds complexity without proportional benefit    │
│   │   for our use case. Building from scratch teaches more.     │
│   └── Single provider (only Ollama) — Rejected: Can't deploy   │
│       Ollama on Render/Vercel free tier (no GPU, no Docker).   │
│       Need a cloud provider for deployment.                     │
│ TRADE-OFFS:                                                      │
│   ✅ $0 during development (Ollama runs locally)                 │
│   ✅ $0 during staging (Groq free tier: 30 req/min)             │
│   ✅ Best quality in production (OpenAI GPT-4)                   │
│   ✅ Swap provider with one env var change                       │
│   ✅ Teaching value — Strategy pattern is a core design pattern │
│   ❌ 3 client implementations to maintain                       │
│   ❌ Slight differences in tool calling format between providers │
│   ❌ Groq doesn't support embeddings (falls back to Ollama)    │
│ AT SCALE: Add AWS Bedrock as 4th provider. Same interface,     │
│   managed scaling, no GPU provisioning.                         │
│ REAL-WORLD: Every production AI system uses provider abstraction│
│   Anthropic, OpenAI, Google all have different APIs. Companies  │
│   like Vercel AI SDK abstract them behind a common interface.   │
│ 🎤 INTERVIEW TIP: "I used the Strategy pattern for LLM         │
│    providers. BaseLLMClient defines chat(), stream_chat(), and  │
│    embed(). Three implementations: Ollama (free dev), Groq      │
│    (free cloud), OpenAI (production). A factory function reads  │
│    LLM_PROVIDER from the environment and returns the right      │
│    client. The rest of the app — agents, RAG, workflows — all  │
│    call the abstract interface. Swapping providers is a config  │
│    change, not a code change."                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 4: Caching Layer

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Caching — Redis with Cache-Aside Pattern    │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Redis 7 with cache-aside (application manages cache)    │
│ WHY: Analytics queries use window functions and CTEs — 50-200ms │
│      per query. Dashboard loads 4 analytics endpoints. Without  │
│      cache: 800ms. With cache: 4ms (200x faster).              │
│ ALTERNATIVES:                                                    │
│   ├── No cache — Rejected: Dashboard loads in 800ms+ every     │
│   │   time. Acceptable for 10 users, painful for 100+.         │
│   ├── Python @lru_cache — Rejected: Per-process cache. If you  │
│   │   have 4 Gunicorn workers, each has its own cache. 4x      │
│   │   memory usage, 4x stale data risk. Redis is shared.       │
│   └── Read-through cache (cache reads DB automatically) —      │
│       Rejected: More complex to implement. Cache-aside is      │
│       simpler and gives us explicit control over invalidation.  │
│ TRADE-OFFS:                                                      │
│   ✅ 200x faster dashboard loads (4ms vs 800ms)                 │
│   ✅ Shared across all workers (one cache, not per-process)     │
│   ✅ TTL auto-expires stale data (5min dashboard, 30min others) │
│   ✅ Same Redis used for rate limiting + token blacklist         │
│   ❌ Cache invalidation complexity (must delete on every write) │
│   ❌ First request after invalidation is slow (cold cache)      │
│   ❌ Redis down = slower app (fail-open, queries hit DB)        │
│ AT SCALE: Redis Cluster for high availability. Separate Redis   │
│   instances for cache vs rate limiting (different eviction).    │
│ REAL-WORLD: Every large website uses cache-aside. Facebook,     │
│   Twitter, Instagram all use Redis/Memcached this way.          │
│ 🎤 INTERVIEW TIP: "Cache-aside: check cache → miss → query DB │
│    → store result in cache with TTL → return. On writes: delete │
│    cache keys → next read recalculates fresh. TTLs: 5 min for  │
│    dashboard (changes often), 30 min for streaks (change daily),│
│    1 hour for correlations (expensive, stable)."                │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 5: Authentication Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Authentication — JWT with Dual Tokens       │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: JWT access tokens (30min) + refresh tokens (7 days),    │
│         token blacklist in Redis for logout support.             │
│ WHY: JWTs are stateless — the server validates without a DB     │
│      lookup on every request. Short access tokens limit damage  │
│      if stolen. Refresh tokens keep users logged in for days.   │
│ ALTERNATIVES:                                                    │
│   ├── Session-based auth — Rejected: Every request needs a      │
│   │   database/cache lookup to validate the session. At 100     │
│   │   requests/second, that's 100 extra Redis GETs. JWTs       │
│   │   validate locally using the secret key (zero I/O).         │
│   └── API keys only — Rejected: API keys don't expire           │
│       (security risk). No concept of "sessions" or "logout."   │
│       Good for server-to-server, not for user-facing apps.      │
│ TRADE-OFFS:                                                      │
│   ✅ Stateless validation (no DB hit per request)                │
│   ✅ Short-lived access tokens limit damage from theft           │
│   ✅ Refresh tokens keep users logged in without re-entering pwd │
│   ✅ Token blacklist enables "real" logout                       │
│   ❌ Can't revoke access tokens instantly (up to 30 min window) │
│   ❌ Token size (~800 bytes) larger than session ID (~32 bytes) │
│   ❌ Blacklist check on every request (Redis GET, but fast)     │
│ AT SCALE: Move to asymmetric JWT (RS256). Identity service      │
│   signs with private key. All other services verify with public │
│   key. No shared secret.                                         │
│ REAL-WORLD: Razorpay uses JWT for dashboard + API keys for      │
│   integration. Auth0 recommends short-lived JWTs + rotation.    │
│ 🎤 INTERVIEW TIP: "Short-lived JWTs (30 min) with refresh      │
│    tokens give us stateless auth with practical revocation.      │
│    Worst case, a compromised access token works for 30 minutes. │
│    The refresh token is stored in Redis — we can revoke it      │
│    immediately on logout or security event."                     │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 6: AI Agent Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: AI Agent — ReAct Pattern (from scratch)     │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Custom ReAct agent with 5 tools, built from scratch    │
│         (not using LangChain or CrewAI).                         │
│ WHY: The ReAct pattern (Reason + Act) gives the LLM ability    │
│      to THINK about what data it needs, CALL tools to fetch    │
│      real data from our database, and ITERATE until it has     │
│      enough information to answer accurately.                    │
│ ALTERNATIVES:                                                    │
│   ├── Simple LLM call (no agent) — Rejected: Without tools,    │
│   │   the LLM gives generic advice ("drink more water") instead │
│   │   of data-driven answers ("you averaged 5.2 glasses, below  │
│   │   your target of 8").                                        │
│   ├── LangChain Agent — Rejected: Heavy dependency (300+ sub-  │
│   │   packages). Abstracts away the learning. Our agent is ~100 │
│   │   lines of code — every line understandable. LangChain's   │
│   │   agent is thousands of lines behind abstractions.           │
│   └── Function calling only (no loop) — Rejected: One tool     │
│       call per question. The agent can't REASON that it needs   │
│       sleep data AND correlation data for "Why am I tired?"     │
│ TRADE-OFFS:                                                      │
│   ✅ Data-driven answers (agent queries YOUR database)           │
│   ✅ Multi-step reasoning (up to 5 tool calls per question)     │
│   ✅ Full understanding (we wrote every line, no black box)      │
│   ✅ Lightweight (no heavy dependencies like LangChain)          │
│   ❌ Slower than direct LLM call (multiple round trips)          │
│   ❌ Token cost multiplied by number of iterations               │
│   ❌ Tool errors can confuse the LLM                             │
│ AT SCALE: Add tool result caching. Add cost-based routing       │
│   (simple questions → direct mode, complex → agent mode).       │
│ REAL-WORLD: OpenAI's function calling, Anthropic's tool use,   │
│   Google's Gemini all use the same pattern. LangChain and       │
│   CrewAI are built on top of ReAct.                              │
│ 🎤 INTERVIEW TIP: "I built a ReAct agent from scratch. The     │
│    loop: send message + tool schemas to LLM → LLM returns      │
│    either a text response (done) or a tool call (keep going).   │
│    If tool call: execute the tool, add result to conversation,  │
│    loop back. Max 5 iterations. The agent has 5 tools that      │
│    query my actual PostgreSQL database — not generic AI advice."│
└─────────────────────────────────────────────────────────────────┘
```

### Decision 7: RAG Vector Storage

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Vector Storage — pgvector (in PostgreSQL)   │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: pgvector extension in the same PostgreSQL database      │
│ WHY: One database for both relational data AND vector search.   │
│      No separate service to manage. Transactional: document +   │
│      chunks are inserted in the same commit.                    │
│ ALTERNATIVES:                                                    │
│   ├── Pinecone — Rejected: $70/month minimum. Separate service  │
│   │   to manage. Not transactional with our relational data.    │
│   ├── ChromaDB — Rejected: In-memory by default. Not production │
│   │   ready. Limited query capabilities vs pgvector.            │
│   └── Weaviate — Rejected: Another service to deploy and manage.│
│       Overkill for < 1M vectors.                                 │
│ TRADE-OFFS:                                                      │
│   ✅ Free (PostgreSQL extension, no extra cost)                  │
│   ✅ One database (no extra infrastructure)                      │
│   ✅ Transactional (document + chunks in same commit)            │
│   ✅ SQL-friendly (JOIN chunks with documents for metadata)      │
│   ❌ Approximate search only (IVFFlat ~95% recall, not 100%)   │
│   ❌ Slower than dedicated vector DBs at very large scale       │
│   ❌ Limited to one machine (no distributed vector search)      │
│ AT SCALE: At 10M+ vectors, consider Pinecone or Qdrant. But    │
│   for a personal health tracker with < 100K chunks: pgvector.  │
│ REAL-WORLD: Supabase uses pgvector. Neon database uses pgvector.│
│   Many YC startups use pgvector for their RAG implementations. │
│ 🎤 INTERVIEW TIP: "pgvector gives me SQL + vector search in    │
│    one database. IVFFlat index provides 95% recall with 10-100x│
│    speedup over brute force. The <=> operator calculates cosine │
│    distance. For < 1M vectors, pgvector matches dedicated vector│
│    databases in performance while being free and transactional."│
└─────────────────────────────────────────────────────────────────┘
```

### Decision 8: Rate Limiting Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Rate Limiting — Redis + Nginx (Two Layers) │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Nginx rate limiting (L7, per-IP) + Application rate    │
│         limiting (Redis sliding window, per-endpoint-type).     │
│ WHY: Defense in depth. Nginx protects against floods before     │
│      they reach FastAPI. Application rate limiting provides     │
│      granular per-endpoint control (AI costs more than CRUD).  │
│ ALTERNATIVES:                                                    │
│   ├── Nginx only — Rejected: Can't differentiate endpoint types │
│   │   (AI vs CRUD). All endpoints get the same limit.           │
│   ├── Application only — Rejected: Floods reach FastAPI before  │
│   │   being rejected. Wastes CPU on parsing + auth for requests │
│   │   that will be rate-limited anyway.                          │
│   └── Token bucket (instead of sliding window) — Acceptable.    │
│       Sliding window is simpler to implement with Redis INCR.   │
│       Token bucket is better for smooth rate limiting.           │
│ TRADE-OFFS:                                                      │
│   ✅ Two layers — defense in depth                               │
│   ✅ Different limits per endpoint (30r/s API, 2r/s AI, 5r/m login)│
│   ✅ Nginx blocks floods before they reach application           │
│   ✅ Fail-open if Redis down (requests pass through)            │
│   ❌ Two configurations to maintain (nginx.conf + Python)        │
│   ❌ Redis dependency for application rate limiting               │
│ 🎤 INTERVIEW TIP: "Two-layer rate limiting. Nginx limit_req    │
│    blocks IP-level floods before they reach FastAPI. Application │
│    layer uses Redis INCR with TTL for per-endpoint limits: 2r/s │
│    for AI (expensive LLM calls), 5r/min for login (brute force │
│    prevention), 30r/s for general API. If Redis is down, I fail │
│    open — rate limiting shouldn't be a single point of failure."│
└─────────────────────────────────────────────────────────────────┘
```

### Decision 9: Background Task Processing

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Background Tasks — Celery + Lambda          │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: Celery (local dev) + AWS Lambda (production), both     │
│         using Redis as message broker.                           │
│ WHY: Some operations (email, reports, CSV export) take too long │
│      for an API response. Background processing lets the API    │
│      respond immediately ("export started!") while work happens │
│      asynchronously.                                             │
│ ALTERNATIVES:                                                    │
│   ├── Celery only — Acceptable for local dev. But Celery needs  │
│   │   a always-running worker process (costs money on AWS).     │
│   │   Lambda scales to zero (free when idle).                    │
│   ├── Lambda only — Rejected: Can't test Lambda locally easily  │
│   │   (SAM local invoke is clunky). Celery works seamlessly    │
│   │   in Docker Compose for development.                         │
│   └── FastAPI BackgroundTasks — Rejected: Runs in the same      │
│       process as the API. If the process crashes, background    │
│       tasks are lost. No retry logic. No queue persistence.     │
│ TRADE-OFFS:                                                      │
│   ✅ Celery for development (simple, Docker Compose)             │
│   ✅ Lambda for production (auto-scale, free tier, zero cost idle)│
│   ✅ Same logic, different triggers (Celery task vs Lambda handler)│
│   ❌ Two systems to understand (Celery + Lambda)                 │
│   ❌ Lambda cold starts (~1-2 seconds for Python)                │
│ 🎤 INTERVIEW TIP: "I use Celery for local development and AWS  │
│    Lambda for production. The business logic is the same — only │
│    the trigger changes. Celery tasks are triggered by Redis.    │
│    Lambda functions are triggered by EventBridge (cron), SQS    │
│    (async processing), or S3 (file upload events). Lambda's     │
│    advantage: scales to zero, costs nothing when idle."          │
└─────────────────────────────────────────────────────────────────┘
```

### Decision 10: Primary Key Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 DESIGN DECISION: Primary Keys — UUID v4                       │
├─────────────────────────────────────────────────────────────────┤
│ CHOSEN: UUID v4 (random) for all primary keys, stored as        │
│         PostgreSQL UUID type.                                    │
│ WHY: UUIDs are globally unique, non-guessable, and safe to     │
│      expose in URLs. No information leakage (can't guess user  │
│      count from sequential IDs).                                 │
│ ALTERNATIVES:                                                    │
│   ├── Auto-increment (SERIAL/BIGSERIAL) — Rejected:             │
│   │   - Reveals record count: /users/50000 → "they have 50K users"│
│   │   - Enumeration attack: try /users/1, /users/2, ... /users/N │
│   │   - Merge conflicts: two databases both have id=1            │
│   └── UUID v7 (time-ordered) — Acceptable and better for B-tree │
│       performance. We use v4 because Python's uuid4() is built-in│
│       and pgvector/SQLAlchemy support is simpler. For our scale  │
│       (< 1M rows), the B-tree performance difference is negligible.│
│ TRADE-OFFS:                                                      │
│   ✅ Non-guessable (safe in URLs, APIs, logs)                    │
│   ✅ No information leakage (user count hidden)                  │
│   ✅ Generate anywhere (no central ID authority)                  │
│   ✅ Merge-safe (two databases will never conflict)              │
│   ❌ 16 bytes vs 4-8 bytes (more storage + index size)          │
│   ❌ Random UUIDs cause B-tree page splits (minor at our scale) │
│   ❌ Harder to debug (long strings vs simple numbers)            │
│ 🎤 INTERVIEW TIP: "UUID v4 for all primary keys. Non-guessable │
│    — prevents enumeration attacks. No info leakage — competitor  │
│    can't tell we have 50,000 users from /users/50000. Generate  │
│    client-side or server-side — no coordination needed."         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌐 API Design

### Design Principles

| Principle | Rule | Example |
|-----------|------|---------|
| RESTful | Resources as nouns, HTTP verbs for actions | `POST /habits` not `POST /createHabit` |
| Versioned | URL path versioning | `/api/v1/habits` |
| Consistent errors | Standard JSON envelope for all errors | `{"error_code": "...", "message": "..."}` |
| Authenticated | Bearer token in Authorization header | `Authorization: Bearer eyJ...` |
| Paginated | Query parameters for lists | `?page=1&page_size=20` |

### Standard Error Response

Every error from every endpoint returns this exact format:

```json
{
    "error_code": "HABIT_NOT_FOUND",
    "message": "Habit not found",
    "detail": null
}
```

### Standard HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT |
| 201 | Created | Successful POST that creates a resource |
| 401 | Unauthorized | Missing/invalid/expired token |
| 403 | Forbidden | Valid token but accessing another user's data |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate email, duplicate log for same day |
| 422 | Unprocessable Entity | Valid JSON but business rule violation |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server failure |

---

### 🔐 Auth Module API (6 endpoints)

**Base URL:** `/api/v1/auth`
**Auth:** Public (register/login) or JWT (profile/logout)

| # | Method | Path | Description | Auth | Idempotent |
|---|--------|------|-------------|------|------------|
| 1 | POST | `/signup` | Register new user | Public | No |
| 2 | POST | `/login` | Get JWT tokens | Public | No |
| 3 | POST | `/refresh` | Refresh expired access token | Public (refresh token) | Yes |
| 4 | POST | `/logout` | Blacklist current token | JWT | No |
| 5 | GET | `/me` | Get current user profile | JWT | N/A (read) |
| 6 | PUT | `/me` | Update profile | JWT | Yes |

**Register Request:**
```http
POST /api/v1/auth/signup
Content-Type: application/json

{
    "email": "shreya@example.com",
    "password": "SecurePass123",
    "full_name": "Shreya",
    "timezone": "Asia/Kolkata"
}
```

**Register Response (201):**
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "shreya@example.com",
    "full_name": "Shreya",
    "timezone": "Asia/Kolkata",
    "is_active": true,
    "created_at": "2026-09-26T10:00:00Z"
}
```

**Login Response (200):**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
}
```

---

### 📋 Habits Module API (6 endpoints)

**Base URL:** `/api/v1/habits`
**Auth:** JWT required for all

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/` | Create a new habit |
| 2 | GET | `/` | List user's active habits |
| 3 | GET | `/{id}` | Get single habit |
| 4 | PUT | `/{id}` | Update habit properties |
| 5 | DELETE | `/{id}` | Archive habit (soft delete) |
| 6 | PUT | `/reorder` | Reorder habits (drag-and-drop) |

**Create Habit Request:**
```http
POST /api/v1/habits
Authorization: Bearer eyJ...
Content-Type: application/json

{
    "name": "Water Intake",
    "habit_type": "numeric",
    "unit": "glasses",
    "target_value": 8.0,
    "color": "#3B82F6",
    "icon": "💧"
}
```

**Create Habit Response (201):**
```json
{
    "id": "660e8400-...",
    "name": "Water Intake",
    "habit_type": "numeric",
    "unit": "glasses",
    "target_value": 8.0,
    "color": "#3B82F6",
    "icon": "💧",
    "sort_order": 0,
    "is_archived": false,
    "created_at": "2026-09-26T10:05:00Z"
}
```

---

### 📝 Logs Module API (5 endpoints)

**Base URL:** `/api/v1/logs`

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/` | Log single habit for a date |
| 2 | POST | `/bulk` | Log ALL habits at once (daily check-in "Save All") |
| 3 | GET | `/` | Get logs (by date or date range) |
| 4 | PUT | `/{id}` | Update a log value |
| 5 | DELETE | `/{id}` | Delete a log entry |

**Bulk Log Request (daily check-in):**
```http
POST /api/v1/logs/bulk
Authorization: Bearer eyJ...
Content-Type: application/json

{
    "log_date": "2026-09-26",
    "entries": [
        {"habit_id": "water-uuid", "value_numeric": 8.0},
        {"habit_id": "exercise-uuid", "value_boolean": true},
        {"habit_id": "mood-uuid", "value_scale": 7}
    ]
}
```

**Bulk Log Response (201):**
```json
[
    {"id": "log-1-uuid", "habit_id": "water-uuid", "log_date": "2026-09-26", "value_numeric": 8.0, ...},
    {"id": "log-2-uuid", "habit_id": "exercise-uuid", "log_date": "2026-09-26", "value_boolean": true, ...},
    {"id": "log-3-uuid", "habit_id": "mood-uuid", "log_date": "2026-09-26", "value_scale": 7, ...}
]
```

---

### 📊 Analytics Module API (6 endpoints)

**Base URL:** `/api/v1/analytics`

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/dashboard` | Today's progress + best streak + weekly % |
| 2 | GET | `/streaks` | Current + longest streak per habit |
| 3 | GET | `/weekly-summary` | This week vs last week comparison |
| 4 | GET | `/monthly-trend` | 30-day daily values for line chart |
| 5 | GET | `/completion-rate` | Completion % per habit |
| 6 | GET | `/correlations` | Pearson correlation between habit pairs |

**Dashboard Response (200):**
```json
{
    "today_logged": 4,
    "today_total": 6,
    "today_completion_pct": 66.7,
    "total_active_habits": 6,
    "current_best_streak": {
        "habit_id": "water-uuid",
        "habit_name": "Water Intake",
        "habit_color": "#3B82F6",
        "habit_icon": "💧",
        "current_streak": 15,
        "longest_streak": 30,
        "last_logged_date": "2026-09-26"
    },
    "week_completion_pct": 78.5
}
```

**Correlation Response (200):**
```json
{
    "correlations": [
        {
            "habit_a_name": "Sleep Hours",
            "habit_b_name": "Mood",
            "correlation": 0.72,
            "strength": "strong",
            "direction": "positive",
            "data_points": 28,
            "insight": "Your mood tends to be higher on days you sleep more"
        }
    ]
}
```

---

### 🤖 AI Module API (9 endpoints)

**Base URL:** `/api/v1/ai`

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/chat` | Chat with AI health coach (agent or direct) |
| 2 | GET | `/chat/stream` | SSE streaming chat response |
| 3 | GET | `/chat/history` | Get past messages |
| 4 | POST | `/documents` | Upload PDF for RAG |
| 5 | GET | `/documents` | List uploaded documents |
| 6 | DELETE | `/documents/{id}` | Delete document + chunks |
| 7 | POST | `/insights` | Generate on-demand insight |
| 8 | GET | `/insights` | List past insights |
| 9 | POST | `/weekly-report` | Generate weekly report (workflow) |

**Chat Request:**
```http
POST /api/v1/ai/chat
Authorization: Bearer eyJ...
Content-Type: application/json

{
    "message": "Why am I tired this week?",
    "use_agent": true
}
```

**Chat Response (200):**
```json
{
    "response": "Looking at your data from the past 7 days, your average sleep was 5.2 hours — well below the recommended 7-8 hours. I found a strong correlation (0.72) between your sleep and mood scores, meaning your mood tends to be higher on days you sleep more. Your nutrition guide [Source: nutrition_guide.pdf, Page 12] also mentions that iron deficiency can cause fatigue. Since you're vegetarian, consider iron-rich foods like spinach and lentils."
}
```

---

### 🔔 Notifications Module API (3 endpoints)

**Base URL:** `/api/v1/notifications`

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/settings` | Get notification preferences |
| 2 | PUT | `/settings` | Update preferences |
| 3 | POST | `/test-email` | Send test email |

---

### 📁 Export Module API (2 endpoints)

**Base URL:** `/api/v1/export`

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/csv` | Direct CSV download (StreamingResponse) |
| 2 | POST | `/csv/s3` | Upload to S3, return presigned download URL |

---

### 🏥 Health Check (1 endpoint)

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | GET | `/health` | Load balancer health check |

**Total: 38 endpoints across 7 modules + 1 health check**

---

## 🗄️ Database Design

### Database Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ONE PostgreSQL Database: healthtracker                          │
│  ONE Schema: public (default)                                    │
│  Extension: pgvector (for vector similarity search)             │
│  Extension: uuid-ossp (for UUID generation in SQL)              │
│                                                                   │
│  ┌──────────────────┐                                           │
│  │     users        │ ← Auth module                             │
│  ├──────────────────┤                                           │
│  │     habits       │ ← Habits module                           │
│  ├──────────────────┤                                           │
│  │   habit_logs     │ ← Logs module                             │
│  ├──────────────────┤                                           │
│  │   documents      │ ← AI module (RAG)                         │
│  ├──────────────────┤                                           │
│  │ document_chunks  │ ← AI module (RAG + pgvector)              │
│  ├──────────────────┤                                           │
│  │ai_chat_messages  │ ← AI module (chat history)                │
│  ├──────────────────┤                                           │
│  │   ai_insights    │ ← AI module (reports)                     │
│  ├──────────────────┤                                           │
│  │notification_settings│ ← Notifications module                 │
│  └──────────────────┘                                           │
│                                                                   │
│  WHY ONE DATABASE (not database-per-module)?                    │
│  ├── Single developer — no team isolation needed                │
│  ├── Analytics JOINs across habits + logs + users               │
│  ├── Simpler backups, migrations, monitoring                    │
│  ├── One Alembic migration chain for all tables                 │
│  └── Can split later if scale demands it                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Naming Conventions

| Convention | Rule | Example |
|-----------|------|---------|
| Table names | Plural, snake_case | `habits`, `habit_logs` |
| Column names | Singular, snake_case | `user_id`, `log_date` |
| Primary keys | `id` (UUID) | `id UUID PRIMARY KEY` |
| Foreign keys | `{table_singular}_id` | `user_id`, `habit_id` |
| Timestamps | `{action}_at` | `created_at`, `updated_at` |
| Booleans | `is_{adjective}` | `is_active`, `is_archived` |
| Indexes | `ix_{table}_{columns}` | `ix_habits_user_id` |
| Unique constraints | `uq_{table}_{columns}` | `uq_user_habit_date` |

---

### Table 1: users

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(100) NOT NULL,
    timezone        VARCHAR(50)  NOT NULL DEFAULT 'UTC',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE
);

-- Login lookup (every login does WHERE email = ?)
CREATE INDEX ix_users_email ON users(email);
```

**Column explanations:**
- `password_hash`: bcrypt output (~60 chars). NEVER store plain passwords.
- `timezone`: IANA format (e.g., "Asia/Kolkata"). Used for daily reminder scheduling.
- `is_active`: Soft delete. Deactivated users can't log in but data is preserved.

---

### Table 2: habits

```sql
CREATE TABLE habits (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    habit_type      VARCHAR(20)  NOT NULL,    -- 'numeric', 'boolean', 'scale'
    unit            VARCHAR(50)  NOT NULL DEFAULT '',
    target_value    FLOAT,                     -- NULL for boolean/scale habits
    color           VARCHAR(7)   NOT NULL DEFAULT '#3B82F6',  -- hex color
    icon            VARCHAR(50)  NOT NULL DEFAULT '⭐',
    sort_order      INTEGER      NOT NULL DEFAULT 0,
    is_archived     BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE
);

-- Dashboard: "get all active habits for user X" (most common query)
CREATE INDEX ix_habits_user_id ON habits(user_id);
CREATE INDEX ix_habits_user_active ON habits(user_id, is_archived);
```

---

### Table 3: habit_logs

```sql
CREATE TABLE habit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    habit_id        UUID NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    log_date        DATE NOT NULL,
    value_numeric   FLOAT,                     -- for numeric habits
    value_boolean   BOOLEAN,                   -- for boolean habits
    value_scale     INTEGER,                   -- for scale habits (1-10)
    notes           VARCHAR(500),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE,

    -- ONE log per habit per day per user (enforced at DB level)
    CONSTRAINT uq_user_habit_date UNIQUE (user_id, habit_id, log_date)
);

-- Daily check-in: "what did I log today?"
CREATE INDEX ix_habit_logs_user_date ON habit_logs(user_id, log_date);
-- Streak calculation: "which days did I log this habit?"
CREATE INDEX ix_habit_logs_habit_date ON habit_logs(habit_id, log_date);
-- General user queries
CREATE INDEX ix_habit_logs_user_id ON habit_logs(user_id);
```

---

### Table 4: documents (RAG)

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename        VARCHAR(255) NOT NULL,
    file_type       VARCHAR(50) NOT NULL,       -- 'pdf', 'txt', 'md'
    file_size       INTEGER NOT NULL,
    page_count      INTEGER,
    status          VARCHAR(20) NOT NULL DEFAULT 'uploaded',
                    -- 'uploaded', 'processing', 'processed', 'failed'
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    error_message   VARCHAR(500),
    s3_key          VARCHAR(500),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_documents_user_id ON documents(user_id);
```

---

### Table 5: document_chunks (RAG + pgvector)

```sql
CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_text      TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    page_number     INTEGER,
    token_count     INTEGER NOT NULL DEFAULT 0,
    embedding       vector(768),                -- pgvector column!
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX ix_document_chunks_user_id ON document_chunks(user_id);

-- IVFFlat index for fast approximate nearest neighbor search
CREATE INDEX ix_document_chunks_embedding
    ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

### Table 6: ai_chat_messages

```sql
CREATE TABLE ai_chat_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,       -- 'user', 'assistant'
    content         TEXT NOT NULL,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_ai_chat_messages_user_id ON ai_chat_messages(user_id);
CREATE INDEX ix_ai_chat_messages_user_created ON ai_chat_messages(user_id, created_at);
```

---

### Table 7: ai_insights

```sql
CREATE TABLE ai_insights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    insight_type    VARCHAR(50) NOT NULL,       -- 'weekly_report', 'on_demand', 'streak_milestone'
    title           VARCHAR(200) NOT NULL,
    content         TEXT NOT NULL,
    tokens_used     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_ai_insights_user_id ON ai_insights(user_id);
```

---

### Table 8: notification_settings

```sql
CREATE TABLE notification_settings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    daily_reminder  BOOLEAN NOT NULL DEFAULT TRUE,
    weekly_report   BOOLEAN NOT NULL DEFAULT TRUE,
    streak_alerts   BOOLEAN NOT NULL DEFAULT TRUE,
    reminder_time   VARCHAR(5) NOT NULL DEFAULT '08:00',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE
);

CREATE UNIQUE INDEX ix_notification_settings_user_id ON notification_settings(user_id);
```

---

### ER Diagram

```
┌──────────────────┐
│      users       │
├──────────────────┤
│ id          UUID │ PK
│ email    VARCHAR │ UNIQUE
│ password_hash    │
│ full_name        │
│ timezone         │
│ is_active  BOOL  │
│ created_at       │
└───────┬──────────┘
        │ 1:N
   ┌────┴──────────────────────────────────────────┐
   │         │          │          │                │
   ▼         ▼          ▼          ▼                ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐ ┌──────────────────┐
│ habits │ │  docs  │ │ai_chat │ │ ai_insights │ │ notif_settings   │
└───┬────┘ └───┬────┘ └────────┘ └─────────────┘ └──────────────────┘
    │ 1:N      │ 1:N
    ▼          ▼
┌────────┐ ┌──────────────┐
│hab_logs│ │doc_chunks    │
│        │ │              │
│ UNIQUE │ │ embedding    │
│(u,h,d) │ │ vector(768)  │
└────────┘ └──────────────┘
```

### Index Strategy Summary

| Index | Query Pattern | Why |
|-------|--------------|-----|
| `ix_users_email` | `WHERE email = ?` | Login lookup — every login |
| `ix_habits_user_active` | `WHERE user_id = ? AND is_archived = false` | Dashboard habit list |
| `ix_habit_logs_user_date` | `WHERE user_id = ? AND log_date = ?` | Daily check-in page |
| `ix_habit_logs_habit_date` | `WHERE habit_id = ? ORDER BY log_date` | Streak calculation |
| `uq_user_habit_date` | INSERT duplicate detection | Prevent logging same habit twice in one day |
| `ix_document_chunks_embedding` | `ORDER BY embedding <=> query LIMIT 5` | RAG similarity search |
| `ix_ai_chat_messages_user_created` | `WHERE user_id = ? ORDER BY created_at DESC` | Chat history |

---

## 🤖 AI Pipeline Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AI PIPELINE — 4 SUBSYSTEMS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  SUBSYSTEM 1: LLM LAYER (Strategy Pattern)                      │    │
│  │                                                                  │    │
│  │  BaseLLMClient (abstract)                                       │    │
│  │  ├── chat(messages, tools) → LLMResponse (text or tool_calls)  │    │
│  │  ├── stream_chat(messages) → AsyncGenerator[str]                │    │
│  │  └── embed(texts) → list[list[float]] (768-dim vectors)        │    │
│  │                                                                  │    │
│  │  Implementations:                                                │    │
│  │  ├── OllamaClient  → localhost:11434 (free, local, ~2 tok/sec) │    │
│  │  ├── GroqClient     → api.groq.com (free, 500 tok/sec)        │    │
│  │  └── OpenAIClient   → api.openai.com (paid, 100 tok/sec)      │    │
│  │                                                                  │    │
│  │  get_llm_client() → reads LLM_PROVIDER env → returns one      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  SUBSYSTEM 2: RAG PIPELINE                                      │    │
│  │                                                                  │    │
│  │  INGESTION (upload time):                                       │    │
│  │  PDF → DocumentProcessor (PyPDF2, page-by-page text extraction)│    │
│  │    → TextChunker (recursive split: 2000 chars, 200 overlap)    │    │
│  │    → EmbeddingGenerator (nomic-embed-text → 768-dim vectors)   │    │
│  │    → VectorStore (INSERT INTO document_chunks ... embedding)    │    │
│  │                                                                  │    │
│  │  RETRIEVAL (query time):                                        │    │
│  │  Question → EmbeddingGenerator.embed_query()                    │    │
│  │    → VectorStore.similarity_search(query_vec, top_k=5)         │    │
│  │    → Retriever (token budget filter + source citation format)   │    │
│  │    → "RELEVANT DOCUMENTS:\n[Source: report.pdf, Page 3]..."    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  SUBSYSTEM 3: REACT AGENT                                       │    │
│  │                                                                  │    │
│  │  HealthCoachAgent (pre-configured with 5 tools + memory)       │    │
│  │  └── BaseAgent (generic ReAct loop)                             │    │
│  │      ├── tools: {query_logs, get_analytics, search_documents,  │    │
│  │      │           correlate_habits, create_plan}                 │    │
│  │      ├── memory: ShortTermMemory (20 messages) +               │    │
│  │      │           LongTermMemory (Redis persistent insights)    │    │
│  │      └── loop: THINK → ACT → OBSERVE → REPEAT (max 5x)       │    │
│  │                                                                  │    │
│  │  Tool calling format: OpenAI function calling schema            │    │
│  │  Each tool: name + description + parameters_schema + execute() │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  SUBSYSTEM 4: AGENTIC WORKFLOW                                   │    │
│  │                                                                  │    │
│  │  WeeklyReportWorkflow:                                          │    │
│  │  Step 1: DataCollector → query all data (Python, no LLM)      │    │
│  │  Step 2: Analyzer → find patterns + insights (LLM call)        │    │
│  │  Step 3: ReportWriter → write personalized report (LLM call)   │    │
│  │                                                                  │    │
│  │  WorkflowOrchestrator:                                          │    │
│  │  ├── Runs steps in sequence (1 → 2 → 3)                       │    │
│  │  ├── Retry failed steps (max 2 retries)                        │    │
│  │  ├── Graceful fallback (if step 2 fails → partial report)     │    │
│  │  └── Logs timing, tokens, success/failure per step             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Security Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  LAYER 1: Network (Nginx)                                                │
│  ├── Rate limiting: 30r/s API, 2r/s AI, 5r/min login                   │
│  ├── Security headers: X-Frame-Options, X-Content-Type-Options, HSTS   │
│  ├── Gzip compression                                                    │
│  └── Request size limit                                                  │
│                                                                           │
│  LAYER 2: Authentication (JWT)                                           │
│  ├── Access token: 30 min expiry, HS256 signed                         │
│  ├── Refresh token: 7 day expiry, HS256 signed                         │
│  ├── Token blacklist: Redis SETEX with token's remaining TTL           │
│  └── Password: bcrypt cost 12 (~100ms per hash)                        │
│                                                                           │
│  LAYER 3: Authorization (Row-Level)                                      │
│  ├── Every query filters by user_id (from JWT)                          │
│  ├── User A cannot access User B's habits/logs/documents                │
│  └── Same error message for "wrong email" and "wrong password"          │
│                                                                           │
│  LAYER 4: Application (FastAPI Middleware)                                │
│  ├── Rate limiting: Redis sliding window (application layer)            │
│  ├── Input validation: Pydantic schemas on every endpoint               │
│  ├── Error handling: never expose internal errors to users              │
│  └── CORS: whitelist specific frontend origins                          │
│                                                                           │
│  LAYER 5: Data                                                            │
│  ├── Passwords: bcrypt hashed, NEVER stored as plain text               │
│  ├── Secrets: .env file, NEVER committed to Git                         │
│  ├── SQL injection: SQLAlchemy parameterized queries only               │
│  └── Token blacklist: Redis with auto-expiry                            │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Capacity Planning

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAPACITY ESTIMATION                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  USERS:                                                                  │
│  ├── Total registered: ~1,000                                            │
│  ├── Daily active (DAU): ~200 (20%)                                     │
│  └── Concurrent at peak: ~50                                             │
│                                                                           │
│  STORAGE PER USER PER DAY:                                               │
│  ├── Habit logs: 5 habits × 200 bytes = 1 KB                           │
│  ├── Chat messages: 3 messages × 500 bytes = 1.5 KB                    │
│  ├── Misc: 0.5 KB                                                        │
│  └── TOTAL: ~3 KB per user per day                                       │
│                                                                           │
│  ANNUAL STORAGE:                                                         │
│  ├── 1,000 users × 3 KB/day × 365 = 1.1 GB/year                       │
│  ├── + Indexes, vectors, documents: ~2 GB/year                          │
│  ├── TOTAL: ~3 GB/year                                                   │
│  └── → ONE PostgreSQL instance handles this for 10+ years               │
│                                                                           │
│  REQUESTS PER SECOND:                                                    │
│  ├── Dashboard load: 4 API calls × 200 DAU / 86,400 sec = 0.01 RPS   │
│  ├── Daily check-in: 1 bulk call × 200 DAU = 200 calls/day            │
│  ├── AI chat: 5 messages × 50 users / 3,600 sec = 0.07 RPS           │
│  ├── Peak (morning check-in): ~10 RPS for 15 minutes                  │
│  ├── TOTAL PEAK: ~10 RPS                                                │
│  ├── FastAPI handles: 1,000+ RPS                                        │
│  └── → SINGLE SERVER IS SUFFICIENT                                       │
│                                                                           │
│  REDIS MEMORY:                                                           │
│  ├── Analytics cache: ~5 MB (1000 users × 5 KB/user)                   │
│  ├── Rate limit counters: ~100 KB                                       │
│  ├── Token blacklist: ~500 KB                                            │
│  ├── Token usage tracking: ~200 KB                                       │
│  ├── TOTAL: ~6 MB                                                        │
│  └── → 128 MB allocation is 20x headroom                                │
│                                                                           │
│  AI COSTS:                                                               │
│  ├── Ollama (dev): $0/month                                             │
│  ├── Groq (staging): $0/month (free tier)                               │
│  ├── OpenAI (production): ~$0.50/active user/month                     │
│  ├── 200 DAU × $0.50 = $100/month for AI                               │
│  └── → Well within budget                                                │
│                                                                           │
│  💡 AT 10x SCALE (10,000 users):                                        │
│  ├── Storage: 30 GB/year (still one database)                           │
│  ├── Peak RPS: ~100 (add 1-2 more FastAPI workers)                     │
│  ├── Redis: 60 MB (still single instance)                               │
│  └── AI cost: ~$1,000/month (consider Groq or fine-tuned model)        │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🗃️ Caching Strategy

### What Gets Cached (and for How Long)

| Cache Key Pattern | TTL | What's Cached | When Invalidated |
|-------------------|-----|--------------|------------------|
| `analytics:{user_id}:dashboard` | 5 min | Dashboard summary (today's progress, best streak) | On new log create/update/delete |
| `analytics:{user_id}:streaks` | 30 min | Current + longest streak per habit | On new log create/update/delete |
| `analytics:{user_id}:weekly` | 30 min | This week vs last week comparison | On new log create/update/delete |
| `analytics:{user_id}:monthly:{habit_id}` | 1 hour | 30-day daily values for chart | On new log create/update/delete |
| `analytics:{user_id}:completion` | 30 min | Completion % per habit | On new log create/update/delete |
| `analytics:{user_id}:correlations` | 1 hour | Pearson correlations between habits | On new log create/update/delete |
| `rl:{ip}:{path}:{window}` | window_seconds | Rate limit counter | Auto-expires (Redis TTL) |
| `token_blacklist:{token[:32]}` | token remaining TTL | Logged-out tokens | Auto-expires when token would naturally expire |
| `tokens:{user_id}:{date}` | 48 hours | Daily AI token usage | Auto-expires |
| `memory:{user_id}:insights` | 24 hours (refreshed on access) | Long-term agent memory | On access (TTL refreshed) |

### Cache-Aside Pattern Flow

```
GET /api/v1/analytics/dashboard
  │
  ▼
AnalyticsService.get_dashboard(user_id)
  │
  ▼
AnalyticsCache.get_dashboard(user_id)
  │
  ├── HIT (data in Redis) → return cached JSON (< 1ms)
  │
  └── MISS (not in Redis)
        │
        ▼
      AnalyticsRepository.get_today_progress(user_id) → PostgreSQL (50ms)
      AnalyticsRepository.get_week_completion(user_id) → PostgreSQL (100ms)
      AnalyticsRepository.get_streaks(user_id) → PostgreSQL (150ms)
        │
        ▼
      Transform raw data → DashboardData schema
        │
        ▼
      AnalyticsCache.set_dashboard(user_id, data, TTL=300s)
        │
        ▼
      Return fresh data to client

INVALIDATION (on log create/update/delete):
  LogService.create_log()
    → session.commit()
    → redis.delete("analytics:{user_id}:*")  ← DELETE ALL analytics cache
    → Next dashboard request recalculates fresh
```

---

## 📝 What You Learned

### Concepts Summary Table

| # | Concept | Key Takeaway | Interview Value |
|---|---------|-------------|-----------------|
| 1 | **Modular Monolith** | Microservice boundaries without microservice overhead | ⭐⭐⭐ |
| 2 | **PostgreSQL + pgvector** | SQL + vector search in one database | ⭐⭐⭐ |
| 3 | **Strategy Pattern (LLM)** | Swap AI provider with config change | ⭐⭐⭐ |
| 4 | **Cache-Aside Pattern** | Redis cache with explicit invalidation | ⭐⭐⭐ |
| 5 | **JWT Dual Tokens** | Access (30min) + refresh (7d) + blacklist | ⭐⭐⭐ |
| 6 | **ReAct Agent** | LLM that thinks, calls tools, iterates | ⭐⭐⭐ |
| 7 | **RAG Pipeline** | PDF → chunk → embed → search → cited answer | ⭐⭐⭐ |
| 8 | **Two-Layer Rate Limiting** | Nginx (IP-level) + Redis (endpoint-level) | ⭐⭐ |
| 9 | **Celery + Lambda** | Celery for dev, Lambda for production | ⭐⭐ |
| 10 | **UUID Primary Keys** | Non-guessable, no info leakage | ⭐⭐ |

### Interview-Ready One-Liners

| Topic | One-Liner |
|-------|-----------|
| Architecture | "Modular monolith — microservice boundaries without operational overhead. Any module can be extracted by replacing a function call with an HTTP call." |
| Database | "PostgreSQL with pgvector — ACID compliance for streaks AND vector search for RAG in one database." |
| LLM | "Strategy pattern with 3 providers — $0 in dev (Ollama), $0 in staging (Groq), best quality in production (OpenAI)." |
| Caching | "Cache-aside with Redis — 200x faster dashboard (4ms vs 800ms). TTL per query type. Explicit invalidation on writes." |
| Auth | "Short-lived JWTs (30 min) with refresh tokens. Redis blacklist enables real logout. Same error for wrong email and wrong password." |
| Agent | "ReAct loop — LLM thinks, calls tools (query DB, search docs, correlate), observes results, iterates up to 5 times." |
| RAG | "PDF → chunk → embed → pgvector. Cosine similarity search with IVFFlat index. Cited answers with source references." |
| Rate limit | "Two layers — Nginx blocks floods before FastAPI. Redis sliding window gives per-endpoint limits: 2r/s for AI." |

---

## 📚 Document Index

| Phase | Document | Description | Status |
|-------|----------|-------------|--------|
| 0.1 | [phase0-part1-project-overview.md](./phase0-part1-project-overview.md) | Project vision, features, architecture | ✅ |
| 0.2 | [phase0-part2-environment-setup.md](./phase0-part2-environment-setup.md) | Install Python, Docker, Node.js, etc. | ✅ |
| **1** | **phase1-system-design.md** | **Requirements, decisions, API, DB, AI pipeline** | **← You are here** |
| 2 | [phase2-high-level-design.md](./phase2-high-level-design.md) | Component diagrams, data flows, scaling | ⬜ Next |
| 3 | [phase3-low-level-design.md](./phase3-low-level-design.md) | Model/repo/service/router signatures | ⬜ |
| 4.01 | [phase4-part01-project-setup-docker.md](./phase4-part01-project-setup-docker.md) | .env, docker-compose, Makefile | ⬜ |
| ... | ... | ... | ... |

---

> **"The best system design is one where each decision has a clear reason, each trade-off is acknowledged, and each component can evolve independently."**

---

*End of Phase 1: System Design*
*Next: [Phase 2: High-Level Design →](./phase2-high-level-design.md)*
