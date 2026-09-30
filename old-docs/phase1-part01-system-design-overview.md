# 📐 Phase 1 — Part 01: System Design Overview

> **"A system design interview tests if you can THINK about a problem before you CODE a solution."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 1 — System Design |
| **Part** | 01 |
| **Previous** | [Phase 0 Part 05 — AI Concepts](./phase0-part05-ai-concepts-from-zero.md) |
| **Next** | [Phase 2 Part 01 — High-Level Design](./phase2-part01-high-level-design.md) |
| **Time to Read** | ~25 minutes |

---

## The 7-Step System Design Process

Every system design — whether in an interview or at a company — follows these steps. We apply each to the Health Tracker.

---

## Step 1: Clarify Requirements (2 minutes)

### What to Ask (Before Designing Anything)

```
"How many users?"         → ~1,000 users, 200 daily active
"Real-time needed?"       → Near real-time for AI chat, not for analytics
"Read or write heavy?"    → Read heavy (dashboard loads 100x more than logs created)
"Consistency important?"  → Yes — streak counts must be accurate
"What devices?"           → Web browser only (no mobile app)
"Budget?"                 → $0 for development, ~$100-180/month production
```

### Functional Requirements

| Category | Requirements |
|----------|-------------|
| **Auth** | Register, login, JWT tokens, profile management |
| **Habits** | Create habits (3 types), edit, archive (soft delete), reorder |
| **Logging** | Daily check-in (single + bulk), one per habit per day, no future dates |
| **Analytics** | Streaks, weekly comparison, monthly trends, correlations, completion rates |
| **AI** | Chat with health coach, upload documents for RAG, agent with tools, weekly report |
| **Notifications** | Daily reminder email, weekly report email, streak milestone email |
| **Export** | CSV download, S3 upload with presigned URL |

### Non-Functional Requirements

| Requirement | Target | How We Achieve It |
|------------|--------|-------------------|
| **Latency** | Dashboard < 500ms | Redis cache (5 min TTL) |
| **Latency** | CRUD < 200ms | PostgreSQL with indexes |
| **Latency** | AI chat < 10s | Agent with max 5 iterations |
| **Throughput** | 10 RPS peak | Single FastAPI server (handles 1000+ RPS) |
| **Availability** | 99.9% uptime | Docker restart policies, health checks |
| **Security** | No data breaches | bcrypt, JWT, rate limiting, row-level access |
| **Cost** | $0 development | Ollama, Docker, MinIO — all free |

---

## Step 2: Capacity Estimation (2 minutes)

### Users
```
Total users:           1,000
Daily active (DAU):    200 (20%)
Concurrent at peak:    50
```

### Storage Per User Per Day
```
Habit logs:     5 habits × 200 bytes = 1 KB
Chat messages:  3 messages × 500 bytes = 1.5 KB
Misc:           0.5 KB
TOTAL:          ~3 KB per user per day
```

### Annual Storage
```
1,000 users × 3 KB/day × 365 days = 1.1 GB/year
+ Indexes, vectors, documents:      ~2 GB/year
TOTAL:                              ~3 GB/year
→ One PostgreSQL instance handles this easily for 10+ years
```

### Requests Per Second
```
Dashboard load: 4 API calls × 200 DAU / 86,400 sec = 0.01 RPS (trivial)
Peak (morning check-in): ~10 RPS for 15 minutes
AI chat: 5 messages × 50 users / 3600 sec = 0.07 RPS

TOTAL PEAK: ~10 RPS
FastAPI handles: 1,000+ RPS
CONCLUSION: Single server is sufficient. No need for clustering.
```

### Interview Tip
> Always show the math. Even if the numbers are approximate, interviewers want to see you THINK about scale. "I estimated 10 RPS at peak, which a single FastAPI server handles comfortably. I'd add a second server behind a load balancer if we hit 500+ concurrent users."

---

## Step 3: API Design (5 minutes)

### REST Conventions We Follow

| Convention | Rule | Example |
|-----------|------|---------|
| Base path | `/api/v1/{resource}` | `/api/v1/habits` |
| Plural nouns | Always plural | `/habits` not `/habit` |
| HTTP methods | GET=read, POST=create, PUT=update, DELETE=remove | `PUT /habits/:id` |
| Status codes | 200 OK, 201 Created, 401 Unauthorized, 404 Not Found, 422 Validation, 429 Rate Limit | |
| Error format | `{"error_code": "...", "message": "...", "detail": null}` | Consistent across ALL endpoints |
| Auth | Bearer token in Authorization header | `Authorization: Bearer eyJ...` |
| IDs | UUID v4 (not auto-increment) | Safe to expose, no info leakage |

### Endpoint Summary (38 endpoints across 7 modules)

```
Auth:          6 endpoints  (signup, login, refresh, logout, GET/PUT profile)
Habits:        6 endpoints  (CRUD + reorder)
Logs:          5 endpoints  (single, bulk, query, update, delete)
Analytics:     6 endpoints  (dashboard, streaks, weekly, monthly, completion, correlations)
AI:            9 endpoints  (chat, stream, history, documents×3, insights×2, report)
Notifications: 3 endpoints  (GET/PUT settings, test email)
Export:        2 endpoints  (CSV download, S3 upload)
Health:        1 endpoint   (load balancer health check)
TOTAL:         38 endpoints
```

---

## Step 4: Data Model (5 minutes)

### Entity Identification

