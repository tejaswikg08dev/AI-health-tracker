# 🏗️ Phase 4 Part 03: Shared Utilities & Middleware — Overview & Roadmap

> **"Shared code is the silent hero — every module depends on it, but nobody notices when it works perfectly."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Health Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 03 (split into 03a through 03h) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 (Shared) + Release 1.3 (Middleware) |
| **Files in this group** | 8 files |
| **Endpoints** | 0 (infrastructure — no routes) |
| **Total typing time** | ~70 minutes |
| **Previous** | [Part 02g — dependencies.py](./phase4-part02g-dependencies.md) |
| **Next** | [Part 04 — Auth Module Overview](./phase4-part04-auth-module-overview.md) |

---

## 🎯 What Is This Group?

This group creates TWO categories of shared code:

### Shared Utilities (03a–03e) — Reusable building blocks

| File | What It Provides | Used By |
|------|-----------------|---------|
| `exceptions.py` | 5 error types that map to HTTP status codes | EVERY module's exceptions.py |
| `base_schemas.py` | Pagination, error response, generic list response | EVERY module's schemas.py |
| `base_repository.py` | Generic CRUD: create, get, update, delete, count | EVERY module's repository.py |
| `date_utils.py` | UTC now, timezone conversion, week/month helpers | Analytics, Logs, AI |
| `logging.py` | Structured JSON logging for production | EVERY file that logs |

### Middleware (03f–03h) — Code that runs on EVERY request

| File | What It Does | When It Runs |
|------|-------------|-------------|
| `error_handler.py` | Catches exceptions → JSON response | On EVERY error |
| `logging_middleware.py` | Logs request method, path, duration, status | On EVERY request |
| `rate_limiter.py` | Checks Redis counter → blocks if over limit | On EVERY request |

---

## Real-World Analogy

**Shared utilities** are like kitchen tools (knives, cutting boards, measuring cups). Every chef uses them, but they don't belong to any one recipe.

**Middleware** is like the restaurant's front door protocol:
1. Security guard checks the guest list (rate limiter)
2. Receptionist logs the guest's arrival time (logging)
3. If something goes wrong, the manager handles complaints (error handler)

This happens for EVERY guest, regardless of whether they ordered pasta or steak.

---

## 🛠️ Tech Stack — What's NEW

| Technology | Purpose | NEW? |
|-----------|---------|------|
| **Python ABC** (Abstract Base Class) | Define base error hierarchy | 🆕 **NEW** |
| **Python Generics** (TypeVar, Generic[T]) | Type-safe reusable CRUD | 🆕 **NEW** |
| **Pydantic Generic models** | PaginatedResponse[T] works with any type | 🆕 **NEW** |
| **zoneinfo** (Python 3.9+) | Timezone handling without pytz | 🆕 **NEW** |
| **structlog** | Structured JSON logging | 🆕 **NEW** |
| **Starlette BaseHTTPMiddleware** | Middleware pattern for FastAPI | 🆕 **NEW** |

---

## 📄 Sub-Parts — Build Order (03a → 03h)

```
┌──────────────────────────────────────────────────────────┐
│                    BUILD ORDER                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  SHARED UTILITIES (no dependencies between them):        │
│                                                          │
│  03a  shared/exceptions.py       Error hierarchy         │
│  03b  shared/base_schemas.py     Pydantic base models    │
│  03c  shared/base_repository.py  Generic CRUD            │
│  03d  shared/date_utils.py       Date/timezone helpers   │
│  03e  shared/logging.py          Structlog config        │
│                                                          │
│  MIDDLEWARE (03f depends on 03a and 03e):                │
│                                                          │
│  03f  middleware/error_handler.py  Exception → JSON      │
│   ▼                                                      │
│  03g  middleware/logging_middleware.py  Request logger    │
│   ▼                                                      │
│  03h  middleware/rate_limiter.py  Redis rate limiting ⭐  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🗂️ Complete File List (8 files)

```
backend/app/
├── shared/
│   ├── __init__.py                  ← (create empty file)
│   ├── exceptions.py                ← 03a
│   ├── base_schemas.py              ← 03b
│   ├── base_repository.py           ← 03c
│   ├── date_utils.py                ← 03d
│   └── logging.py                   ← 03e
│
└── middleware/
    ├── __init__.py                  ← (create empty file)
    ├── error_handler.py             ← 03f
    ├── logging_middleware.py        ← 03g
    └── rate_limiter.py              ← 03h
