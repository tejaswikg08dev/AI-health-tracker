# 🎯 Line-by-Line Typing Guide — Health Tracker

## How to Use This Guide

This guide is structured like the PayFlow Payment Gateway docs — organized as **sprints** where you type every file line by line, in the correct order, so each file builds on the previous one.

**Rules:**
1. Type every line — don't copy-paste
2. Follow the exact order — each file depends on the ones before it
3. After each file, run the app to verify it works
4. If you get an error, fix it before moving on — that's where real learning happens

---

## Sprint Overview (5 Sprints, 5 Weeks)

| Sprint | Focus | Files | What You Can Do After |
|--------|-------|-------|----------------------|
| **Sprint 1** | Foundation + Auth | 25 files | Signup, login, JWT auth working |
| **Sprint 2** | Habits + Logs + Analytics | 25 files | Full habit tracking with streaks & charts |
| **Sprint 3** | AI Module (LLM + RAG + Agents) | 35 files | Chat with AI, upload documents, agent tools |
| **Sprint 4** | Notifications + Export + Lambda | 25 files | Email, CSV export, serverless functions |
| **Sprint 5** | Frontend + Tests + Deploy | 55 files | Full working app, tested, deployed |

---

## 🏃 Sprint 1: Foundation + Auth (Week 1)

### Release 1.0: Project Skeleton (Day 1)

**Goal:** Docker running, FastAPI responding on localhost:8000

Type these files in this exact order:

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
1.  .env.example                    Environment variables, secrets
2.  .env                            Copy from example, fill values
3.  .gitignore                      What to never commit
4.  .dockerignore                   What Docker doesn't need
5.  docker-compose.yml              Multi-service orchestration
6.  docker-compose.dev.yml          Dev overrides, hot reload
7.  docker-compose.test.yml         Test isolation
8.  Makefile                        Shortcut commands
```

**After typing:** Run `docker-compose up postgres redis -d` → verify containers are healthy

### Release 1.1: FastAPI Foundation (Day 2)

**Goal:** `http://localhost:8000/health` returns `{"status": "healthy"}`

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
9.  backend/requirements.txt        Pinned dependencies, why each
10. backend/requirements-dev.txt    Dev vs prod dependencies
11. backend/pyproject.toml          Tool config (ruff, mypy, pytest)
12. backend/Dockerfile              Multi-stage builds
13. backend/app/__init__.py         Python packages
14. backend/app/config.py           Pydantic Settings, env vars
15. backend/app/database.py         Async SQLAlchemy, connection pool
16. backend/app/redis_client.py     Redis connection, why Redis
17. backend/app/dependencies.py     FastAPI DI, Annotated types
```

**After typing:** These don't run yet — you need main.py. Keep going.

### Release 1.2: Shared Utilities (Day 3)

**Goal:** Error handling, logging, and base patterns ready

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
18. backend/app/shared/__init__.py          Package init
19. backend/app/shared/exceptions.py        Error hierarchy → HTTP codes
20. backend/app/shared/base_schemas.py      Pydantic models, generics
21. backend/app/shared/base_repository.py   Generic CRUD, TypeVar
22. backend/app/shared/date_utils.py        Timezone handling, date math
23. backend/app/shared/logging.py           Structlog, JSON logs
```

### Release 1.3: Middleware (Day 3 continued)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
24. backend/app/middleware/__init__.py       Package init
25. backend/app/middleware/error_handler.py  Exception → JSON response
26. backend/app/middleware/logging_middleware.py  Request timing, request_id
27. backend/app/middleware/rate_limiter.py   Redis sliding window
```

### Release 1.4: Auth Module (Day 4-5)

**Goal:** Signup → Login → Get profile → all working via Swagger docs

Type auth files in this order (dependencies flow top to bottom):

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
28. backend/app/modules/__init__.py         Package init
29. backend/app/modules/auth/__init__.py    Module init

--- LAYER 1: Database (what's stored) ---
30. backend/app/modules/auth/models.py      User table, UUID PK, bcrypt

--- LAYER 2: Errors (what can go wrong) ---
31. backend/app/modules/auth/exceptions.py  InvalidCredentials, TokenExpired

--- LAYER 3: Validation (what comes in/out) ---
32. backend/app/modules/auth/schemas.py     UserCreate, TokenResponse

--- LAYER 4: Security (crypto) ---
33. backend/app/modules/auth/security.py    bcrypt, JWT create/decode

--- LAYER 5: Data access (SQL queries) ---
34. backend/app/modules/auth/repository.py  get_by_email, email_exists

--- LAYER 6: Business logic ---
35. backend/app/modules/auth/service.py     register, login, refresh, logout

--- LAYER 7: HTTP endpoints ---
36. backend/app/modules/auth/router.py      POST /signup, /login, GET /me

--- LAYER 8: Wire it all together ---
37. backend/app/main.py                     App factory, register auth router
```

