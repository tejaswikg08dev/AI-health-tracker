# 🏗️ Phase 2 — Part 01: High-Level Design (HLD)

> **"HLD answers: WHAT components exist and HOW they talk. LLD answers: HOW each component works internally."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 2 — High-Level Design |
| **Part** | 01 |
| **Previous** | [Phase 1 — System Design Overview](./phase1-part01-system-design-overview.md) |
| **Next** | [Phase 3 Part 01 — Low-Level Design](./phase3-part01-low-level-design.md) |
| **Time to Read** | ~20 minutes |

---

## What is HLD?

High-Level Design shows the **big picture** — which boxes exist on the whiteboard and which arrows connect them. You DON'T show implementation details (no class names, no SQL queries, no function signatures). Just components and data flows.

**Analogy:** HLD is a city map — you can see the hospital, the school, and the roads between them. LLD is the floor plan of the hospital — you can see each room, each bed, each equipment.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USERS (Browser)                                │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTPS
┌───────────────────────────────▼──────────────────────────────────────┐
│                    FRONTEND (React + TypeScript)                       │
│  8 pages │ Axios with JWT auto-refresh │ Zustand state │ Recharts    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP / SSE
┌───────────────────────────────▼──────────────────────────────────────┐
│                        NGINX (Reverse Proxy)                          │
│  Rate limiting │ Security headers │ Gzip │ SSE proxy │ Static files  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│                    FASTAPI BACKEND (7 Modules)                        │
│                                                                       │
│  ┌─────┐ ┌──────┐ ┌────┐ ┌─────────┐ ┌────┐ ┌──────┐ ┌──────┐    │
│  │Auth │ │Habits│ │Logs│ │Analytics│ │ AI │ │Notif.│ │Export│    │
│  └──┬──┘ └──┬───┘ └─┬──┘ └────┬────┘ └─┬──┘ └──┬───┘ └──┬───┘    │
│     │       │       │         │         │       │        │          │
│  ┌──▼───────▼───────▼─────────▼─────────▼───────▼────────▼──────┐  │
│  │                    SHARED LAYER                                │  │
│  │  Config │ Database │ Redis │ Dependencies │ Middleware         │  │
│  └──┬──────────┬──────────┬───────────────────────────────────── │  │
└─────┼──────────┼──────────┼──────────────────────────────────────┘  │
      │          │          │                                          │
 ┌────▼───┐ ┌───▼───┐ ┌───▼────┐ ┌──────────┐ ┌───────────────────┐
 │Postgres│ │ Redis │ │ MinIO  │ │  Ollama  │ │  AWS Lambda (6)   │
 │+pgvec  │ │       │ │  (S3)  │ │(local AI)│ │  EventBridge/SQS  │
 │8 tables│ │4 uses │ │ files  │ │  Groq    │ │  S3 triggers      │
 └────────┘ └───────┘ └────────┘ └──────────┘ └───────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Receives | Sends To |
|-----------|---------------|----------|----------|
| **Nginx** | Rate limit, SSL, routing, compression | Browser requests | FastAPI |
| **FastAPI** | Business logic, auth, validation | Nginx requests | DB, Redis, LLM |
| **PostgreSQL** | Persistent data, vector search | SQL queries | Query results |
| **Redis** | Cache, rate limits, token blacklist, broker | GET/SET commands | Cached data |
| **Ollama/Groq** | Generate AI text, embeddings | Prompts | Completions |
| **MinIO/S3** | Store files (PDFs, CSVs, reports) | Upload requests | Download URLs |
| **Lambda** | Event-driven tasks (email, cleanup, RAG) | EventBridge/SQS/S3 | DB, SES, S3 |

---

## Data Flows

### Flow 1: User Signup → Login → Use App

```
Browser → POST /auth/signup → FastAPI → bcrypt hash → PostgreSQL (INSERT user)
Browser → POST /auth/login → FastAPI → verify password → create JWT → return tokens
Browser → GET /habits (Authorization: Bearer token) → FastAPI → decode JWT → query DB → return habits
```

### Flow 2: Daily Check-In

```
Browser → POST /logs/bulk → FastAPI → validate types → PostgreSQL (INSERT logs)
                                    → Redis (DELETE analytics cache)
                                    → SQS (streak milestone check)
```

### Flow 3: AI Chat with Agent

