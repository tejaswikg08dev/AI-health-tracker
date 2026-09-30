# 🏗️ Phase 2: High-Level Design (HLD)

> **"HLD answers WHAT components exist and HOW they connect. LLD answers HOW each component works internally."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 2 — High-Level Design |
| **Previous** | [phase1-system-design.md](./phase1-system-design.md) |
| **Next** | [phase3-low-level-design.md](./phase3-low-level-design.md) |
| **Time to Read** | ~45 minutes |

---

## 📖 Table of Contents

1. [What is HLD?](#what-is-hld)
2. [Complete Architecture Diagram](#architecture-diagram)
3. [Component Responsibilities](#component-responsibilities)
4. [Module Dependency Map](#module-dependencies)
5. [5 Data Flow Traces](#data-flows)
6. [Technology Choice Rationale](#tech-rationale)
7. [Scaling Strategy](#scaling-strategy)
8. [Failure Handling](#failure-handling)
9. [What You Learned](#what-you-learned)

---

<a name="what-is-hld"></a>
## What is HLD?

HLD shows the **big picture** — which boxes exist on the whiteboard and which arrows connect them. You do NOT show class names, function signatures, or SQL queries. Just components, connections, and data flows.

**Analogy:** HLD is a **city map** — you can see the hospital, the school, the train station, and the roads between them. LLD (Phase 3) is the **floor plan of the hospital** — you can see each room, each bed, each piece of equipment.

**In an interview**, you draw HLD on a whiteboard first (10 minutes), then deep-dive into 2-3 components (20 minutes).

---

<a name="architecture-diagram"></a>
## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PRESENTATION (React + TypeScript)                                   │
│                                                                               │
│   8 Pages: Login │ Signup │ Dashboard │ Habits │ Check-In │ Analytics        │
│            AI Chat │ Settings                                                │
│                                                                               │
│   API Layer: Axios with JWT auto-refresh interceptor                         │
│   State: Zustand (auth) + TanStack Query (server data)                       │
│   Charts: Recharts (bar, line, pie)                                          │
│   Styling: Tailwind CSS                                                      │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ HTTP / SSE
┌────────────────────────────────────────▼────────────────────────────────────┐
│ LAYER 2: REVERSE PROXY (Nginx)                                               │
│                                                                               │
│   Rate Limiting:    30 req/sec API │ 2 req/sec AI │ 5 req/min login         │
│   Security Headers: X-Frame-Options, X-Content-Type-Options, HSTS           │
│   Compression:      Gzip (100KB → ~15KB)                                     │
│   SSE Support:      proxy_buffering off (AI chat streaming)                  │
│   Static Files:     Serves React build in production                         │
│   Health Check:     Proxies /health to backend                               │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ HTTP (internal)
┌────────────────────────────────────────▼────────────────────────────────────┐
│ LAYER 3: APPLICATION — FastAPI Modular Monolith (Python 3.11)                │
│                                                                               │
│ ┌───────────────────────────────────────────────────────────────────────┐   │
│ │                    MIDDLEWARE CHAIN                                     │   │
│ │  Request → CORS → Logging (request_id) → RateLimiter → ErrorHandler  │   │
│ └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│ ┌──────┐ ┌──────┐ ┌────┐ ┌─────────┐ ┌──────────────────┐ ┌─────┐ ┌─────┐│
│ │ Auth │ │Habits│ │Logs│ │Analytics│ │       AI         │ │Notif│ │Exprt││
│ │ 6 ep │ │ 6 ep │ │5 ep│ │  6 ep   │ │     9 ep         │ │ 3 ep│ │2 ep ││
│ │      │ │      │ │    │ │         │ │ ┌───┐┌───┐┌────┐ │ │     │ │     ││
│ │ JWT  │ │ CRUD │ │Bulk│ │ Window  │ │ │LLM││RAG││Agnt│ │ │Email│ │ CSV ││
│ │bcrypt│ │ Soft │ │Type│ │ funcs   │ │ │3  ││pgv││5   │ │ │3    │ │ S3  ││
│ │token │ │delete│ │val │ │ Redis   │ │ │prov││ect││tool│ │ │provs│ │MinIO││
│ │black │ │reord │ │cach│ │ cache   │ │ └───┘└───┘└────┘ │ │     │ │     ││
│ │list  │ │      │ │inv │ │ Pearson │ │ ┌────┐ ┌───────┐ │ │     │ │     ││
│ └──┬───┘ └──┬───┘ └─┬──┘ └───┬─────┘ │ │Wkfl│ │Memory│ │ └──┬──┘ └──┬──┘│
│    │        │       │        │        │ │3stp│ │S+L tm│ │    │       │    │
│    │        │       │        │        │ └────┘ └───────┘ │    │       │    │
│    │        │       │        │        └────────┬─────────┘    │       │    │
│ ┌──▼────────▼───────▼────────▼────────────────▼──────────────▼───────▼──┐ │
│ │                    SHARED LAYER                                         │ │
│ │  config.py │ database.py │ redis_client.py │ dependencies.py           │ │
│ │  base_repository.py │ base_schemas.py │ exceptions.py │ date_utils.py  │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└────────┬──────────┬──────────┬──────────┬──────────┬────────────────────┘
         │          │          │          │          │
┌────────▼──────────▼──────────▼──────────▼──────────▼────────────────────┐
│ LAYER 4: DATA & INFRASTRUCTURE                                           │
│                                                                           │
│ ┌──────────┐ ┌───────┐ ┌──────┐ ┌───────────┐ ┌────────────────────┐  │
│ │PostgreSQL│ │ Redis │ │MinIO │ │  Ollama   │ │  Celery Workers   │  │
│ │+pgvector │ │       │ │ (S3) │ │(Local LLM)│ │  (background)     │  │
│ │          │ │ Cache │ │      │ │           │ │                   │  │
│ │ 8 tables │ │ Rate  │ │PDFs  │ │ Llama 3.1 │ │  Daily reminders  │  │
│ │ Vectors  │ │ Black │ │CSVs  │ │ nomic-    │ │  Weekly reports   │  │
│ │ Indexes  │ │ Token │ │      │ │ embed-text│ │  Streak checks    │  │
│ └──────────┘ └───────┘ └──────┘ └───────────┘ └────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: SERVERLESS (AWS Lambda — 6 Functions)                            │
│                                                                           │
│ ┌──────────────────────┐ ┌─────────────────────┐ ┌───────────────────┐  │
│ │ EventBridge (cron)   │ │ SQS (event-driven)  │ │ S3 (file events) │  │
│ │ ├── Daily Reminder   │ │ ├── CSV Export       │ │ └── Doc Processor│  │
│ │ ├── Weekly Report    │ │ └── Streak Milestone │ │     (RAG ingest) │  │
│ │ └── Data Cleanup     │ │                     │ │                   │  │
│ └──────────────────────┘ └─────────────────────┘ └───────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
```

---

<a name="component-responsibilities"></a>
## Component Responsibilities

| Component | What It Does | Receives From | Sends To |
|-----------|-------------|---------------|----------|
| **React Frontend** | UI for all 8 pages, charts, AI chat | User interactions | Axios → Nginx |
| **Nginx** | Rate limit, route, compress, security headers | Browser HTTPS | FastAPI HTTP |
| **FastAPI (Auth)** | Register, login, JWT tokens, blacklist | Nginx | PostgreSQL, Redis |
| **FastAPI (Habits)** | Habit CRUD, soft delete, reorder | Nginx | PostgreSQL |
| **FastAPI (Logs)** | Daily check-ins, bulk save, type validation | Nginx | PostgreSQL, Redis (invalidate) |
| **FastAPI (Analytics)** | Streaks, weekly, monthly, correlations | Nginx | PostgreSQL, Redis (cache) |
| **FastAPI (AI)** | Chat, RAG, agents, workflows, streaming | Nginx | Ollama/Groq, PostgreSQL, Redis |
| **FastAPI (Notifications)** | Email settings, send emails | Nginx, Celery | Email provider (Console/Resend/SES) |
| **FastAPI (Export)** | CSV generation, S3 upload | Nginx | PostgreSQL, MinIO/S3 |
| **PostgreSQL** | 8 tables, pgvector embeddings | SQLAlchemy queries | Query results |
| **Redis** | Cache, rate limits, token blacklist, Celery broker | Redis client commands | Cached data |
| **MinIO/S3** | PDF storage, CSV exports, reports | boto3 upload/download | Presigned URLs |
| **Ollama** | Local LLM (Llama 3.1) + embeddings (nomic-embed) | HTTP from AI module | Text completions, vectors |
| **Celery** | Background tasks (email, reports) | Redis broker | PostgreSQL, email |
| **Lambda (6)** | Scheduled + event-driven tasks | EventBridge, SQS, S3 | PostgreSQL, SES, S3 |

---

<a name="module-dependencies"></a>
## Module Dependency Map

```
                        ┌──────────┐
                        │   Auth   │ ← Foundation — depends on NOTHING
                        └────┬─────┘
                             │ provides user_id to ALL modules
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼───┐    ┌────▼────┐   ┌─────▼──────────┐
         │ Habits │    │  Logs   │   │ Notifications  │
         └────┬───┘    └────┬────┘   └────────┬───────┘
              │             │                  │
              └──────┬──────┘                  │
                     │                         │
              ┌──────▼──────┐                  │
              │  Analytics  │ reads Habits + Logs data
              └──────┬──────┘                  │
                     │                         │
              ┌──────▼──────┐                  │
              │     AI      │──────────────────┘
              │ LLM + RAG + │ reads ALL modules, triggers notifications
              │ Agent + Flow│
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   Export    │ reads Logs + Habits for CSV
              └─────────────┘

KEY RULE: Modules communicate through SERVICE INTERFACES.
  AI agent calls: analytics_service.get_streaks(user_id)
  NOT: SELECT * FROM habit_logs WHERE ...

  This means extracting AI into a separate microservice requires
  changing ONE line: service call → HTTP call. Zero business logic changes.
```

---

<a name="data-flows"></a>
## 5 Data Flow Traces

### Flow 1: User Signs Up and Logs In

```
Browser                Nginx               FastAPI              PostgreSQL        Redis
  │ POST /auth/signup    │                    │                    │               │
  │─────────────────────>│                    │                    │               │
  │                      │ rate check (OK)    │                    │               │
  │                      │───────────────────>│                    │               │
  │                      │                    │ check email exists │               │
  │                      │                    │───────────────────>│               │
  │                      │                    │   false (new user) │               │
  │                      │                    │<───────────────────│               │
  │                      │                    │ bcrypt hash password│              │
  │                      │                    │ INSERT INTO users   │              │
  │                      │                    │───────────────────>│               │
  │                      │                    │   user created      │              │
  │                      │                    │<───────────────────│               │
  │                      │ 201 Created        │                    │               │
  │<─────────────────────│<───────────────────│                    │               │
  │                      │                    │                    │               │
  │ POST /auth/login     │                    │                    │               │
  │─────────────────────>│                    │                    │               │
  │                      │───────────────────>│                    │               │
  │                      │                    │ find user by email │               │
  │                      │                    │───────────────────>│               │
  │                      │                    │ verify bcrypt hash │               │
  │                      │                    │ create JWT access  │               │
  │                      │                    │ create JWT refresh │               │
  │                      │ 200 OK {tokens}    │                    │               │
  │<─────────────────────│<───────────────────│                    │               │
```

### Flow 2: Daily Check-In ("Save All")

```
Browser               FastAPI              PostgreSQL        Redis           Lambda (async)
  │ POST /logs/bulk     │                    │               │                │
  │ {5 habit entries}   │                    │               │                │
  │────────────────────>│                    │               │                │
  │                     │ decode JWT         │               │                │
  │                     │ validate date      │               │                │
  │                     │ for each entry:    │               │                │
  │                     │  ├── check habit   │               │                │
  │                     │  ├── type validate │               │                │
  │                     │  └── upsert log    │               │                │
  │                     │────────────────────>│               │                │
  │                     │  (one transaction) │               │                │
  │                     │<────────────────────│               │                │
  │                     │                    │               │                │
  │                     │ DELETE analytics:* │               │                │
  │                     │──────────────────────────────────>│                │
  │                     │ (cache invalidated)│               │                │
  │                     │                    │               │                │
  │                     │ SQS message        │               │                │
  │                     │────────────────────────────────────────────────────>│
  │                     │ (streak check)     │               │               │
  │ 201 Created         │                    │               │                │
  │<────────────────────│                    │               │                │
```

### Flow 3: AI Agent Chat ("Why am I tired?")

```
Browser               FastAPI              AI Agent            Tools              LLM (Ollama)
  │ POST /ai/chat       │                    │                   │                  │
  │ "Why am I tired?"   │                    │                   │                  │
  │────────────────────>│                    │                   │                  │
  │                     │ create agent       │                   │                  │
  │                     │───────────────────>│                   │                  │
  │                     │                    │                   │                  │
  │                     │                    │ ── ITERATION 1 ─────────────────────│
  │                     │                    │ Send: system + tools + question     │
  │                     │                    │────────────────────────────────────>│
  │                     │                    │ Response: tool_call(query_logs)     │
  │                     │                    │<────────────────────────────────────│
  │                     │                    │                   │                  │
  │                     │                    │ Execute tool      │                  │
  │                     │                    │──────────────────>│                  │
  │                     │                    │ "Sleep avg: 5.2h" │                  │
  │                     │                    │<──────────────────│                  │
  │                     │                    │                   │                  │
  │                     │                    │ ── ITERATION 2 ─────────────────────│
  │                     │                    │ Send: + tool result                 │
  │                     │                    │────────────────────────────────────>│
  │                     │                    │ Response: tool_call(correlate)      │
  │                     │                    │<────────────────────────────────────│
  │                     │                    │                   │                  │
  │                     │                    │ Execute tool      │                  │
  │                     │                    │──────────────────>│                  │
  │                     │                    │ "r=0.72 strong"   │                  │
  │                     │                    │<──────────────────│                  │
  │                     │                    │                   │                  │
  │                     │                    │ ── ITERATION 3 ─────────────────────│
  │                     │                    │ Send: + tool result                 │
  │                     │                    │────────────────────────────────────>│
  │                     │                    │ Response: TEXT (final answer)       │
  │                     │                    │<────────────────────────────────────│
  │                     │                    │                   │                  │
  │                     │ save to DB         │                   │                  │
  │                     │<───────────────────│                   │                  │
  │ 200 OK              │                    │                   │                  │
  │ "You averaged 5.2h" │                    │                   │                  │
  │<────────────────────│                    │                   │                  │
```

### Flow 4: RAG Document Upload + Query

```
UPLOAD (one-time):
  Browser → POST /ai/documents (PDF file)
    → FastAPI saves to MinIO/S3
    → Extract text (PyPDF2, page by page)
    → Chunk text (recursive split: 2000 chars, 200 overlap)
    → Embed each chunk (Ollama nomic-embed-text → 768 floats)
    → Store chunks + vectors in pgvector
    → Update document status = "processed"

QUERY (every time):
  Browser → POST /ai/chat "What's my iron level?"
    → Agent THINKS: "I should search uploaded documents"
    → Agent CALLS: search_documents("iron level")
      → Embed the question → 768 floats
      → pgvector: SELECT ... ORDER BY embedding <=> query_vector LIMIT 5
      → Top 5 chunks with similarity > 0.3
      → Format: "[Source: blood_report.pdf, Page 3] Iron: 45 µg/dL..."
    → Agent THINKS: "I have enough info"
    → Agent ANSWERS: "Your iron is 45 µg/dL [Source: blood_report.pdf, p.3],
                      which is below normal (60-170 µg/dL)."
```

### Flow 5: Weekly Report (Agentic Workflow)

```
EventBridge (Sunday 9 AM)
    │
    ▼
Lambda: weekly_report_generator
    │
    ├── Step 1: DataCollector
    │     → Query PostgreSQL: all habits, logs, streaks, weekly comparison
    │     → Format as structured text summary
    │     → Output: data_summary (string)
    │
    ├── Step 2: Analyzer (LLM call)
    │     → Send data_summary to Groq LLM
    │     → Prompt: "Find top 3 improvements, concerning trends, recommendations"
    │     → Output: analysis (markdown)
    │
    ├── Step 3: ReportWriter (LLM call)
    │     → Send data_summary + analysis to Groq LLM
    │     → Prompt: "Write a friendly, personalized weekly report"
    │     → Output: report (HTML)
    │
    ├── Upload report to S3
    │
    └── Send email via SES with report content
```

---

<a name="tech-rationale"></a>
## Technology Choice Rationale

| Decision | Chose | Why | Over | Why Not |
|----------|-------|-----|------|---------|
| Backend | FastAPI | Async, Pydantic, auto docs, AI ecosystem | Django | No native async, heavy for API-only |
| Frontend | React + TS | Type safety, ecosystem, Recharts | Vue, Svelte | React has largest ecosystem |
| Database | PostgreSQL + pgvector | ACID + vector search in ONE DB | PG + Pinecone | Two DBs, $70/month, no transactions |
| Cache | Redis | Sub-ms, 4 use cases, Celery broker | Memcached | No TTL cleanup, no data structures |
| AI (dev) | Ollama | Free, local, no API key | Groq | Can't run on Render free tier |
| AI (prod) | OpenAI | Best quality | Ollama | Can't scale, no GPU in production |
| Proxy | Nginx | Rate limiting, SSE, battle-tested | Caddy | Less ecosystem, fewer tutorials |
| Containers | Docker Compose | One command, reproducible | Manual install | "Works on my machine" |
| CI/CD | GitHub Actions | Free, service containers | Jenkins | More setup, self-hosted |
| Serverless | Lambda + SAM | Free tier, auto-scale | Only Celery | Lambda handles spikes better |
| State | Zustand | 1KB, no boilerplate | Redux | 10KB, too much boilerplate |
| Charts | Recharts | React-native, bar/line/pie | Chart.js | Recharts is more React-idiomatic |

---

<a name="scaling-strategy"></a>
## Scaling Strategy

| Scale Point | Current (1K users) | 10K users | 100K users |
|-------------|-------------------|-----------|------------|
| API servers | 1 FastAPI (Docker) | 2-3 behind load balancer | ECS Fargate (auto-scale 2-10) |
| Database | 1 PostgreSQL | Same + read replica for analytics | RDS Multi-AZ + 2 read replicas |
| Cache | 1 Redis (128MB) | Same (1GB) | ElastiCache cluster |
| AI | Ollama local | Groq cloud (free) | AWS Bedrock (managed) |
| Background | Celery (1 worker) | Lambda (all functions) | Lambda (auto-scale 1000 concurrent) |
| Storage | MinIO (Docker) | S3 | S3 + CloudFront CDN |
| Frontend | Vite dev server | Vercel | S3 + CloudFront |

**The key insight:** Our modular monolith design means we scale the ENTIRE app at first (just add more FastAPI instances). Only when one module becomes a bottleneck do we extract it. The AI module is the most likely candidate — it's the most expensive and has the most independent logic.

---

<a name="failure-handling"></a>
## Failure Handling

| What Fails | Impact | Our Response |
|-----------|--------|-------------|
| **PostgreSQL down** | App stops | Docker restart policy. Production: RDS Multi-AZ auto-failover |
| **Redis down** | Slower (no cache), no rate limiting | Fail-open: cache miss → query DB. Rate limiter passes all requests. Token blacklist fails open (tokens temporarily valid until natural expiry) |
| **Ollama/Groq down** | AI chat returns error | Graceful degradation: AI features show "AI temporarily unavailable." Habit tracking, analytics, export all still work. |
| **MinIO/S3 down** | Can't upload/download files | Uploads return error. Existing data in PostgreSQL unaffected. |
| **Lambda fails** | Emails not sent, exports delayed | Lambda auto-retries (2x). Dead letter queue for persistent failures. |
| **Nginx down** | Nothing accessible | Docker restart. Production: multiple Nginx instances behind ALB. |
| **Network timeout (LLM)** | Agent hangs | 30-second timeout per LLM call. Max 5 iterations. After timeout: "I couldn't complete the analysis. Please try again." |
| **Database migration fails** | App won't start | Alembic rolls back. Fix migration, redeploy. |

**Design principle:** No single infrastructure failure should take down the ENTIRE app. AI down? Tracking still works. Redis down? App is slower but functional. This is called **graceful degradation**.

---

<a name="what-you-learned"></a>
## What You Learned

| # | Concept | Key Takeaway |
|---|---------|-------------|
| 1 | HLD scope | Components + connections + data flows (NO class names or SQL) |
| 2 | 5-layer architecture | Presentation → Proxy → Application → Data → Serverless |
| 3 | Module dependencies | Auth → Habits → Logs → Analytics → AI → Export |
| 4 | Data flow tracing | Follow a request through every component step by step |
| 5 | Tech rationale | Every choice has a WHY and a "why NOT the alternative" |
| 6 | Scaling strategy | Start with 1 server. Add instances. Extract modules last. |
| 7 | Failure handling | Graceful degradation — AI down ≠ app down |

---

## 📚 Document Index

| Phase | Document | Status |
|-------|----------|--------|
| 0.1 | [Project Overview](./phase0-part1-project-overview.md) | ✅ |
| 0.2 | [Environment Setup](./phase0-part2-environment-setup.md) | ✅ |
| 1 | [System Design](./phase1-system-design.md) | ✅ |
| **2** | **High-Level Design** | **← You are here** |
| 3 | [Low-Level Design](./phase3-low-level-design.md) | ⬜ Next |
| 4.01 | [Project Setup + Docker](./phase4-part01-project-setup-docker.md) | ⬜ |

---
*End of Phase 2: High-Level Design*
*Next: [Phase 3: Low-Level Design →](./phase3-low-level-design.md)*
