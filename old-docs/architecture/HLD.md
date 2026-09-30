# High-Level Design (HLD) — Health Tracker

## 1. System Overview

An AI-powered personal health and habit tracking platform that enables users to track daily habits, visualize progress, and receive AI-driven insights.

## 2. Architecture Diagram

```
                    ┌──────────────┐
                    │   Browser    │
                    │  React + TS  │
                    └──────┬───────┘
                           │ HTTPS
                    ┌──────▼───────┐
                    │    Nginx     │ SSL termination, rate limiting,
                    │ Reverse Proxy│ static files, SSE support
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼─────┐ ┌───▼──────────┐
        │ FastAPI   │ │ Celery   │ │ AWS Lambda   │
        │ Backend   │ │ Workers  │ │ (6 functions)│
        │ (7 modules)│ │          │ │              │
        └──┬──┬──┬──┘ └────┬─────┘ └───┬──────────┘
           │  │  │         │            │
     ┌─────▼┐│┌─▼────┐ ┌──▼──┐  ┌─────▼─────┐
     │Postgres││Redis │ │Redis│  │S3 / MinIO │
     │+pgvec.│││      │ │(broker)│           │
     └───────┘│└──────┘ └─────┘  └───────────┘
              │
        ┌─────▼─────┐
        │  Ollama   │
        │ (Local LLM)│
        └───────────┘
```

## 3. Architecture: Modular Monolith

**Why modular monolith (not microservices):**
- Single team, single database — microservices add operational overhead without benefit
- Clear module boundaries allow future extraction into microservices if needed
- Each module has: router → service → repository → models (same as microservice layers)
- Modules communicate through service interfaces, never direct SQL across boundaries

## 4. Modules

| Module | Responsibility | Tables |
|--------|---------------|--------|
| Auth | User registration, JWT tokens, access control | users |
| Habits | Habit CRUD, soft delete, reordering | habits |
| Logs | Daily check-ins, bulk logging, type validation | habit_logs |
| Analytics | Streaks, weekly comparison, trends, correlations | (reads from habit_logs) |
| AI | LLM chat, RAG, agents, workflows | documents, document_chunks, ai_chat_messages, ai_insights |
| Notifications | Email delivery, scheduling, settings | notification_settings |
| Export | CSV/PDF generation, S3 storage | (reads from habit_logs) |

## 5. Data Flow

### User Logs a Habit
```
Browser → POST /api/v1/logs → FastAPI validates → PostgreSQL INSERT
    → Redis cache invalidated (analytics stale)
    → SQS message → Lambda checks streak milestone → SES email (if milestone)
```

### AI Chat Question
```
Browser → POST /api/v1/ai/chat → FastAPI → HealthCoachAgent created
    Agent Loop:
    → LLM thinks: "need sleep data" → calls query_logs tool → PostgreSQL
    → LLM thinks: "need correlation" → calls correlate tool → Python math
    → LLM generates final answer using tool results → Response to browser
```

### RAG Document Upload
```
Browser → POST /api/v1/ai/documents → FastAPI → S3 upload
    → S3 event → Lambda (doc processor)
    → Extract text (PyPDF2) → Chunk (recursive split) → Embed (Ollama)
    → Store chunks + vectors in pgvector → Document status = "processed"
```

## 6. Technology Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| API framework | FastAPI | Async, auto OpenAPI docs, dependency injection, type safety |
| Database | PostgreSQL + pgvector | ACID transactions + vector search in one DB, no separate vector DB |
| Cache | Redis | Sub-millisecond reads, pub/sub, Celery broker, rate limiting, token blacklist |
| LLM | Ollama (dev) / Groq (staging) | Free, Strategy pattern allows provider swap via config |
| Frontend | React + TypeScript | Type safety, large ecosystem, Recharts for charts |
| Containers | Docker Compose | Reproducible environments, one-command startup |
| CI/CD | GitHub Actions | Free for public repos, PostgreSQL service containers |

## 7. Scalability Strategy

| Scale Point | Current | Future |
|-------------|---------|--------|
| API servers | 1 (Docker) | ECS Fargate (auto-scale 2-10 tasks) |
| Database | Single PostgreSQL | RDS Multi-AZ + read replicas |
| Cache | Single Redis | ElastiCache cluster |
| LLM | Ollama local | AWS Bedrock (managed, auto-scale) |
| Background jobs | Celery (1 worker) | Lambda (auto-scale to 1000 concurrent) |
| Storage | MinIO | S3 with CloudFront CDN |

## 8. Security

- Passwords: bcrypt with cost factor 12
- Auth: JWT with short-lived access (30 min) + long-lived refresh (7 days)
- Token blacklist: Redis with TTL (auto-cleanup)
- Rate limiting: Nginx (L7) + application-level (Redis sliding window)
- CORS: configured per environment
- Row-level security: every query filters by user_id
- SQL injection: ORM parameterized queries (never raw string concatenation)
- Secrets: environment variables, never hardcoded
