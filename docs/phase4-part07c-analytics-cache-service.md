# 📈 Phase 4 Part 07c: Analytics — Cache Layer & Service

> **"The cache-aside pattern turns a 200ms SQL query into a 1ms Redis lookup. The Pearson correlation turns raw numbers into 'your mood is higher on days you sleep more.' This file is where data becomes insight."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07c (Analytics Cache + Business Logic) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part07b-analytics-repository-sql.md](./phase4-part07b-analytics-repository-sql.md) |
| **Next** | [phase4-part07d-analytics-controller.md](./phase4-part07d-analytics-controller.md) |
| **Files in This Doc** | 2 files (cache.py, service.py) |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Hard (cache-aside pattern, JSON serialization, Pearson formula, data transformation) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: cache.py — Redis Cache Layer](#cache)
3. [File 2: service.py — Cache-Aside + Pearson Correlation](#service)
4. [Deep Dive: Pearson Correlation](#pearson)
5. [Design Decisions](#design-decisions)
6. [How to Verify Your Work](#verify)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Two files that work together:
- **cache.py** — a clean Redis wrapper with typed accessors and TTL management
- **service.py** — orchestrates cache checks, database queries, data transformation, and Pearson correlation computation

### The Cache-Aside Pattern (Every Service Method)

```
Request → Service:
  1. cache.get_streaks(user_id) → Redis GET
  2a. HIT? → Return cached data (1ms)
  2b. MISS? → repo.get_streaks(user_id) → SQL query (100ms)
           → Transform to Pydantic schema
           → cache.set_streaks(user_id, data) → Redis SET
           → Return fresh data
```

Every public method in the service follows this exact pattern. The cache class handles JSON serialization/deserialization and TTL.

---

<a name="cache"></a>
## 2. File 1: `cache.py` — Redis Cache Layer

### Type This Code: `backend/app/modules/analytics/cache.py`

```python
# ============================================================================
# Analytics Module — Redis Cache Layer
# ============================================================================
# WHAT THIS FILE DOES:
#   Caches expensive analytics query results in Redis.
#   The dashboard loads faster because it reads from cache (< 1ms)
#   instead of running complex SQL queries (50-200ms).
#
# CACHING STRATEGY:
#   - Cache key format: "analytics:{user_id}:{query_type}"
#   - TTL (Time-To-Live): 30 min for most analytics, 5 min for dashboard
#   - Invalidation: cache is cleared when user creates/updates/deletes a log
#     (done in LogService._invalidate_cache)
#
# WHY CACHE ANALYTICS (not raw data):
#   Streak calculation runs 4 CTEs with window functions — ~100ms per query.
#   The dashboard calls 4 endpoints on load → 400ms just for analytics SQL.
#   With cache: 4 Redis GETs → ~4ms total.
#
# CACHE INVALIDATION STRATEGY:
#   "There are only two hard things in Computer Science:
#    cache invalidation and naming things." — Phil Karlton
#
#   Our approach: DELETE on write (simple, correct, slightly wasteful).
#   When a log is created/updated/deleted:
#   1. LogService calls _invalidate_cache(user_id)
#   2. That deletes ALL analytics:user_id:* keys from Redis
#   3. Next dashboard load recalculates fresh data
#   4. Fresh data is cached again for 30 minutes
#
#   Trade-off: First request after a log change is slow (100ms).
#   All subsequent requests are fast (1ms) until the next change.
#   For a personal health tracker, this is perfect.
# ============================================================================

import json
from typing import Any

import redis.asyncio as redis

from app.shared.logging import get_logger

logger = get_logger(__name__)

# Cache TTLs (seconds)
CACHE_TTL_DASHBOARD = 300       # 5 minutes — dashboard data changes often
CACHE_TTL_STREAKS = 1800        # 30 minutes — streaks only change once per day
CACHE_TTL_WEEKLY = 1800         # 30 minutes
CACHE_TTL_MONTHLY = 3600        # 1 hour — monthly trend is stable
CACHE_TTL_COMPLETION = 1800     # 30 minutes
CACHE_TTL_CORRELATION = 3600    # 1 hour — correlations are expensive + stable


class AnalyticsCache:
    """
    Redis cache for analytics results.

    Each method follows the same pattern:
    1. Build the cache key
    2. Try to GET from Redis
    3. If hit → return cached JSON (parsed back to Python)
    4. If miss → return None (caller computes fresh data and calls set_*)

    WHY a separate cache class (not inline in service):
    1. Testable — mock the cache in unit tests without mocking Redis
    2. Swappable — could change to memcached or in-memory cache
    3. Clean — service focuses on business logic, cache handles caching
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # ── Generic get/set ──

    async def get(self, key: str) -> Any | None:
        """
        Get a cached value by key.
        Returns parsed JSON or None if not found.
        Silently handles Redis errors (cache miss is fine, crash is not).
        """
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug("cache_hit", key=key)
                return json.loads(data)
            logger.debug("cache_miss", key=key)
            return None
        except Exception:
            logger.warning("cache_get_error", key=key)
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in cache with TTL (auto-expires).
        value is JSON-serialized. Redis stores it as a string.
        """
        try:
            serialized = json.dumps(value, default=str)  # default=str handles UUID, date
            await self.redis.setex(key, ttl, serialized)
            logger.debug("cache_set", key=key, ttl=ttl)
        except Exception:
            logger.warning("cache_set_error", key=key)

    async def invalidate_user(self, user_id: str) -> None:
        """Delete ALL cached analytics for a user."""
        try:
            pattern = f"analytics:{user_id}:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await self.redis.delete(*keys)
                logger.debug("cache_invalidated", user_id=user_id, keys_deleted=len(keys))
        except Exception:
            logger.warning("cache_invalidate_error", user_id=user_id)

    # ── Typed accessors ──

    def _key(self, user_id: str, query_type: str) -> str:
        return f"analytics:{user_id}:{query_type}"

    async def get_dashboard(self, user_id: str) -> dict | None:
        return await self.get(self._key(user_id, "dashboard"))

    async def set_dashboard(self, user_id: str, data: dict) -> None:
        await self.set(self._key(user_id, "dashboard"), data, CACHE_TTL_DASHBOARD)

    async def get_streaks(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "streaks"))

    async def set_streaks(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "streaks"), data, CACHE_TTL_STREAKS)

    async def get_weekly(self, user_id: str) -> dict | None:
        return await self.get(self._key(user_id, "weekly"))

    async def set_weekly(self, user_id: str, data: dict) -> None:
        await self.set(self._key(user_id, "weekly"), data, CACHE_TTL_WEEKLY)

    async def get_monthly(self, user_id: str, habit_id: str | None = None) -> dict | None:
        suffix = f"monthly:{habit_id}" if habit_id else "monthly:all"
        return await self.get(self._key(user_id, suffix))

    async def set_monthly(self, user_id: str, data: dict, habit_id: str | None = None) -> None:
        suffix = f"monthly:{habit_id}" if habit_id else "monthly:all"
        await self.set(self._key(user_id, suffix), data, CACHE_TTL_MONTHLY)

    async def get_completion(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "completion"))

    async def set_completion(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "completion"), data, CACHE_TTL_COMPLETION)

    async def get_correlations(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "correlations"))

    async def set_correlations(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "correlations"), data, CACHE_TTL_CORRELATION)
```

### Key Concepts in cache.py

**`json.dumps(value, default=str)`**
- Converts Python dict/list to a JSON string for Redis storage
- `default=str` — when JSON encounters a type it can't serialize (UUID, date), it calls `str()` on it. `UUID("abc-123")` → `"abc-123"`, `date(2026,9,26)` → `"2026-09-26"`

**`json.loads(data)`**
- Converts JSON string back to Python dict/list when reading from cache
- UUIDs and dates come back as strings — Pydantic handles the conversion when constructing schemas

**TTL Constants at Module Level**
```python
CACHE_TTL_DASHBOARD = 300       # 5 minutes
CACHE_TTL_CORRELATION = 3600    # 1 hour
```
- Module-level constants — easy to find and change
- Different TTLs for different analytics based on how frequently the data changes
- Dashboard changes often (user is logging right now) → short TTL
- Correlations are expensive and stable → long TTL

**Fail-Open Pattern (Every Method)**
```python
try:
    data = await self.redis.get(key)
except Exception:
    return None  # Cache failure = cache miss, NOT application failure
```
- If Redis is down, every cache call returns `None` (miss)
- The service computes fresh data from the database — slower but correct
- The application NEVER crashes because of a cache failure

**Typed Accessors**
```python
async def get_streaks(self, user_id: str) -> list | None:
    return await self.get(self._key(user_id, "streaks"))
```
- Instead of `cache.get("analytics:uuid:streaks")` (typo-prone), call `cache.get_streaks(uuid)`
- Consistent key naming via `_key()` — all keys follow `analytics:{user_id}:{type}`
- Monthly trend has a variant: `monthly:all` vs `monthly:{habit_id}` — key includes the filter

---

<a name="service"></a>
## 3. File 2: `service.py` — Cache-Aside + Pearson Correlation

### Type This Code: `backend/app/modules/analytics/service.py`

```python
# ============================================================================
# Analytics Module — Service Layer
# ============================================================================
# WHAT THIS FILE DOES:
#   Orchestrates between the repository (SQL queries) and cache (Redis).
#   Transforms raw query results into structured response schemas.
#   Computes correlations in Python (not SQL).
#
# CACHE-ASIDE PATTERN (Read-Through):
#   1. Check cache → if hit, return cached data
#   2. If miss → query database → transform data → cache result → return
#
#   This is the most common caching pattern in production systems.
#   The service is the "single source of truth" for what gets cached.
#
# DATA TRANSFORMATION:
#   Repository returns raw dicts (from SQL rows).
#   Service transforms them into typed Pydantic schemas.
#   This separation keeps SQL in the repo and business logic in the service.
# ============================================================================

import math
from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.cache import AnalyticsCache
from app.modules.analytics.exceptions import InsufficientDataError
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import (
    AllStreaksResponse,
    CompletionRateResponse,
    CorrelationResponse,
    CorrelationResult,
    DashboardData,
    HabitCompletionRate,
    HabitTrendData,
    HabitWeeklySummary,
    MonthlyTrendResponse,
    StreakInfo,
    TrendDataPoint,
    WeeklySummaryResponse,
)
from app.shared.date_utils import (
    end_of_week,
    start_of_week,
    today_utc,
    days_ago,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """
    Analytics service — computes and caches all analytics data.
    Every public method follows the cache-aside pattern.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.repo = AnalyticsRepository(session)
        self.cache = AnalyticsCache(redis_client)
        self.session = session

    async def get_dashboard(self, user_id: UUID) -> DashboardData:
        """Dashboard overview — cached 5 minutes."""
        uid = str(user_id)
        cached = await self.cache.get_dashboard(uid)
        if cached:
            return DashboardData(**cached)

        progress = await self.repo.get_today_progress(user_id)
        week_pct = await self.repo.get_week_completion(user_id)
        streaks_raw = await self.repo.get_streaks(user_id)

        total = progress["total_habits"]
        logged = progress["logged_today"]
        today_pct = round((logged / total * 100) if total > 0 else 0, 1)

        best_streak = None
        if streaks_raw:
            top = max(streaks_raw, key=lambda s: s["current_streak"])
            if top["current_streak"] > 0:
                best_streak = StreakInfo(
                    habit_id=top["habit_id"],
                    habit_name=top["habit_name"],
                    habit_color=top["habit_color"],
                    habit_icon=top["habit_icon"],
                    current_streak=top["current_streak"],
                    longest_streak=top["longest_streak"],
                    last_logged_date=top["last_logged_date"],
                )

        dashboard = DashboardData(
            today_logged=logged, today_total=total,
            today_completion_pct=today_pct, total_active_habits=total,
            current_best_streak=best_streak,
            week_completion_pct=round(week_pct, 1),
        )
        await self.cache.set_dashboard(uid, dashboard.model_dump())
        return dashboard

    async def get_streaks(self, user_id: UUID) -> AllStreaksResponse:
        """All habit streaks — cached 30 minutes."""
        uid = str(user_id)
        cached = await self.cache.get_streaks(uid)
        if cached:
            return AllStreaksResponse(streaks=[StreakInfo(**s) for s in cached])

        rows = await self.repo.get_streaks(user_id)
        streaks = [
            StreakInfo(
                habit_id=row["habit_id"], habit_name=row["habit_name"],
                habit_color=row["habit_color"], habit_icon=row["habit_icon"],
                current_streak=row["current_streak"],
                longest_streak=row["longest_streak"],
                last_logged_date=row["last_logged_date"],
            )
            for row in rows
        ]
        response = AllStreaksResponse(streaks=streaks)
        await self.cache.set_streaks(uid, [s.model_dump() for s in streaks])
        return response

    async def get_weekly_summary(self, user_id: UUID) -> WeeklySummaryResponse:
        """This week vs last week — cached 30 minutes."""
        uid = str(user_id)
        cached = await self.cache.get_weekly(uid)
        if cached:
            return WeeklySummaryResponse(**cached)

        rows = await self.repo.get_weekly_summary(user_id)
        habits = []
        for row in rows:
            this_avg = float(row["this_week_avg"]) if row["this_week_avg"] else None
            last_avg = float(row["last_week_avg"]) if row["last_week_avg"] else None
            change_pct = None
            if this_avg is not None and last_avg is not None and last_avg > 0:
                change_pct = round(((this_avg - last_avg) / last_avg) * 100, 1)

            habits.append(HabitWeeklySummary(
                habit_id=row["habit_id"], habit_name=row["habit_name"],
                habit_color=row["habit_color"],
                this_week_avg=round(this_avg, 1) if this_avg is not None else None,
                last_week_avg=round(last_avg, 1) if last_avg is not None else None,
                change_pct=change_pct,
                this_week_count=row["this_week_count"],
                last_week_count=row["last_week_count"],
            ))

        today = today_utc()
        response = WeeklySummaryResponse(
            week_start=start_of_week(today), week_end=end_of_week(today), habits=habits,
        )
        await self.cache.set_weekly(uid, response.model_dump())
        return response

    async def get_monthly_trend(
        self, user_id: UUID, habit_id: UUID | None = None, days: int = 30,
    ) -> MonthlyTrendResponse:
        """30-day trend chart data — cached 1 hour."""
        uid = str(user_id)
        hid = str(habit_id) if habit_id else None
        cached = await self.cache.get_monthly(uid, hid)
        if cached:
            return MonthlyTrendResponse(**cached)

        rows = await self.repo.get_monthly_trend(user_id, habit_id, days)

        habit_data: dict[str, list] = defaultdict(list)
        habit_meta: dict[str, dict] = {}
        for row in rows:
            hid_key = str(row["habit_id"])
            if hid_key not in habit_meta:
                habit_meta[hid_key] = {
                    "habit_id": row["habit_id"], "habit_name": row["habit_name"],
                    "habit_color": row["habit_color"], "habit_type": row["habit_type"],
                }
            habit_data[hid_key].append(TrendDataPoint(
                date=row["log_date"],
                value=round(float(row["value"]), 1) if row["value"] is not None else None,
            ))

        habits = [
            HabitTrendData(
                habit_id=meta["habit_id"], habit_name=meta["habit_name"],
                habit_color=meta["habit_color"], habit_type=meta["habit_type"],
                data_points=habit_data[hid_key],
            )
            for hid_key, meta in habit_meta.items()
        ]

        response = MonthlyTrendResponse(
            start_date=days_ago(days - 1), end_date=today_utc(), habits=habits,
        )
        await self.cache.set_monthly(uid, response.model_dump(), hid)
        return response

    async def get_completion_rates(
        self, user_id: UUID, days: int = 30,
    ) -> CompletionRateResponse:
        """Completion rate per habit — cached 30 minutes."""
        uid = str(user_id)
        cached = await self.cache.get_completion(uid)
        if cached:
            return CompletionRateResponse(**cached)

        rows = await self.repo.get_completion_rates(user_id, days)
        habits = [
            HabitCompletionRate(
                habit_id=row["habit_id"], habit_name=row["habit_name"],
                habit_color=row["habit_color"], habit_icon=row["habit_icon"],
                days_logged=row["days_logged"], total_days=row["total_days"],
                completion_pct=round((row["days_logged"] / max(row["total_days"], 1)) * 100, 1),
            )
            for row in rows
        ]

        response = CompletionRateResponse(
            period_start=days_ago(days - 1), period_end=today_utc(), habits=habits,
        )
        await self.cache.set_completion(uid, response.model_dump())
        return response

    async def get_correlations(
        self, user_id: UUID, days: int = 30,
    ) -> CorrelationResponse:
        """Pearson correlations between habit pairs — cached 1 hour."""
        uid = str(user_id)
        cached = await self.cache.get_correlations(uid)
        if cached:
            return CorrelationResponse(correlations=[CorrelationResult(**c) for c in cached])

        rows = await self.repo.get_correlation_data(user_id, days)
        if not rows:
            return CorrelationResponse(correlations=[])

        # Group data by habit pairs
        pairs: dict[tuple, dict] = defaultdict(lambda: {
            "habit_a_name": "", "habit_b_name": "",
            "values_a": [], "values_b": [],
        })
        for row in rows:
            pair_key = (str(row["habit_a_id"]), str(row["habit_b_id"]))
            pairs[pair_key]["habit_a_id"] = row["habit_a_id"]
            pairs[pair_key]["habit_a_name"] = row["habit_a_name"]
            pairs[pair_key]["habit_b_id"] = row["habit_b_id"]
            pairs[pair_key]["habit_b_name"] = row["habit_b_name"]
            pairs[pair_key]["values_a"].append(float(row["value_a"]))
            pairs[pair_key]["values_b"].append(float(row["value_b"]))

        correlations = []
        for pair_key, pair_data in pairs.items():
            values_a = pair_data["values_a"]
            values_b = pair_data["values_b"]
            if len(values_a) < 5:
                continue

            r = self._pearson_correlation(values_a, values_b)
            if r is None:
                continue

            strength, direction = self._interpret_correlation(r)
            insight = self._generate_insight(
                pair_data["habit_a_name"], pair_data["habit_b_name"],
                r, strength, direction,
            )

            correlations.append(CorrelationResult(
                habit_a_id=pair_data["habit_a_id"],
                habit_a_name=pair_data["habit_a_name"],
                habit_b_id=pair_data["habit_b_id"],
                habit_b_name=pair_data["habit_b_name"],
                correlation=round(r, 3), strength=strength,
                direction=direction, data_points=len(values_a), insight=insight,
            ))

        correlations.sort(key=lambda c: abs(c.correlation), reverse=True)
        response = CorrelationResponse(correlations=correlations)
        await self.cache.set_correlations(uid, [c.model_dump() for c in correlations])
        return response

    # ══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
        """
        Pearson correlation coefficient.
        r = Σ((xi - x̄)(yi - ȳ)) / √(Σ(xi - x̄)² × Σ(yi - ȳ)²)
        Returns None if calculation is impossible (zero variance).
        """
        n = len(x)
        if n != len(y) or n < 2:
            return None
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)
        denominator = math.sqrt(sum_sq_x * sum_sq_y)
        if denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def _interpret_correlation(r: float) -> tuple[str, str]:
        """Classify correlation into strength and direction."""
        abs_r = abs(r)
        strength = "weak" if abs_r < 0.3 else ("moderate" if abs_r < 0.7 else "strong")
        direction = "positive" if r > 0.1 else ("negative" if r < -0.1 else "none")
        return strength, direction

    @staticmethod
    def _generate_insight(habit_a: str, habit_b: str, r: float, strength: str, direction: str) -> str:
        """Generate human-readable insight about the correlation."""
        if direction == "none" or strength == "weak":
            return f"No clear relationship found between {habit_a} and {habit_b}"
        verb = "tends to be higher" if strength == "strong" else "may be slightly higher"
        if direction == "negative":
            verb = "tends to be lower" if strength == "strong" else "may be slightly lower"
        return f"Your {habit_b} {verb} on days when {habit_a} is higher"
```

---

<a name="pearson"></a>
## 4. Deep Dive: Pearson Correlation

### What Is Pearson Correlation?

A number between **-1** and **+1** that measures how two variables move together:

```
r = +1.0  →  Perfect positive: both go up together
              Sleep ↑ → Mood ↑ (always)

r =  0.0  →  No relationship: movement is random
              Water intake has nothing to do with steps

r = -1.0  →  Perfect negative: one goes up, other goes down
              Screen time ↑ → Sleep ↓ (always)
```

### The Formula (Step by Step)

Given 5 days of Sleep and Mood data:

```
Day 1: Sleep = 6,  Mood = 5
Day 2: Sleep = 7,  Mood = 7
Day 3: Sleep = 8,  Mood = 8
Day 4: Sleep = 5,  Mood = 4
Day 5: Sleep = 9,  Mood = 9

Step 1: Calculate means
  mean_sleep = (6+7+8+5+9) / 5 = 7.0
  mean_mood  = (5+7+8+4+9) / 5 = 6.6

Step 2: Calculate deviations from mean
  Day 1: (6-7.0) × (5-6.6) = (-1.0) × (-1.6) = +1.60
  Day 2: (7-7.0) × (7-6.6) = ( 0.0) × (+0.4) =  0.00
  Day 3: (8-7.0) × (8-6.6) = (+1.0) × (+1.4) = +1.40
  Day 4: (5-7.0) × (4-6.6) = (-2.0) × (-2.6) = +5.20
  Day 5: (9-7.0) × (9-6.6) = (+2.0) × (+2.4) = +4.80
  numerator = 1.60 + 0.00 + 1.40 + 5.20 + 4.80 = 13.00

Step 3: Calculate sum of squared deviations
  sum_sq_sleep = 1+0+1+4+4 = 10.0
  sum_sq_mood  = 2.56+0.16+1.96+6.76+5.76 = 17.2
  denominator = √(10.0 × 17.2) = √172 = 13.11

Step 4: r = 13.00 / 13.11 = 0.992 (VERY strong positive!)

Interpretation: Sleep and Mood are strongly correlated.
  "Your mood tends to be higher on days you sleep more"
```

### Strength Classification

```python
abs_r = abs(r)
if abs_r < 0.3:    strength = "weak"
elif abs_r < 0.7:  strength = "moderate"
else:               strength = "strong"
```

| |r| Range | Strength | Example |
|-----------|----------|---------|
| 0.0 – 0.3 | Weak | Water and Steps (no real connection) |
| 0.3 – 0.7 | Moderate | Exercise and Sleep (some connection) |
| 0.7 – 1.0 | Strong | Sleep and Mood (clear relationship) |

### Minimum 5 Data Points

```python
if len(values_a) < 5:
    continue  # Skip — not enough data for meaningful correlation
```

With only 2-3 data points, any random data can produce a high correlation by chance. 5 is the minimum for a statistically meaningful result (though 14+ is ideal).

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision: Service Constructs Both Repo and Cache

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Service Dependencies                              │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Service creates AnalyticsRepository + AnalyticsCache       │
│                                                                     │
│  def __init__(self, session, redis_client):                         │
│      self.repo = AnalyticsRepository(session)                       │
│      self.cache = AnalyticsCache(redis_client)                      │
│                                                                     │
│  WHY:                                                               │
│  • Service is the ONLY place that touches both repo and cache       │
│  • Cache-aside logic lives in ONE place (not scattered)             │
│  • Testable: mock repo OR cache independently                       │
│                                                                     │
│  PATTERN: Every public method follows:                              │
│    1. cache.get_X() → hit? return                                   │
│    2. repo.get_X() → SQL query                                      │
│    3. Transform raw dicts → Pydantic schemas                        │
│    4. cache.set_X() → store for next time                           │
│    5. Return                                                        │
│                                                                     │
│  INTERVIEW TIP: "The service is the single orchestration point for  │
│  cache and database. Every method checks cache first, queries DB on │
│  miss, transforms data into typed schemas, and caches the result."  │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 6. How to Verify Your Work

```bash
docker-compose exec backend python -c "
from app.modules.analytics.cache import AnalyticsCache, CACHE_TTL_DASHBOARD
from app.modules.analytics.service import AnalyticsService
print(f'Dashboard TTL: {CACHE_TTL_DASHBOARD}s ({CACHE_TTL_DASHBOARD/60} min)')
print('✅ cache.py imports OK')
print('✅ service.py imports OK')

# Test Pearson correlation
r = AnalyticsService._pearson_correlation([6,7,8,5,9], [5,7,8,4,9])
print(f'Pearson r (sleep vs mood): {r:.3f}')
assert r > 0.9, 'Expected strong positive correlation'
print('✅ Pearson correlation works!')

# Test interpretation
strength, direction = AnalyticsService._interpret_correlation(0.72)
print(f'r=0.72 → {strength} {direction}')
assert strength == 'strong' and direction == 'positive'
print('✅ Interpretation works!')
"
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Cache-Aside Pattern** | Check cache → miss → query DB → cache → return | Every service method |
| 2 | **`json.dumps(default=str)`** | Serialize Python objects (UUID, date) to JSON string | `cache.set()` |
| 3 | **Typed cache accessors** | `get_streaks()` / `set_streaks()` with consistent key naming | `cache.py` |
| 4 | **TTL constants** | Different expiry per analytics type | Module-level constants |
| 5 | **Fail-open cache** | Cache errors = cache miss (never crash) | All cache methods |
| 6 | **`defaultdict(list)`** | Auto-creates empty list for new keys | Grouping trend data |
| 7 | **Pearson correlation** | Statistical measure of linear relationship (-1 to +1) | `_pearson_correlation()` |
| 8 | **`math.sqrt()`** | Square root — part of Pearson formula | Denominator calculation |
| 9 | **`zip(x, y)`** | Pair elements from two lists: [(x1,y1), (x2,y2), ...] | Pearson numerator |
| 10 | **Correlation interpretation** | |r| < 0.3 weak, 0.3-0.7 moderate, > 0.7 strong | `_interpret_correlation()` |
| 11 | **Natural language insight** | Convert math to "Your mood tends to be higher when..." | `_generate_insight()` |
| 12 | **`model_dump()`** | Pydantic → dict for JSON serialization to cache | All cache.set calls |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: Explain the cache-aside pattern and why you chose it.
**A:** "Cache-aside means the application manages the cache explicitly. On read: check cache first — if hit, return cached data (1ms). If miss, query the database (100ms), store the result in cache with a TTL, and return. On write (in our Logs module): invalidate the cache by deleting keys. We chose this over write-through (update cache on every write) because analytics are read-heavy — the dashboard loads 100x more often than logs are created. Cache-aside minimizes write overhead."

### Q2: How does Pearson correlation work in your app?
**A:** "SQL fetches paired daily values for all habit combinations using a self-join. In Python, we group by habit pair, then calculate the Pearson coefficient: sum of products of deviations divided by the product of standard deviations. We require at least 5 overlapping data points and filter to correlations with |r| > 0.3. The result includes a human-readable insight generated from the direction and strength: 'Your mood tends to be higher on days you sleep more.'"

### Q3: Why separate cache.py from service.py?
**A:** "Separation of concerns and testability. The cache class handles Redis operations, JSON serialization, and TTL management. The service handles business logic, data transformation, and cache orchestration. In unit tests, I can mock the cache (return None for every get) to test the service's computation logic without Redis. I can also mock the repository to test the cache integration path."

### Q4: What happens if Redis is down?
**A:** "Every cache operation is wrapped in try/except that silently catches errors and returns None (for gets) or does nothing (for sets). The service treats cache errors as cache misses — it queries the database and returns fresh data. The application is slower (100ms vs 1ms) but never crashes. We log warnings so the ops team knows Redis is down. This is the fail-open pattern."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 07b: Analytics Repository (★★★)](./phase4-part07b-analytics-repository-sql.md) |
| ➡️ Next | [Phase 4 Part 07d: Analytics Router](./phase4-part07d-analytics-controller.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Analytics Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 07a | ✅ Done | Analytics Schemas & Exceptions |
| 07b | ✅ Done | Analytics Repository (★★★ Complex SQL) |
| **07c** | ✅ **You are here** | Analytics Cache & Service |
| 07d | ⬜ Next | Analytics Router |
| 07e | ⬜ | Analytics Connections & Flows |

---

**End of Phase 4 Part 07c: Analytics Cache & Service**

*The brains are done — cache-aside orchestration, data transformation, and Pearson correlation. Next: the router that exposes 6 GET endpoints.*
