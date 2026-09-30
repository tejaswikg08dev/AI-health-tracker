# Documentation Generation Prompt — Health Tracker

Copy and paste this entire prompt into a new AI chat session to generate comprehensive teaching documentation for the Health Tracker project.

---

## THE PROMPT (copy everything below this line)

---

I need comprehensive teaching documentation for my Python AI project — same depth as a 115-doc PayFlow Payment Gateway project that included line-by-line code explanations, 22 interactive visual HTML pages, and 30 source code bug fixes.

**PROJECT NAME:** AI-Powered Personal Health & Habit Tracker

**REPO PATH:** `health-tracker/`

**WHAT IT DOES:** A full-stack health habit tracking application where users track daily habits (water, sleep, exercise, mood), visualize progress with charts and streaks, and chat with an AI health coach that uses RAG to search uploaded health documents and a ReAct agent with 5 tools to fetch real data from the database. Includes an agentic workflow pipeline that generates personalized weekly health reports.

**TECH STACK:**
- Backend: Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, Redis, PostgreSQL + pgvector
- Frontend: React 18, TypeScript, Vite, TanStack Query, Zustand, Recharts, Tailwind CSS
- AI: Ollama (free local LLM), Groq (free cloud LLM), OpenAI (production), pgvector for RAG
- Infrastructure: Docker Compose (7 services), Nginx, AWS Lambda (6 functions), SAM, GitHub Actions CI/CD
- Storage: MinIO (local S3-compatible) / AWS S3

**ABOUT ME:**
- First time working with Python for a real project
- First time with AI/ML concepts (LLMs, embeddings, vector databases, RAG, agents, agentic workflows)
- First time with FastAPI, SQLAlchemy, Alembic, Celery, Docker, Nginx, AWS Lambda
- First time with React + TypeScript, TanStack Query, Zustand, Recharts
- Preparing for AI full-stack developer interviews — need to explain every design decision
- I will type this code line by line to learn, so docs must match source code EXACTLY

**PROJECT STRUCTURE (actual files I have):**

