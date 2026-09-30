# 📋 Part Overview Guide — What Each Overview Doc Contains

## The Pattern

Every `phase4-partNN-{module}-overview.md` is a **roadmap document** that:
1. Explains WHAT this module/group does and WHY it exists
2. Lists ALL sub-parts (a, b, c...) with one-line descriptions
3. Shows how the sub-parts depend on each other (build order)
4. Provides the architecture diagram for this group
5. Sets expectations: difficulty, time, concepts you'll learn

Think of it like a **chapter introduction** before the sections.

---

## Every Overview Doc Follows This Template:

```markdown
# Phase 4 — Part {NN}: {Module Name} Overview

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Sprint** | Sprint {X} |
| **Release** | Release {X.Y} |
| **Files in this group** | {N} files |
| **Endpoints** | {N} endpoints |
| **Database tables** | {table names or "none — reads only"} |
| **Total typing time** | ~{N} minutes |

---

## What is {Module}?

{3-4 paragraphs explaining this module's purpose in the system.
Real-world analogy. Why this module exists. What problem it solves.}

---

## Sub-Parts in This Group

| Order | Doc | File | What You'll Type | Difficulty | Time |
|-------|-----|------|-----------------|-----------|------|
| 1 | Part {NN}a | `models.py` | Database table definition | 🟢 | 15 min |
| 2 | Part {NN}b | `exceptions.py` | Custom error classes | 🟢 | 10 min |
| 3 | Part {NN}c | `schemas.py` | Request/response validation | 🟡 | 20 min |
| ... | ... | ... | ... | ... | ... |

---

## Build Order (Dependency Graph)

```
models.py ← exceptions.py ← schemas.py
                                 ↓
                          repository.py
                                 ↓
                           service.py
                                 ↓
                            router.py
                                 ↓
                       (register in main.py)
```

**You MUST type in this order.** Each file imports from the ones above it.

---

## Architecture: Where This Module Fits

```
[Previous Module] → [THIS MODULE] → [Next Module]
                         ↓
                    PostgreSQL
```

---

## What You'll Learn in This Group

| Concept | Which Sub-Part |
|---------|---------------|
| {concept 1} | Part {NN}a |
| {concept 2} | Part {NN}d |
| ... | ... |

---

## After This Group

When you finish all sub-parts, you should be able to:
- [ ] {verification 1}
- [ ] {verification 2}
- [ ] {verification 3}

---

| ← Previous Group | [📚 Index](./INDEX.md) | Next Group → |
|:-----------------|:---------------------:|-------------:|
| [Part {prev}](./{prev}) | | [Part {next}](./{next}) |
```

---

## Complete List of Overview Docs (What Each One Covers)

### `phase4-part01-project-skeleton-overview.md`
**Release 1.0 — Project Skeleton**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part01a | `.env.example` | Every environment variable explained — what each controls, security implications |
| part01b | `.gitignore` | Why these 40+ patterns are ignored, security (never commit .env) |
| part01c | `docker-compose.yml` | 7 Docker services: what each does, how they connect, health checks |
| part01d | `docker-compose.dev.yml` | Dev overrides: volume mounts for hot reload, debug settings |
| part01e | `Makefile` | 12 shortcut commands — what each runs, why Makefiles exist |

**After this group:** `docker-compose up` starts all services ✅

---

### `phase4-part02-fastapi-foundation-overview.md`
**Release 1.1 — FastAPI Foundation**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part02a | `requirements.txt` | 20+ packages — what each does, why pinned versions, pip install |
| part02b | `pyproject.toml` | Tool config: ruff (linting), mypy (type checking), pytest (testing) |
| part02c | `Dockerfile` | 3-stage build: builder → development → production. Non-root user. Why multi-stage |
| part02d | `config.py` | Pydantic Settings: reads .env, validates types, provides defaults. @lru_cache |
| part02e | `database.py` | Async SQLAlchemy: engine (connection pool), session factory, Base class |
| part02f | `redis_client.py` | Redis connection pool: why Redis, what it stores, async client |
| part02g | `dependencies.py` | FastAPI Depends(): Annotated type aliases (DBSession, RedisClient, AppSettings) |