| Entity | What It Represents | Key Fields |
|--------|-------------------|------------|
| **User** | A registered person | email, password_hash, timezone |
| **Habit** | A trackable behavior | name, type (numeric/boolean/scale), target |
| **HabitLog** | One day's value for one habit | habit_id, log_date, value, notes |
| **Document** | Uploaded health PDF/text | filename, status, chunk_count |
| **DocumentChunk** | A piece of a document with embedding | chunk_text, embedding vector(768) |
| **AiChatMessage** | One message in AI conversation | role (user/assistant), content |
| **AiInsight** | Saved AI-generated report | type, title, content |
| **NotificationSettings** | User's email preferences | daily_reminder, weekly_report |

### Relationships

```
User (1) ──── (N) Habit
User (1) ──── (N) HabitLog
Habit (1) ─── (N) HabitLog
User (1) ──── (N) Document
Document (1) ─ (N) DocumentChunk
User (1) ──── (N) AiChatMessage
User (1) ──── (N) AiInsight
User (1) ──── (1) NotificationSettings
```

### Key Constraints

```
UNIQUE(user_id, habit_id, log_date)  → One log per habit per day
UNIQUE(notification_settings.user_id) → One settings row per user
INDEX(habits.user_id, is_archived)    → Fast "get active habits" query
INDEX(habit_logs.user_id, log_date)   → Fast "get today's logs" query
INDEX(document_chunks.embedding)      → IVFFlat for vector search
```

---

## Step 5: High-Level Design (10 minutes)

*(Covered in detail in [Phase 2 — HLD](./phase2-part01-high-level-design.md))*

```
Browser → Nginx → FastAPI (7 modules) → PostgreSQL + Redis + Ollama
                                      → S3/MinIO (files)
                                      → Lambda (6 serverless functions)
```

---

## Step 6: Deep Dives (10 minutes)

Pick 2-3 of these to explain in depth during an interview:

| Deep Dive | Interesting Because |
|-----------|-------------------|
| **JWT Auth Flow** | Two-token pattern, blacklist in Redis, refresh without re-login |
| **Streak Calculation** | Gaps-and-islands SQL with window functions |
| **Cache-Aside** | Redis TTL, invalidation on writes, fail-open on Redis down |
| **Rate Limiting** | Sliding window in Redis, different limits per endpoint type |
| **RAG Pipeline** | PDF → chunk → embed → pgvector → retrieve → cite |
| **ReAct Agent** | Think → act → observe loop with 5 custom tools |
| **Agentic Workflow** | 3-step pipeline with orchestrator, retry, fallback |

---

## Step 7: Trade-offs (5 minutes)

| Decision | Chose | Over | Because |
|----------|-------|------|---------|
| Architecture | Modular monolith | Microservices | Single team, shared DB |
| Database | PostgreSQL + pgvector | PG + Pinecone | One DB, free, transactional |
| Cache strategy | Cache-aside (Redis) | Read-through | Simpler, explicit control |
| LLM providers | 3 behind Strategy pattern | Hardcoded one | Free dev, free staging, paid prod |
| Auth | JWT (stateless) | Sessions (stateful) | Scales horizontally, no session store |
| Habit delete | Soft delete (is_archived) | Hard delete | Preserves analytics data |
| Log values | 3 typed columns | Single JSONB | Type safety at DB level |
| Background jobs | Celery + Lambda | Just one | Celery for dev, Lambda for production |

---

## 🎤 Interview Q&A

### Q: "Design a health habit tracking application" (the full interview)

**Your 40-minute answer structure:**

> **(0-2 min) Clarify:** "How many users? Read or write heavy? Real-time needed? What devices?"
>
> **(2-5 min) Estimates:** "1,000 users, 200 DAU, ~3 KB/day/user, 10 RPS peak. Single server is sufficient."
>
> **(5-10 min) API Design:** "38 endpoints across 7 modules. REST with /api/v1/ prefix. JWT auth. Consistent error format."
>
> **(10-15 min) Data Model:** "8 tables. Key constraint: UNIQUE(user_id, habit_id, log_date). UUID primary keys. pgvector for AI embeddings."
>
> **(15-25 min) HLD:** [draw the architecture diagram] "Modular monolith. 7 modules. Each has Router → Service → Repository layers. PostgreSQL + Redis + Ollama."
>
> **(25-35 min) Deep Dives:** "Let me deep dive into two areas: First, the streak calculation uses a gaps-and-islands SQL algorithm with ROW_NUMBER window function... Second, the AI agent uses the ReAct pattern — it thinks about what data it needs, calls tools to query the database, and iterates up to 5 times..."
>
> **(35-40 min) Trade-offs:** "I chose a modular monolith because... I chose pgvector over Pinecone because... I chose JWT over sessions because..."

### Q: "How would you scale this to 1 million users?"

> "Three changes: First, horizontally scale FastAPI behind an ALB — it's stateless (JWT auth), so any server can handle any request. Second, add PostgreSQL read replicas for analytics queries (which are read-heavy), keeping writes on the primary. Third, extract the AI module into a separate service with its own scaling policy — AI requests are 100x more expensive than CRUD operations. The modular monolith design makes extraction straightforward — replace service calls with HTTP calls."

### Q: "What would you do differently if starting over?"

> "Two things: First, I'd use an async task queue from day one instead of adding it later — some operations like document processing are inherently async. Second, I'd add structured logging from the start — debugging without request IDs across services is painful. I did add both, but they would have been easier if planned from the beginning."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Phase 0 Part 05 — AI Concepts](./phase0-part05-ai-concepts-from-zero.md) | | [Phase 2 — High-Level Design](./phase2-part01-high-level-design.md) |