**After typing:** Run `uvicorn app.main:app --reload` → open `http://localhost:8000/docs`
- Try POST /signup → should return user
- Try POST /login → should return tokens
- Try GET /me with Bearer token → should return profile

### Release 1.5: Database Migration (Day 5)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
38. backend/alembic.ini                     Alembic config
39. backend/alembic/env.py                  Migration engine, model imports
40. backend/alembic/script.py.mako          Migration template
41. backend/alembic/versions/001_create_users_table.py  First migration
```

**After typing:** Run `alembic upgrade head` → check database has `users` table

### Release 1.6: Nginx (Day 5)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
42. nginx/default.conf              Reverse proxy, rate limiting, SSE
```

**✅ Sprint 1 Complete — 42 files**
**You can now:** register users, login, get JWT tokens, and access protected endpoints.

---

## 🏃 Sprint 2: Core Tracking (Week 2)

### Release 2.0: Habits Module (Day 1-2)

**Goal:** Create, list, update, archive habits

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
43. backend/app/modules/habits/__init__.py
44. backend/app/modules/habits/models.py      Habit table, FK to users
45. backend/app/modules/habits/exceptions.py   HabitNotFound, LimitExceeded
46. backend/app/modules/habits/schemas.py      HabitType enum, color validator
47. backend/app/modules/habits/repository.py   User-scoped queries, reorder
48. backend/app/modules/habits/service.py      Max 20 limit, duplicate check
49. backend/app/modules/habits/router.py       6 endpoints: CRUD + reorder
50. backend/alembic/versions/002_create_habits_table.py
```

**After typing:** Update main.py to register habits router → Test CRUD via Swagger

### Release 2.1: Logs Module (Day 3-4)

**Goal:** Log daily habits, bulk save, query by date

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
51. backend/app/modules/logs/__init__.py
52. backend/app/modules/logs/models.py        3 value columns, UNIQUE constraint
53. backend/app/modules/logs/exceptions.py    FutureDate, DuplicateLog
54. backend/app/modules/logs/schemas.py       BulkLogCreate, type-specific values
55. backend/app/modules/logs/repository.py    Date range queries, streak dates
56. backend/app/modules/logs/service.py       Type validation, bulk upsert, cache invalidation
57. backend/app/modules/logs/router.py        Bulk create, filtered GET
58. backend/alembic/versions/003_create_habit_logs_table.py
```

**After typing:** Register logs router → test creating logs, bulk save, date queries

### Release 2.2: Analytics Module (Day 5-7)

**Goal:** Dashboard, streaks, weekly comparison, correlations

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
59. backend/app/modules/analytics/__init__.py
60. backend/app/modules/analytics/exceptions.py
61. backend/app/modules/analytics/schemas.py   12 response schemas for charts
62. backend/app/modules/analytics/repository.py  ⭐ HARDEST FILE — 6 complex SQL queries
63. backend/app/modules/analytics/cache.py     Redis cache-aside pattern
64. backend/app/modules/analytics/service.py   Pearson correlation from scratch
65. backend/app/modules/analytics/router.py    6 GET endpoints
```

**After typing:** Register analytics router → seed data → test dashboard endpoint

### Release 2.3: Seed Data (Day 7)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
66. scripts/seed_data.py            Generate realistic 30-day demo data
```

**After typing:** Run `python -m scripts.seed_data` → test all analytics endpoints with real data

**✅ Sprint 2 Complete — 66 files total**
**You can now:** track habits, view streaks, compare weeks, see correlations.

---

## 🏃 Sprint 3: AI Module (Week 3-4)

### Release 3.0: LLM Layer (Day 1-2)