```
health-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py                    # Package init, version
│   │   ├── main.py                        # FastAPI app factory, lifespan, middleware, 7 routers
│   │   ├── config.py                      # Pydantic Settings (all env vars)
│   │   ├── database.py                    # Async SQLAlchemy engine, session factory, Base
│   │   ├── redis_client.py                # Redis async connection pool
│   │   ├── dependencies.py                # FastAPI DI type aliases (DBSession, RedisClient)
│   │   │
│   │   ├── modules/
│   │   │   ├── auth/                      # MODULE 1: JWT auth, bcrypt, token blacklist
│   │   │   │   ├── models.py              # User table (UUID, email, password_hash, timezone)
│   │   │   │   ├── schemas.py             # UserCreate, UserLogin, TokenResponse, UserUpdate
│   │   │   │   ├── security.py            # hash_password, verify_password, create/decode JWT
│   │   │   │   ├── repository.py          # UserRepository (get_by_email, email_exists)
│   │   │   │   ├── service.py             # AuthService (register, login, refresh, logout)
│   │   │   │   ├── router.py              # 6 endpoints: signup, login, refresh, logout, GET/PUT /me
│   │   │   │   └── exceptions.py          # InvalidCredentials, TokenExpired, AccountDeactivated
│   │   │   │
│   │   │   ├── habits/                    # MODULE 2: Habit CRUD, soft delete, reorder
│   │   │   │   ├── models.py              # Habit table (name, type, unit, target, color, icon, sort_order)
│   │   │   │   ├── schemas.py             # HabitType enum, HabitCreate, HabitUpdate, HabitReorder
│   │   │   │   ├── repository.py          # HabitRepository (user-scoped, duplicate check, reorder)
│   │   │   │   ├── service.py             # HabitService (max 20 limit, name uniqueness)
│   │   │   │   ├── router.py              # 6 endpoints: CRUD + reorder
│   │   │   │   └── exceptions.py          # HabitNotFound, DuplicateName, LimitExceeded
│   │   │   │
│   │   │   ├── logs/                      # MODULE 3: Daily check-ins, bulk upsert
│   │   │   │   ├── models.py              # HabitLog (3 value columns, UNIQUE constraint)
│   │   │   │   ├── schemas.py             # LogCreate, BulkLogCreate, LogUpdate
│   │   │   │   ├── repository.py          # LogRepository (date queries, range, streak dates)
│   │   │   │   ├── service.py             # LogService (type validation, bulk upsert, cache invalidation)
│   │   │   │   ├── router.py              # 5 endpoints: single, bulk, filtered GET, update, delete
│   │   │   │   └── exceptions.py          # DuplicateLog, FutureDate, InvalidLogValue
│   │   │   │
│   │   │   ├── analytics/                 # MODULE 4: Complex SQL, Redis caching
│   │   │   │   ├── schemas.py             # DashboardData, StreakInfo, WeeklySummary, Correlation, etc.
│   │   │   │   ├── repository.py          # 6 complex SQL: streaks (window fn), weekly (CASE), trends (generate_series), correlations (self-join)
│   │   │   │   ├── cache.py               # AnalyticsCache (Redis cache-aside, typed accessors, TTLs)
│   │   │   │   ├── service.py             # AnalyticsService (cache-aside pattern, Pearson correlation)
│   │   │   │   ├── router.py              # 6 GET endpoints: dashboard, streaks, weekly, monthly, completion, correlations
│   │   │   │   └── exceptions.py          # InsufficientData, InvalidDateRange
│   │   │   │
│   │   │   ├── ai/                        # MODULE 5: LLM + RAG + Agents + Workflows
│   │   │   │   ├── models.py              # Document, DocumentChunk (pgvector), AiChatMessage, AiInsight
│   │   │   │   ├── schemas.py             # ChatRequest, StreamChunk, DocumentResponse, InsightResponse
│   │   │   │   ├── service.py             # AiService (chat, stream, upload, RAG, insights, weekly report)
│   │   │   │   ├── router.py              # 9 endpoints: chat, stream SSE, history, documents CRUD, insights, report
│   │   │   │   │
│   │   │   │   ├── llm/                   # LLM Provider Abstraction (Strategy Pattern)
│   │   │   │   │   ├── base_client.py     # Abstract BaseLLMClient (LLMMessage, ToolCall, LLMResponse)
│   │   │   │   │   ├── ollama_client.py   # OllamaClient — free local (localhost:11434)
│   │   │   │   │   ├── groq_client.py     # GroqClient — free cloud (api.groq.com)
│   │   │   │   │   ├── openai_client.py   # OpenAIClient — paid production
│   │   │   │   │   ├── factory.py         # get_llm_client() factory with lru_cache
│   │   │   │   │   ├── prompt_templates.py # 6 Jinja2 templates (health coach, RAG, agent, weekly report)
│   │   │   │   │   └── token_tracker.py   # Redis daily token usage per user
│   │   │   │   │
│   │   │   │   ├── rag/                   # RAG Pipeline
│   │   │   │   │   ├── document_processor.py  # PDF text extraction (PyPDF2)
│   │   │   │   │   ├── chunker.py         # Recursive character text splitting with overlap
│   │   │   │   │   ├── embeddings.py      # Batch embedding generation via LLM client
│   │   │   │   │   ├── vector_store.py    # pgvector: store, cosine similarity search (<=>)
│   │   │   │   │   └── retriever.py       # Full pipeline: embed → search → token budget → citations
│   │   │   │   │
│   │   │   │   ├── agents/                # AI Agents (ReAct Pattern)
│   │   │   │   │   ├── base_agent.py      # ReAct loop: think → act → observe → repeat
│   │   │   │   │   ├── health_coach.py    # Pre-configured agent with 5 tools + memory
│   │   │   │   │   ├── tools/
│   │   │   │   │   │   ├── base_tool.py   # Abstract BaseTool (to_openai_schema)
│   │   │   │   │   │   ├── query_logs.py  # Fetch habit data by name + date range
│   │   │   │   │   │   ├── get_analytics.py # Streaks, weekly summary, completion
│   │   │   │   │   │   ├── search_docs.py # RAG vector search on uploaded documents
│   │   │   │   │   │   ├── correlate.py   # Pearson correlation between two habits
│   │   │   │   │   │   └── create_plan.py # Structured improvement plan
│   │   │   │   │   └── memory/
│   │   │   │   │       ├── short_term.py  # Sliding window conversation buffer
│   │   │   │   │       └── long_term.py   # Redis persistent insights across sessions
│   │   │   │   │
│   │   │   │   └── workflows/             # Agentic Workflows
│   │   │   │       ├── base_workflow.py   # Abstract pipeline with StepResult/WorkflowResult
│   │   │   │       ├── orchestrator.py    # Step runner with retry, timeout, fallback
│   │   │   │       └── weekly_report/
│   │   │   │           ├── data_collector.py  # Step 1: gather all habit data
│   │   │   │           ├── analyzer.py    # Step 2: LLM finds patterns
│   │   │   │           └── report_writer.py # Step 3: LLM writes report
│   │   │   │
│   │   │   ├── notifications/             # MODULE 6: Email, Celery tasks
│   │   │   │   ├── models.py              # NotificationSettings
│   │   │   │   ├── schemas.py             # Settings response/update
│   │   │   │   ├── email_provider.py      # Abstract + Console/Resend/SES implementations
│   │   │   │   ├── service.py             # 4 send methods with Jinja2 templates
│   │   │   │   ├── tasks.py              # Celery task placeholders
│   │   │   │   ├── router.py              # 3 endpoints: GET/PUT settings, test email
│   │   │   │   └── templates/             # 4 HTML email templates
│   │   │   │
│   │   │   └── export/                    # MODULE 7: CSV, S3 storage
│   │   │       ├── schemas.py             # ExportRequest, ExportResponse
│   │   │       ├── csv_generator.py       # In-memory CSV via io.StringIO
│   │   │       ├── pdf_generator.py       # HTML report (WeasyPrint placeholder)
│   │   │       ├── storage.py             # S3/MinIO abstraction (boto3)
│   │   │       ├── service.py             # Sync CSV + async S3 export
│   │   │       └── router.py              # 2 endpoints: CSV download, S3 upload
│   │   │
│   │   ├── shared/                        # Cross-module utilities
│   │   │   ├── base_repository.py         # Generic CRUD (create, get, update, delete, count)
│   │   │   ├── base_schemas.py            # PaginationParams, PaginatedResponse, ErrorResponse
│   │   │   ├── date_utils.py              # UTC now, timezone conversion, week/month boundaries
│   │   │   ├── logging.py                # Structlog JSON logging config
│   │   │   └── exceptions.py             # BaseAppError hierarchy (5 error types → HTTP codes)
│   │   │
│   │   ├── middleware/                    # Request pipeline
│   │   │   ├── rate_limiter.py            # Redis sliding window (30r/s API, 2r/s AI, 5r/m login)
│   │   │   ├── logging_middleware.py      # Request/response logging with request_id
│   │   │   └── error_handler.py           # Global exception → JSON response mapping
│   │   │
│   │   └── tasks/
│   │       └── celery_app.py              # Celery config with Redis broker
│   │
│   ├── tests/
│   │   ├── conftest.py                    # Test DB, test client, auth fixtures
│   │   ├── factories.py                   # make_user_data, make_habit_data, make_log_data
│   │   ├── mocks/                         # MockLLMClient, MockStorage, MockEmail
│   │   ├── unit/                          # 4 files: auth_security, date_utils, ai_agent, rag_chunker
│   │   └── integration/                   # 3 files: auth_api, habits_api, logs_api
│   │
│   ├── alembic/                           # 5 migrations: users, habits, habit_logs, ai_tables, notifications
│   ├── requirements.txt                   # 20+ pinned production dependencies
│   ├── requirements-dev.txt               # Test + dev dependencies
│   ├── Dockerfile                         # Multi-stage: builder → development → production
│   └── pyproject.toml                     # Ruff, mypy, pytest config
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx, App.tsx              # React root, routing
│   │   ├── types/                         # 7 TypeScript interfaces (mirror backend)
│   │   ├── services/                      # 8 API service files (axios + interceptors)
│   │   ├── hooks/                         # 5 TanStack Query hooks (24 query/mutation hooks)
│   │   ├── store/auth-store.ts            # Zustand auth state
│   │   ├── components/                    # Layout (5), Habits (2), Logs (1), Charts (3), AI Chat (3)
│   │   ├── pages/                         # 8 pages: Login, Signup, Dashboard, Habits, CheckIn, Analytics, Chat, Settings
│   │   └── lib/utils.ts                   # cn(), formatDate, todayString
│   ├── package.json, tsconfig.json, vite.config.ts, tailwind.config.js
│   └── Dockerfile                         # 3-stage: install → build → nginx serve
│
├── lambda_functions/
│   ├── 01_daily_reminder/handler.py       # EventBridge → query users → SES email
│   ├── 02_weekly_report/handler.py        # EventBridge → gather data → Groq LLM → S3 → email
│   ├── 03_csv_export/handler.py           # SQS → query logs → CSV → S3 → presigned URL → email
│   ├── 04_streak_milestone/handler.py     # SQS → streak SQL → idempotency → celebration email
│   ├── 05_data_cleanup/handler.py         # EventBridge → delete old data → VACUUM ANALYZE
│   ├── 06_document_processor/handler.py   # S3 trigger → PDF extract → chunk → embed → pgvector
│   ├── shared/ (config, db_utils, email_utils, s3_utils)
│   ├── template.yaml                      # AWS SAM template
│   └── events/                            # Sample event JSONs for local testing
│
├── nginx/default.conf                     # Reverse proxy, 3 rate limit zones, SSE, security headers
├── docker-compose.yml                     # 7 services: nginx, backend, celery-worker, celery-beat, postgres+pgvector, redis, minio, ollama
├── docker-compose.dev.yml                 # Dev override: hot reload, debug
├── docker-compose.test.yml                # Test: postgres + redis only
├── Makefile                               # 12 shortcut commands
├── .github/workflows/ci.yml              # 3-stage: lint → test → build
├── scripts/seed_data.py                   # Demo user + 5 habits + 30 days realistic data
│
├── docs/
│   ├── architecture/ (HLD.md, LLD.md, ai-architecture.md, database-design.md, api-design.md, system-flowchart.md)
│   ├── deployment/ (local-setup.md, staging-deploy.md, aws-deploy.md, lambda-deploy.md)
│   ├── interview-prep/ (system-design-answers.md, sql-queries.md, ai-concepts.md)
│   └── learning-notes/ (week-1 through week-5 templates)
│
├── .env.example, .gitignore, .dockerignore, README.md, PROJECT_STRUCTURE.md
└── Makefile
```