```

---

## 🔐 Key Concepts

### Exception Hierarchy (03a)
```
BaseAppError (500)
├── NotFoundError (404)      → "Habit not found"
├── ConflictError (409)      → "Email already exists"
├── ValidationError (422)    → "Future date not allowed"
├── UnauthorizedError (401)  → "Token expired"
└── ForbiddenError (403)     → "Can't access other user's data"
```

Every module creates SPECIFIC errors from these BASE errors:
```
NotFoundError ← HabitNotFoundError, LogNotFoundError
ConflictError ← UserAlreadyExistsError, DuplicateLogError
```

### Generic CRUD (03c)
```python
class BaseRepository(Generic[ModelType]):
    async def create(**kwargs) → ModelType
    async def get_by_id(id: UUID) → ModelType | None
    async def get_all(offset, limit) → list[ModelType]
    async def update(id, **kwargs) → ModelType | None
    async def delete(id) → bool
    async def count() → int
```
Write once. Every module's repository inherits these 6 methods. Only write CUSTOM queries.

### Middleware Chain (03f-03h)
```
Request → CORS → LoggingMiddleware → RateLimiter → ErrorHandler → Router
Response ← CORS ← LoggingMiddleware ← RateLimiter ← ErrorHandler ← Router
```
Order matters. CORS must be FIRST (handles preflight OPTIONS). Logging wraps everything (measures total time).

---

## ✅ Verification Checklist (After All 8 Sub-Parts)

```python
# In Python REPL:
from app.shared.exceptions import NotFoundError, ConflictError
from app.shared.base_schemas import PaginatedResponse
from app.shared.date_utils import today_utc, start_of_week
from app.shared.logging import get_logger

# These should all work without errors:
print(today_utc())
print(start_of_week())
logger = get_logger("test")
logger.info("test_message", key="value")

# Middleware won't be testable until main.py is created (Part 04k)
```

---

## 🎤 Interview Q&A

### Q: "How do you handle errors consistently across your API?"

> "A five-level exception hierarchy. `BaseAppError` is the root with a status_code, error_code, and message. Subclasses like `NotFoundError` (404), `ConflictError` (409), `UnauthorizedError` (401) inherit from it. Each module creates specific errors — `HabitNotFoundError` extends `NotFoundError` with a specific error_code 'HABIT_NOT_FOUND'. A global error handler middleware catches any `BaseAppError` and converts it to a JSON response: `{\"error_code\": \"HABIT_NOT_FOUND\", \"message\": \"Habit not found\", \"detail\": null}`. This means every error from every endpoint follows the exact same format — the frontend can parse them consistently."

### Q: "What is the Generic Repository pattern?"

> "A base class with type parameter `Generic[ModelType]` that implements CRUD operations once — create, get_by_id, get_all, update, delete, count. Every module's repository inherits these 6 methods and only adds CUSTOM queries. `UserRepository(BaseRepository[User])` gets all 6 CRUD methods for free and adds `get_by_email()`. This is the same as Spring Boot's `JpaRepository<T, ID>` — write the common stuff once, specialize per entity."

### Q: "How does your middleware chain work?"

> "Three middleware layers wrap every request: LoggingMiddleware logs method, path, status code, and response time with a unique request_id. RateLimiterMiddleware checks a Redis counter per IP and endpoint — 30r/s for API, 2r/s for AI, 5r/min for login. ErrorHandler catches exceptions and returns structured JSON. The order matters — CORS is outermost (handles preflight), logging wraps everything (measures total time), error handler is closest to the route (catches business exceptions)."

---

## 📚 Navigation

| Document | Title |
|----------|-------|
| **This document** | **Shared + Middleware Overview** |
| [Part 03a](./phase4-part03a-exceptions.md) | Exception Hierarchy — 5 Error Types |
| [Part 03b](./phase4-part03b-base-schemas.md) | Base Schemas — Pagination, Generic Response |
| [Part 03c](./phase4-part03c-base-repository.md) | Generic CRUD — TypeVar, Generic[T] ⭐ |
| [Part 03d](./phase4-part03d-date-utils.md) | Date Utilities — Timezone, Week/Month |
| [Part 03e](./phase4-part03e-logging.md) | Structured Logging — Structlog JSON |
| [Part 03f](./phase4-part03f-error-handler.md) | Error Handler — Exception → JSON |
| [Part 03g](./phase4-part03g-logging-middleware.md) | Request Logger — Timing, Request ID |
| [Part 03h](./phase4-part03h-rate-limiter.md) | Rate Limiter — Redis Sliding Window ⭐ |

---

*Start with [Part 03a — Exceptions](./phase4-part03a-exceptions.md) →*