**Goal:** Send a message to Ollama/Groq, get a response

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
67. backend/app/modules/ai/__init__.py
68. backend/app/modules/ai/llm/__init__.py
69. backend/app/modules/ai/llm/base_client.py    ⭐ Strategy pattern interface
70. backend/app/modules/ai/llm/ollama_client.py   HTTP calls to local LLM
71. backend/app/modules/ai/llm/groq_client.py     OpenAI-compatible cloud API
72. backend/app/modules/ai/llm/openai_client.py   Production API
73. backend/app/modules/ai/llm/factory.py          ⭐ Factory pattern
74. backend/app/modules/ai/llm/prompt_templates.py Jinja2 templates
75. backend/app/modules/ai/llm/token_tracker.py    Redis usage tracking
```

**After typing:** Write a quick test script to verify LLM responds

### Release 3.1: RAG Pipeline (Day 3-4)

**Goal:** Upload PDF → chunk → embed → search → get cited answer

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
76. backend/app/modules/ai/rag/__init__.py
77. backend/app/modules/ai/rag/document_processor.py  PDF text extraction
78. backend/app/modules/ai/rag/chunker.py      ⭐ Recursive splitting algorithm
79. backend/app/modules/ai/rag/embeddings.py   Text → 768-dim vectors
80. backend/app/modules/ai/rag/vector_store.py  ⭐ pgvector cosine similarity
81. backend/app/modules/ai/rag/retriever.py    Full retrieval pipeline
```

### Release 3.2: Agent Tools (Day 5-6)

**Goal:** 5 tools the agent can call to fetch real data

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
82. backend/app/modules/ai/agents/__init__.py
83. backend/app/modules/ai/agents/tools/__init__.py
84. backend/app/modules/ai/agents/tools/base_tool.py   ⭐ Tool interface
85. backend/app/modules/ai/agents/tools/query_logs.py   Fetch habit data
86. backend/app/modules/ai/agents/tools/get_analytics.py Streaks, completion
87. backend/app/modules/ai/agents/tools/search_docs.py  RAG search
88. backend/app/modules/ai/agents/tools/correlate.py    Pearson correlation
89. backend/app/modules/ai/agents/tools/create_plan.py  Improvement plan
```

### Release 3.3: Agent + Memory (Day 7-8)

**Goal:** ReAct agent thinks, calls tools, remembers across sessions

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
90. backend/app/modules/ai/agents/memory/__init__.py
91. backend/app/modules/ai/agents/memory/short_term.py  Conversation buffer
92. backend/app/modules/ai/agents/memory/long_term.py   Redis persistent memory
93. backend/app/modules/ai/agents/base_agent.py   ⭐ THE REACT LOOP — hardest AI file
94. backend/app/modules/ai/agents/health_coach.py  Pre-configured agent
```

### Release 3.4: Agentic Workflow (Day 9)

**Goal:** 3-step weekly report pipeline

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
95. backend/app/modules/ai/workflows/__init__.py
96. backend/app/modules/ai/workflows/base_workflow.py    Pipeline pattern
97. backend/app/modules/ai/workflows/orchestrator.py     ⭐ Retry + fallback
98. backend/app/modules/ai/workflows/weekly_report/__init__.py
99. backend/app/modules/ai/workflows/weekly_report/data_collector.py
100. backend/app/modules/ai/workflows/weekly_report/analyzer.py
101. backend/app/modules/ai/workflows/weekly_report/report_writer.py
```

### Release 3.5: AI Service + Router + Migration (Day 10)

**Goal:** All AI endpoints working: chat, documents, insights, weekly report

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
102. backend/app/modules/ai/models.py          4 AI tables + pgvector
103. backend/app/modules/ai/schemas.py         ChatRequest, StreamChunk
104. backend/app/modules/ai/service.py         ⭐ Orchestrates everything
105. backend/app/modules/ai/router.py          9 endpoints: chat, stream, docs, insights
106. backend/alembic/versions/004_create_ai_tables.py
```

**After typing:** Register AI router in main.py → test chat endpoint → upload a PDF → ask about it

**✅ Sprint 3 Complete — 106 files total**
**You can now:** chat with AI agent, upload documents for RAG, generate weekly reports.

---

## 🏃 Sprint 4: Delivery + Lambda (Week 4)