**DESIGN PATTERNS USED (explain each in docs):**
- Strategy Pattern (LLM providers, email providers, storage)
- Factory Pattern (get_llm_client, get_email_provider)
- Repository Pattern (every module has Router → Service → Repository layers)
- Service Layer Pattern (business logic separated from HTTP)
- Cache-Aside Pattern (Analytics with Redis TTL)
- Abstract Base Class (BaseLLMClient, BaseTool, BaseWorkflow, BaseEmailProvider)
- ReAct Agent Pattern (think → act → observe loop)
- Pipeline Pattern (agentic weekly report workflow)
- Modular Monolith (7 modules with clear boundaries)
- Dependency Injection (FastAPI Depends)

**WHAT I NEED YOU TO DO:**

1. **READ MY ACTUAL SOURCE CODE FIRST** — never write docs from imagination. Every code snippet in docs must match the real file character-for-character. If you find bugs, fix them first, then document the fixed version.

2. **EXPLAIN EVERYTHING FROM ZERO** — I don't know Python decorators, virtual environments, pip, FastAPI, SQLAlchemy, Alembic, Celery, Redis, Docker, Nginx, AWS Lambda, React, TypeScript, LLMs, embeddings, vector stores, prompt engineering, RAG, agents, or any AI concept. Explain each like I'm hearing it for the first time. Use real-world analogies. Explain WHY before HOW.

