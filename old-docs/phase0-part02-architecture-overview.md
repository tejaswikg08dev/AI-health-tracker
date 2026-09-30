# 🏗️ Phase 0 — Part 02: Architecture Overview

> **"Architecture is the decisions you make early that are expensive to change later."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 0 — Overview & Setup |
| **Part** | 02 of 05 |
| **Previous** | [Part 01 — Project Overview](./phase0-part01-project-overview.md) |
| **Next** | [Part 03 — Tech Stack Explained](./phase0-part03-tech-stack-explained.md) |
| **Time to Read** | ~25 minutes |

---

## 🎯 What is Software Architecture?

Architecture is the **high-level structure** of your application — which pieces exist, what each piece does, and how they talk to each other.

**Real-world analogy:** Architecture is like a city plan. Before building houses (code), you decide: where are the roads (data flows)? Where is the power plant (database)? Where is the water treatment (cache)? Where is the hospital (AI service)? You can't easily move the power plant after building 100 houses on top of it.

---

## 🏛️ Our Architecture: Modular Monolith

### What is a Modular Monolith?

There are 3 common architectures:

| Architecture | What It Is | When to Use |
|-------------|-----------|-------------|
| **Monolith** | Everything in one big folder, no separation | Small scripts, prototypes |
| **Modular Monolith** ✅ | ONE deployed app, but internally organized as separate modules | Small-medium teams, shared database |
| **Microservices** | Each module is a separate app with its own database | Large teams (10+), different scaling needs |

**We chose Modular Monolith because:**

1. **Single team** — Microservices need service discovery, API gateways, distributed tracing. That's 3 months of infrastructure before writing business logic.

2. **Shared database** — All modules read from PostgreSQL. In microservices, each service owns its database. If Habits, Logs, and Analytics all need `habit_logs` table, splitting into 3 databases means distributed joins or data duplication.

3. **Clear boundaries** — Each module has its own: models, schemas, repository, service, router, exceptions. Modules communicate through service interfaces, NEVER direct SQL across boundaries. If we ever need microservices, we extract a module — just replace the service call with an HTTP call.

---

## 🗺️ Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER (Browser)                                │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                      FRONTEND (React + TypeScript)                       │
│                                                                         │
│  LoginPage → DashboardPage → HabitsPage → CheckInPage → AnalyticsPage  │
│                                   ChatPage → SettingsPage               │
│                                                                         │
│  Axios API Service ──── auto JWT attachment ──── auto token refresh      │
│  Zustand Auth Store ──── localStorage persistence                       │
│  TanStack Query ──── cache, refetch on focus, optimistic updates        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP / SSE
┌────────────────────────────────▼────────────────────────────────────────┐
│                         NGINX (Reverse Proxy)                           │
│                                                                         │
│  Rate Limiting: 30r/s API │ 2r/s AI │ 5r/min login                     │
│  Security Headers: X-Frame-Options, XSS, HSTS                          │
│  Gzip Compression: 100KB → ~15KB                                        │
│  SSE Support: proxy_buffering off (for AI streaming)                    │
│  Static Files: serves React build in production                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                   FASTAPI APPLICATION (Python 3.11)                      │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │  Auth    │ │  Habits  │ │   Logs   │ │Analytics │                  │
│  │ Module 1 │ │ Module 2 │ │ Module 3 │ │ Module 4 │                  │
│  │ 6 endpts │ │ 6 endpts │ │ 5 endpts │ │ 6 endpts │                  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘                  │
│       │             │            │             │                         │
│  ┌────┴─────────────┴────────────┴─────────────┴──────────────────┐    │
│  │                    SHARED LAYER                                  │    │
│  │  base_repository.py │ base_schemas.py │ exceptions.py           │    │
│  │  date_utils.py │ logging.py │ dependencies.py │ config.py       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    AI MODULE (Module 5)                           │   │
│  │                                                                  │   │
│  │  ┌─────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐ │   │
│  │  │  LLM    │ │    RAG    │ │  Agents   │ │    Workflows      │ │   │
│  │  │ Layer   │ │ Pipeline  │ │ (ReAct)   │ │ (Weekly Report)   │ │   │
│  │  │         │ │           │ │           │ │                   │ │   │
│  │  │ Ollama  │ │ PDF→Chunk │ │ 5 tools   │ │ DataCollector     │ │   │
│  │  │ Groq    │ │ →Embed    │ │ Short-term│ │ → Analyzer        │ │   │
│  │  │ OpenAI  │ │ →pgvector │ │ Long-term │ │ → ReportWriter    │ │   │
│  │  │ (swap)  │ │ →Retrieve │ │ memory    │ │ + Orchestrator    │ │   │
│  │  └─────────┘ └───────────┘ └───────────┘ └───────────────────┘ │   │
│  │  9 endpoints: chat, stream, history, documents, insights, report│   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────┐ ┌──────────────┐                                     │
│  │Notifications │ │    Export    │                                     │
│  │  Module 6    │ │  Module 7   │                                     │
│  │ 3 endpoints  │ │ 2 endpoints │                                     │
│  │ Email: SES/  │ │ CSV, S3,    │                                     │
│  │ Resend/      │ │ presigned   │                                     │
│  │ Console      │ │ URLs        │                                     │
│  └──────┬───────┘ └──────┬──────┘                                     │
│         │                │                                              │
│  ┌──────┴────────────────┴──────────────────────────────────────────┐  │
│  │                    MIDDLEWARE LAYER                                │  │
│  │  CORS → Logging (request_id) → Rate Limiter → Error Handler      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    CELERY WORKERS (Background)                    │  │
│  │  Daily reminders │ Weekly reports │ Streak milestones            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────┬──────────┬──────────┬──────────┬───────────────────────────────┘
         │          │          │          │
    ┌────▼────┐ ┌───▼───┐ ┌───▼───┐ ┌───▼─────────┐
    │PostgreSQL│ │ Redis │ │ MinIO │ │   Ollama    │
    │+pgvector│ │       │ │  (S3) │ │  (Local LLM)│
    │ 8 tables│ │ Cache │ │ Files │ │ llama3.1:8b │
    │ Vectors │ │ Rate  │ │ PDFs  │ │ nomic-embed │
    │         │ │ Tokens│ │ CSVs  │ │             │
    └─────────┘ └───────┘ └───────┘ └─────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS LAMBDA (6 Serverless Functions)                   │