**After this group:** All infrastructure code ready, main.py can import everything ✅

**Concepts taught:**
- Virtual environments and pip
- Why pin dependency versions
- Multi-stage Docker builds
- Pydantic Settings and environment variables
- Async SQLAlchemy connection pooling
- Redis data structures and use cases
- FastAPI dependency injection

---

### `phase4-part03-shared-utilities-overview.md`
**Release 1.2 + 1.3 — Shared Utilities + Middleware**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part03a | `shared/exceptions.py` | 5-level error hierarchy: BaseAppError → NotFound/Conflict/Validation/Unauthorized/Forbidden |
| part03b | `shared/base_schemas.py` | Pydantic base: BaseSchema, PaginationParams, PaginatedResponse[T], ErrorResponse |
| part03c | `shared/base_repository.py` | Generic CRUD: create(), get_by_id(), get_all(), update(), delete(), count() with TypeVar |
| part03d | `shared/date_utils.py` | UTC handling, timezone conversion, week/month boundaries, date ranges |
| part03e | `shared/logging.py` | Structlog: JSON logging in prod, colored in dev. Log levels, request binding |
| part03f | `middleware/error_handler.py` | Catches all exceptions → structured JSON response. 4 handler functions |
| part03g | `middleware/logging_middleware.py` | Logs every request: method, path, status, duration_ms, request_id header |
| part03h | `middleware/rate_limiter.py` | Redis sliding window: 30r/s API, 2r/s AI, 5r/min login. RATE_LIMITS dict |

**After this group:** Error handling, logging, rate limiting all work before any module code ✅

**Concepts taught:**
- Python exception hierarchy and custom exceptions
- Pydantic Generic models (PaginatedResponse[T])
- Python Generics with TypeVar and Generic[ModelType]
- Timezone-aware datetime handling
- Structured logging (JSON for machines, colored for humans)
- Middleware pattern (code that runs on EVERY request)
- Rate limiting algorithms (sliding window vs fixed window)

---

### `phase4-part04-auth-overview.md`
**Release 1.4 + 1.5 — Auth Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part04a | `auth/models.py` | User table: UUID PK, email (unique, indexed), password_hash, timezone, is_active, timestamps |
| part04b | `auth/exceptions.py` | 5 auth errors: InvalidCredentials, UserAlreadyExists, TokenExpired, TokenInvalid, AccountDeactivated |
| part04c | `auth/schemas.py` | UserCreate (EmailStr, min 8 password), UserLogin, TokenResponse, UserUpdate, UserResponse |
| part04d | `auth/security.py` | ⭐ bcrypt: hash+verify. JWT: create access (30min) + refresh (7day), decode with type check |
| part04e | `auth/repository.py` | UserRepository: get_by_email (login), get_active_by_id (auth check), email_exists (signup) |
| part04f | `auth/service.py` | ⭐ AuthService: register (hash+create), login (verify+token), refresh (blacklist old), logout |
| part04g | `auth/router.py` | 6 endpoints + get_current_user_id dependency (JWT decode + blacklist check) |
| part04h | `auth/connections-and-flows.md` | Sequence diagrams: signup flow, login flow, token refresh flow, logout flow |
| part04i | `alembic.ini` + `env.py` | Alembic configuration: how migrations connect to models |
| part04j | `001_create_users_table.py` | First migration: CREATE TABLE users, CREATE EXTENSION pgvector |
| part04k | `main.py` | ⭐ App factory: create_app(), lifespan, register middleware + routers, /health endpoint |
| part04l | `nginx/default.conf` | Reverse proxy: upstream backend, rate limit zones, SSE, security headers, gzip |

**After this group:** Full auth working — signup, login, JWT tokens, protected endpoints ✅