3. **FOR EACH FILE/MODULE CREATE A DETAILED DOC** with this structure:
   - Document metadata table (phase, part, previous/next links)
   - "What is [concept]? Read This First" section with analogies
   - Line-by-line code walkthrough matching actual source
   - "How This Connects" section with ASCII architecture diagram
   - "What You Learned" summary table
   - "Common Errors & Fixes" troubleshooting table
   - Navigation footer with prev/next links

4. **COVER THESE PHASES IN ORDER:**

   **Phase 0:** Project overview (what it does, architecture, tech stack) + environment setup (Python, pip, venv, .env, Docker, Node.js, Ollama)

   **Phase 1-3:** System design, high-level design, low-level design — using my existing HLD.md, LLD.md, ai-architecture.md but expanded with beginner explanations

   **Phase 4:** Implementation — EVERY file explained line by line (this is 80% of docs):
   - 4.01: `__init__.py`, `config.py` (Pydantic Settings, env vars)
   - 4.02: `database.py` (async SQLAlchemy, connection pool, Base)
   - 4.03: `redis_client.py` (Redis connection, why Redis)
   - 4.04: `dependencies.py` (FastAPI DI, Annotated type aliases)
   - 4.05: `main.py` (app factory, lifespan, middleware registration, router registration)
   - 4.06: `shared/exceptions.py` (error hierarchy)
   - 4.07: `shared/base_schemas.py` (Pydantic models, pagination)
   - 4.08: `shared/base_repository.py` (generic CRUD, TypeVar, Generic)
   - 4.09: `shared/date_utils.py` (timezone handling, date math)
   - 4.10: `shared/logging.py` (structlog, JSON logging)
   - 4.11: `middleware/error_handler.py` (exception → HTTP response)
   - 4.12: `middleware/logging_middleware.py` (request timing, request_id)
   - 4.13: `middleware/rate_limiter.py` (Redis sliding window algorithm)
   - 4.14-4.20: Auth module (7 files — models, security, schemas, repo, service, router, exceptions)
   - 4.21-4.26: Habits module (6 files)
   - 4.27-4.32: Logs module (6 files)
   - 4.33-4.39: Analytics module (7 files — including complex SQL)
   - 4.40-4.65: AI module (25+ files — LLM layer, RAG pipeline, agents, workflows)
   - 4.66-4.76: Notifications module (11 files including templates)
   - 4.77-4.82: Export module (6 files)
   - 4.83-4.85: Celery tasks
   - 4.86-4.90: Alembic migrations (5 files)
   - 4.91-4.98: Frontend (types, services, hooks, store, pages, components)

   **Phase 5:** Testing — conftest.py, factories.py, mocks, all unit + integration tests

   **Phase 6:** Docker — Dockerfile (multi-stage), docker-compose.yml (7 services), docker-compose.dev.yml, docker-compose.test.yml

   **Phase 7:** CI/CD — GitHub Actions pipeline (lint → test → build)

   **Phase 8:** Cloud deployment — local setup, staging (Render+Vercel+Supabase free), AWS production architecture, Lambda deployment (SAM)

   **Phase 9:** Nginx — reverse proxy, rate limiting, SSE support, security headers

   **Phase 10:** End-to-end testing — dev + production, exact curl commands for all 38 endpoints