```
Browser → POST /ai/chat → FastAPI → create HealthCoachAgent
  Agent Loop (max 5 iterations):
    → LLM: "I need sleep data" → tool: query_logs → PostgreSQL → result
    → LLM: "I need correlation" → tool: correlate → Python math → result
    → LLM: "I have enough" → generate final response
  → Return response to browser
```

### Flow 4: RAG Document Upload

```
Browser → POST /ai/documents (PDF file) → FastAPI → MinIO (store file)
  → Extract text (PyPDF2)
  → Chunk (recursive split, 500 tokens, 50 overlap)
  → Embed chunks (Ollama nomic-embed-text → 768-dim vectors)
  → Store chunks + vectors in pgvector
  → Update document status: "processed"
```

### Flow 5: Weekly Report (Agentic Workflow)

```
EventBridge (Sunday 9 AM) → Lambda
  → Step 1: DataCollector queries PostgreSQL (all week's data)
  → Step 2: Analyzer calls Groq LLM (find patterns)
  → Step 3: ReportWriter calls Groq LLM (write report)
  → Upload HTML to S3
  → Send email via SES
```

---

## Technology Choice Rationale

| Decision | Chose | Why | Alternative | Why Not |
|----------|-------|-----|-------------|---------|
| Architecture | Modular monolith | Single team, shared DB, clear boundaries | Microservices | Operational overhead without benefit |
| Backend | FastAPI (Python) | Async, auto docs, AI ecosystem | Django | No native async, heavy for API-only |
| Database | PostgreSQL + pgvector | SQL + vector search in ONE DB | PG + Pinecone | Two databases to manage, $70/month |
| Cache | Redis (cache-aside) | Sub-ms reads, 4 use cases | Memcached | No TTL auto-cleanup, no pub/sub |
| AI | 3 providers (Strategy) | Free dev, free staging, paid prod | Hardcoded OpenAI | $0 vs $50+/month in development |
| Frontend | React + TypeScript | Type safety, Recharts, ecosystem | Vue, Svelte | React has largest ecosystem |
| Containers | Docker Compose | One-command startup, reproducible | Manual install | "Works on my machine" problems |
| Serverless | Lambda + SAM | Free tier, auto-scale, event-driven | Only Celery | Lambda handles spikes better |

---

## Scaling Strategy

| Scale Point | Current (1K users) | Future (100K users) |
|-------------|-------------------|---------------------|
| API servers | 1 FastAPI (Docker) | ECS Fargate (auto-scale 2-10) |
| Database | 1 PostgreSQL | RDS Multi-AZ + read replicas |
| Cache | 1 Redis | ElastiCache cluster |
| AI | Ollama (local) | AWS Bedrock (managed, auto-scale) |
| Background | Celery (1 worker) | Lambda (auto-scale to 1000) |
| Storage | MinIO (Docker) | S3 + CloudFront CDN |
| Frontend | Vite dev server | S3 + CloudFront (static) |

---

## 🎤 Interview Q&A

### Q: "Draw the architecture of your system"

> [Draw the diagram above] "There are 5 main layers: Browser → Nginx → FastAPI → Data stores → Background workers. The FastAPI backend is a modular monolith with 7 modules. Each module follows Router → Service → Repository layers. The data layer has PostgreSQL for persistent data with pgvector for AI embeddings, Redis for 4 use cases (cache, rate limiting, token blacklist, task broker), MinIO for file storage, and Ollama for free local AI. Lambda functions handle event-driven work: scheduled emails, async exports, and document processing for RAG."

### Q: "What are the most critical components?"

> "PostgreSQL is the most critical — all persistent data is there. If it goes down, the app stops. That's why in production I'd use RDS Multi-AZ with automatic failover and daily backups with point-in-time recovery. Redis is second — if Redis goes down, the app still works but is slower (cache miss → query DB) and rate limiting doesn't work. I designed the rate limiter to 'fail open' — if Redis is unreachable, requests are allowed through. Better slow than blocked."

### Q: "How do you handle failures?"

> "Three levels: First, graceful degradation — if the AI (Ollama) is down, the app still works for tracking habits and viewing analytics. The AI chat shows an error but doesn't crash the app. Second, retry logic — the agentic workflow orchestrator retries failed steps twice before falling back to a partial report. Third, circuit breaker concept — if Redis is down, the rate limiter passes requests through (fail open), and the cache layer returns cache misses (query PostgreSQL directly). No single infrastructure failure should take down the entire app."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Phase 1 — System Design](./phase1-part01-system-design-overview.md) | | [Phase 3 Part 01 — LLD](./phase3-part01-low-level-design.md) |