**Concepts taught:**
- bcrypt: why hashing is one-way, what salt does, cost factor
- JWT: header.payload.signature, why two tokens, refresh flow
- Token blacklist: why Redis (speed), TTL (auto-cleanup)
- Repository pattern: data access layer separated from business logic
- Service pattern: business logic separated from HTTP
- Password security: same error for wrong email AND wrong password (prevent enumeration)
- Alembic: schema versioning, upgrade/downgrade, autogenerate
- App factory pattern: create_app() for testability
- Nginx: how reverse proxy works, why rate limiting at multiple levels

---

### `phase4-part05-habits-overview.md`
**Release 2.0 — Habits Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part05a | `habits/models.py` | Habit table: name, habit_type (numeric/boolean/scale), unit, target, color, icon, sort_order, is_archived |
| part05b | `habits/exceptions.py` | HabitNotFound, DuplicateHabitName, HabitLimitExceeded, InvalidHabitType |
| part05c | `habits/schemas.py` | HabitType enum, HabitCreate (hex color validator), HabitUpdate, HabitReorderRequest |
| part05d | `habits/repository.py` | User-scoped queries, duplicate name check, count active, next sort_order, batch reorder, archive |
| part05e | `habits/service.py` | Max 20 limit, name uniqueness per user, auto sort_order |
| part05f | `habits/router.py` | 6 endpoints: POST, GET list, GET single, PUT, DELETE (archive), PUT reorder |
| part05g | `002_create_habits_table.py` | Migration with composite index (user_id, is_archived) |
| part05h | `habits/connections-and-flows.md` | Create habit flow, reorder flow, archive flow |

**Concepts taught:**
- Foreign keys: ON DELETE CASCADE
- Composite indexes: when to use, why (user_id, is_archived)
- Soft delete pattern: is_archived instead of DELETE FROM
- Enum validation: Pydantic enum → string in DB
- Hex color validation: field_validator
- Drag-and-drop: how sort_order maps to UI reordering

---

### `phase4-part06-logs-overview.md`
**Release 2.1 — Logs Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part06a-f | models → router | 6 standard files + migration |
| part06h | connections-and-flows | Single log flow, bulk save flow, cache invalidation flow |

**Concepts taught:**
- UNIQUE constraint: (user_id, habit_id, log_date) — database-level duplicate prevention
- Polymorphic storage: 3 value columns for 3 habit types
- Bulk upsert: create-or-update in a single transaction
- Cache invalidation: deleting Redis keys when data changes
- Date validation: reject future dates

---

### `phase4-part07-analytics-overview.md`
**Release 2.2 — Analytics Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part07a | `schemas.py` | 12 response types (DashboardData, StreakInfo, WeeklySummary, Correlation, etc.) |
| part07b | `repository.py` | ⭐⭐ THE HARDEST SQL FILE: 6 queries with window functions, CTEs, generate_series, self-joins |
| part07c | `cache.py` | Redis cache-aside: get → miss → compute → set with TTL → invalidate on write |
| part07d | `service.py` | Pearson correlation from scratch, cache-aside orchestration |
| part07e | `router.py` | 6 GET-only endpoints with query params (days, habit_id) |
| part07f | connections-and-flows | Dashboard load flow, cache hit vs miss flow, correlation calculation flow |

**Concepts taught:**
- Window functions: ROW_NUMBER(), PARTITION BY
- CTEs: WITH clauses, 4 levels deep
- Gaps and islands: the classic streak calculation algorithm
- generate_series: fill date gaps for charts
- CASE WHEN inside AVG: conditional aggregation
- Self-join: pair habits logged on the same day
- Cache-aside pattern: check cache → miss → compute → cache → return
- Pearson correlation: the math from scratch (Σ((x-x̄)(y-ȳ)) / √(...))

---

### `phase4-part08-ai-llm-overview.md` through `phase4-part12-ai-complete-overview.md`
**Release 3.0-3.5 — AI Module (5 overview docs for 5 sub-releases)**

The AI module is so large it gets **5 separate overview docs**:

| Overview | Release | Sub-Parts | Focus |
|----------|---------|-----------|-------|
| part08 | 3.0 | 08a-08g (7 files) | LLM provider abstraction — Strategy + Factory patterns |
| part09 | 3.1 | 09a-09f (6 files) | RAG pipeline — ingest → chunk → embed → search → generate |
| part10 | 3.2-3.3 | 10a-10k (11 files) | Agent tools + memory + ReAct loop |
| part11 | 3.4 | 11a-11f (6 files) | Agentic workflow — 3-step pipeline with orchestrator |
| part12 | 3.5 | 12a-12f (6 files) | AI service + router + migration — wiring it all together |

---

### `phase4-part13-notifications-overview.md`
**Release 4.0 — Notifications Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part13a-h | models → migration | 8 files + 4 HTML email templates |

**Concepts taught:**
- Strategy pattern for email providers (Console → Resend → SES)
- Jinja2 HTML templates with variables
- Celery: task queue, broker (Redis), worker, beat (scheduler)
- HTML email: inline CSS (email clients strip `<style>` tags)

---

### `phase4-part14-export-overview.md`
**Release 4.1 — Export Module**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part14a-f | csv → connections | 6 files |

**Concepts taught:**
- io.StringIO: in-memory file generation (no disk I/O)
- csv module: Python's built-in CSV writer
- boto3: AWS SDK — same API for MinIO (local) and S3 (production)
- Pre-signed URLs: temporary download links with expiry

---

### `phase4-part15-lambda-overview.md`
**Release 4.2 — Lambda Functions**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part15a-h | shared → 6 handlers | 8 files + SAM template |

**Concepts taught:**
- Serverless: runs only when triggered, scales to zero
- Event sources: EventBridge (cron), SQS (queue), S3 (file upload)
- Lambda handler: event + context → response
- SAM template: infrastructure as code for Lambda
- Warm starts: connection reuse between invocations

---

### `phase4-part16-frontend-overview.md`
**Release 5.0-5.2 — Frontend**

| Sub-Part | File | What It Does |
|----------|------|-------------|
| part16a-p | config → connections | 16 docs covering all frontend files |

**Concepts taught:**
- React component lifecycle, hooks (useState, useEffect)
- TypeScript: interfaces, generics, strict mode
- Vite: why faster than CRA, proxy configuration
- TanStack Query: queries, mutations, cache invalidation
- Zustand: global state without Redux boilerplate
- Axios interceptors: auto token refresh
- Recharts: data format for bar, line, pie charts
- SSE: Server-Sent Events for streaming AI responses
- Tailwind CSS: utility-first styling

---

## Visual Summary: All Overview Docs

```
phase4-part01  Project Skeleton ───── 5 sub-parts (env, git, docker, make)
phase4-part02  FastAPI Foundation ─── 7 sub-parts (deps, config, db, redis, DI)
phase4-part03  Shared + Middleware ── 8 sub-parts (errors, base classes, middleware)
phase4-part04  Auth Module ────────── 12 sub-parts (models → router → main → nginx)
phase4-part05  Habits Module ──────── 8 sub-parts (models → router → migration)
phase4-part06  Logs Module ────────── 8 sub-parts (models → router → migration)
phase4-part07  Analytics Module ────── 7 sub-parts (schemas → SQL → cache → service)
phase4-part08  AI: LLM Layer ──────── 7 sub-parts (base → 3 clients → factory)
phase4-part09  AI: RAG Pipeline ────── 6 sub-parts (PDF → chunk → embed → search)
phase4-part10  AI: Agents ──────────── 11 sub-parts (tools → memory → agent)
phase4-part11  AI: Workflows ──────── 6 sub-parts (base → orchestrator → 3 steps)
phase4-part12  AI: Service + Router ── 6 sub-parts (models → service → router)
phase4-part13  Notifications ──────── 8 sub-parts (models → email → templates)
phase4-part14  Export ──────────────── 6 sub-parts (CSV → S3 → router)
phase4-part15  Lambda Functions ────── 8 sub-parts (shared → 6 handlers)
phase4-part16  Frontend ───────────── 16 sub-parts (config → types → pages)
```

**Total: 16 overview docs + 88 implementation docs = 104 Phase 4 docs**
