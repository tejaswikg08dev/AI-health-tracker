# Phase 0 Part 1: Project Overview — What Is Health Tracker?

| Field | Details |
|-------|---------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 0 — Project Overview & Setup |
| **Part** | 1 of 2 |
| **Previous** | None (this is the beginning!) |
| **Next** | [Phase 0 Part 2: Environment Setup](./phase0-part2-environment-setup.md) |
| **Time to Complete** | 1-2 hours (reading + understanding) |
| **Difficulty** | Beginner |
| **Prerequisites** | None — just curiosity |
| **What You'll Learn** | What health trackers do, how AI agents work, what we're building |
| **Git Commit** | N/A (no code in this part) |

---

## Table of Contents
- [What Are We Building?](#what-are-we-building)
- [How Health Tracking Works in Real Life](#how-health-tracking-works)
- [The AI Ecosystem — 4 Subsystems](#the-ai-ecosystem)
- [What Each Module Does](#what-each-module-does)
- [Technical Challenges We'll Solve](#technical-challenges)
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [What Makes This Production-Grade?](#production-grade)
- [Design Patterns You'll Learn](#design-patterns)
- [Phase Roadmap](#phase-roadmap)
- [Project Folder Structure](#folder-structure)
- [Next Steps](#next-steps)

---

## What You'll Learn in This Part
- What a health habit tracker does and why AI makes it 10x more useful
- How an AI agent THINKS, calls TOOLS, and generates data-driven answers
- What RAG (Retrieval-Augmented Generation) is and why it matters
- What each of Health Tracker's 7 modules does (with real-world analogies)
- Why this project teaches more than 90% of tutorial apps
- The complete technology stack and why each tool was chosen

---

<a name="what-are-we-building"></a>
## What Are We Building?

### The One-Paragraph Explanation (Tell Your Parents This)

Health Tracker is a **personal health companion app** — like Fitbit meets ChatGPT. You tell it what habits you want to track (water intake, sleep, exercise, mood), log your data every day, and it shows you streaks, charts, and trends. The special part: it has an **AI health coach** you can chat with. You ask "Why am I tired this week?" and it actually checks YOUR sleep data (averaged 5.2 hours), finds correlations (sleep and mood have a 0.72 correlation), searches your uploaded blood reports, and gives you a personalized answer with citations. It even writes you a weekly health report automatically.

### The Technical Explanation

Health Tracker is a **full-stack web application** with a Python FastAPI backend (7 modules, 38 API endpoints), React TypeScript frontend (8 pages with charts), PostgreSQL + pgvector for data + vector search, Redis for caching and rate limiting, and a complete AI system with:
- **3 LLM providers** (Ollama free/local, Groq free/cloud, OpenAI paid/production) behind a Strategy pattern
- **RAG pipeline** (PDF upload → chunk → embed → pgvector → retrieval with citations)
- **ReAct agent** (5 tools that query YOUR database for data-driven answers)
- **Agentic workflow** (3-step pipeline: DataCollector → Analyzer → ReportWriter)

Plus 6 AWS Lambda functions, Docker Compose with 7 services, Nginx reverse proxy, GitHub Actions CI/CD, and comprehensive testing.

### Why This Project? (Career Value)

| What You'll Learn | Why Companies Care |
|---|---|
| Full-stack Python + React + TypeScript | The most in-demand stack for AI applications |
| FastAPI with async SQLAlchemy | Production-grade Python API development |
| AI agents (ReAct pattern from scratch) | The hottest skill in AI engineering right now |
| RAG pipeline with pgvector | Every company building AI features needs this |
| LLM provider abstraction (Strategy pattern) | Shows you understand production AI architecture |
| Modular monolith with clean layers | The architecture 80% of successful startups use |
| Docker + CI/CD + AWS Lambda | Full DevOps pipeline from zero to production |
| System design (HLD, LLD, trade-offs) | The #1 topic in senior engineer interviews |

**Real companies that use these exact patterns:** OpenAI (FastAPI for their API), Stripe (modular monolith), LangChain (ReAct agents), Notion (RAG for AI features), Vercel (React + TypeScript), every YC startup in 2024-2026 (FastAPI + LLM).

---

<a name="how-health-tracking-works"></a>
## How Health Tracking Works in Real Life

### The Story: Shreya's Daily Health Routine

Shreya wants to improve her health. She tracks 5 habits every day. Let's follow her through one day:

```
┌──────────────┐   ①   ┌──────────────┐   ②   ┌──────────────┐
│   Morning    │──────>│  Health      │──────>│  Database    │
│  (Shreya)    │       │  Tracker App │       │ (PostgreSQL) │
│              │       │              │       │              │
│ Opens app,   │       │ Validates    │       │ Stores:      │
│ logs 5 habits│       │ each value,  │       │ Water: 8     │
│ for today    │       │ saves all    │       │ Sleep: 7.5   │
│              │       │ at once      │       │ Exercise: ✅  │
│              │       │              │       │ Mood: 7/10   │
│              │       │              │       │ Reading: 30m │
└──────────────┘       └──────────────┘       └──────┬───────┘
                                                      │
     ⑥                    ⑤                    ③     │
┌──────────────┐   ┌──────────────┐    ┌──────────────▼──┐
│   Shreya     │   │  Dashboard   │    │   Analytics     │
│              │   │              │    │   Engine        │
│ Sees:        │   │ Shows:       │    │                 │
│ "Your sleep  │<──│ 🔥 15-day    │<───│ Calculates:    │
│ is 12% better│   │   streak!    │    │ • Streaks (SQL  │
│ this week!"  │   │ 📊 Trends    │    │   window fn)   │
│              │   │ 📈 78% done  │    │ • Weekly avg   │
│              │   │              │    │ • Correlations  │
└──────────────┘   └──────────────┘    └─────────────────┘
```

**That's basic health tracking.** But what makes our app SPECIAL is the AI:

```
     ⑦ — THE AI PART (what makes this project interview-worthy)

┌──────────────┐        ┌──────────────────────────────────────────┐
│   Shreya     │        │          AI HEALTH COACH                  │
│              │        │                                          │
│ Asks:        │  ────> │  AGENT THINKS: "I need sleep data"      │
│ "Why am I    │        │      ↓                                   │
│  tired this  │        │  TOOL CALL: query_logs("Sleep", 7 days) │
│  week?"      │        │      ↓                                   │
│              │        │  RESULT: avg 5.2 hours this week         │
│              │        │      ↓                                   │
│              │        │  AGENT THINKS: "Check correlation"       │
│              │        │      ↓                                   │
│              │        │  TOOL CALL: correlate("Sleep", "Mood")  │
│              │        │      ↓                                   │
│              │        │  RESULT: r = 0.72 (strong positive)     │
│              │        │      ↓                                   │
│ Gets:        │  <──── │  ANSWER: "You averaged 5.2 hours of     │
│ Personalized │        │  sleep this week — well below 7-8 hours.│
│ data-driven  │        │  I found a strong correlation (0.72)    │
│ answer!      │        │  between sleep and mood. Your mood is   │
│              │        │  higher on days you sleep more."        │
└──────────────┘        └──────────────────────────────────────────┘
```

**This is NOT a generic ChatGPT response.** The agent queried Shreya's ACTUAL database, calculated REAL correlations, and gave a personalized answer with specific numbers.

### The 3 Levels of Health Tracking

| Level | What It Does | Example Apps |
|-------|-------------|-------------|
| **Level 1: Logging** | Record data, show it back | Apple Health, Google Fit |
| **Level 2: Analytics** | Calculate streaks, trends, comparisons | Habitica, Streaks |
| **Level 3: AI-Powered** ✅ | Agent queries YOUR data, searches YOUR documents, generates personalized insights | **Our App**, Whoop (partially) |

We build Level 3 — the most technically challenging and interview-impressive.

---

<a name="the-ai-ecosystem"></a>
## The AI Ecosystem — 4 Subsystems

Our AI module has 4 subsystems, each solving a different problem:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI MODULE (4 SUBSYSTEMS)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  SUBSYSTEM 1: LLM LAYER                                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ What: Talks to AI models (Ollama / Groq / OpenAI)                    │   │
│  │ Pattern: Strategy (abstract interface, 3 implementations)            │   │
│  │ Why: Swap AI provider with a config change, not a code change       │   │
│  │                                                                      │   │
│  │  BaseLLMClient (abstract)                                           │   │
│  │  ├── OllamaClient  → free, runs on your laptop                     │   │
│  │  ├── GroqClient     → free, runs in the cloud (30 req/min)         │   │
│  │  └── OpenAIClient   → paid, best quality (production)              │   │
│  │                                                                      │   │
│  │  get_llm_client() → reads LLM_PROVIDER from .env → returns one     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  SUBSYSTEM 2: RAG PIPELINE                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ What: Upload health documents → AI can reference them in answers    │   │
│  │ Flow: PDF → extract text → chunk (500 tokens) → embed (768 floats) │   │
│  │       → store in pgvector → search by meaning → cite in answer     │   │
│  │                                                                      │   │
│  │  User: "What's my iron level?"                                      │   │
│  │  RAG: [searches blood_report.pdf] → "Your iron is 45 µg/dL         │   │
│  │        [Source: blood_report.pdf, Page 3], which is below the       │   │
│  │        normal range of 60-170 µg/dL."                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  SUBSYSTEM 3: REACT AGENT                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ What: AI that THINKS, calls TOOLS, and generates data-driven answers│   │
│  │ Pattern: ReAct (Reason + Act) — the core of modern AI agents       │   │
│  │                                                                      │   │
│  │  5 TOOLS the agent can call:                                        │   │
│  │  ├── query_logs      → fetch habit data from PostgreSQL             │   │
│  │  ├── get_analytics   → get streaks, weekly summaries                │   │
│  │  ├── search_documents → RAG search across uploaded PDFs             │   │
│  │  ├── correlate_habits → Pearson correlation between two habits      │   │
│  │  └── create_plan     → generate structured improvement plan         │   │
│  │                                                                      │   │
│  │  Loop: THINK → ACT (call tool) → OBSERVE (result) → REPEAT         │   │
│  │  Max 5 iterations, then generate final answer                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  SUBSYSTEM 4: AGENTIC WORKFLOW                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ What: 3 specialized agents working in a pipeline                    │   │
│  │ Pattern: Pipeline with orchestrator (retry, timeout, fallback)      │   │
│  │                                                                      │   │
│  │  Step 1: DataCollector → gathers all week's habit data (Python)    │   │
│  │      ↓ data_summary                                                 │   │
│  │  Step 2: Analyzer → finds patterns, correlations (LLM call)        │   │
│  │      ↓ analysis                                                     │   │
│  │  Step 3: ReportWriter → writes personalized report (LLM call)      │   │
│  │      ↓ report                                                       │   │
│  │  Orchestrator manages: retry on failure, timeout, graceful fallback │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why 4 Subsystems? (Not Just "Call OpenAI API")

| Subsystem | Without It | With It |
|-----------|-----------|---------|
| LLM Layer | Hardcoded to one provider. Dev costs $50/month (OpenAI). | Free dev (Ollama), free staging (Groq), paid only in production. Swap with config change. |
| RAG Pipeline | AI can only answer from training data. "Normal iron is 60-170" (generic). | AI references YOUR blood report. "Your iron is 45 [Source: report.pdf]" (personalized). |
| ReAct Agent | One LLM call → generic advice. "Drink more water." | Agent queries YOUR database → "You averaged 5.2 hours sleep this week, correlating 0.72 with mood." |
| Agentic Workflow | Manual report writing. | Automated weekly report: collect data → analyze patterns → write personalized prose. |

---

<a name="what-each-module-does"></a>
## What Each Module Does — In Plain English

Health Tracker is built as **7 modules** in a modular monolith. Each module does ONE thing well:

| # | Module | Real-World Analogy | What It Actually Does |
|---|--------|-------------------|----------------------|
| 1 | **Auth** | 🏢 Reception desk at a building | Checks who you are. Register, login, get an ID badge (JWT token). Your badge expires every 30 minutes — refresh it without re-entering your password. If you log out, your badge is blacklisted. |
| 2 | **Habits** | 📋 A customizable checklist | Create the habits you want to track: "Water" (numeric — glasses), "Exercise" (yes/no), "Mood" (scale 1-10). Max 20 habits. Drag to reorder. Archive (don't delete) to preserve history. |
| 3 | **Logs** | 📝 A daily journal entry form | Every day, fill in today's values for all your habits. "Save All" button saves everything at once. Can't log for future dates. One entry per habit per day (database constraint). |
| 4 | **Analytics** | 📊 A personal dashboard with charts | Calculates: current streak (consecutive days), weekly comparison (this vs last week with % change), monthly trends (30-day line chart), correlations (does sleep affect mood?), completion rate. ALL cached in Redis for speed. |
| 5 | **AI** | 🤖 A personal health coach who can read your diary | The big one. Chat with AI (agent with 5 tools). Upload health documents (RAG with pgvector). Generate weekly reports (agentic workflow). Stream responses word-by-word (SSE). Track token usage per user. |
| 6 | **Notifications** | 🔔 A reminder system | Daily "time to log!" email at 8 AM. Weekly health report email on Sunday. "🔥 30-day streak!" celebration email. Uses Console (dev), Resend (staging), or AWS SES (production). |
| 7 | **Export** | 📁 A data download button | Export your habit data as CSV (direct download or async via S3 with presigned URL). Generate HTML/PDF reports. S3-compatible storage (MinIO locally, AWS S3 in production). |

### Plus Infrastructure Components

| Component | What It Does |
|-----------|-------------|
| **Nginx** | Reverse proxy: routes requests, rate limits (30r/s API, 2r/s AI, 5r/min login), security headers, SSE support for streaming |
| **Docker Compose** | Runs 7 services with one command: PostgreSQL+pgvector, Redis, MinIO, Ollama, Backend, Celery, Nginx |
| **6 Lambda Functions** | Serverless: daily reminders (cron), weekly reports (cron), CSV export (SQS), streak milestones (SQS), data cleanup (cron), document processing (S3 event) |
| **GitHub Actions** | CI/CD: lint (ruff+mypy) → test (pytest with real DB) → build Docker images → deploy |

---

<a name="technical-challenges"></a>
## Technical Challenges We'll Solve

| # | Challenge | Why It's Hard | Our Solution |
|---|-----------|---------------|--------------|
| 1 | **Streak calculation** | Finding consecutive day sequences in SQL is a classic hard problem | Gaps-and-islands algorithm with ROW_NUMBER() window function — one SQL query |
| 2 | **AI provider lock-in** | Tied to OpenAI? Costs $50/month in dev. Ollama is free but different API. | Strategy pattern: abstract BaseLLMClient → 3 implementations. Swap via config. |
| 3 | **Semantic search (RAG)** | User asks "iron levels" but document says "ferritin count" — keyword search fails | Vector embeddings + cosine similarity in pgvector. Finds meaning, not just words. |
| 4 | **AI that uses real data** | Generic ChatGPT says "drink more water." Useless. | ReAct agent with 5 tools that query YOUR PostgreSQL database for actual numbers. |
| 5 | **Cache invalidation** | Dashboard shows stale streaks after user logs a new habit | Cache-aside pattern: Redis cache with TTL + explicit invalidation on every write |
| 6 | **Rate limiting** | One user sends 1000 AI requests → your LLM bill explodes | Redis sliding window: 30r/s API, 2r/s AI, 5r/min login. Different limits per endpoint type. |
| 7 | **Bulk operations** | User fills in 5 habits → "Save All" → must be atomic (all or nothing) | Single database transaction wrapping bulk upsert. Fails entirely or succeeds entirely. |
| 8 | **Type-safe logging** | Habit "Water" = 8 glasses (number). "Exercise" = yes (boolean). "Mood" = 7 (scale). One log table? | Three typed columns: value_numeric, value_boolean, value_scale. Only one filled per row. |
| 9 | **Token refresh** | JWT expires every 30 min. User shouldn't re-login every 30 min. | Access token (30 min) + refresh token (7 days). Auto-refresh in Axios interceptor — user never notices. |
| 10 | **Streaming AI responses** | User asks a question → waits 10 seconds for full response → feels broken | Server-Sent Events (SSE). Response appears word-by-word like ChatGPT. Nginx configured with proxy_buffering off. |
| 11 | **Multi-step AI report** | One LLM call to write a report → mediocre quality | Agentic workflow: 3 specialized agents (DataCollector → Analyzer → ReportWriter). Each does one thing well. Orchestrator handles retry and fallback. |
| 12 | **Document processing** | User uploads a 50-page PDF → must chunk, embed, store vectors | Lambda triggered by S3 upload event → extract text (PyPDF2) → recursive chunk (500 tokens, 50 overlap) → embed → pgvector INSERT |

---

<a name="tech-stack"></a>
## Tech Stack

### Backend

| Category | Technology | Version | Why We Chose It |
|----------|-----------|---------|-----------------|
| Language | **Python** | 3.11+ | AI ecosystem (90% of AI/ML libraries are Python-first) |
| Framework | **FastAPI** | 0.115 | Async, auto Swagger docs, Pydantic validation, dependency injection |
| ORM | **SQLAlchemy** | 2.0 (async) | Async queries, relationship mapping, migration support |
| Migrations | **Alembic** | 1.13 | Version-controlled database schema changes |
| Background Tasks | **Celery** | 5.4 | Distributed task queue for email, reports |
| SQL Database | **PostgreSQL** | 16 + pgvector | ACID transactions + vector similarity search in ONE database |
| Cache / Broker | **Redis** | 7 | Sub-ms cache, rate limiting, token blacklist, Celery broker |
| AI (dev) | **Ollama** | Latest | Free, local. Runs Llama 3.1 on your laptop |
| AI (staging) | **Groq** | API | Free tier: 30 req/min. Ultra-fast inference |
| AI (production) | **OpenAI** | API | Best quality. Company pays for it |
| Embeddings | **nomic-embed-text** | via Ollama | Free, 768 dimensions, good quality |
| HTTP Client | **httpx** | 0.27 | Async HTTP for LLM API calls |
| PDF Parsing | **PyPDF2** | 3.0 | Extract text from uploaded health documents |
| Templating | **Jinja2** | 3.1 | Prompt templates, email templates |
| Logging | **structlog** | 24.4 | Structured JSON logging (searchable in ELK/CloudWatch) |
| Auth | **python-jose** + **passlib** | 3.3 / 1.7 | JWT tokens + bcrypt password hashing |
| AWS | **boto3** | 1.35 | S3 (MinIO locally), SES, SQS, Lambda |
| Validation | **Pydantic** | 2.9 | Request/response validation with type safety |
| Settings | **pydantic-settings** | 2.5 | Environment variable management from .env files |

### Frontend

| Category | Technology | Version | Why We Chose It |
|----------|-----------|---------|-----------------|
| Framework | **React** | 18 | Component-based, huge ecosystem |
| Language | **TypeScript** | 5.0 | Catch bugs at compile time, IDE autocomplete |
| Build | **Vite** | 5.4 | 10x faster than Webpack, instant hot reload |
| Data Fetching | **TanStack Query** | 5.0 | Auto cache, refetch on focus, mutations |
| State | **Zustand** | 4.5 | 1KB, zero boilerplate, works outside React |
| Charts | **Recharts** | 2.12 | Line, bar, pie charts for analytics |
| Forms | **React Hook Form** + **Zod** | 7.0 / 3.0 | Type-safe form validation |
| Styling | **Tailwind CSS** | 3.4 | Utility-first, responsive, no CSS files |
| Icons | **Lucide React** | Latest | Clean, consistent icon set |
| HTTP | **Axios** | 1.7 | Interceptors for JWT auto-refresh |

### Infrastructure

| Category | Technology | Why |
|----------|-----------|-----|
| Reverse Proxy | **Nginx** | Rate limiting, SSL, SSE support, static files |
| Containers | **Docker Compose** | 7 services with one command |
| CI/CD | **GitHub Actions** | Free, service containers for real DB in tests |
| Serverless | **AWS Lambda + SAM** | 6 event-driven functions, free tier |
| Object Storage | **MinIO** (dev) / **S3** (prod) | Same boto3 API, free locally |
| Email | **Console** (dev) / **Resend** (staging) / **SES** (prod) | Strategy pattern, zero cost in dev |

---

<a name="architecture-overview"></a>
## Architecture Overview — The 5 Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: PRESENTATION                                                        │
│ What users see and interact with                                             │
│                                                                               │
│   React + TypeScript (8 pages)                                               │
│   Login → Dashboard → Habits → Check-In → Analytics → AI Chat → Settings    │
│   Axios with auto JWT refresh │ Zustand auth state │ Recharts visualizations │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ HTTP / SSE (Server-Sent Events)
┌────────────────────────────────────────▼────────────────────────────────────┐
│ LAYER 2: GATEWAY                                                             │
│ Single entry point — security, routing, rate limiting                        │
│                                                                               │
│   Nginx Reverse Proxy                                                        │
│   - Rate limiting: 30r/s API │ 2r/s AI │ 5r/min login                       │
│   - Security headers (X-Frame-Options, XSS, HSTS)                           │
│   - Gzip compression (100KB → ~15KB)                                         │
│   - SSE support (proxy_buffering off for AI streaming)                       │
│   - Static files (React build in production)                                 │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ HTTP (internal)
┌────────────────────────────────────────▼────────────────────────────────────┐
│ LAYER 3: APPLICATION (Modular Monolith — 7 Modules)                          │
│                                                                               │
│ ┌──────┐ ┌──────┐ ┌────┐ ┌─────────┐ ┌────────┐ ┌──────┐ ┌──────┐       │
│ │ Auth │ │Habits│ │Logs│ │Analytics│ │   AI   │ │Notif │ │Export│       │
│ │ 6 ep │ │ 6 ep │ │5 ep│ │  6 ep   │ │  9 ep  │ │ 3 ep │ │ 2 ep│       │
│ └──┬───┘ └──┬───┘ └─┬──┘ └───┬─────┘ └───┬────┘ └──┬───┘ └──┬──┘       │
│    │        │       │        │            │         │        │            │
│ ┌──▼────────▼───────▼────────▼────────────▼─────────▼────────▼──────────┐│
│ │                    SHARED LAYER                                         ││
│ │  config.py │ database.py │ redis_client.py │ dependencies.py           ││
│ │  base_repository.py │ base_schemas.py │ exceptions.py │ date_utils.py  ││
│ └──┬──────────┬──────────┬──────────────────────────────────────────────┘│
│    │          │          │                                                │
│ ┌──▼──────────▼──────────▼──────────────────────────────────────────────┐│
│ │                    MIDDLEWARE LAYER                                     ││
│ │  CORS → LoggingMiddleware → RateLimiter → ErrorHandler → Router       ││
│ └───────────────────────────────────────────────────────────────────────┘│
└────────┬──────────┬──────────┬──────────┬───────────────────────────────┘
         │          │          │          │
┌────────▼──────────▼──────────▼──────────▼───────────────────────────────┐
│ LAYER 4: DATA & INFRASTRUCTURE                                           │
│                                                                           │
│ ┌──────────┐ ┌───────┐ ┌──────┐ ┌───────────┐ ┌────────────────────┐  │
│ │PostgreSQL│ │ Redis │ │MinIO │ │  Ollama   │ │  Celery Workers   │  │
│ │+pgvector │ │       │ │ (S3) │ │(Local LLM)│ │  (background)     │  │
│ │ 8 tables │ │4 uses │ │files │ │ Llama 3.1 │ │  reminders,       │  │
│ │ vectors  │ │       │ │      │ │ nomic-embed│ │  reports           │  │
│ └──────────┘ └───────┘ └──────┘ └───────────┘ └────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: SERVERLESS (AWS Lambda — 6 Functions)                            │
│                                                                           │
│ EventBridge cron ──► Daily Reminder │ Weekly Report │ Data Cleanup        │
│ SQS messages ─────► CSV Export │ Streak Milestone                         │
│ S3 events ────────► Document Processor (RAG ingestion)                   │
└───────────────────────────────────────────────────────────────────────────┘
```

**Why these 5 layers?**
- Layer 1 (React) can be rebuilt in Vue.js without touching the backend
- Layer 2 (Nginx) can be replaced by AWS ALB in production
- Layer 3 (FastAPI) is a modular monolith — any module can be extracted into a microservice
- Layer 4 (data) can swap MinIO for real S3, Ollama for Bedrock — config changes only
- Layer 5 (Lambda) can replace Celery for production workloads

---

<a name="production-grade"></a>
## What Makes This Production-Grade?

| Feature | Tutorial/Toy App | Our Health Tracker |
|---------|-----------------|-------------------|
| Error handling | `try-except: return 500` | 5-level exception hierarchy → structured JSON. Global handler catches ALL errors. |
| Security | Hardcoded passwords | bcrypt (cost 12), JWT (access 30min + refresh 7d), Redis token blacklist, row-level access |
| Rate limiting | None | Redis sliding window: 3 different zones (API/AI/login), fail-open if Redis down |
| Caching | None or `@lru_cache` | Cache-aside pattern: Redis TTL (5min-1hr), explicit invalidation on writes |
| AI integration | `openai.chat()` one-liner | Strategy pattern (3 providers), ReAct agent (5 tools), RAG pipeline (pgvector), agentic workflow (3-step) |
| Database | SQLite, no migrations | PostgreSQL + pgvector, Alembic migrations, connection pooling (20 pool + 10 overflow) |
| Testing | Manual Postman clicks | pytest: 37+ tests, fixtures, mocks, factory functions, async test client |
| Deployment | `python app.py` on laptop | Docker Compose → GitHub Actions CI/CD → Render/Vercel staging → AWS production |
| Observability | `print("debug")` | structlog JSON logging, request_id tracing, per-request timing |
| Configuration | Hardcoded strings | Pydantic Settings from .env, validated at startup, `@lru_cache` singleton |

---

<a name="design-patterns"></a>
## Design Patterns You'll Learn

| # | Pattern | Where It's Used | Real-World Analogy | Interview Value |
|---|---------|----------------|-------------------|-----------------|
| 1 | **Strategy** | LLM providers (Ollama/Groq/OpenAI swap via config) | A restaurant that sources ingredients from 3 suppliers — swap without changing recipes | ⭐⭐⭐ |
| 2 | **Factory** | `get_llm_client()` reads config → returns the right provider | A car dealership that gives you a Toyota, Honda, or BMW based on your budget | ⭐⭐⭐ |
| 3 | **Repository** | Every module: Router → Service → Repository → Database | A librarian (repository) who finds books (data) for readers (service) — readers never enter the stacks | ⭐⭐⭐ |
| 4 | **Service Layer** | Business logic separated from HTTP in every module | A kitchen (service) that cooks food — the waiter (router) never touches the stove | ⭐⭐⭐ |
| 5 | **Cache-Aside** | Analytics cached in Redis with TTL, invalidated on writes | A sticky note (cache) on your desk. If it's there, use it. If not, look up the answer and write a new sticky note. | ⭐⭐ |
| 6 | **Abstract Base Class** | BaseLLMClient, BaseTool, BaseWorkflow, BaseEmailProvider | A job description (abstract class) that says "must be able to cook" — the chef (implementation) decides HOW | ⭐⭐ |
| 7 | **ReAct Agent** | Think → Act (call tool) → Observe → Repeat | A detective who THINKS about what clue to look for, GOES to find it, EXAMINES it, then decides what to do next | ⭐⭐⭐ |
| 8 | **Pipeline** | Agentic 3-step weekly report: collect → analyze → write | A car assembly line — each station does one thing, passes to the next | ⭐⭐ |
| 9 | **Modular Monolith** | 7 modules with clear service boundaries, communicating through interfaces | Departments in a company — each has its own space but shares the same building | ⭐⭐⭐ |
| 10 | **Dependency Injection** | FastAPI Depends() provides DB sessions, Redis, auth | A restaurant where the waiter (handler) doesn't buy ingredients — the kitchen (DI) provides them | ⭐⭐ |

---

<a name="phase-roadmap"></a>
## Phase Roadmap

| Phase | What We Do | Outcome | Docs |
|-------|-----------|---------|------|
| **0** | Understand the project + set up environment | Tools installed, concepts understood | 2 docs |
| **1** | System design (requirements, decisions, APIs, DB) | Complete design document | 1 doc (~3000 lines) |
| **2** | High-level design (architecture, flows, scaling) | Component diagrams, data flows | 1 doc (~2000 lines) |
| **3** | Low-level design (models, repos, services, routers) | All Python class signatures | 1 doc (~2500 lines) |
| **4** | **Code everything** (the main event!) | 230+ source files, working app | ~55 docs |
| **5** | Write tests | 37+ tests, mocks, fixtures | 3 docs |
| **6** | Dockerize everything | All services in containers | 1 doc |
| **7** | CI/CD pipeline | Auto-build + auto-test on push | 1 doc |
| **8** | Deploy (local, staging, AWS, Lambda) | Live system | 4 docs |
| **9** | Nginx + Monitoring | Reverse proxy, structured logs | 1 doc |
| **10** | E2E testing + Interview prep | curl commands, prepared answers | 2 docs |

**Total: ~72 documents, each 1,000-5,000 lines**

---

<a name="folder-structure"></a>
## Project Folder Structure

```
health-tracker/
│
├── backend/                          ← Python FastAPI backend (100+ files)
│   ├── app/
│   │   ├── __init__.py               ← Package init, version
│   │   ├── main.py                   ← FastAPI app factory, 7 routers
│   │   ├── config.py                 ← Pydantic Settings (env vars)
│   │   ├── database.py               ← Async SQLAlchemy engine
│   │   ├── redis_client.py           ← Redis connection pool
│   │   ├── dependencies.py           ← FastAPI DI type aliases
│   │   │
│   │   ├── modules/                  ← 7 business modules
│   │   │   ├── auth/                 ← JWT, bcrypt, token blacklist
│   │   │   ├── habits/               ← Habit CRUD, soft delete, reorder
│   │   │   ├── logs/                 ← Daily check-ins, bulk upsert
│   │   │   ├── analytics/            ← Streaks, SQL window functions, Redis cache
│   │   │   ├── ai/                   ← LLM + RAG + Agents + Workflows (39 files!)
│   │   │   ├── notifications/        ← Email providers, Celery tasks
│   │   │   └── export/               ← CSV, S3/MinIO storage
│   │   │
│   │   ├── shared/                   ← Reusable: base_repository, exceptions, date_utils
│   │   ├── middleware/               ← error_handler, logging, rate_limiter
│   │   └── tasks/                    ← Celery app config
│   │
│   ├── tests/                        ← pytest: unit + integration + mocks
│   ├── alembic/                      ← 5 database migrations
│   ├── requirements.txt              ← 20+ pinned dependencies
│   ├── Dockerfile                    ← Multi-stage: builder → dev → production
│   └── pyproject.toml                ← Ruff, mypy, pytest config
│
├── frontend/                         ← React + TypeScript (50+ files)
│   ├── src/
│   │   ├── types/                    ← 7 TypeScript interfaces
│   │   ├── services/                 ← 8 API service files (Axios)
│   │   ├── hooks/                    ← 5 TanStack Query hooks (24 queries)
│   │   ├── store/                    ← Zustand auth state
│   │   ├── components/               ← Layout, habits, logs, charts, AI chat
│   │   └── pages/                    ← 8 pages
│   ├── package.json
│   └── Dockerfile
│
├── lambda_functions/                 ← 6 AWS Lambda functions
│   ├── 01_daily_reminder/
│   ├── 02_weekly_report/
│   ├── 03_csv_export/
│   ├── 04_streak_milestone/
│   ├── 05_data_cleanup/
│   ├── 06_document_processor/
│   ├── shared/                       ← DB, email, S3 utilities
│   └── template.yaml                ← AWS SAM infrastructure
│
├── nginx/default.conf                ← Reverse proxy config
├── docker-compose.yml                ← 7 services
├── docker-compose.dev.yml            ← Dev overrides (hot reload)
├── docker-compose.test.yml           ← Test-only (PG + Redis)
├── Makefile                          ← 12 shortcut commands
├── .github/workflows/ci.yml          ← CI/CD pipeline
├── scripts/seed_data.py              ← Demo data generator
│
├── docs/                             ← 72 documentation files
│
├── .env.example                      ← Environment variables template
├── .gitignore
├── .dockerignore
└── README.md
```

**Total: ~230+ source files across backend, frontend, Lambda, and infrastructure.**

---

<a name="next-steps"></a>
## Next Steps

**What's coming in Part 2 (Environment Setup):**
- Install Python 3.11, Docker Desktop, Node.js 20, Git, VS Code (step-by-step)
- Set up virtual environment, pip, venv
- Verify every tool with a PowerShell script
- 20+ common installation errors and how to fix them

**Before moving on, verify you understand:**
- [ ] What a health habit tracker does (Levels 1-3)
- [ ] What the 4 AI subsystems do (LLM, RAG, Agent, Workflow)
- [ ] What each of the 7 modules does
- [ ] The difference between a chatbot and an AI agent
- [ ] Why we need 3 LLM providers (Strategy pattern)
- [ ] Why pgvector (not Pinecone) for RAG

---

## Document Index

| Phase | Part | Document | Status |
|-------|------|----------|--------|
| 0 | **1** | **Project Overview** | ← You are here |
| 0 | 2 | [Environment Setup](./phase0-part2-environment-setup.md) | ⬜ Next |
| 1 | - | [System Design](./phase1-system-design.md) | ⬜ |
| 2 | - | [High-Level Design](./phase2-high-level-design.md) | ⬜ |
| 3 | - | [Low-Level Design](./phase3-low-level-design.md) | ⬜ |
| 4 | 01 | [Project Setup + Docker](./phase4-part01-project-setup-docker.md) | ⬜ |
| 4 | 02 | [Backend Foundation](./phase4-part02-backend-foundation.md) | ⬜ |
| 4 | 03 | [Shared Utilities + Middleware](./phase4-part03-shared-utilities-middleware.md) | ⬜ |
| 4 | 04 | [Auth Module Overview](./phase4-part04-auth-module-overview.md) | ⬜ |
| ... | ... | ... | ... |

---
*End of Phase 0 Part 1 — Project Overview*
*Next: [Phase 0 Part 2 — Environment Setup](./phase0-part2-environment-setup.md)*
