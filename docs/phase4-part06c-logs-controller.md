# 📝 Phase 4 Part 06c: Logs — Router

> **"The GET /logs endpoint is the most flexible in the app — it handles single dates, date ranges, habit filters, and defaults. One endpoint, four query patterns. This is how real APIs work."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 06c (Logs HTTP Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.2 — Daily Logging |
| **Previous** | [phase4-part06b-logs-repository-service.md](./phase4-part06b-logs-repository-service.md) |
| **Next** | [phase4-part06d-logs-connections-and-flows.md](./phase4-part06d-logs-connections-and-flows.md) |
| **Files in This Doc** | 1 file (router.py) — 5 endpoints |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (query aliases, conditional routing, bulk POST, date params) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File: router.py — Full Source Code](#router)
3. [Endpoint-by-Endpoint Walkthrough](#walkthrough)
4. [What's New Compared to Habits Router](#whats-new)
5. [How to Verify Your Work](#verify)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Five endpoints, including the most complex GET endpoint in the app:

| # | Method | Path | What's Special |
|---|--------|------|---------------|
| 1 | `POST` | `/logs` | Single log creation |
| 2 | `POST` | `/logs/bulk` | Bulk daily check-in (array of entries) |
| 3 | `GET` | `/logs` | **Flexible filtering** — 4 query patterns in one endpoint |
| 4 | `PUT` | `/logs/{log_id}` | Update value/notes |
| 5 | `DELETE` | `/logs/{log_id}` | Hard delete |

### The Flexible GET — 4 Patterns in One Endpoint

```
GET /logs?date=2026-09-26                    → "Today's logs" (check-in page)
GET /logs?start=2026-09-01&end=2026-09-30    → "September" (monthly chart)
GET /logs?start=...&end=...&habit_id=...     → "Water this month" (habit chart)
GET /logs                                     → Defaults to today
```

This is ONE endpoint that handles ALL log retrieval patterns. The service picks the right query based on which parameters are provided.

---

<a name="router"></a>
## 2. File: `router.py` — Full Source Code

### Type This Code: `backend/app/modules/logs/router.py`

```python
# ============================================================================
# Logs Module — Router (API Endpoints)
# ============================================================================
# ENDPOINTS:
#   POST   /api/v1/logs           → Create a single log entry
#   POST   /api/v1/logs/bulk      → Log multiple habits at once (daily check-in)
#   GET    /api/v1/logs            → Get logs (by date or date range)
#   PUT    /api/v1/logs/:id        → Update a log entry
#   DELETE /api/v1/logs/:id        → Delete a log entry
#
# ALL ENDPOINTS REQUIRE AUTHENTICATION.
# ============================================================================

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.auth.router import get_current_user_id
from app.modules.logs.schemas import (
    BulkLogCreate,
    LogCreate,
    LogResponse,
    LogUpdate,
)
from app.modules.logs.service import LogService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()


# ── Dependency: Get Log Service ──
async def get_log_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> LogService:
    return LogService(session, redis_client)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "",
    response_model=LogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a habit for a specific date",
)
async def create_log(
    data: LogCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
) -> LogResponse:
    """
    Create a single log entry for a habit on a specific date.

    - Validates the value matches the habit type (numeric/boolean/scale)
    - Prevents future dates
    - Prevents duplicate logs (same habit + same date)

    For logging all habits at once, use POST /logs/bulk instead.
    """
    log = await service.create_log(user_id, data)
    return LogResponse.model_validate(log)


@router.post(
    "/bulk",
    response_model=list[LogResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Log multiple habits at once (daily check-in)",
)
async def bulk_create_logs(
    data: BulkLogCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
) -> list[LogResponse]:
    """
    Log multiple habits in a single request (daily check-in "Save All").

    If a log already exists for a habit on that date, it's UPDATED (not rejected).
    This makes the daily check-in page idempotent — user can hit save multiple times.

    All entries are saved atomically — if the request fails, none are saved.
    """
    logs = await service.bulk_create_logs(user_id, data)
    return [LogResponse.model_validate(log) for log in logs]


@router.get(
    "",
    response_model=list[LogResponse],
    summary="Get logs by date or date range",
)
async def get_logs(
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
    date: date | None = Query(
        default=None,
        description="Get logs for a specific date (e.g., 2026-09-26)",
    ),
    start_date: date | None = Query(
        default=None,
        alias="start",
        description="Start of date range (inclusive)",
    ),
    end_date: date | None = Query(
        default=None,
        alias="end",
        description="End of date range (inclusive)",
    ),
    habit_id: UUID | None = Query(
        default=None,
        description="Filter by a specific habit",
    ),
) -> list[LogResponse]:
    """
    Get log entries with flexible filtering.

    Usage patterns:
    - GET /logs?date=2026-09-26           → Today's logs (for check-in page)
    - GET /logs?start=2026-09-01&end=2026-09-30  → Month's logs (for charts)
    - GET /logs?start=...&end=...&habit_id=...    → Specific habit's logs
    - GET /logs                            → Defaults to today

    At least one filter (date or start+end) should be provided.
    Without any filter, defaults to today's date.
    """
    if date:
        # Single date query
        logs = await service.get_logs_for_date(user_id, date)
    elif start_date and end_date:
        # Date range query
        logs = await service.get_logs_for_range(
            user_id, start_date, end_date, habit_id
        )
    else:
        # Default: today
        from app.shared.date_utils import today_utc
        logs = await service.get_logs_for_date(user_id, today_utc())

    return [LogResponse.model_validate(log) for log in logs]


@router.put(
    "/{log_id}",
    response_model=LogResponse,
    summary="Update a log entry",
)
async def update_log(
    log_id: UUID,
    data: LogUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
) -> LogResponse:
    """
    Update an existing log entry's value or notes.

    Only provided fields are updated. The habit type validation still applies.
    """
    log = await service.update_log(user_id, log_id, data)
    return LogResponse.model_validate(log)


@router.delete(
    "/{log_id}",
    response_model=SuccessResponse,
    summary="Delete a log entry",
)
async def delete_log(
    log_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
) -> SuccessResponse:
    """
    Delete a log entry (hard delete).

    Used when a user logged incorrect data and wants to remove it.
    """
    await service.delete_log(user_id, log_id)
    return SuccessResponse(message="Log entry deleted successfully")
```

---

<a name="walkthrough"></a>
## 3. Endpoint-by-Endpoint Walkthrough

### Log Service Dependency — Includes Redis

```python
async def get_log_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> LogService:
    return LogService(session, redis_client)
```

Unlike the HabitService dependency (session only), LogService also gets Redis — for cache invalidation. The service uses Redis to delete stale analytics cache keys when logs change.

### POST `/logs` — Single Log

```python
async def create_log(
    data: LogCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
) -> LogResponse:
    log = await service.create_log(user_id, data)
    return LogResponse.model_validate(log)
```

Thin handler — 2 lines. The service does all validation (future date, habit exists, no duplicate, type match).

### POST `/logs/bulk` — Daily Check-In

```python
async def bulk_create_logs(
    data: BulkLogCreate,
    ...
) -> list[LogResponse]:
    logs = await service.bulk_create_logs(user_id, data)
    return [LogResponse.model_validate(log) for log in logs]
```

- `BulkLogCreate` body contains `log_date` + `entries[]` — all habits for one day
- Returns a list of created/updated logs
- The service handles upsert — existing logs are updated, new ones are created

### GET `/logs` — The Flexible Query Endpoint (★ Most Complex)

```python
async def get_logs(
    user_id: UUID = Depends(get_current_user_id),
    service: LogService = Depends(get_log_service),
    date: date | None = Query(default=None, description="..."),
    start_date: date | None = Query(default=None, alias="start", description="..."),
    end_date: date | None = Query(default=None, alias="end", description="..."),
    habit_id: UUID | None = Query(default=None, description="..."),
) -> list[LogResponse]:
```

**Four query parameters, all optional:**

| Parameter | URL Example | Python Variable | What It Does |
|-----------|------------|----------------|-------------|
| `date` | `?date=2026-09-26` | `date` | Single day |
| `start` | `?start=2026-09-01` | `start_date` | Range start |
| `end` | `?end=2026-09-30` | `end_date` | Range end |
| `habit_id` | `?habit_id=uuid` | `habit_id` | Filter by habit |

**What is `alias="start"`?**
```python
start_date: date | None = Query(default=None, alias="start")
```
- The URL uses `?start=2026-09-01` (short, clean)
- The Python variable is `start_date` (descriptive)
- `alias="start"` maps between them: URL param `start` → Python variable `start_date`
- Without alias, the URL would need `?start_date=2026-09-01` (less clean)

**Conditional routing logic:**
```python
if date:
    logs = await service.get_logs_for_date(user_id, date)
elif start_date and end_date:
    logs = await service.get_logs_for_range(user_id, start_date, end_date, habit_id)
else:
    from app.shared.date_utils import today_utc
    logs = await service.get_logs_for_date(user_id, today_utc())
```

Three paths:
1. `?date=2026-09-26` → single date query (check-in page loads today's logs)
2. `?start=...&end=...` → date range query (charts, analytics). Optional `&habit_id=...` narrows to one habit
3. No params → default to today (convenience for the dashboard)

**Why one endpoint, not three?**
- `GET /logs/today`, `GET /logs/range`, `GET /logs/habit` — three endpoints would be redundant
- REST convention: one resource collection (`/logs`), filter via query params
- Same pattern used by GitHub API, Stripe API, AWS APIs

### PUT `/logs/{log_id}` — Update

```python
async def update_log(log_id: UUID, data: LogUpdate, ...):
    log = await service.update_log(user_id, log_id, data)
    return LogResponse.model_validate(log)
```

- Standard partial update (same as habits)
- The service re-validates the value against the habit type

### DELETE `/logs/{log_id}` — Hard Delete

```python
async def delete_log(log_id: UUID, ...):
    await service.delete_log(user_id, log_id)
    return SuccessResponse(message="Log entry deleted successfully")
```

- Unlike habits (soft delete), this is a real DELETE — the row is gone
- Used when the user entered wrong data and wants to correct it

---

<a name="whats-new"></a>
## 4. What's New Compared to Habits Router

| Feature | Habits Router | Logs Router |
|---------|-------------|-------------|
| Service dependency | Session only | Session + Redis (for cache) |
| Bulk endpoint | None | `POST /logs/bulk` (array of entries) |
| Query complexity | One optional `?include_archived` | Four params: `date`, `start`, `end`, `habit_id` |
| Query aliases | None | `alias="start"` maps URL `?start=` to Python `start_date` |
| Conditional logic in handler | None | if/elif/else routing in GET |
| Delete behavior | Soft delete (archive) | Hard delete (real DELETE) |
| `date` type in params | None | `date \| None = Query()` parses ISO date strings |

### Registration in main.py

Already registered (from Part 04d):

```python
from app.modules.logs.router import router as logs_router
app.include_router(logs_router, prefix="/api/v1/logs", tags=["Logs"])
```

---

<a name="verify"></a>
## 5. How to Verify Your Work

```bash
# Login and get token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}' | jq -r '.access_token')

# Get a habit ID
HABIT_ID=$(curl -s http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')

# 1. Single log
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"habit_id\":\"$HABIT_ID\",\"log_date\":\"2026-09-26\",\"value_numeric\":7}"
# Expected: 201

# 2. Bulk log
curl -X POST http://localhost/api/v1/logs/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"log_date\":\"2026-09-25\",\"entries\":[{\"habit_id\":\"$HABIT_ID\",\"value_numeric\":8}]}"
# Expected: 201

# 3. Get today's logs
curl "http://localhost/api/v1/logs?date=2026-09-26" \
  -H "Authorization: Bearer $TOKEN"
# Expected: array with the log entry

# 4. Get date range
curl "http://localhost/api/v1/logs?start=2026-09-25&end=2026-09-26" \
  -H "Authorization: Bearer $TOKEN"
# Expected: logs for both dates

# 5. Get default (today)
curl http://localhost/api/v1/logs \
  -H "Authorization: Bearer $TOKEN"
# Expected: today's logs

# 6. Test duplicate rejection
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"habit_id\":\"$HABIT_ID\",\"log_date\":\"2026-09-26\",\"value_numeric\":9}"
# Expected: 409 DUPLICATE_LOG

# 7. Test future date
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"habit_id\":\"$HABIT_ID\",\"log_date\":\"2099-12-31\",\"value_numeric\":5}"
# Expected: 422 FUTURE_DATE

# 8. Check Swagger docs
# http://localhost/docs — "Logs" section should show all 5 endpoints
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Query `alias`** | Map URL param name to Python variable name | `alias="start"` |
| 2 | **`date` type in Query** | Pydantic auto-parses `"2026-09-26"` → `date` object | GET params |
| 3 | **Conditional routing** | if/elif/else in handler based on which params provided | GET handler |
| 4 | **Default query behavior** | No params → default to today | GET handler |
| 5 | **Bulk POST** | Accept array body, return array response | POST /bulk |
| 6 | **Idempotent bulk** | Saving twice = same result (upsert) | POST /bulk |
| 7 | **Redis in service dependency** | LogService gets Redis for cache invalidation | `get_log_service` |
| 8 | **Hard delete endpoint** | Actual DELETE (not soft) for correcting mistakes | DELETE |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: Why one GET endpoint with query params instead of multiple endpoints?
**A:** "REST convention. The `/logs` resource represents the log collection. Filtering is done via query parameters — `?date=`, `?start=&end=`, `?habit_id=`. This is how GitHub, Stripe, and most APIs work. Multiple endpoints (`/logs/today`, `/logs/range`) would be redundant and harder to document. The single endpoint with flexible params covers all use cases: the check-in page needs today's logs, charts need date ranges, and habit detail pages need per-habit filtering."

### Q2: What does `alias="start"` do in Query()?
**A:** "It decouples the URL parameter name from the Python variable name. The URL uses `?start=2026-09-01` (concise, API-consumer-friendly), while the Python code uses `start_date` (descriptive, follows naming conventions). Without the alias, the URL would need `?start_date=2026-09-01` — less clean. This is a common FastAPI pattern for keeping both the API and the codebase clean."

### Q3: How is the bulk endpoint different from calling POST /logs five times?
**A:** "Three advantages: atomicity, performance, and idempotency. Atomically, all entries succeed or fail together — no partial saves. Performance-wise, one HTTP request instead of five reduces network overhead. And the upsert behavior makes it idempotent — the user can hit 'Save' multiple times on the check-in page without duplicate errors. Five individual POST calls would each reject duplicates and wouldn't be atomic."

### Q4: Why does the Logs router need Redis but the Habits router doesn't?
**A:** "The Log service invalidates the analytics cache in Redis whenever logs change. Streaks, weekly summaries, and correlations are cached because the SQL queries are expensive. When a log is created, updated, or deleted, stale cache keys must be deleted. Habits don't affect cached analytics directly — only log data drives those calculations. So the Habits service doesn't need Redis."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 06b: Logs Repository & Service](./phase4-part06b-logs-repository-service.md) |
| ➡️ Next | [Phase 4 Part 06d: Logs Connections & Flows](./phase4-part06d-logs-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Logs Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 06a | ✅ Done | Logs Models, Exceptions, Schemas & Migration |
| 06b | ✅ Done | Logs Repository & Service |
| **06c** | ✅ **You are here** | Logs Router |
| 06d | ⬜ Next | Logs Connections & Flows |

---

**End of Phase 4 Part 06c: Logs Router**

*All 5 log endpoints are live — single log, bulk check-in, flexible GET filtering, update, and delete. The Logs module is functionally complete. Next: flow diagrams connecting everything together.*
