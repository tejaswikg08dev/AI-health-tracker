# 🔄 Phase 4 Part 06d: Logs — Connections & Flows

> **"The Logs module sits at the center of the data pipeline. Auth identifies the user, Habits defines what to track, Logs records the data, Analytics crunches it, and AI interprets it. Every module downstream depends on the rows in habit_logs."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 06d (Logs Flows & Architecture) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.2 — Daily Logging |
| **Previous** | [phase4-part06c-logs-controller.md](./phase4-part06c-logs-controller.md) |
| **Next** | [phase4-part07-analytics-service-overview.md](./phase4-part07-analytics-service-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only) |
| **Time to Read** | ~15 minutes |

---

## 📖 Table of Contents

1. [Logs Module — Complete File Map](#file-map)
2. [Flow 1: Single Log Creation](#single-flow)
3. [Flow 2: Bulk Daily Check-In (Upsert)](#bulk-flow)
4. [Flow 3: Flexible GET Query](#get-flow)
5. [Flow 4: Cache Invalidation](#cache-flow)
6. [Error Paths](#error-flows)
7. [Cross-Module Data Pipeline](#pipeline)
8. [Logs Module Summary](#summary)
9. [Navigation](#navigation)

---

<a name="file-map"></a>
## 1. Logs Module — Complete File Map

```
backend/app/modules/logs/
├── models.py          ─── Part 06a ── HabitLog (10 columns, 2 FKs, UNIQUE constraint)
├── exceptions.py      ─── Part 06a ── 4 exception classes
├── schemas.py         ─── Part 06a ── 6 schemas (LogCreate, BulkLogCreate, BulkLogEntry, LogUpdate, LogResponse, DailyLogSummary)
├── repository.py      ─── Part 06b ── 8 custom queries (date ranges, duplicate check, hard delete)
├── service.py         ─── Part 06b ── 6 methods + 4 helpers (upsert, type validation, cache invalidation)
├── router.py          ─── Part 06c ── 5 endpoints (single, bulk, flexible GET, update, delete)
└── __init__.py

Dependency chain:
  router.py → service.py → log_repo (LogRepository) + habit_repo (HabitRepository)
       │           │                                        ↑
       │           ├── cache invalidation → Redis           │ cross-module
       │           └── type validation ─────────────────────┘
       └── auth/router.py (get_current_user_id)
```

---

<a name="single-flow"></a>
## 2. Flow 1: Single Log Creation

```
STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Browser              POST /api/v1/logs
                           Body: {"habit_id":"water-id",
                                  "log_date":"2026-09-26",
                                  "value_numeric":7.0}

 2    Pydantic             Validate → LogCreate schema:
                             ✅ habit_id: valid UUID
                             ✅ log_date: "2026-09-26" → date object
                             ✅ value_numeric: 7.0 (ge=0, le=100000)

 3    get_current_user_id  Decode JWT → user_id = uuid-001 ✅

 4    service.create_log:
        a) data.log_date > today_utc()?
           Sep 26 > Sep 26? → No ✅ (today is allowed)

        b) habit_repo.get_user_habit(uuid-001, water-id)
           → Habit(name="Water", type="numeric") ✅
           (cross-module: using HabitRepository from habits module)

        c) log_repo.get_existing_log(uuid-001, water-id, Sep-26)
           → None ✅ (no duplicate)

        d) _extract_value_dict(habit_type="numeric", value_numeric=7.0, ...)
           → {"value_numeric": 7.0, "value_boolean": None, "value_scale": None}

        e) log_repo.create(user_id=uuid-001, habit_id=water-id,
                          log_date=Sep-26, value_numeric=7.0, ...)
           → INSERT INTO habit_logs (...)

        f) session.commit()

        g) _invalidate_cache(uuid-001)
           → redis: DELETE analytics:uuid-001:*

 5    Response             HTTP 201
                           {"id":"log-001","habit_id":"water-id",
                            "log_date":"2026-09-26","value_numeric":7.0,
                            "value_boolean":null,"value_scale":null,...}
```

---

<a name="bulk-flow"></a>
## 3. Flow 2: Bulk Daily Check-In (Upsert)

```
STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Browser              POST /api/v1/logs/bulk
                           Body: {
                             "log_date": "2026-09-26",
                             "entries": [
                               {"habit_id":"water-id","value_numeric":8},
                               {"habit_id":"sleep-id","value_numeric":7.5},
                               {"habit_id":"mood-id","value_scale":7}
                             ]
                           }

 2    service.bulk_create_logs:
        → date check: Sep 26 > today? No ✅

        ENTRY 1 (Water — numeric):
          → habit_repo.get_user_habit → Habit(type="numeric") ✅
          → _extract_value_dict → {value_numeric: 8.0, ...}
          → log_repo.get_existing_log(user, water, Sep-26)
            → HabitLog(value_numeric=7.0)  ← EXISTS! (logged earlier)
          → UPDATE: setattr(existing, "value_numeric", 8.0)
          → flush()

        ENTRY 2 (Sleep — numeric):
          → habit_repo.get_user_habit → Habit(type="numeric") ✅
          → _extract_value_dict → {value_numeric: 7.5, ...}
          → log_repo.get_existing_log → None ← doesn't exist
          → CREATE: log_repo.create(value_numeric=7.5, ...)

        ENTRY 3 (Mood — scale):
          → habit_repo.get_user_habit → Habit(type="scale") ✅
          → _extract_value_dict → {value_scale: 7, ...}
          → log_repo.get_existing_log → None ← doesn't exist
          → CREATE: log_repo.create(value_scale=7, ...)

        → session.commit()  (all 3 operations in ONE transaction)
        → _invalidate_cache(uuid-001)

 3    Response             HTTP 201
                           [
                             {"habit_id":"water-id","value_numeric":8.0,...},
                             {"habit_id":"sleep-id","value_numeric":7.5,...},
                             {"habit_id":"mood-id","value_scale":7,...}
                           ]

KEY INSIGHT:
  Water was UPDATED (7→8), Sleep and Mood were CREATED.
  User hit "Save" twice — first time created all 3, second time
  updated Water (changed value) and updated Sleep/Mood (same values).
  No errors. This is the UPSERT pattern — idempotent bulk save.
```

---

<a name="get-flow"></a>
## 4. Flow 3: Flexible GET Query

```
PATTERN 1: "What did I log today?" (check-in page)
──────────────────────────────────────────────────
  GET /logs?date=2026-09-26
    → date param provided → service.get_logs_for_date(user, Sep-26)
    → SQL: SELECT * FROM habit_logs
           WHERE user_id = ? AND log_date = '2026-09-26'
           ORDER BY created_at ASC
    → Returns: 3 logs (water, sleep, mood)

PATTERN 2: "Show me this month's data" (chart page)
──────────────────────────────────────────────────
  GET /logs?start=2026-09-01&end=2026-09-30
    → start + end provided → service.get_logs_for_range(user, Sep-1, Sep-30)
    → SQL: SELECT * FROM habit_logs
           WHERE user_id = ? AND log_date >= '2026-09-01'
           AND log_date <= '2026-09-30'
           ORDER BY log_date ASC
    → Returns: ~90 logs (3 habits × 30 days)

PATTERN 3: "Show me Water Intake history" (habit detail)
──────────────────────────────────────────────────
  GET /logs?start=2026-09-01&end=2026-09-30&habit_id=water-id
    → start + end + habit_id → service.get_logs_for_range(user, ..., water-id)
    → SQL: adds AND habit_id = ? to the query
    → Returns: ~30 logs (just water)

PATTERN 4: "No params" (default = today)
──────────────────────────────────────────────────
  GET /logs
    → no params → default to today_utc()
    → Same as Pattern 1 with today's date
```

---

<a name="cache-flow"></a>
## 5. Flow 4: Cache Invalidation

```
BEFORE: Redis has cached analytics
  analytics:uuid-001:dashboard     = {"today_logged":3,"today_total":6,...}
  analytics:uuid-001:streaks       = {"streaks":[{"habit":"Water","days":14},...]}
  analytics:uuid-001:weekly        = {"habits":[{"this_week_avg":7.2,...},...]}

USER ACTION: Logs 8 glasses of water for today

AFTER LOG CREATION:
  service._invalidate_cache(uuid-001):
    → redis.scan_iter(match="analytics:uuid-001:*")
    → Found 3 keys
    → redis.delete("analytics:uuid-001:dashboard",
                   "analytics:uuid-001:streaks",
                   "analytics:uuid-001:weekly")

NEXT ANALYTICS REQUEST:
  GET /analytics/dashboard
    → Cache MISS (key was deleted)
    → Query database (fresh calculation)
    → today_logged is now 4 (was 3) ✅
    → streak for Water is now 15 (was 14) ✅
    → Cache the new result

WHY NOT SURGICAL INVALIDATION:
  Creating a water log affects: dashboard (today_logged count),
  streaks (consecutive days), weekly summary (this_week_avg),
  monthly trend (today's data point), completion rate (logged count).
  Almost EVERY analytics key is affected. Deleting all is simpler
  and barely less efficient than surgical deletion.
```

---

<a name="error-flows"></a>
## 6. Error Paths

### Future Date
```
POST /logs {"habit_id":"water","log_date":"2027-01-01","value_numeric":5}
  → service: data.log_date > today_utc() → True
  → raise FutureDateError()
  → 422: {"error_code":"FUTURE_DATE","message":"Cannot log for a future date"}
```

### Duplicate Log (Single Endpoint)
```
POST /logs {"habit_id":"water","log_date":"2026-09-26","value_numeric":9}
  → service: get_existing_log → HabitLog exists!
  → raise DuplicateLogError("Water Intake", "2026-09-26")
  → 409: {"error_code":"DUPLICATE_LOG",
           "message":"A log for 'Water Intake' already exists on 2026-09-26. Use update instead."}
```

### Wrong Value Type
```
POST /logs {"habit_id":"water","log_date":"2026-09-26","value_boolean":true}
  → Habit type is "numeric" but value_boolean was provided
  → _extract_value_dict: habit_type="numeric", value_numeric=None
  → raise InvalidLogValueError("Numeric habit requires value_numeric")
  → 422: {"error_code":"INVALID_LOG_VALUE",
           "message":"Invalid log value: Numeric habit requires value_numeric"}
```

### Habit Not Found
```
POST /logs {"habit_id":"nonexistent-uuid","log_date":"2026-09-26","value_numeric":5}
  → habit_repo.get_user_habit → None
  → raise HabitNotFoundError()
  → 404: {"error_code":"HABIT_NOT_FOUND","message":"Habit not found"}
```

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
│  💧 Water          │
│  🛌 Sleep          │
│  😊 Mood           │
└────────┬───────────┘
         │ defines structure
         ▼
┌─── LOGS (this) ───┐     ┌─── REDIS CACHE ──┐
│  "How much today?" │     │  analytics:*     │
│  Sep 26:           │────>│  (invalidated    │
│    Water = 8       │     │   on every write) │
│    Sleep = 7.5     │     └──────────────────┘
│    Mood  = 7       │
└────────┬───────────┘
         │ raw data feeds into
         ▼
┌─── ANALYTICS (Part 07) ──────────────────────────┐
│  "What are the patterns?"                          │
│  AVG(water this week) = 7.4 glasses                │
│  Water streak: 15 consecutive days                 │
│  Sleep ↔ Mood correlation: r = 0.72 (strong)       │
│  Completion rate: Exercise 80%, Meditation 45%      │
└────────┬───────────────────────────────────────────┘
         │ insights feed into
         ▼
┌─── AI (Parts 08-12) ─────────────────────────────┐
│  "What should I do differently?"                    │
│  RAG: retrieves your habit data as context          │
│  Agent: "You sleep better on days you exercise.     │
│          Your mood correlates strongly with sleep.   │
│          Consider exercising before 6 PM for         │
│          better sleep quality."                      │
│  Weekly Report: AI-generated summary of your week   │
└──────────────────────────────────────────────────────┘
```

### What Each Module Needs from Logs

| Module | What It Reads | Query Used |
|--------|-------------|-----------|
| **Analytics** | Daily values for all habits | `get_logs_for_range` (date range) |
| **Analytics** | Dates logged per habit | `get_habit_log_dates` (streak calc) |
| **AI Agent** | Recent habit data for context | `get_logs_for_range` (last 7 days) |
| **AI RAG** | Historical patterns | `get_logs_for_range` (last 30-90 days) |
| **Notifications** | "Logged today?" check | `count_logs_for_date` |
| **Export** | All data for CSV | `get_logs_for_range` (full history) |
| **Frontend** | Today's check-in status | `get_logs_for_date` (today) |
| **Frontend** | Chart data | `get_logs_for_range` (30 days) |

---

<a name="summary"></a>
## 8. Logs Module Summary

### What You Built (Parts 06a–06d)

| Part | Files | What It Does |
|------|-------|-------------|
| **06a** | models.py, exceptions.py, schemas.py, migration | Data layer — UNIQUE constraint, 3 value columns, bulk schema |
| **06b** | repository.py, service.py | Business layer — upsert, type validation, cache invalidation |
| **06c** | router.py | HTTP layer — 5 endpoints, flexible GET filtering |
| **06d** | (this doc) | Architecture — flows, cache, data pipeline |

### By the Numbers

| Metric | Count |
|--------|-------|
| Python files | 7 |
| Endpoints | 5 |
| Exception classes | 4 |
| Pydantic schemas | 6 |
| Repository methods | 8 custom + 5 inherited |
| Service methods | 6 + 4 private helpers |
| Database columns | 10 |
| Foreign keys | 2 (users + habits) |
| Indexes | 3 + UNIQUE |
| Business rules | 5 (future date, type match, duplicate, bulk upsert, cache) |

### Three Modules Complete — Pattern Comparison

| Aspect | Auth | Habits | Logs |
|--------|------|--------|------|
| CRUD type | Register/Login (custom) | Standard CRUD + reorder | CRUD + bulk upsert |
| External services | Redis (blacklist), bcrypt, JWT | None | Redis (cache), HabitRepo |
| Delete type | N/A (logout = blacklist) | Soft (archive) | Hard (DELETE) |
| Key innovation | Token management | Drag-and-drop ordering | Polymorphic values, upsert |
| Cross-module | None (provides to others) | Uses Auth | Uses Auth + Habits |

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 06c: Logs Router](./phase4-part06c-logs-controller.md) |
| ➡️ Next | [Phase 4 Part 07: Analytics Module Overview](./phase4-part07-analytics-service-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Logs Module — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 06a | ✅ Done | Logs Models, Exceptions, Schemas & Migration |
| 06b | ✅ Done | Logs Repository & Service |
| 06c | ✅ Done | Logs Router |
| **06d** | ✅ **Done** | Logs Connections & Flows |

---

**End of Phase 4 Part 06d: Logs Connections & Flows**

**🎉 The Logs module is COMPLETE.**

*Users can log daily values (single or bulk), query by date or range, update mistakes, and delete incorrect entries. Every write invalidates the analytics cache. The data pipeline flows: Auth → Habits → Logs → Analytics → AI. Next: the Analytics module — where raw data becomes insights.*