│                                                                         │
│  EventBridge cron ────► Daily Reminder │ Weekly Report │ Data Cleanup   │
│  SQS messages ────────► CSV Export │ Streak Milestone                   │
│  S3 events ───────────► Document Processor (RAG ingestion)             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Request Lifecycle — What Happens When You Click "Save All"

Let's trace a real request through the entire system:

```
1. USER clicks "Save All" on Check-In page
   │
2. React calls: POST /api/v1/logs/bulk
   │  Body: {"log_date": "2026-09-26", "entries": [{habit_id, value_numeric: 8}, ...]}
   │  Header: Authorization: Bearer eyJhbG...
   │
3. AXIOS INTERCEPTOR attaches the JWT token from localStorage
   │
4. NGINX receives the request
   │  ├── Checks rate limit (30 requests/second per IP) — OK
   │  ├── Adds X-Request-ID header
   │  └── Forwards to FastAPI backend (proxy_pass http://backend:8000)
   │
5. FASTAPI MIDDLEWARE CHAIN
   │  ├── LoggingMiddleware: logs method, path, starts timer
   │  ├── RateLimiter: checks Redis counter — OK
   │  └── CORS: allows origin http://localhost:3000
   │
6. ROUTER: POST /api/v1/logs/bulk
   │  ├── Depends(get_current_user_id):
   │  │   ├── Extract token from "Bearer eyJhbG..."
   │  │   ├── jwt.decode(token) → get user_id
   │  │   └── Check Redis blacklist (not blacklisted → proceed)
   │  └── Depends(get_log_service): creates LogService with DB session + Redis
   │
7. LOG SERVICE: bulk_create_logs()
   │  ├── Validate: log_date not in the future — OK
   │  ├── For each entry:
   │  │   ├── Validate habit exists and belongs to user (HabitRepository)
   │  │   ├── Check if log already exists (upsert: create or update)
   │  │   ├── Validate value type matches habit type
   │  │   └── Create HabitLog record
   │  ├── session.commit() — all saved in ONE transaction
   │  └── Invalidate Redis cache: DELETE analytics:{user_id}:*
   │
8. RESPONSE flows back through middleware
   │  ├── LoggingMiddleware: logs status=201, duration_ms=45
   │  └── Nginx adds response headers
   │
9. REACT receives 201 Created
   │  ├── TanStack Query invalidates ["logs"] and ["analytics"] cache
   │  └── Dashboard auto-refreshes with new data
   │
10. BACKGROUND (async, doesn't block the response):
    ├── SQS message sent → Lambda checks streak milestones
    └── If milestone hit → SES sends celebration email
```

