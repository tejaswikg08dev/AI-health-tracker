# ☁️ Phase 4 Part 15: AWS Lambda Functions — Overview & Roadmap

> **"Lambda handles what the API shouldn't: daily reminders at 8 AM, weekly AI reports on Sunday, streak milestone celebrations, CSV exports that take 30 seconds, document processing with embeddings, and monthly data cleanup. Serverless means $0 when idle, auto-scales when busy, and each function is isolated — one failure doesn't affect the others."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 15 (AWS Lambda Functions — Overview) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Release** | Release 4.3 — Serverless Scheduled Tasks |
| **Previous** | [phase4-part14c-export-connections-and-flows.md](./phase4-part14c-export-connections-and-flows.md) |
| **Next** | [phase4-part15a-lambda-shared-sam-template.md](./phase4-part15a-lambda-shared-sam-template.md) |
| **Lambda Functions** | 6 |
| **Shared Utilities** | 4 files (config, db, email, S3) |
| **Infrastructure** | SAM template (template.yaml) — IaC for all Lambdas + SQS + S3 |
| **Sub-Parts** | 4 documents (15a shared/SAM, 15b scheduled, 15c event-driven, 15d flows) |
| **Difficulty** | Medium-Hard (Lambda lifecycle, SAM template, SQS triggers, S3 events, sync DB in serverless) |

---

## 📖 Table of Contents