### Release 4.0: Notifications Module (Day 1-2)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
107. backend/app/modules/notifications/__init__.py
108. backend/app/modules/notifications/models.py
109. backend/app/modules/notifications/schemas.py
110. backend/app/modules/notifications/email_provider.py  Strategy for emails
111. backend/app/modules/notifications/service.py
112. backend/app/modules/notifications/tasks.py           Celery placeholders
113. backend/app/modules/notifications/router.py
114-117. backend/app/modules/notifications/templates/*.html  4 email templates
118. backend/alembic/versions/005_create_notification_settings.py
119. backend/app/tasks/__init__.py
120. backend/app/tasks/celery_app.py
```

### Release 4.1: Export Module (Day 3)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
121. backend/app/modules/export/__init__.py
122. backend/app/modules/export/schemas.py
123. backend/app/modules/export/csv_generator.py   In-memory CSV
124. backend/app/modules/export/pdf_generator.py   HTML report
125. backend/app/modules/export/storage.py         ⭐ S3/MinIO abstraction
126. backend/app/modules/export/service.py
127. backend/app/modules/export/router.py
```

**After typing:** Register both routers in main.py → test CSV export

### Release 4.2: Lambda Functions (Day 4-5)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
128-131. lambda_functions/shared/ (config, db_utils, email_utils, s3_utils)
132. lambda_functions/template.yaml           SAM infrastructure
133. lambda_functions/01_daily_reminder/handler.py
134. lambda_functions/02_weekly_report/handler.py
135. lambda_functions/03_csv_export/handler.py
136. lambda_functions/04_streak_milestone/handler.py
137. lambda_functions/05_data_cleanup/handler.py
138. lambda_functions/06_document_processor/handler.py
139-140. lambda_functions/events/*.json       Test events
```

**✅ Sprint 4 Complete — 140 files total**

---

## 🏃 Sprint 5: Frontend + Tests + Deploy (Week 5)

### Release 5.0: Frontend Setup + Types + API (Day 1)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
141-149. frontend/ config files (package.json, tsconfig, vite, tailwind, etc.)
150-156. frontend/src/types/ (7 TypeScript interfaces)
157-164. frontend/src/services/ (8 API service files)
165. frontend/src/services/api.ts   ⭐ Axios interceptors, auto token refresh
```

### Release 5.1: Hooks + Store + Layout (Day 2)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
166. frontend/src/store/auth-store.ts    Zustand state management
167-170. frontend/src/hooks/ (useHabits, useLogs, useAnalytics, useChat)
171. frontend/src/lib/utils.ts
172-177. frontend/src/components/layout/ (Navbar, Sidebar, PageLayout, etc.)
178. frontend/src/main.tsx               React entry point
179. frontend/src/App.tsx                Routing
```

### Release 5.2: Pages + Components (Day 3-4)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
180-187. frontend/src/pages/ (8 pages)
188-189. frontend/src/components/habits/ (HabitCard, HabitForm)
190. frontend/src/components/logs/DailyCheckIn.tsx
191-193. frontend/src/components/charts/ (WeeklyBar, MonthlyLine, CompletionPie)
194-196. frontend/src/components/ai/ (ChatWindow, ChatMessage, ChatInput)
```

### Release 5.3: Tests (Day 5)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
197. backend/tests/conftest.py       Test fixtures, DB override
198. backend/tests/factories.py      Test data generation
199-201. backend/tests/mocks/ (LLM, storage, email)
202-205. backend/tests/unit/ (auth, dates, agent, chunker)
206-208. backend/tests/integration/ (auth, habits, logs API)
```

### Release 5.4: CI/CD + Docs (Day 6-7)

```
FILE ORDER                          WHAT YOU LEARN
──────────────────────────────────  ────────────────────────────
209. .github/workflows/ci.yml       GitHub Actions pipeline
210. README.md                       Project README
211-227. docs/ (17 documentation files)
```

**✅ Sprint 5 Complete — 227+ files total**

---

## File Difficulty Rating

| Difficulty | Files | What Makes Them Hard |
|-----------|-------|---------------------|
| 🟢 Easy | config.py, __init__.py, schemas.py, exceptions.py | Mostly declarations, no complex logic |
| 🟡 Medium | models.py, repository.py, router.py, service.py | Need to understand the pattern, but straightforward |
| 🟠 Hard | main.py, base_repository.py, cache.py, service.py (AI) | Orchestration, generics, async patterns |
| 🔴 Very Hard | base_agent.py, repository.py (analytics), chunker.py, vector_store.py, api.ts | Complex algorithms, SQL, system design |

**⭐ Star files (most learning value):**
- `backend/app/modules/analytics/repository.py` — SQL window functions, CTEs
- `backend/app/modules/ai/agents/base_agent.py` — ReAct loop from scratch
- `backend/app/modules/ai/rag/vector_store.py` — pgvector cosine similarity
- `backend/app/modules/ai/llm/base_client.py` — Strategy pattern interface
- `backend/app/modules/ai/workflows/orchestrator.py` — Pipeline with retry
- `frontend/src/services/api.ts` — Axios interceptors, token refresh queue

---

## Daily Checklist Template

```
## Day ___ | Sprint ___ | Release ___

### Files typed today:
- [ ] File 1: _____________ (__ min)
- [ ] File 2: _____________ (__ min)
- [ ] File 3: _____________ (__ min)

### Verification:
- [ ] Code compiles/runs without errors
- [ ] Tested via Swagger / browser / curl
- [ ] I can explain what every line does

### What I learned:
1. ___
2. ___
3. ___

### Bugs I hit:
1. Error: ___ | Fix: ___

### Questions I still have:
1. ___
```