---

## 📦 Module Dependency Map

```
                        ┌──────────┐
                        │   Auth   │ ← Foundation (depends on nothing)
                        └────┬─────┘
                             │ provides user_id to all modules
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼───┐    ┌────▼────┐   ┌─────▼──────────┐
         │ Habits │    │  Logs   │   │ Notifications  │
         └────┬───┘    └────┬────┘   └────────┬───────┘
              │             │                  │
              └──────┬──────┘                  │
                     │                         │
              ┌──────▼──────┐                  │
              │  Analytics  │ (reads Habits + Logs)
              └──────┬──────┘                  │
                     │                         │
              ┌──────▼──────┐                  │
              │     AI      │──────────────────┘
              │ LLM + RAG + │ (reads ALL modules, triggers notifications)
              │ Agent + Flow│
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │   Export    │ (reads Logs + Habits for CSV)
              └─────────────┘
```

**Key rule:** Modules call each other through **service interfaces**, never direct SQL. AI module calls `analytics_service.get_streaks()`, not `SELECT * FROM habit_logs...`. This means we can extract any module into a microservice by replacing the service call with an HTTP call.

---

## 🎤 Interview Q&A

### Q1: "Walk me through the architecture of your project"

> "It's a modular monolith with 7 modules: Auth, Habits, Logs, Analytics, AI, Notifications, and Export. Each module follows a layered pattern — Router handles HTTP, Service handles business logic, Repository handles database queries. Modules communicate through service interfaces, not direct SQL, so any module can be extracted into a microservice if needed.
>
> The request flow goes: Browser → Nginx (rate limiting, SSL) → FastAPI (middleware chain: logging, CORS, rate limiter) → Router (JWT auth via dependency injection) → Service (business logic) → Repository (SQL query) → PostgreSQL.
>
> The AI module is the most complex — it has 4 subsystems: LLM layer with 3 providers behind a Strategy pattern, a RAG pipeline using pgvector, a ReAct agent with 5 tools, and an agentic workflow for weekly reports.
>
> Infrastructure: Docker Compose runs 7 services — the backend, PostgreSQL + pgvector, Redis, MinIO for S3-compatible storage, Nginx, and Ollama for free local AI."

### Q2: "Why modular monolith instead of microservices?"

> "Three reasons. First, I'm a single developer — microservices need service discovery, distributed tracing, API gateways, separate CI/CD per service. That's months of infrastructure before writing business logic. Second, all modules share PostgreSQL — the Analytics module joins habits, logs, and user tables. In microservices, each service owns its database, so I'd need distributed joins or data duplication. Third, the module boundaries are clean — each has its own models, services, and repositories. If traffic grows and I need to extract the AI module into a separate service, I just replace `analytics_service.get_streaks()` with an HTTP call. Zero business logic changes."

### Q3: "What happens when a request hits your server?"

> "Request → Nginx (rate limit check, security headers) → FastAPI middleware chain (logging with request_id, CORS, application rate limiter) → Router (JWT decoded, user_id extracted, Redis blacklist checked) → Service (business rules validated, cache checked/invalidated) → Repository (SQL executed via SQLAlchemy async) → PostgreSQL. Response flows back through the same chain in reverse, with the logging middleware recording status code and duration."

### Q4: "How do your modules communicate?"

> "Through service interfaces, never direct SQL across module boundaries. For example, the AI agent's query_logs tool calls `LogRepository.get_logs_for_range()` — it doesn't write raw SQL against the habit_logs table. This is the same pattern whether it's a modular monolith or microservices — the only difference is whether the call is in-process (function call) or over the network (HTTP call). This design means I can extract any module into a microservice by changing one line: the service call becomes an HTTP call."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 01 — Project Overview](./phase0-part01-project-overview.md) | | [Part 03 — Tech Stack](./phase0-part03-tech-stack-explained.md) |
