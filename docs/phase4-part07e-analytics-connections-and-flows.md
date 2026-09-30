# 🔄 Phase 4 Part 07e: Analytics — Connections & Flows

> **"Analytics reads from Habits + Logs, caches in Redis, and feeds into AI. It's the intelligence layer between raw data and actionable insights."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07e (Analytics Flows & Architecture) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part07d-analytics-controller.md](./phase4-part07d-analytics-controller.md) |
| **Next** | [phase4-part08-ai-llm-overview.md](./phase4-part08-ai-llm-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only) |
| **Time to Read** | ~15 minutes |

---

## 📖 Table of Contents

1. [Analytics Module — Complete File Map](#file-map)
2. [Flow 1: Cache-Aside (Every Endpoint)](#cache-flow)
3. [Flow 2: Streak Calculation End-to-End](#streak-flow)
4. [Flow 3: Correlation Discovery](#correlation-flow)
5. [Flow 4: Cache Invalidation Lifecycle](#invalidation-flow)
6. [Performance: Cached vs Uncached](#performance)
7. [Cross-Module Data Pipeline](#pipeline)
8. [Analytics Module Summary](#summary)
9. [Navigation](#navigation)

---

<a name="file-map"></a>
## 1. Analytics Module — Complete File Map

```
backend/app/modules/analytics/
├── schemas.py      ─── Part 07a ── 12 response schemas (no request schemas)
├── exceptions.py   ─── Part 07a ── 2 exceptions (InsufficientData, InvalidDateRange)
├── repository.py   ─── Part 07b ── ★★★ 6 complex SQL queries (raw SQL via text())
├── cache.py        ─── Part 07c ── Redis cache with typed accessors + TTLs
├── service.py      ─── Part 07c ── Cache-aside orchestration + Pearson correlation
├── router.py       ─── Part 07d ── 6 GET endpoints (all cached, all read-only)
└── __init__.py

NO models.py — Analytics reads from habits + habit_logs tables
NO migrations — No tables to create
UNIQUE: cache.py — first module with a dedicated cache layer
UNIQUE: Raw SQL — first module using text() instead of ORM
```

---

<a name="cache-flow"></a>
## 2. Flow 1: Cache-Aside (Every Endpoint)

Every analytics endpoint follows this exact pattern:

```
GET /analytics/streaks
  │
  ▼
router.py: service.get_streaks(user_id)
  │
  ▼
service.py:
  ┌─ cache.get_streaks(uid) ──→ Redis GET "analytics:uuid-001:streaks"
  │
  ├─ CACHE HIT (data exists, TTL not expired):
  │    → json.loads(cached_data)
  │    → AllStreaksResponse(streaks=[StreakInfo(**s) for s in cached])
  │    → Return immediately
  │    → Response time: ~1ms
  │
  └─ CACHE MISS (no data or TTL expired):
       │
       ├─ repo.get_streaks(user_id)
       │    → Complex SQL: 6 CTEs with ROW_NUMBER, DISTINCT ON
       │    → Returns: list[dict] (raw query results)
       │    → Time: ~100ms
       │
       ├─ Transform: raw dicts → StreakInfo Pydantic schemas
       │
       ├─ cache.set_streaks(uid, [s.model_dump() for s in streaks])
       │    → Redis SETEX "analytics:uuid-001:streaks" 1800 <json>
       │    → TTL: 30 minutes (auto-expires)
       │
       └─ Return AllStreaksResponse
            → Response time: ~101ms (SQL + cache write)

NEXT REQUEST (within 30 min): HIT → 1ms
```

---

<a name="streak-flow"></a>
## 3. Flow 2: Streak Calculation End-to-End

```
GET /analytics/streaks
  │
  ▼
service.get_streaks(user_id):
  │
  ├─ Cache miss → repo.get_streaks(user_id)
  │
  ▼
repository.py (SQL execution):

  CTE 1: habit_info
    SELECT id, name, color, icon FROM habits
    WHERE user_id = ? AND is_archived = false
    → [Water, Sleep, Mood, Exercise]

  CTE 2: logged_dates
    SELECT habit_id, log_date, ROW_NUMBER() OVER (PARTITION BY habit_id ORDER BY log_date)
    FROM habit_logs WHERE user_id = ? AND value IS NOT NULL
    → Water: Sep20=1, Sep21=2, Sep22=3, Sep24=4, Sep25=5, Sep26=6

  CTE 3: streaks (the magic)
    SELECT habit_id, log_date, log_date - (rn * INTERVAL '1 day') AS grp
    → Sep20-1d=Sep19, Sep21-2d=Sep19, Sep22-3d=Sep19  ← GROUP A
    → Sep24-4d=Sep20, Sep25-5d=Sep20, Sep26-6d=Sep20  ← GROUP B

  CTE 4: streak_lengths
    GROUP BY habit_id, grp → COUNT(*)
    → Group A: 3 days (Sep 20-22)
    → Group B: 3 days (Sep 24-26)

  CTE 5: current_streaks
    WHERE streak_end >= CURRENT_DATE - 1 day
    → Group B includes today → current_streak = 3

  CTE 6: longest_streaks
    DISTINCT ON (habit_id) ORDER BY streak_length DESC
    → longest = 3

  FINAL: LEFT JOIN all CTEs
    → Water: current=3, longest=3, last_logged=Sep-26
    → Sleep: current=7, longest=14, last_logged=Sep-26
    → Mood: current=0, longest=5, last_logged=Sep-24 (missed yesterday)
    → Exercise: current=2, longest=10, last_logged=Sep-26

  ▼
service.py: Transform dicts → StreakInfo schemas → cache → return
```

---

<a name="correlation-flow"></a>
## 4. Flow 3: Correlation Discovery

```
GET /analytics/correlations?days=30
  │
  ▼
service.get_correlations(user_id, days=30):
  │
  ├─ Cache miss → repo.get_correlation_data(user_id, 30)
  │
  ▼
repository.py (SQL):
  CTE: habit_values
    Normalize all types to float:
      numeric → value_numeric directly
      boolean → true=1.0, false=0.0
      scale → value_scale::float

  Self-join: a.habit_id < b.habit_id (unique pairs only)
    Water × Sleep: [(Sep20: 7,7.5), (Sep21: 8,6.0), (Sep22: 7,8.0), ...]
    Water × Mood:  [(Sep20: 7,8), (Sep21: 8,6), ...]
    Sleep × Mood:  [(Sep20: 7.5,8), (Sep21: 6.0,6), (Sep22: 8.0,9), ...]
    ... all C(4,2) = 6 pairs for 4 habits

  ▼
service.py (Python computation):
  For each pair with ≥ 5 data points:
    Sleep × Mood:
      mean_sleep = 7.0, mean_mood = 6.6
      numerator = Σ((xi - 7.0)(yi - 6.6)) = 13.00
      denominator = √(10.0 × 17.2) = 13.11
      r = 13.00 / 13.11 = 0.992

    Interpret:
      |0.992| > 0.7 → strength = "strong"
      0.992 > 0.1 → direction = "positive"

    Generate insight:
      "Your Mood tends to be higher on days when Sleep Hours is higher"

  Sort by |r| descending → strongest correlations first
  Cache for 1 hour → return CorrelationResponse
```

---

<a name="invalidation-flow"></a>
## 5. Flow 4: Cache Invalidation Lifecycle

```
TIME 10:00 — Dashboard loads (cache empty)
  GET /analytics/dashboard → MISS → SQL (150ms) → cache → return
  Redis: analytics:uuid-001:dashboard = {...} TTL=300s

TIME 10:01 — Dashboard loads again
  GET /analytics/dashboard → HIT → return (1ms)

TIME 10:02 — User logs 8 glasses of water
  POST /logs → LogService.create_log() → session.commit()
    → LogService._invalidate_cache(uuid-001)
    → Redis: SCAN analytics:uuid-001:* → DELETE 5 keys
  Redis: analytics:uuid-001:* = (all deleted)

TIME 10:02 — Dashboard refreshes
  GET /analytics/dashboard → MISS → SQL (150ms) → cache → return
  Now shows: today_logged = 5 (was 4 before the water log)
  Redis: analytics:uuid-001:dashboard = {updated data} TTL=300s

TIME 10:07 — TTL expires (5 min dashboard cache)
  Redis auto-deletes: analytics:uuid-001:dashboard
  Next request → MISS → fresh SQL calculation

TWO INVALIDATION PATHS:
  1. EXPLICIT: LogService deletes keys when data changes (immediate)
  2. TTL: Redis auto-deletes expired keys (eventual, safety net)
```

---

<a name="performance"></a>
## 6. Performance: Cached vs Uncached

| Endpoint | Uncached (SQL) | Cached (Redis) | Speedup |
|----------|---------------|----------------|---------|
| Dashboard | ~150ms (3 queries) | ~1ms | 150× |
| Streaks | ~100ms (6 CTEs) | ~1ms | 100× |
| Weekly Summary | ~80ms | ~1ms | 80× |
| Monthly Trend | ~120ms (generate_series) | ~1ms | 120× |
| Completion Rate | ~60ms | ~1ms | 60× |
| Correlations | ~200ms (self-join + Python) | ~1ms | 200× |
| **Dashboard load (all 6)** | **~710ms** | **~6ms** | **~120×** |

### When Is Cache Cold?

| Event | Cache State | Next Request |
|-------|------------|-------------|
| First visit ever | Cold (empty) | ~710ms (all SQL) |
| User logs a habit | Invalidated (deleted) | ~710ms (recalculate) |
| TTL expires (5min–1hr) | Expired (auto-deleted) | One endpoint recalculates |
| Redis restarts | Cold (lost) | ~710ms (all SQL) |
| Normal dashboard visit | Warm (cached) | ~6ms |

For a personal health tracker: user logs habits 1–2 times per day, views dashboard 10–20 times. Cache hit rate: **~90%+**.

---

<a name="pipeline"></a>
## 7. Cross-Module Data Pipeline

```
┌─── AUTH ──────────┐
│  "Who are you?"    │
│  user_id from JWT  │
└────────┬───────────┘
         │
         ▼
┌─── HABITS ────────┐
│  "What do you     │
│   track?"          │
│  💧🛌😊🏃         │
└────────┬───────────┘
         │ defines structure
         ▼
┌─── LOGS ──────────┐     ┌─── REDIS CACHE ──────┐
│  "How much today?" │────>│  analytics:uuid:*    │
│  Water=8, Sleep=7  │     │  (invalidated on     │
│  Mood=7, Run=true  │     │   every log change)  │
└────────┬───────────┘     └──────────┬───────────┘
         │ raw data                   │ cached results
         ▼                            ▼
┌─── ANALYTICS (this module) ─────────────────────┐
│  Dashboard: "4/6 logged (67%), streak: Water 15d"│
│  Streaks: Water 15d, Sleep 7d, Exercise 2d       │
│  Weekly: Sleep ↑10%, Mood ↓5%                    │
│  Trend: 30 data points per habit                 │
│  Completion: Water 93%, Meditation 47%            │
│  Correlations: Sleep↔Mood r=0.72 (strong +)      │
└────────┬────────────────────────────────────────┘
         │ insights feed into
         ▼
┌─── AI (Parts 08-12) ────────────────────────────┐
│  Agent uses analytics as tool:                    │
│    [tool: get_analytics] → weekly summary         │
│    [tool: correlate] → habit correlations          │
│                                                    │
│  "You sleep better on exercise days (r=0.72).    │
│   Your mood is strongly tied to sleep. Consider   │
│   a 30-minute walk before dinner."                │
└──────────────────────────────────────────────────┘
```

---

<a name="summary"></a>
## 8. Analytics Module Summary

### What You Built (Parts 07a–07e)

| Part | Files | What It Does |
|------|-------|-------------|
| **07a** | schemas.py, exceptions.py | 12 response schemas + 2 exceptions |
| **07b** | repository.py | ★★★ Complex SQL (streaks, CTEs, generate_series, self-join) |
| **07c** | cache.py, service.py | Redis cache layer + cache-aside + Pearson correlation |
| **07d** | router.py | 6 cached GET endpoints |
| **07e** | (this doc) | Flows, performance, data pipeline |

### By the Numbers

| Metric | Count |
|--------|-------|
| Python files | 7 (including cache.py — unique to this module) |
| Endpoints | 6 (ALL GET, ALL cached) |
| Response schemas | 12 |
| SQL queries | 6 (raw SQL with text()) |
| SQL concepts | CTEs, ROW_NUMBER, generate_series, self-join, CASE, COALESCE |
| Cache TTLs | 5min (dashboard) to 1hr (correlations) |
| Python computation | Pearson correlation with insight generation |

### Module Pattern Comparison (All 4 Completed)

| Aspect | Auth | Habits | Logs | Analytics |
|--------|------|--------|------|-----------|
| **Style** | Custom (JWT) | Standard CRUD | CRUD + Bulk | Read-only aggregation |
| **SQL** | Simple ORM | Simple ORM | ORM + date filters | ★★★ Raw SQL (CTEs, window funcs) |
| **External** | Redis (blacklist), bcrypt | None | Redis (cache invalidation) | Redis (cache-aside) |
| **Delete** | N/A (logout) | Soft (archive) | Hard (DELETE) | N/A (read-only) |
| **Caching** | None | None | Invalidates analytics | Full cache-aside pattern |
| **Unique** | Token management | Drag-and-drop sort | Polymorphic values, upsert | Pearson correlation, gap-filling |

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 07d: Analytics Router](./phase4-part07d-analytics-controller.md) |
| ➡️ Next | [Phase 4 Part 08: AI LLM Layer Overview](./phase4-part08-ai-llm-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Analytics Module — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 07a | ✅ Done | Analytics Schemas & Exceptions |
| 07b | ✅ Done | Analytics Repository (★★★ Complex SQL) |
| 07c | ✅ Done | Analytics Cache & Service |
| 07d | ✅ Done | Analytics Router |
| **07e** | ✅ **Done** | Analytics Connections & Flows |

---

**🎉 The Analytics module is COMPLETE.**

*Four core backend modules done: Auth ✅, Habits ✅, Logs ✅, Analytics ✅. Raw data flows from check-ins through complex SQL aggregations and Pearson correlations into cached dashboard widgets. Next: the AI module — where data becomes conversation.*
