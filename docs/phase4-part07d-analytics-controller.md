# 📈 Phase 4 Part 07d: Analytics — Router

> **"Six GET endpoints. No POST, no PUT, no DELETE. Analytics is read-only — it computes, it never mutates. Every response is cached. This is the simplest router in the project, but it powers the most impressive dashboard."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07d (Analytics HTTP Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part07c-analytics-cache-service.md](./phase4-part07c-analytics-cache-service.md) |
| **Next** | [phase4-part07e-analytics-connections-and-flows.md](./phase4-part07e-analytics-connections-and-flows.md) |
| **Files in This Doc** | 1 file (router.py) — 6 endpoints |
| **Time to Type** | ~20 minutes |
| **Difficulty** | Easy (all GET endpoints, configurable query params) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File: router.py — Full Source Code](#router)
3. [Endpoint-by-Endpoint Walkthrough](#walkthrough)
4. [What's Unique About This Router](#unique)
5. [How to Verify Your Work](#verify)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

The simplest router in the project — 6 GET endpoints, no request bodies, all cached.

| # | Endpoint | Response | Cache | Params |
|---|----------|----------|-------|--------|
| 1 | `GET /analytics/dashboard` | `DashboardData` | 5 min | None |
| 2 | `GET /analytics/streaks` | `AllStreaksResponse` | 30 min | None |
| 3 | `GET /analytics/weekly-summary` | `WeeklySummaryResponse` | 30 min | None |
| 4 | `GET /analytics/monthly-trend` | `MonthlyTrendResponse` | 1 hour | `habit_id?`, `days` |
| 5 | `GET /analytics/completion-rate` | `CompletionRateResponse` | 30 min | `days` |
| 6 | `GET /analytics/correlations` | `CorrelationResponse` | 1 hour | `days` (min 14) |

### What Makes This Router Special

- **All GET** — no mutations. Analytics reads from habits + habit_logs, never writes
- **All cached** — every response comes from Redis (1ms) or is computed then cached
- **Configurable periods** — `days` param lets the frontend request 7, 30, or 90 days
- **No path parameters** — all endpoints are at fixed paths under `/analytics/`

---

<a name="router"></a>
## 2. File: `router.py` — Full Source Code

### Type This Code: `backend/app/modules/analytics/router.py`

```python
# ============================================================================
# Analytics Module — Router (API Endpoints)
# ============================================================================
# ENDPOINTS:
#   GET /api/v1/analytics/dashboard       → Dashboard overview
#   GET /api/v1/analytics/streaks         → All habit streaks
#   GET /api/v1/analytics/weekly-summary  → This week vs last week
#   GET /api/v1/analytics/monthly-trend   → 30-day daily values (chart data)
#   GET /api/v1/analytics/completion-rate → Completion % per habit
#   GET /api/v1/analytics/correlations    → Habit-to-habit correlations
#
# ALL ENDPOINTS ARE READ-ONLY (GET only).
# ALL ENDPOINTS REQUIRE AUTHENTICATION.
# ALL RESPONSES ARE CACHED IN REDIS.
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query

import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.analytics.schemas import (
    AllStreaksResponse,
    CompletionRateResponse,
    CorrelationResponse,
    DashboardData,
    MonthlyTrendResponse,
    WeeklySummaryResponse,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.router import get_current_user_id
from app.redis_client import get_redis_client

router = APIRouter()


# ── Dependency: Get Analytics Service ──
async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AnalyticsService:
    return AnalyticsService(session, redis_client)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get(
    "/dashboard",
    response_model=DashboardData,
    summary="Get dashboard overview",
)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DashboardData:
    """
    Get the main dashboard data in a single request.

    Returns: today's progress, total habits, best current streak,
    and weekly completion percentage.

    Cached for 5 minutes. Invalidated when logs change.
    """
    return await service.get_dashboard(user_id)


@router.get(
    "/streaks",
    response_model=AllStreaksResponse,
    summary="Get all habit streaks",
)
async def get_streaks(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AllStreaksResponse:
    """
    Get current and longest streaks for all active habits.

    A streak is the number of consecutive days a habit was logged.
    Missing a day resets the current streak to 0.

    Ordered by current streak (longest first).
    Cached for 30 minutes.
    """
    return await service.get_streaks(user_id)


@router.get(
    "/weekly-summary",
    response_model=WeeklySummaryResponse,
    summary="Compare this week vs last week",
)
async def get_weekly_summary(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> WeeklySummaryResponse:
    """
    Compare this week's habit data against last week.

    For each habit: average value, days logged, and percentage change.
    Useful for spotting improvements or declines.

    Cached for 30 minutes.
    """
    return await service.get_weekly_summary(user_id)


@router.get(
    "/monthly-trend",
    response_model=MonthlyTrendResponse,
    summary="Get 30-day trend data for charts",
)
async def get_monthly_trend(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    habit_id: UUID | None = Query(
        default=None,
        description="Filter to a specific habit (omit for all habits)",
    ),
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Number of days to include (7-90)",
    ),
) -> MonthlyTrendResponse:
    """
    Get daily values for the last N days — powers the line chart.

    Returns one data point per day per habit.
    Days without logs show as null (chart draws gaps).

    Optionally filter to a single habit.
    Cached for 1 hour.
    """
    return await service.get_monthly_trend(user_id, habit_id, days)


@router.get(
    "/completion-rate",
    response_model=CompletionRateResponse,
    summary="Get completion rate per habit",
)
async def get_completion_rate(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Period to calculate over (7-90 days)",
    ),
) -> CompletionRateResponse:
    """
    Get completion percentage for each habit over a period.

    Completion = days_logged / total_possible_days × 100.

    Ordered by completion rate (highest first).
    Cached for 30 minutes.
    """
    return await service.get_completion_rates(user_id, days)


@router.get(
    "/correlations",
    response_model=CorrelationResponse,
    summary="Find correlations between habits",
)
async def get_correlations(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    days: int = Query(
        default=30,
        ge=14,          # Need at least 14 days for meaningful correlations
        le=90,
        description="Period to analyze (14-90 days)",
    ),
) -> CorrelationResponse:
    """
    Discover correlations between habit pairs.

    Uses Pearson correlation coefficient to find relationships.
    Example: "Your mood tends to be higher on days you sleep more" (r=0.72)

    Requires at least 5 overlapping data points per pair.
    Ordered by correlation strength (strongest first).
    Cached for 1 hour.
    """
    return await service.get_correlations(user_id, days)
```

---

<a name="walkthrough"></a>
## 3. Endpoint-by-Endpoint Walkthrough

### Analytics Service Dependency — Needs Redis

```python
async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AnalyticsService:
    return AnalyticsService(session, redis_client)
```

Same pattern as LogService — needs both session (for SQL queries) and Redis (for caching).

### Dashboard + Streaks + Weekly — No Parameters

```python
@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DashboardData:
    return await service.get_dashboard(user_id)
```

The simplest endpoints — just auth + service call. No query params needed because the data is always "for the current user, for now."

### Monthly Trend — Two Optional Params

```python
@router.get("/monthly-trend", response_model=MonthlyTrendResponse)
async def get_monthly_trend(
    ...,
    habit_id: UUID | None = Query(default=None, description="Filter to a specific habit"),
    days: int = Query(default=30, ge=7, le=90, description="Number of days (7-90)"),
) -> MonthlyTrendResponse:
    return await service.get_monthly_trend(user_id, habit_id, days)
```

- `habit_id: UUID | None` — optional filter. `None` = all habits. Specific UUID = one habit's trend
- `days: int = 30` — configurable period. Frontend offers "Last 7 days / Last 30 days / Last 90 days" buttons
- `ge=7, le=90` — Pydantic validates the range. Prevents absurdly large queries (1000 days)

### Correlations — Minimum 14 Days

```python
days: int = Query(default=30, ge=14, le=90, description="Period to analyze (14-90 days)")
```

Correlation's minimum is `ge=14` (not `ge=7` like others). Why? With fewer than 14 days, there aren't enough data points for statistically meaningful correlations. The service additionally requires 5 overlapping data points per habit pair.

### The Handler Pattern — Ultra-Thin

Every handler is 1 line:
```python
return await service.get_dashboard(user_id)
return await service.get_streaks(user_id)
return await service.get_weekly_summary(user_id)
return await service.get_monthly_trend(user_id, habit_id, days)
return await service.get_completion_rates(user_id, days)
return await service.get_correlations(user_id, days)
```

No data transformation, no error handling, no caching logic in the router — everything is in the service. The router is purely an HTTP translation layer.

---

<a name="unique"></a>
## 4. What's Unique About This Router

| Feature | Other Routers | Analytics Router |
|---------|--------------|-----------------|
| HTTP methods | GET, POST, PUT, DELETE | **GET only** |
| Request bodies | UserCreate, HabitCreate, LogCreate... | **None** |
| Mutations | Create, update, delete | **None — read-only** |
| Path params | `/{habit_id}`, `/{log_id}` | **None** |
| Query params | 0-1 per endpoint | 0-2 per endpoint (`days`, `habit_id`) |
| Caching | None | **Every response cached** |
| Handler complexity | 2-5 lines | **1 line each** |
| Return type | Single object or list | **Aggregated schemas** |

### Registration in main.py

Already registered (from Part 04d):
```python
from app.modules.analytics.router import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
```

---

<a name="verify"></a>
## 5. How to Verify Your Work

```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}' | jq -r '.access_token')

# 1. Dashboard
curl http://localhost/api/v1/analytics/dashboard \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"today_logged":4,"today_total":6,"today_completion_pct":66.7,...}

# 2. Streaks
curl http://localhost/api/v1/analytics/streaks \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"streaks":[{"habit_name":"Water","current_streak":15,...},...]}

# 3. Weekly Summary
curl http://localhost/api/v1/analytics/weekly-summary \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"week_start":"2026-09-21","habits":[{"this_week_avg":7.2,...},...]}

# 4. Monthly Trend (all habits, 30 days)
curl http://localhost/api/v1/analytics/monthly-trend \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"habits":[{"data_points":[{"date":"Sep-1","value":7.0},...]},...]}

# 5. Monthly Trend (specific habit, 7 days)
curl "http://localhost/api/v1/analytics/monthly-trend?habit_id=WATER_ID&days=7" \
  -H "Authorization: Bearer $TOKEN"

# 6. Completion Rate
curl http://localhost/api/v1/analytics/completion-rate \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"habits":[{"habit_name":"Water","completion_pct":93.3,...},...]}

# 7. Correlations
curl http://localhost/api/v1/analytics/correlations \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"correlations":[{"habit_a_name":"Sleep","habit_b_name":"Mood","correlation":0.72,...},...]}

# 8. Test days validation
curl "http://localhost/api/v1/analytics/correlations?days=5" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 422 (ge=14 — minimum 14 days)

# 9. Verify caching (second call should be faster)
time curl http://localhost/api/v1/analytics/streaks -H "Authorization: Bearer $TOKEN" -s -o /dev/null
# First call: ~100ms (SQL)
time curl http://localhost/api/v1/analytics/streaks -H "Authorization: Bearer $TOKEN" -s -o /dev/null
# Second call: ~5ms (cached!)

# 10. Check Swagger docs
# http://localhost/docs — "Analytics" section shows all 6 GET endpoints
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **All-GET module** | No mutations — read-only analytics | All 6 endpoints |
| 2 | **Configurable `days` param** | `Query(default=30, ge=7, le=90)` — user picks period | Trend, completion, correlation |
| 3 | **Different minimum per endpoint** | `ge=7` for trend, `ge=14` for correlations | Validation constraints |
| 4 | **Ultra-thin handlers** | 1 line per handler — all logic in service | All endpoints |
| 5 | **Cached responses** | Every response comes from Redis or is computed + cached | Via service layer |
| 6 | **Docstring as Swagger docs** | Python docstrings render in `/docs` Swagger UI | All endpoints |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: Why are all analytics endpoints GET instead of POST?
**A:** "Analytics is purely read-only — it computes insights from existing data. GET is semantically correct for retrieval operations and has practical benefits: GET responses can be cached by browsers and CDNs, bookmarked, and shared. POST would imply mutation, which doesn't happen here. The query parameters (days, habit_id) are simple enough for URL encoding."

### Q2: Why different minimum days for different endpoints?
**A:** "Data quality requirements differ. Trend charts make sense with 7 days — you can see a week of values. Correlations need at least 14 days (and 5 overlapping data points per pair) for statistically meaningful results. Pearson correlation with 3 data points is meaningless — random data could produce a high r value. 14 days gives enough data for the 5-point minimum across most habit pairs."

### Q3: How do the analytics endpoints perform under load?
**A:** "First request after cache invalidation: 100-200ms (SQL queries). All subsequent requests within the TTL window: 1-5ms (Redis cache hit). With 6 endpoints on dashboard load, that's either 600ms (cold) or 6ms (warm). The cold-start penalty only happens after the user logs a new entry (which invalidates the cache). For a personal health tracker, this is excellent — the user logs once, then views the dashboard many times."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 07c: Analytics Cache & Service](./phase4-part07c-analytics-cache-service.md) |
| ➡️ Next | [Phase 4 Part 07e: Analytics Connections & Flows](./phase4-part07e-analytics-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Analytics Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 07a | ✅ Done | Analytics Schemas & Exceptions |
| 07b | ✅ Done | Analytics Repository (★★★ Complex SQL) |
| 07c | ✅ Done | Analytics Cache & Service |
| **07d** | ✅ **You are here** | Analytics Router |
| 07e | ⬜ Next | Analytics Connections & Flows |

---

**End of Phase 4 Part 07d: Analytics Router**

*Six GET endpoints are live — dashboard, streaks, weekly summary, monthly trend, completion rates, and correlations. All cached, all authenticated, all read-only. Next: the final Analytics doc — flow diagrams showing the cache-aside pattern in action.*