5. **AFTER ALL DOCS** — audit entire source code for bugs, fix them, create bug fix report, update affected docs.

6. **CREATE INTERACTIVE VISUAL HTML PAGES** in a `visual-docs/` folder:
   - `index.html` (dashboard with project stats, animated cards, floating particles)
   - `architecture.html` (clickable module diagram with hover tooltips showing file counts, endpoints)
   - `ai-pipeline-flow.html` (animated step-by-step: user question → agent thinks → tool call → database query → LLM response)
   - `rag-pipeline.html` (animated: PDF upload → extract → chunk → embed → pgvector → retrieval → LLM answer with citations)
   - `api-reference.html` (searchable 38 endpoints with request/response JSON, grouped by module)
   - `database-er.html` (8 tables with relationships, column tooltips, pgvector explanation)
   - `interview-qa.html` (30+ project-specific Q&A with difficulty badges: "Design a habit tracker", "How does your RAG work?", "Explain the ReAct agent loop")
   - `flashcards.html` (flip cards with score tracking: Python, FastAPI, SQL, AI concepts)
   - `cheat-sheet.html` (printable one-page: all patterns, all endpoints, all SQL queries, all AI concepts)
   - `elevator-pitch.html` (timed 2/5/15 min practice scripts for this project)
   - `module-deep-dive.html` (detailed per-module: auth, habits, logs, analytics, AI, notifications, export)
   - `docker-vs-cloud.html` (side-by-side: local Docker vs staging vs AWS production)
   - `cost-calculator.html` (cloud cost estimator: EC2, RDS, Lambda, Bedrock — with sliders)
   - `live-demo.html` (simulated walkthrough: signup → create habits → daily check-in → view analytics → chat with AI → export CSV)
   - `project-timeline.html` (scroll-triggered: Week 1 backend → Week 2 frontend → Week 3 AI → Week 4 agents → Week 5 deploy)
   - `agent-simulator.html` (interactive ReAct loop: type a question → see agent think → call tools → generate answer step by step)
   - `sql-playground.html` (paste streak/weekly/correlation queries with sample data and visual output)

   All with: dark theme (#0F172A background), floating particles, glass-morphism cards, hover tooltips, staggered entrance animations, self-contained HTML/CSS/JS (no external dependencies)

7. **AI-SPECIFIC CONCEPTS TO EXPLAIN IN DEPTH** (since I'm a complete AI beginner):
   - What is an LLM? How does Ollama/Groq/OpenAI work? What are tokens?
   - What are embeddings? Why convert text to 768 numbers? How does nomic-embed-text work?
   - What is pgvector? How does cosine similarity work? What is the <=> operator?
   - What is RAG? Why not just ask the LLM directly? What are the 5 steps?
   - What is a prompt template? Why use Jinja2? What is prompt engineering?
   - What is the ReAct pattern? How is an agent different from a chatbot?
   - What is tool/function calling? How does the LLM decide which tool to use?
   - What is agent memory? Short-term vs long-term? Why both?
   - What is an agentic workflow? Why 3 agents better than 1?
   - What is chunking? Why 500 tokens? Why overlap?
   - What is temperature, top_p, max_tokens?
   - How does the AI pipeline flow end-to-end? (with diagram)
   - Cost estimation: how much does each API call cost?
   - Strategy pattern for LLM providers: why and how?
   - IVFFlat index: how does approximate nearest neighbor search work?

8. **PYTHON/FASTAPI CONCEPTS TO EXPLAIN** (since I'm a Python beginner):
   - Virtual environments, pip, requirements.txt
   - Type hints, Annotated, Generic[T], TypeVar
   - Decorators (@app.get, @property, @abstractmethod)
   - async/await and why FastAPI is async
   - Pydantic models vs SQLAlchemy models (when to use which)
   - Dependency injection with Depends()
   - Middleware (request/response pipeline)
   - Alembic migrations (why not just CREATE TABLE)
   - Context managers (async with, yield)
   - ABC (Abstract Base Class) and the Strategy pattern

**START NOW:** Read my project structure, understand every file, then begin with Phase 0 overview. Create one document at a time, in order. Each document should be 2000-4000 words with actual code from my files.