1. [What Are Lambda Functions?](#what-is-lambda)
2. [The 6 Lambda Functions](#six-functions)
3. [Three Trigger Types](#triggers)
4. [Lambda vs Celery — Why Lambda?](#lambda-vs-celery)
5. [File Structure](#file-structure)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Design Decisions](#design-decisions)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="what-is-lambda"></a>
## 1. What Are Lambda Functions?

**AWS Lambda** runs your code without managing servers. You write a function, define a trigger, and AWS handles everything: scaling, availability, patching, monitoring.

### Real-World Analogy

Think of a **taxi vs owning a car**:
- **Owning a car (server/Celery):** You pay for the car even when parked. Insurance, maintenance, parking — all ongoing costs. Always available, but expensive.
- **Taxi (Lambda):** You pay ONLY when riding. No car, no maintenance, no parking. Call when needed, pay per trip.

For tasks that run a few times a day (reminders, reports), Lambda is the taxi — vastly cheaper than keeping a server running 24/7.

### Lambda Lifecycle

```
COLD START (first invocation or after idle):
  1. AWS downloads your code package
  2. Creates a new container
  3. Initializes Python runtime + imports
  4. Runs your handler function
  Time: ~500ms-2s (one-time penalty)

WARM START (subsequent invocations within ~15 min):
  1. Reuses existing container
  2. Runs your handler function directly
  Time: ~10-50ms (no init overhead)

  Global variables (like DB connections) persist across warm starts.
  This is WHY we reuse the DB connection in db_utils.py.
```

### Free Tier

| Resource | Free Tier | Our Usage |
|----------|-----------|-----------|
| Requests | 1,000,000/month | ~5,000 (6 functions × ~25 invocations/day) |
| Compute | 400,000 GB-seconds | ~2,000 GB-seconds |
| Cost | **$0** | **$0** (well within free tier) |

---

<a name="six-functions"></a>
## 2. The 6 Lambda Functions

| # | Function | Trigger | Schedule/Event | What It Does |
|---|----------|---------|---------------|-------------|
| 1 | `daily_reminder` | EventBridge (cron) | Daily 8 AM UTC | Email users who haven't logged today |
| 2 | `weekly_report` | EventBridge (cron) | Sunday 9 AM UTC | Generate AI weekly report for each user |
| 3 | `csv_export` | SQS | On-demand (API sends message) | Generate large CSV, upload to S3, email link |
| 4 | `streak_milestone` | SQS | After each log creation | Check if streak hit 7/14/30/60/90/365 days |
| 5 | `data_cleanup` | EventBridge (cron) | 1st of each month | Delete expired tokens, old chat messages |
| 6 | `document_processor` | S3 event | On file upload | Extract text, chunk, embed, store in pgvector |

### Why These 6 (Not More, Not Fewer)

Each function maps to a **specific background need** that the API can't handle:

| Need | Why Not API? | Lambda Solution |
|------|-------------|----------------|
| Daily reminders | API doesn't have a scheduler | Cron trigger at 8 AM |
| Weekly reports | Takes 10-30s per user × 50 users = too long | Lambda runs up to 15 min |
| CSV export | Large exports take >60s (API timeout) | Lambda processes async |
| Streak check | Must run after EVERY log (event-driven) | SQS → Lambda (decoupled) |
| Data cleanup | Maintenance task, no user interaction | Monthly cron |
| Document processing | PDF → embed pipeline takes 30s+ | S3 upload → Lambda trigger |

---

<a name="triggers"></a>
## 3. Three Trigger Types

### Type 1: EventBridge Schedule (Cron)

```
"Run this Lambda every day at 8 AM UTC"
"Run this Lambda every Sunday at 9 AM"
"Run this Lambda on the 1st of every month"

SAM template:
  Events:
    Schedule:
      Type: Schedule
      Properties:
        Schedule: cron(0 8 * * ? *)   ← 8 AM UTC daily
```

**Cron syntax:** `cron(minutes hours day-of-month month day-of-week year)`
- `cron(0 8 * * ? *)` = at minute 0, hour 8, every day, every month, any day-of-week
- `cron(0 9 ? * SUN *)` = at 9:00, any day-of-month, every month, Sundays only

### Type 2: SQS Queue (Event-Driven)

```
"Run this Lambda when a message arrives in the queue"

Flow: FastAPI creates log → sends SQS message → Lambda picks it up → processes

SAM template:
  Events:
    SQSEvent:
      Type: SQS
      Properties:
        Queue: !GetAtt StreakQueue.Arn
        BatchSize: 1
```

**Why SQS (not direct Lambda invoke)?**
- **Decoupling:** The API doesn't wait for the Lambda. It sends a message and returns immediately
- **Retry:** If Lambda fails, SQS retries the message automatically
- **Buffering:** Spikes in log creation → messages queue up → Lambda processes at its own pace

### Type 3: S3 Event

```
"Run this Lambda when a file is uploaded to the documents/ prefix in S3"

SAM template:
  Events:
    S3Upload:
      Type: S3
      Properties:
        Bucket: !Ref DocumentsBucket
        Events: s3:ObjectCreated:*
        Filter:
          S3Key:
            Rules:
              - Name: prefix
                Value: documents/
```

When a user uploads a PDF via `POST /ai/documents`, the API saves the file to S3. S3 triggers the `document_processor` Lambda automatically. The Lambda extracts text, chunks it, generates embeddings, and stores in pgvector.

---

<a name="lambda-vs-celery"></a>
## 4. Lambda vs Celery — Why Lambda?

| Feature | Celery | Lambda |
|---------|--------|--------|
| **Idle cost** | Worker process running 24/7 (~$15-50/month) | **$0 when idle** |
| **Scheduling** | Celery Beat (another process to manage) | **Built-in (EventBridge)** |
| **Scaling** | Manual (add workers) | **Automatic (up to 1000 concurrent)** |
| **Isolation** | Shared worker process | **Each function isolated** |
| **Failure blast radius** | Worker crash → all tasks affected | **One function fails → others unaffected** |
| **Setup complexity** | Redis/RabbitMQ broker + worker + beat | **SAM template → `sam deploy`** |
| **Cold start** | None (always running) | **~1-2s first invocation** |
| **Max duration** | Unlimited | **15 minutes** |
| **Best for** | High-frequency, low-latency tasks | **Scheduled/event-driven, cost-sensitive** |

**For our use case (6 tasks, each runs 1-50 times/day):**
- Lambda: $0/month, zero maintenance
- Celery: $15-50/month (worker + beat + Redis broker), ongoing management

Lambda is the clear winner for low-frequency scheduled tasks.

---

<a name="file-structure"></a>
## 5. File Structure

```
health-tracker/lambda_functions/
├── template.yaml              ← SAM template: all 6 Lambdas + SQS + S3 (IaC)
├── shared/                    ← Shared utilities across all functions
│   ├── __init__.py
│   ├── config.py              ← Environment variables (DATABASE_URL, S3_BUCKET, etc.)
│   ├── db_utils.py            ← Sync PostgreSQL (psycopg2, connection reuse)
│   ├── email_utils.py         ← SES email sending
│   └── s3_utils.py            ← S3 upload, download, presigned URLs
├── 01_daily_reminder/
│   └── handler.py             ← Lambda 1: daily email reminders
├── 02_weekly_report/
│   └── handler.py             ← Lambda 2: AI weekly report generation
├── 03_csv_export/
│   └── handler.py             ← Lambda 3: CSV export to S3
├── 04_streak_milestone/
│   └── handler.py             ← Lambda 4: streak milestone checker
├── 05_data_cleanup/
│   └── handler.py             ← Lambda 5: monthly data cleanup
├── 06_document_processor/
│   └── handler.py             ← Lambda 6: PDF → RAG pipeline
└── events/                    ← Test event JSON files (for sam local invoke)
    ├── daily.json
    ├── weekly.json
    └── streak.json
```

### Build Order

| # | File(s) | Why This Order |
|---|---------|---------------|
| 1 | `shared/config.py` | All functions read environment variables |
| 2 | `shared/db_utils.py` | Database queries used by 5 of 6 functions |
| 3 | `shared/email_utils.py` | Email sending used by 4 of 6 functions |
| 4 | `shared/s3_utils.py` | S3 operations used by 3 of 6 functions |
| 5 | `template.yaml` | Defines all 6 functions + infrastructure |
| 6 | `01_daily_reminder/handler.py` through `06_*/handler.py` | One handler per function |

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 15a: Shared Utilities & SAM Template

```
📄 phase4-part15a-lambda-shared-sam-template.md
├── shared/config.py    — Environment variable access
├── shared/db_utils.py  — Sync PostgreSQL with connection reuse for warm starts
├── shared/email_utils.py — SES email sending
├── shared/s3_utils.py  — S3 upload/download/presigned URLs
└── template.yaml       — SAM: 6 functions + 2 SQS queues + 1 S3 bucket

KEY CONCEPTS: Lambda warm start connection reuse, psycopg2 (sync), SAM globals, cron syntax
TIME: ~45 minutes
```

### Part 15b: Scheduled Functions (3 Lambdas)

```
📄 phase4-part15b-lambda-scheduled-functions.md
├── 01_daily_reminder/handler.py  — SQL: find users not logged today → send email
├── 02_weekly_report/handler.py   — Gather data → Groq LLM → HTML report → S3 → email
└── 05_data_cleanup/handler.py    — Delete expired tokens, old messages

KEY CONCEPTS: Gaps-and-islands SQL in Lambda, Groq API (free LLM), batch email sending
TIME: ~45 minutes
```

### Part 15c: Event-Driven Functions (3 Lambdas)

```
📄 phase4-part15c-lambda-event-driven-functions.md
├── 03_csv_export/handler.py        — SQS trigger → CSV → S3 → presigned URL → email
├── 04_streak_milestone/handler.py  — SQS trigger → calculate streak → check milestone → email
└── 06_document_processor/handler.py — S3 trigger → extract → chunk → embed → pgvector

KEY CONCEPTS: SQS message parsing, idempotent milestone checking, S3 event structure
TIME: ~45 minutes
```

### Part 15d: Connections & Flows

```
📄 phase4-part15d-lambda-connections-and-flows.md
├── Daily timeline: all 6 Lambdas mapped to their trigger times
├── End-to-end: user logs habit → SQS → streak Lambda → milestone email
├── End-to-end: user uploads PDF → S3 → document processor → pgvector
├── SAM deployment flow: sam build → sam deploy → CloudFormation
└── Module summary

TIME: ~20 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAMBDA ARCHITECTURE                               │
│                                                                          │
│  TRIGGERS:                                                               │
│  ┌───────────────────┐ ┌───────────────┐ ┌────────────────────────────┐│
│  │  EventBridge      │ │  SQS Queues   │ │  S3 Events                 ││
│  │  (cron schedules) │ │  (messages)    │ │  (file uploads)            ││
│  │                   │ │               │ │                            ││
│  │  8 AM daily ──────│ │  export-queue │ │  s3:ObjectCreated:*        ││
│  │  Sun 9 AM ────────│ │  streak-queue │ │  prefix: documents/        ││
│  │  1st monthly ─────│ │               │ │                            ││
│  └────────┬──────────┘ └──────┬────────┘ └──────────┬─────────────────┘│
│           │                   │                      │                   │
│           ▼                   ▼                      ▼                   │
│  ┌────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐  │
│  │ 01_daily_      │ │ 03_csv_export    │ │ 06_document_processor    │  │
│  │ reminder       │ │ 04_streak_       │ │                          │  │
│  │ 02_weekly_     │ │ milestone        │ │ PDF → text → chunks →    │  │
│  │ report         │ │                  │ │ embed → pgvector         │  │
│  │ 05_data_       │ │ SQS → process   │ │                          │  │
│  │ cleanup        │ │ → email/S3       │ │ S3 event → Lambda        │  │
│  └────────┬───────┘ └──────┬───────────┘ └──────────┬───────────────┘  │
│           │                │                         │                   │
│           ▼                ▼                         ▼                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  SHARED UTILITIES                                                │   │
│  │  config.py → env vars   db_utils.py → psycopg2 (sync, reused)  │   │
│  │  email_utils.py → SES   s3_utils.py → boto3 S3                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│           │                │                         │                   │
│           ▼                ▼                         ▼                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐   │
│  │ PostgreSQL    │  │ AWS SES      │  │ S3                          │   │
│  │ (RDS)        │  │ (email)      │  │ (exports + documents)       │   │
│  └──────────────┘  └──────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘

DEPLOYED VIA: SAM (template.yaml → CloudFormation → AWS resources)
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Lambda handler** | `lambda_handler(event, context)` — entry point for every function | All handler.py files |
| 2 | **Cold start vs warm start** | First invocation slower; subsequent reuse the container | All functions |
| 3 | **Connection reuse** | Global `_connection` variable survives warm starts | db_utils.py |
| 4 | **psycopg2 (sync)** | Synchronous PostgreSQL driver (Lambda doesn't need async) | db_utils.py |
| 5 | **RealDictCursor** | psycopg2 returns rows as dicts (not tuples) | db_utils.py |
| 6 | **SAM template** | Infrastructure-as-code for Lambda + triggers + queues | template.yaml |
| 7 | **EventBridge cron** | Schedule triggers using cron expressions | template.yaml |
| 8 | **SQS trigger** | Lambda auto-invoked when message arrives in queue | template.yaml |
| 9 | **S3 event trigger** | Lambda invoked when file uploaded to S3 bucket | template.yaml |
| 10 | **Groq API (free LLM)** | Lambda calls Groq for AI report generation ($0) | weekly_report handler |
| 11 | **Idempotent processing** | Check "already sent this milestone?" before sending | streak handler |
| 12 | **`sam build && sam deploy`** | Build + deploy all Lambdas in one command | Deployment |

---

<a name="design-decisions"></a>
## 9. Design Decisions

### Decision 1: Lambda over Celery

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Background Task Infrastructure                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: AWS Lambda for all 6 scheduled/event-driven tasks          │
│                                                                     │
│  WHY:                                                               │
│  • $0 idle cost — Lambda runs only when triggered                   │
│  • Built-in scheduling — EventBridge cron, no Celery Beat needed    │
│  • Isolated — one function failure doesn't affect others            │
│  • Auto-scaling — 1000 concurrent invocations if needed             │
│  • SAM deployment — one command deploys everything                  │
│  • Free tier — 1M requests + 400K GB-seconds/month                  │
│                                                                     │
│  WHY NOT CELERY:                                                    │
│  • Celery needs: Redis/RabbitMQ broker + worker process + beat      │
│  • Idle cost: $15-50/month for always-running worker                │
│  • Failure blast: worker crash → all tasks stop                     │
│  • For 6 tasks running 1-50 times/day, Celery is overkill          │
│                                                                     │
│  WHEN CELERY IS BETTER:                                             │
│  • Tasks triggered thousands of times per second (low latency)      │
│  • Tasks needing sub-second response time (Lambda cold start ~1s)   │
│  • Tasks with heavy state sharing between invocations               │
│                                                                     │
│  INTERVIEW TIP: "We chose Lambda because our 6 tasks are low-      │
│  frequency (daily/weekly). Lambda costs $0 idle with built-in       │
│  scheduling. Celery would add a broker + worker + beat for $15-50/  │
│  month with no benefit for our workload."                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Sync psycopg2 (Not Async asyncpg)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Lambda Database Driver                            │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: psycopg2 (synchronous) — not asyncpg (async)               │
│                                                                     │
│  WHY:                                                               │
│  • Lambda runs ONE request at a time — async provides zero benefit  │
│  • psycopg2 is the most stable PostgreSQL driver for Python         │
│  • Simpler code: no `async/await`, no event loop management         │
│  • Same driver Alembic uses (Part 04e) — proven reliable            │
│                                                                     │
│  CONTRAST WITH FASTAPI:                                             │
│  FastAPI handles 100+ concurrent requests → async is essential      │
│  Lambda handles 1 request at a time → sync is simpler + sufficient  │
│                                                                     │
│  CONNECTION REUSE:                                                  │
│  `_connection` is a global variable → survives across warm starts   │
│  First invocation: create connection (~50ms)                        │
│  Subsequent invocations: reuse connection (~1ms)                    │
│                                                                     │
│  INTERVIEW TIP: "Lambda processes one invocation at a time, so      │
│  async provides no concurrency benefit. We use psycopg2 (sync)     │
│  with a global connection that's reused across warm starts."        │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: SQS for Event-Driven (Not Direct Invoke)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Event-Driven Lambda Trigger                       │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: SQS queue between API and Lambda                           │
│                                                                     │
│  WHY:                                                               │
│  • Decoupled — API sends message and returns immediately            │
│  • Reliable — SQS retries if Lambda fails (up to 3 times)          │
│  • Buffered — spikes in log creation don't overwhelm Lambda         │
│  • Visible — monitor queue depth in CloudWatch                      │
│                                                                     │
│  ALTERNATIVES:                                                      │
│  1. Direct Lambda invoke from API                                   │
│     ❌ API waits for Lambda response → slower                      │
│     ❌ No retry on Lambda failure                                  │
│  2. EventBridge events                                              │
│     ⚠️ Works but SQS is simpler for point-to-point messaging      │
│                                                                     │
│  INTERVIEW TIP: "SQS decouples the API from the Lambda. The API    │
│  sends a message and returns instantly. SQS handles retry if Lambda │
│  fails. This prevents the API from being affected by Lambda latency │
│  or failures."                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: Why Lambda instead of Celery for background tasks?
**A:** "Cost and simplicity. Our 6 tasks run 1-50 times per day — low frequency. Lambda costs $0 idle (pay only when running) with built-in scheduling via EventBridge. Celery would require a Redis broker, a worker process, and Celery Beat — $15-50/month for always-running infrastructure. Each Lambda function is isolated: if the streak checker fails, daily reminders still work. For high-frequency, low-latency tasks (thousands per second), Celery is better. For our workload, Lambda is the clear choice."

### Q2: How do you handle database connections in Lambda?
**A:** "Global connection reuse. The `_connection` variable in `db_utils.py` is created on the first invocation and persists across warm starts (Lambda keeps the container alive for ~15 minutes between invocations). First call: ~50ms to connect. Subsequent calls: ~1ms to reuse. We use psycopg2 (synchronous) because Lambda processes one request at a time — async provides no concurrency benefit."

### Q3: What is a SAM template and how does deployment work?
**A:** "SAM (Serverless Application Model) is AWS's framework for defining Lambda functions as infrastructure-as-code. Our `template.yaml` defines all 6 functions, their triggers (EventBridge cron, SQS, S3), memory/timeout settings, and shared environment variables. Deployment: `sam build` packages the code, `sam deploy` creates/updates a CloudFormation stack that provisions all resources. One command → 6 functions + 2 SQS queues + 1 S3 bucket."

### Q4: How does the streak milestone Lambda avoid sending duplicate emails?
**A:** "Idempotency check. After calculating the current streak (using the same gaps-and-islands SQL from Part 07b), we check if this milestone was already recorded: `SELECT 1 FROM ai_insights WHERE insight_type='streak_milestone' AND title LIKE '%Water%30%'`. If the record exists, we skip. If not, we INSERT the milestone record AND send the email. The database record prevents duplicates even if the SQS message is delivered twice (at-least-once delivery)."

### Q5: How does the document processor Lambda connect to the RAG pipeline?
**A:** "When a user uploads a PDF via the API, the file is saved to S3 in the `documents/` prefix. S3 triggers the `document_processor` Lambda automatically. The Lambda downloads the file from S3, extracts text (PyPDF2), splits into chunks (same algorithm as Part 09a), calls the Groq API for embeddings (free, used because Lambda can't run Ollama locally), and stores chunks with embeddings in the pgvector `document_chunks` table. The document status is updated from 'processing' to 'processed'."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 14c: Export Connections & Flows](./phase4-part14c-export-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 15a: Shared Utilities & SAM Template](./phase4-part15a-lambda-shared-sam-template.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Lambda Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 15a | [Shared + SAM](./phase4-part15a-lambda-shared-sam-template.md) | 4 shared files + template.yaml (full source) |
| 15b | [Scheduled Functions](./phase4-part15b-lambda-scheduled-functions.md) | Lambdas 1, 2, 5 — cron-triggered handlers |
| 15c | [Event-Driven Functions](./phase4-part15c-lambda-event-driven-functions.md) | Lambdas 3, 4, 6 — SQS + S3 triggered |
| 15d | [Connections & Flows](./phase4-part15d-lambda-connections-and-flows.md) | Timeline, end-to-end flows, deployment |

---

**End of Phase 4 Part 15: Lambda Functions Overview**

*6 functions, 3 trigger types, $0 idle cost. Lambda handles what the API shouldn't: scheduled emails, AI reports, streak checks, CSV exports, document processing, and cleanup. Next: the shared utilities and SAM template that power all 6 functions.*
