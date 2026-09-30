# 📚 Documentation Plan — Health Tracker

## Complete release-wise documentation structure, naming conventions, templates, and file list.

---

## 1. Naming Convention

### Pattern
```
phase{N}-part{NN}{letter}-{kebab-case-description}.md
```

### Rules
| Part | Rule | Example |
|------|------|---------|
| `phase{N}` | Phase number (0-10) | `phase0`, `phase4`, `phase8` |
| `part{NN}` | Two-digit part number within phase | `part01`, `part14`, `part08` |
| `{letter}` | Sub-part letter (a-z) for files within a module | `part04a`, `part04b`, `part04c` |
| `{description}` | Kebab-case, describes the file/concept | `auth-models`, `rag-chunker` |
| Extension | Always `.md` | |

### Examples
```
phase0-part01-project-overview.md
phase4-part04a-auth-models.md
phase4-part04b-auth-exceptions.md
phase4-part04c-auth-schemas.md
phase4-part04d-auth-security.md
phase4-part04e-auth-repository.md
phase4-part04f-auth-service.md
phase4-part04g-auth-router.md
phase4-part04h-auth-connections-and-flows.md
phase4-part10a-ai-llm-base-client.md
phase4-part10g-ai-rag-chunker.md
phase4-part10m-ai-agent-base.md
phase6-part01-dockerfile-backend.md
```

---

## 2. Document Template (Header + Footer)

Every document follows this EXACT structure:

```markdown
# Phase {N} — Part {NN}{letter}: {Title}

| Field | Value |
|-------|-------|
| **Phase** | {N} — {Phase Name} |
| **Part** | {NN}{letter} |
| **Sprint** | Sprint {X} — {Sprint Name} |
| **Release** | Release {X.Y} — {Release Name} |
| **File** | `{relative/path/to/file}` |
| **Depends On** | Part {prev_part} ({prev_title}) |
| **Next** | Part {next_part} ({next_title}) |
| **Difficulty** | 🟢 Easy / 🟡 Medium / 🟠 Hard / 🔴 Very Hard |
| **Time to Type** | ~{N} minutes |
| **Lines of Code** | ~{N} lines |

---

## What is {Concept}? Read This First

{2-3 paragraphs explaining the concept with real-world analogies.
Written for someone who has never seen this pattern/technology before.
Explain WHY before HOW.}

**Real-world analogy:**
{Simple analogy that makes the concept click}

---

## Architecture: Where This File Fits

```
{ASCII diagram showing this file's position in the architecture}
```

---

## Source Code — Line by Line

> 📁 **File:** `{path/to/file}`
> 📏 **Lines:** {N}
> ⏱️ **Type time:** ~{N} minutes

### Section 1: {Section name}

```python
{EXACT code from the real file — character for character}
```

**Line-by-line explanation:**
- **Line 1-3:** {What these imports do and why}
- **Line 5:** {What this variable/class does}
- ...

{Continue for every section of the file}

---

## How This Connects

```
{ASCII diagram showing data flow through this component}

Example:
  Router (HTTP) → Service (logic) → Repository (SQL) → PostgreSQL
                                                ↓
                                          [THIS FILE]
```

**Incoming:** {What calls this file and why}
**Outgoing:** {What this file calls and why}

---

## What You Learned

| # | Concept | One-Sentence Summary |
|---|---------|---------------------|
| 1 | {concept} | {summary} |
| 2 | {concept} | {summary} |
| 3 | {concept} | {summary} |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `{error message}` | {why it happens} | {how to fix} |
| `{error message}` | {why it happens} | {how to fix} |

---

## Try It Yourself

{Verification steps — commands to run, URLs to visit, expected output}

```bash
{exact commands}
```

Expected output:
```json
{expected response}
```

---

## Interview Question

> **Q:** "{A question an interviewer might ask about this concept}"
>
> **Your answer:** "{How you'd explain it, referencing what you built}"

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part {prev}](./{prev_filename}) | | [Part {next}](./{next_filename}) |
```

---

## 3. Complete File List (115 Documents)

### Phase 0 — Project Overview & Setup (5 docs)

| # | Filename | Title | Sprint | Source File |
|---|----------|-------|--------|-------------|
| 1 | `phase0-part01-project-overview.md` | Project Overview — What We're Building | — | — |
| 2 | `phase0-part02-architecture-overview.md` | Architecture — How It All Fits Together | — | — |
| 3 | `phase0-part03-tech-stack-explained.md` | Tech Stack — Every Technology Explained | — | — |
| 4 | `phase0-part04-environment-setup.md` | Setup — Python, Docker, Node.js, Ollama | — | — |
| 5 | `phase0-part05-ai-concepts-from-zero.md` | AI Concepts — LLM, RAG, Agents, Embeddings | — | — |

### Phase 1-3 — System Design (4 docs)

| # | Filename | Title | Sprint | Source File |
|---|----------|-------|--------|-------------|
| 6 | `phase1-part01-system-design-overview.md` | System Design — Requirements & Constraints | — | — |
| 7 | `phase2-part01-high-level-design.md` | HLD — Components, Data Flows, Scaling | — | `docs/architecture/HLD.md` |
| 8 | `phase3-part01-low-level-design.md` | LLD — Algorithms, Class Diagrams, Sequences | — | `docs/architecture/LLD.md` |
| 9 | `phase3-part02-database-design.md` | Database — ER Diagram, Indexes, Decisions | — | `docs/architecture/database-design.md` |

### Phase 4 — Implementation (88 docs) ← This is 80% of the docs

#### Release 1.0: Project Skeleton (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 10 | `phase4-part01a-env-example.md` | Environment Variables — Secrets Management | `.env.example` |
| 11 | `phase4-part01b-gitignore.md` | Git Ignore — What Never Gets Committed | `.gitignore` |
| 12 | `phase4-part01c-docker-compose.md` | Docker Compose — 7 Services Orchestrated | `docker-compose.yml` |
| 13 | `phase4-part01d-docker-compose-dev.md` | Dev Override — Hot Reload, Debug Mode | `docker-compose.dev.yml` |
| 14 | `phase4-part01e-makefile.md` | Makefile — Shortcut Commands | `Makefile` |

#### Release 1.1: FastAPI Foundation (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 15 | `phase4-part02a-requirements.md` | Dependencies — Every Package Explained | `backend/requirements.txt` |
| 16 | `phase4-part02b-pyproject-toml.md` | Tool Config — Ruff, MyPy, Pytest | `backend/pyproject.toml` |
| 17 | `phase4-part02c-dockerfile-backend.md` | Backend Dockerfile — Multi-Stage Build | `backend/Dockerfile` |
| 18 | `phase4-part02d-config.md` | App Config — Pydantic Settings | `backend/app/config.py` |
| 19 | `phase4-part02e-database.md` | Database — Async SQLAlchemy Engine | `backend/app/database.py` |
| 20 | `phase4-part02f-redis-client.md` | Redis Client — Connection Pool | `backend/app/redis_client.py` |
| 21 | `phase4-part02g-dependencies.md` | FastAPI DI — Type Aliases | `backend/app/dependencies.py` |

#### Release 1.2: Shared Utilities (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 22 | `phase4-part03a-exceptions.md` | Error Hierarchy — 5 Types → HTTP Codes | `backend/app/shared/exceptions.py` |
| 23 | `phase4-part03b-base-schemas.md` | Base Schemas — Pagination, Error Response | `backend/app/shared/base_schemas.py` |
| 24 | `phase4-part03c-base-repository.md` | Generic CRUD — TypeVar, Generic[T] | `backend/app/shared/base_repository.py` |
| 25 | `phase4-part03d-date-utils.md` | Date Utilities — Timezone, Week/Month | `backend/app/shared/date_utils.py` |
| 26 | `phase4-part03e-logging.md` | Structured Logging — Structlog JSON | `backend/app/shared/logging.py` |

#### Release 1.3: Middleware (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 27 | `phase4-part03f-error-handler.md` | Error Handler — Exception → JSON | `backend/app/middleware/error_handler.py` |
| 28 | `phase4-part03g-logging-middleware.md` | Request Logger — Timing, Request ID | `backend/app/middleware/logging_middleware.py` |
| 29 | `phase4-part03h-rate-limiter.md` | Rate Limiter — Redis Sliding Window ⭐ | `backend/app/middleware/rate_limiter.py` |

#### Release 1.4: Auth Module (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 30 | `phase4-part04-auth-overview.md` | Auth Module — Overview & Architecture | — |
| 31 | `phase4-part04a-auth-models.md` | User Model — UUID, Bcrypt, Soft Delete | `backend/app/modules/auth/models.py` |
| 32 | `phase4-part04b-auth-exceptions.md` | Auth Errors — InvalidCredentials, TokenExpired | `backend/app/modules/auth/exceptions.py` |
| 33 | `phase4-part04c-auth-schemas.md` | Auth Schemas — UserCreate, TokenResponse | `backend/app/modules/auth/schemas.py` |
| 34 | `phase4-part04d-auth-security.md` | Security — Bcrypt + JWT Deep Dive ⭐ | `backend/app/modules/auth/security.py` |
| 35 | `phase4-part04e-auth-repository.md` | User Repository — Email Lookup, Exists | `backend/app/modules/auth/repository.py` |
| 36 | `phase4-part04f-auth-service.md` | Auth Service — Register, Login, Refresh ⭐ | `backend/app/modules/auth/service.py` |
| 37 | `phase4-part04g-auth-router.md` | Auth Router — 6 Endpoints | `backend/app/modules/auth/router.py` |
| 38 | `phase4-part04h-auth-connections-and-flows.md` | Auth — Connection Diagram & Complete Flows | — |

#### Release 1.5: Migration + Main (Sprint 1)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 39 | `phase4-part04i-alembic-setup.md` | Alembic — Migration Config | `backend/alembic.ini` + `alembic/env.py` |
| 40 | `phase4-part04j-migration-users.md` | Migration 001 — Users Table | `alembic/versions/001_create_users_table.py` |
| 41 | `phase4-part04k-main.md` | Main.py — App Factory, Lifespan ⭐ | `backend/app/main.py` |
| 42 | `phase4-part04l-nginx.md` | Nginx — Reverse Proxy, Rate Limiting | `nginx/default.conf` |

#### Release 2.0: Habits Module (Sprint 2)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 43 | `phase4-part05-habits-overview.md` | Habits Module — Overview & Architecture | — |
| 44 | `phase4-part05a-habits-models.md` | Habit Model — Types, Color, Sort Order | `modules/habits/models.py` |
| 45 | `phase4-part05b-habits-exceptions.md` | Habit Errors — NotFound, LimitExceeded | `modules/habits/exceptions.py` |
| 46 | `phase4-part05c-habits-schemas.md` | Habit Schemas — HabitType Enum, Validators | `modules/habits/schemas.py` |
| 47 | `phase4-part05d-habits-repository.md` | Habit Repository — Scoped Queries, Reorder | `modules/habits/repository.py` |
| 48 | `phase4-part05e-habits-service.md` | Habit Service — Limit 20, Duplicates | `modules/habits/service.py` |
| 49 | `phase4-part05f-habits-router.md` | Habit Router — 6 CRUD Endpoints | `modules/habits/router.py` |
| 50 | `phase4-part05g-habits-migration.md` | Migration 002 — Habits Table | `alembic/versions/002_...` |
| 51 | `phase4-part05h-habits-connections-and-flows.md` | Habits — Connection Diagram & Flows | — |

#### Release 2.1: Logs Module (Sprint 2)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 52 | `phase4-part06-logs-overview.md` | Logs Module — Overview & Architecture | — |
| 53 | `phase4-part06a-logs-models.md` | HabitLog — 3 Value Columns, UNIQUE | `modules/logs/models.py` |
| 54 | `phase4-part06b-logs-exceptions.md` | Log Errors — FutureDate, DuplicateLog | `modules/logs/exceptions.py` |
| 55 | `phase4-part06c-logs-schemas.md` | Log Schemas — BulkLogCreate, Types | `modules/logs/schemas.py` |
| 56 | `phase4-part06d-logs-repository.md` | Log Repository — Date Queries, Streaks | `modules/logs/repository.py` |
| 57 | `phase4-part06e-logs-service.md` | Log Service — Type Validation, Upsert ⭐ | `modules/logs/service.py` |
| 58 | `phase4-part06f-logs-router.md` | Log Router — Bulk, Filtered GET | `modules/logs/router.py` |
| 59 | `phase4-part06g-logs-migration.md` | Migration 003 — Habit Logs Table | `alembic/versions/003_...` |
| 60 | `phase4-part06h-logs-connections-and-flows.md` | Logs — Connection Diagram & Flows | — |

#### Release 2.2: Analytics Module (Sprint 2)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 61 | `phase4-part07-analytics-overview.md` | Analytics Module — Overview | — |
| 62 | `phase4-part07a-analytics-schemas.md` | Analytics Schemas — 12 Response Types | `modules/analytics/schemas.py` |
| 63 | `phase4-part07b-analytics-repository.md` | Analytics SQL — Window Functions, CTEs ⭐⭐ | `modules/analytics/repository.py` |
| 64 | `phase4-part07c-analytics-cache.md` | Redis Cache — Cache-Aside Pattern ⭐ | `modules/analytics/cache.py` |
| 65 | `phase4-part07d-analytics-service.md` | Analytics Service — Pearson Correlation ⭐ | `modules/analytics/service.py` |
| 66 | `phase4-part07e-analytics-router.md` | Analytics Router — 6 GET Endpoints | `modules/analytics/router.py` |
| 67 | `phase4-part07f-analytics-connections-and-flows.md` | Analytics — Connection Diagram & Flows | — |

#### Release 2.3: Seed Data (Sprint 2)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 68 | `phase4-part07g-seed-data.md` | Seed Script — Realistic Demo Data | `scripts/seed_data.py` |

#### Release 3.0: LLM Layer (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 69 | `phase4-part08-ai-overview.md` | AI Module — LLM + RAG + Agents + Workflows | — |
| 70 | `phase4-part08a-llm-base-client.md` | Abstract LLM Client — Strategy Pattern ⭐⭐ | `ai/llm/base_client.py` |
| 71 | `phase4-part08b-llm-ollama.md` | Ollama Client — Free Local AI | `ai/llm/ollama_client.py` |
| 72 | `phase4-part08c-llm-groq.md` | Groq Client — Free Cloud AI | `ai/llm/groq_client.py` |
| 73 | `phase4-part08d-llm-openai.md` | OpenAI Client — Production AI | `ai/llm/openai_client.py` |
| 74 | `phase4-part08e-llm-factory.md` | LLM Factory — Provider Swap via Config | `ai/llm/factory.py` |
| 75 | `phase4-part08f-prompt-templates.md` | Prompt Templates — Jinja2 Engineering | `ai/llm/prompt_templates.py` |
| 76 | `phase4-part08g-token-tracker.md` | Token Tracker — Redis Usage Limits | `ai/llm/token_tracker.py` |

#### Release 3.1: RAG Pipeline (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 77 | `phase4-part09-rag-overview.md` | RAG Overview — Why & How | — |
| 78 | `phase4-part09a-document-processor.md` | PDF Extraction — PyPDF2 | `ai/rag/document_processor.py` |
| 79 | `phase4-part09b-chunker.md` | Text Chunking — Recursive Splitting ⭐ | `ai/rag/chunker.py` |
| 80 | `phase4-part09c-embeddings.md` | Embeddings — Text → Vectors | `ai/rag/embeddings.py` |
| 81 | `phase4-part09d-vector-store.md` | pgvector — Cosine Similarity Search ⭐⭐ | `ai/rag/vector_store.py` |
| 82 | `phase4-part09e-retriever.md` | Retriever — Full RAG Pipeline | `ai/rag/retriever.py` |
| 83 | `phase4-part09f-rag-connections-and-flows.md` | RAG — End-to-End Flow Diagram | — |

#### Release 3.2: Agent Tools (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 84 | `phase4-part10-agents-overview.md` | Agents Overview — ReAct Pattern | — |
| 85 | `phase4-part10a-base-tool.md` | Base Tool — OpenAI Function Schema | `agents/tools/base_tool.py` |
| 86 | `phase4-part10b-tool-query-logs.md` | Query Logs Tool — Fetch Habit Data | `agents/tools/query_logs.py` |
| 87 | `phase4-part10c-tool-get-analytics.md` | Analytics Tool — Streaks, Summary | `agents/tools/get_analytics.py` |
| 88 | `phase4-part10d-tool-search-docs.md` | Search Docs Tool — RAG Integration | `agents/tools/search_docs.py` |
| 89 | `phase4-part10e-tool-correlate.md` | Correlate Tool — Pearson Math | `agents/tools/correlate.py` |
| 90 | `phase4-part10f-tool-create-plan.md` | Plan Tool — Improvement Template | `agents/tools/create_plan.py` |

#### Release 3.3: Agent + Memory (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 91 | `phase4-part10g-memory-short-term.md` | Short-Term Memory — Conversation Buffer | `agents/memory/short_term.py` |
| 92 | `phase4-part10h-memory-long-term.md` | Long-Term Memory — Redis Persistent | `agents/memory/long_term.py` |
| 93 | `phase4-part10i-base-agent.md` | Base Agent — ReAct Loop ⭐⭐⭐ | `agents/base_agent.py` |
| 94 | `phase4-part10j-health-coach.md` | Health Coach — Pre-Configured Agent ⭐ | `agents/health_coach.py` |
| 95 | `phase4-part10k-agent-connections-and-flows.md` | Agent — Complete Execution Trace | — |

#### Release 3.4: Agentic Workflow (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 96 | `phase4-part11-workflows-overview.md` | Agentic Workflows — Multi-Step Pipelines | — |
| 97 | `phase4-part11a-base-workflow.md` | Base Workflow — Pipeline Interface | `workflows/base_workflow.py` |
| 98 | `phase4-part11b-orchestrator.md` | Orchestrator — Retry + Fallback ⭐ | `workflows/orchestrator.py` |
| 99 | `phase4-part11c-data-collector.md` | Step 1 — Gather Week's Data | `weekly_report/data_collector.py` |
| 100 | `phase4-part11d-analyzer.md` | Step 2 — LLM Finds Patterns | `weekly_report/analyzer.py` |
| 101 | `phase4-part11e-report-writer.md` | Step 3 — LLM Writes Report | `weekly_report/report_writer.py` |
| 102 | `phase4-part11f-workflow-connections-and-flows.md` | Workflow — Pipeline Execution Diagram | — |

#### Release 3.5: AI Service + Router + Migration (Sprint 3)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 103 | `phase4-part12a-ai-models.md` | AI Models — 4 Tables + pgvector | `ai/models.py` |
| 104 | `phase4-part12b-ai-schemas.md` | AI Schemas — Chat, Documents, Insights | `ai/schemas.py` |
| 105 | `phase4-part12c-ai-service.md` | AI Service — Orchestrates Everything ⭐⭐ | `ai/service.py` |
| 106 | `phase4-part12d-ai-router.md` | AI Router — 9 Endpoints, SSE Streaming | `ai/router.py` |
| 107 | `phase4-part12e-ai-migration.md` | Migration 004 — AI Tables + pgvector Index | `alembic/versions/004_...` |
| 108 | `phase4-part12f-ai-complete-connections.md` | AI Module — Complete Architecture Diagram | — |

#### Release 4.0: Notifications Module (Sprint 4)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 109 | `phase4-part13-notifications-overview.md` | Notifications — Overview | — |
| 110 | `phase4-part13a-notifications-models.md` | Settings Model | `notifications/models.py` |
| 111 | `phase4-part13b-notifications-schemas.md` | Settings Schemas | `notifications/schemas.py` |
| 112 | `phase4-part13c-email-provider.md` | Email Provider — Strategy Pattern | `notifications/email_provider.py` |
| 113 | `phase4-part13d-notifications-service.md` | Notification Service + Templates | `notifications/service.py` |
| 114 | `phase4-part13e-celery-tasks.md` | Celery Tasks — Background Jobs | `notifications/tasks.py` + `tasks/celery_app.py` |
| 115 | `phase4-part13f-notifications-router.md` | Notifications Router — 3 Endpoints | `notifications/router.py` |
| 116 | `phase4-part13g-email-templates.md` | HTML Email Templates — Jinja2 | `notifications/templates/*.html` |
| 117 | `phase4-part13h-notification-migration.md` | Migration 005 | `alembic/versions/005_...` |

#### Release 4.1: Export Module (Sprint 4)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 118 | `phase4-part14-export-overview.md` | Export — Overview | — |
| 119 | `phase4-part14a-csv-generator.md` | CSV Generator — In-Memory io.StringIO | `export/csv_generator.py` |
| 120 | `phase4-part14b-pdf-generator.md` | PDF Generator — HTML Reports | `export/pdf_generator.py` |
| 121 | `phase4-part14c-storage.md` | S3/MinIO Storage — boto3 Abstraction ⭐ | `export/storage.py` |
| 122 | `phase4-part14d-export-service.md` | Export Service — Sync + S3 | `export/service.py` |
| 123 | `phase4-part14e-export-router.md` | Export Router — CSV Download, S3 URL | `export/router.py` |
| 124 | `phase4-part14f-export-connections-and-flows.md` | Export — Flow Diagram | — |

#### Release 4.2: Lambda Functions (Sprint 4)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 125 | `phase4-part15-lambda-overview.md` | Lambda — Serverless Overview | — |
| 126 | `phase4-part15a-lambda-shared.md` | Shared Utils — DB, Email, S3 | `lambda_functions/shared/` |
| 127 | `phase4-part15b-sam-template.md` | SAM Template — Infrastructure as Code | `lambda_functions/template.yaml` |
| 128 | `phase4-part15c-lambda-daily-reminder.md` | Lambda 1 — Daily Reminder | `01_daily_reminder/handler.py` |
| 129 | `phase4-part15d-lambda-weekly-report.md` | Lambda 2 — AI Weekly Report | `02_weekly_report/handler.py` |
| 130 | `phase4-part15e-lambda-csv-export.md` | Lambda 3 — Async CSV Export | `03_csv_export/handler.py` |
| 131 | `phase4-part15f-lambda-streak-milestone.md` | Lambda 4 — Streak Milestone ⭐ | `04_streak_milestone/handler.py` |
| 132 | `phase4-part15g-lambda-data-cleanup.md` | Lambda 5 — Monthly Cleanup | `05_data_cleanup/handler.py` |
| 133 | `phase4-part15h-lambda-document-processor.md` | Lambda 6 — RAG Doc Processor | `06_document_processor/handler.py` |

#### Release 5.0-5.2: Frontend (Sprint 5)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 134 | `phase4-part16-frontend-overview.md` | Frontend — React + TypeScript Overview | — |
| 135 | `phase4-part16a-frontend-config.md` | Frontend Config — Vite, Tailwind, TS | Config files |
| 136 | `phase4-part16b-typescript-types.md` | TypeScript Types — Mirror Backend | `src/types/` |
| 137 | `phase4-part16c-api-service.md` | API Service — Axios + Auto Refresh ⭐⭐ | `src/services/api.ts` |
| 138 | `phase4-part16d-api-modules.md` | Module Services — Auth, Habits, AI | `src/services/*.ts` |
| 139 | `phase4-part16e-auth-store.md` | Zustand Store — Global Auth State | `src/store/auth-store.ts` |
| 140 | `phase4-part16f-hooks.md` | TanStack Query Hooks — 24 Hooks | `src/hooks/` |
| 141 | `phase4-part16g-layout.md` | Layout — Navbar, Sidebar, Protected Routes | `src/components/layout/` |
| 142 | `phase4-part16h-auth-pages.md` | Auth Pages — Login + Signup | `src/pages/Login+Signup` |
| 143 | `phase4-part16i-dashboard-page.md` | Dashboard Page — Summary Cards, Streaks | `src/pages/DashboardPage.tsx` |
| 144 | `phase4-part16j-habits-page.md` | Habits Page — Card Grid + Create Form | `src/pages/HabitsPage.tsx` |
| 145 | `phase4-part16k-checkin-page.md` | Check-In Page — Daily Logging Form ⭐ | `src/pages/CheckInPage.tsx` |
| 146 | `phase4-part16l-analytics-page.md` | Analytics Page — 4 Tabs, 3 Charts | `src/pages/AnalyticsPage.tsx` |
| 147 | `phase4-part16m-chat-page.md` | AI Chat Page — Agent Chat UI ⭐ | `src/pages/ChatPage.tsx` |
| 148 | `phase4-part16n-settings-page.md` | Settings — Profile, Export, Notifications | `src/pages/SettingsPage.tsx` |
| 149 | `phase4-part16o-components.md` | Key Components — Cards, Forms, Charts | Components |
| 150 | `phase4-part16p-frontend-connections.md` | Frontend — Complete Flow Diagram | — |

### Phase 5 — Testing (6 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 151 | `phase5-part01-testing-overview.md` | Testing Strategy — Unit vs Integration | — |
| 152 | `phase5-part02-conftest.md` | Test Config — Fixtures, DB Override | `tests/conftest.py` |
| 153 | `phase5-part03-factories-and-mocks.md` | Factories + Mocks — Test Data | `tests/factories.py` + `mocks/` |
| 154 | `phase5-part04-unit-tests.md` | Unit Tests — Auth, Dates, Agent, Chunker | `tests/unit/` |
| 155 | `phase5-part05-integration-tests.md` | Integration Tests — Auth, Habits, Logs API | `tests/integration/` |
| 156 | `phase5-part06-testing-connections.md` | Testing — What Tests Cover (Matrix) | — |

### Phase 6 — Docker (3 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 157 | `phase6-part01-docker-deep-dive.md` | Docker — Containers, Images, Volumes | All Dockerfiles |
| 158 | `phase6-part02-compose-services.md` | Docker Compose — 7 Services Explained | `docker-compose*.yml` |
| 159 | `phase6-part03-docker-networking.md` | Docker Networking — Service Communication | — |

### Phase 7 — CI/CD (2 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 160 | `phase7-part01-cicd-overview.md` | CI/CD — What, Why, How | — |
| 161 | `phase7-part02-github-actions.md` | GitHub Actions — Lint → Test → Build | `.github/workflows/ci.yml` |

### Phase 8 — Deployment (4 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 162 | `phase8-part01-local-setup.md` | Local Dev — Step by Step | `docs/deployment/local-setup.md` |
| 163 | `phase8-part02-staging-deploy.md` | Staging — Render + Vercel + Supabase (Free) | `docs/deployment/staging-deploy.md` |
| 164 | `phase8-part03-aws-production.md` | AWS Production — ECS, RDS, Bedrock | `docs/deployment/aws-deploy.md` |
| 165 | `phase8-part04-lambda-deploy.md` | Lambda Deploy — SAM Build + Deploy | `docs/deployment/lambda-deploy.md` |

### Phase 9 — Nginx & Monitoring (2 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 166 | `phase9-part01-nginx-deep-dive.md` | Nginx — How It Works Internally | `nginx/default.conf` |
| 167 | `phase9-part02-monitoring.md` | Monitoring — Structlog, CloudWatch, Alerts | — |

### Phase 10 — E2E Testing & Interview (4 docs)

| # | Filename | Title | Source File |
|---|----------|-------|-------------|
| 168 | `phase10-part01-e2e-curl-commands.md` | E2E — Curl Commands for All 38 Endpoints | — |
| 169 | `phase10-part02-interview-system-design.md` | Interview — 8 System Design Answers | `docs/interview-prep/` |
| 170 | `phase10-part03-interview-sql.md` | Interview — 7 SQL Queries Explained | `docs/interview-prep/sql-queries.md` |
| 171 | `phase10-part04-interview-ai-concepts.md` | Interview — AI Concepts (LLM, RAG, Agents) | `docs/interview-prep/ai-concepts.md` |

### INDEX + Bug Fix Report (2 docs)

| # | Filename | Title |
|---|----------|-------|
| 172 | `INDEX.md` | 📚 Master Index — All 171 Documents |
| 173 | `BUG-FIX-REPORT.md` | 🐛 Bug Audit — Fixes Found During Documentation |

---

## 4. Folder Structure

```
health-tracker/
├── docs/
│   ├── INDEX.md                              # Master index of all 171 docs
│   ├── BUG-FIX-REPORT.md                    # Bugs found and fixed
│   ├── DOCS_PLAN.md                          # THIS FILE — the plan
│   ├── DOCUMENTATION_PROMPT.md               # AI prompt to generate docs
│   ├── TYPING_GUIDE.md                       # Sprint-based typing order
│   │
│   ├── phase0-part01-project-overview.md
│   ├── phase0-part02-architecture-overview.md
│   ├── phase0-part03-tech-stack-explained.md
│   ├── phase0-part04-environment-setup.md
│   ├── phase0-part05-ai-concepts-from-zero.md
│   │
│   ├── phase1-part01-system-design-overview.md
│   ├── phase2-part01-high-level-design.md
│   ├── phase3-part01-low-level-design.md
│   ├── phase3-part02-database-design.md
│   │
│   ├── phase4-part01a-env-example.md         # ← Implementation starts
│   ├── phase4-part01b-gitignore.md
│   ├── phase4-part01c-docker-compose.md
│   ├── phase4-part01d-docker-compose-dev.md
│   ├── phase4-part01e-makefile.md
│   ├── phase4-part02a-requirements.md
│   ├── ...                                   # (88 implementation docs)
│   ├── phase4-part16p-frontend-connections.md
│   │
│   ├── phase5-part01-testing-overview.md
│   ├── ...                                   # (6 testing docs)
│   │
│   ├── phase6-part01-docker-deep-dive.md
│   ├── ...                                   # (3 Docker docs)
│   │
│   ├── phase7-part01-cicd-overview.md
│   ├── phase7-part02-github-actions.md
│   │
│   ├── phase8-part01-local-setup.md
│   ├── ...                                   # (4 deployment docs)
│   │
│   ├── phase9-part01-nginx-deep-dive.md
│   ├── phase9-part02-monitoring.md
│   │
│   ├── phase10-part01-e2e-curl-commands.md
│   ├── ...                                   # (4 interview + E2E docs)
│   │
│   ├── architecture/                         # (existing architecture docs)
│   ├── deployment/                           # (existing deployment docs)
│   ├── interview-prep/                       # (existing interview docs)
│   └── learning-notes/                       # (weekly note templates)
│
├── visual-docs/                              # Interactive HTML pages
│   ├── index.html
│   ├── architecture.html
│   ├── ai-pipeline-flow.html
│   ├── rag-pipeline.html
│   ├── api-reference.html
│   ├── database-er.html
│   ├── interview-qa.html
│   ├── flashcards.html
│   ├── cheat-sheet.html
│   ├── elevator-pitch.html
│   ├── module-deep-dive.html
│   ├── docker-vs-cloud.html
│   ├── cost-calculator.html
│   ├── live-demo.html
│   ├── project-timeline.html
│   ├── agent-simulator.html
│   └── sql-playground.html
```

---

## 5. Summary

| Metric | Count |
|--------|-------|
| **Total documents** | 173 |
| **Phase 0 (Overview)** | 5 |
| **Phase 1-3 (Design)** | 4 |
| **Phase 4 (Implementation)** | 88 |
| **Phase 5 (Testing)** | 6 |
| **Phase 6 (Docker)** | 3 |
| **Phase 7 (CI/CD)** | 2 |
| **Phase 8 (Deployment)** | 4 |
| **Phase 9 (Nginx/Monitoring)** | 2 |
| **Phase 10 (E2E/Interview)** | 4 |
| **Index + Bug Report** | 2 |
| **Visual HTML pages** | 17 |
| **⭐ Star docs (hardest)** | 15 |
| **Modules with overview + connections docs** | 7 |

---

## 6. How to Generate These Docs

1. Copy the `DOCUMENTATION_PROMPT.md` into a fresh AI chat
2. Tell it: "Start with Phase 0, Part 01"
3. It generates one doc at a time, reading your actual source code
4. Review each doc, verify code matches, save to the docs/ folder
5. Continue: "Next doc please" until all 173 are done
6. Generate the visual HTML pages last
7. Run the bug audit at the end
