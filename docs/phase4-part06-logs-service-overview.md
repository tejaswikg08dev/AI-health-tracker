# 📝 Phase 4 Part 06: Logs Module — Overview & Roadmap

> **"Habits define WHAT you track. Logs record HOW MUCH. Every data point — '8 glasses of water on September 26th' — is a log entry. This module is the beating heart of the tracker, generating the data that analytics and AI consume."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 06 (Logs Module — Overview) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.2 — Daily Logging |
| **Previous** | [phase4-part05e-habits-connections-and-flows.md](./phase4-part05e-habits-connections-and-flows.md) |
| **Next** | [phase4-part06a-logs-entities-migrations.md](./phase4-part06a-logs-entities-migrations.md) |
| **Module Files** | 7 Python files + 1 Alembic migration |
| **Endpoints** | 5 (create, bulk create, get/filter, update, delete) |
| **Sub-Parts** | 4 documents (06a through 06d) |
| **Time to Type** | ~3 hours (across all 4 sub-parts) |
| **Difficulty** | Medium-Hard (polymorphic values, bulk operations, cache invalidation, date filtering) |

---

## 📖 Table of Contents

1. [What Is the Logs Module?](#what-is-logs)
2. [How Logs Connect to Habits](#habits-connection)
3. [The Three Value Types — Polymorphic Storage](#value-types)
4. [Endpoints Overview](#endpoints)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Prerequisites](#prerequisites)
10. [Design Decisions Summary](#design-decisions)
11. [Verification Checklist](#verification)
12. [Interview Q&A](#interview)
13. [Navigation](#navigation)

---

<a name="what-is-logs"></a>
## 1. What Is the Logs Module?

The Logs module records **daily check-in values** for each habit. When Shreya opens the app at night and enters "I drank 7 glasses of water today," that creates a log entry.

| Concept | Analogy |
|---------|---------|
| **Habit** = column header in a journal | "Water Intake", "Sleep Hours", "Mood" |
| **Log** = daily entry in that column | "7 glasses", "7.5 hours", "mood: 8/10" |

### What a Log Entry Looks Like

```json
{
    "id": "log-uuid-001",
    "user_id": "user-uuid",
    "habit_id": "water-habit-uuid",
    "log_date": "2026-09-26",
    "value_numeric": 7.0,
    "value_boolean": null,
    "value_scale": null,
    "notes": "Forgot to drink in the afternoon",
    "created_at": "2026-09-26T22:00:00Z"
}
```

### Key Constraint: One Log Per Habit Per Day

```
UNIQUE constraint: (user_id, habit_id, log_date)

✅ Sep 26 + Water = 7 glasses      (first log for today)
❌ Sep 26 + Water = 8 glasses      (DUPLICATE — use update instead)
✅ Sep 27 + Water = 8 glasses      (different date — OK)
✅ Sep 26 + Sleep = 7.5 hours      (different habit — OK)
```

This constraint is enforced at the database level AND the service level. The database prevents accidental duplicates even if the service check fails (belt and suspenders).

---

<a name="habits-connection"></a>
## 2. How Logs Connect to Habits

```
users (1) ──── (many) habits (1) ──── (many) habit_logs

User "Shreya" (id=user-001)
  ├── Habit: 💧 Water Intake (id=habit-001, type=numeric, target=8)
  │     ├── Log: Sep 25 → 7 glasses
  │     ├── Log: Sep 26 → 8 glasses ✅ (hit target)
  │     └── Log: Sep 27 → 6 glasses
  │
  ├── Habit: 🛌 Sleep Hours (id=habit-002, type=numeric, target=7)
  │     ├── Log: Sep 25 → 7.5 hours
  │     └── Log: Sep 26 → 6.0 hours
  │
  ├── Habit: 🧘 Meditated? (id=habit-003, type=boolean)
  │     ├── Log: Sep 25 → true ✅
  │     └── Log: Sep 26 → false ❌
  │
  └── Habit: 😊 Mood (id=habit-004, type=scale)
        ├── Log: Sep 25 → 8 out of 10
        └── Log: Sep 26 → 6 out of 10
```

The **habit_id** foreign key links each log to its habit. The habit's **type** determines which value column is used.

---

<a name="value-types"></a>
## 3. The Three Value Types — Polymorphic Storage

Each log entry has THREE value columns, but only ONE is filled per entry:

```
┌─────────────────────────────────────────────────────────────────┐
│  habit_logs table                                                │
│                                                                   │
│  id │ habit_id │ log_date   │ value_numeric │ value_boolean │ value_scale │
│ ───┼──────────┼────────────┼───────────────┼───────────────┼─────────────│
│  1 │ water    │ 2026-09-26 │     7.0       │     NULL      │    NULL     │
│  2 │ meditate │ 2026-09-26 │     NULL      │     true      │    NULL     │
│  3 │ mood     │ 2026-09-26 │     NULL      │     NULL      │      8      │
└─────────────────────────────────────────────────────────────────┘
```

### Why Three Columns Instead of One?

```
OPTION 1: Single "value" column (FLOAT)
  Water: value = 7.0         ← fine
  Sleep: value = 7.5         ← fine
  Meditated: value = 1.0     ← weird: what does 1.0 mean? true?
  Mood: value = 8.0          ← works but loses scale semantics

OPTION 2: Three typed columns (what we chose)
  Water: value_numeric = 7.0       ← clear type
  Meditated: value_boolean = true   ← actual boolean
  Mood: value_scale = 8             ← integer 1-10

  ✅ Type-correct storage
  ✅ Clear querying (AVG on value_numeric, COUNT(true) on value_boolean)
  ✅ Validation per type (scale must be 1-10, numeric must be ≥ 0)
```

### How Analytics Uses Each Type

| Type | Log Value | Analytics Calculation |
|------|-----------|---------------------|
| **numeric** | `value_numeric = 7.0` | `AVG(value_numeric)` → average water intake |
| **boolean** | `value_boolean = true` | `COUNT(value_boolean = true) / COUNT(*)` → % of days exercised |
| **scale** | `value_scale = 8` | `AVG(value_scale)` → average mood rating |

---

<a name="endpoints"></a>
## 4. Endpoints Overview

All endpoints require authentication.

| # | Method | Endpoint | Request Body | Response | Status | Purpose |
|---|--------|----------|-------------|----------|--------|---------|
| 1 | `POST` | `/api/v1/logs` | `LogCreate` | `LogResponse` | `201` | Log a single habit |
| 2 | `POST` | `/api/v1/logs/bulk` | `BulkLogCreate` | `list[LogResponse]` | `201` | Daily check-in (all habits at once) |
| 3 | `GET` | `/api/v1/logs` | — | `list[LogResponse]` | `200` | Get logs by date/range/habit |
| 4 | `PUT` | `/api/v1/logs/{id}` | `LogUpdate` | `LogResponse` | `200` | Update a log value |
| 5 | `DELETE` | `/api/v1/logs/{id}` | — | `SuccessResponse` | `200` | Delete a log entry |

### The Bulk Endpoint — Daily Check-In

The most important endpoint is **POST /logs/bulk**. This is the daily check-in page: user fills in all habits at once and hits "Save All."

```json
// POST /api/v1/logs/bulk
{
    "log_date": "2026-09-26",
    "entries": [
        {"habit_id": "water-id", "value_numeric": 8.0},
        {"habit_id": "sleep-id", "value_numeric": 7.5},
        {"habit_id": "meditate-id", "value_boolean": true},
        {"habit_id": "mood-id", "value_scale": 7}
    ]
}
```

**Key behavior:** If a log already exists for a habit on that date, it's **UPDATED** (not rejected). This makes the endpoint **idempotent** — the user can hit "Save" multiple times without errors.

### Flexible GET Filtering

```
GET /logs?date=2026-09-26                    → Today's logs (check-in page)
GET /logs?start=2026-09-01&end=2026-09-30    → Month (for charts)
GET /logs?start=...&end=...&habit_id=...     → Specific habit's history
GET /logs                                     → Defaults to today
```

### Error Responses

| Scenario | Status | Error Code |
|----------|--------|------------|
| Log already exists for this habit + date | `409` | `DUPLICATE_LOG` |
| Future date | `422` | `FUTURE_DATE` |
| Wrong value type (numeric habit but boolean value) | `422` | `INVALID_LOG_VALUE` |
| Scale value outside 1-10 | `422` | `INVALID_LOG_VALUE` |
| Habit not found | `404` | `HABIT_NOT_FOUND` |
| Log not found | `404` | `LOG_NOT_FOUND` |

---

<a name="file-list"></a>
## 5. File List & Build Order

### Module File Structure

```
backend/app/modules/logs/
├── __init__.py           ← Empty
├── models.py             ← HabitLog model (10 columns, 2 FKs, UNIQUE constraint)
├── exceptions.py         ← 4 exception classes
├── schemas.py            ← 5 schemas (LogCreate, BulkLogCreate, LogUpdate, LogResponse, BulkLogEntry)
├── repository.py         ← LogRepository (date queries, upsert, range filters)
├── service.py            ← LogService (type validation, cache invalidation, bulk operations)
└── router.py             ← 5 endpoints
```

### Build Order

| # | File | Doc | Why This Order |
|---|------|-----|---------------|
| 1 | `models.py` | Part 06a | Table + UNIQUE constraint must exist first |
| 2 | `exceptions.py` | Part 06a | Service raises these |
| 3 | `schemas.py` | Part 06a | Three-value-type schemas |
| 4 | `003_create_habit_logs.py` | Part 06a | Migration with composite unique |
| 5 | `repository.py` | Part 06b | Date-range queries, upsert |
| 6 | `service.py` | Part 06b | Type validation + cache invalidation |
| 7 | `router.py` | Part 06c | Flexible GET with multiple query params |

### Layer Architecture

```
┌────────────────────────────────────────────────────────┐
│  router.py — 5 endpoints, flexible GET filtering        │
│  schemas.py — LogCreate, BulkLogCreate, BulkLogEntry    │
├────────────────────────────────────────────────────────┤
│  service.py — type validation, bulk upsert, cache bust  │
│  exceptions.py — DuplicateLog, FutureDate, InvalidValue │
├────────────────────────────────────────────────────────┤
│  repository.py — date queries, range filters, upsert    │
│  models.py — HabitLog (10 columns, 2 FKs, UNIQUE)      │
├────────────────────────────────────────────────────────┤
│  PostgreSQL (habit_logs table) + Redis (cache bust)      │
└────────────────────────────────────────────────────────┘
```

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 06a: Logs Models, Exceptions, Schemas & Migration

```
📄 phase4-part06a-logs-entities-migrations.md
├── models.py         — HabitLog (10 columns, 2 FKs, UNIQUE constraint)
├── exceptions.py     — 4 exceptions (DuplicateLog, FutureDate, InvalidLogValue, LogNotFound)
├── schemas.py        — LogCreate, BulkLogCreate, BulkLogEntry, LogUpdate, LogResponse
└── 003_create_habit_logs_table.py — Migration with composite unique index

KEY CONCEPTS: Composite UNIQUE constraint, polymorphic value columns, bulk schema
TIME: ~45 minutes
```

### Part 06b: Logs Repository & Service

```
📄 phase4-part06b-logs-repository-service.md
├── repository.py     — Date range queries, upsert, user-scoped filters
└── service.py        — Type validation, bulk create/update, Redis cache invalidation

KEY CONCEPTS: Upsert (INSERT or UPDATE), cache invalidation, cross-module dependency (HabitRepository)
TIME: ~60 minutes
```

### Part 06c: Logs Router

```
📄 phase4-part06c-logs-controller.md
└── router.py         — 5 endpoints with flexible GET filtering

KEY CONCEPTS: Multiple query parameters with aliases, conditional filtering, bulk POST
TIME: ~30 minutes
```

### Part 06d: Logs Connections & Flows

```
📄 phase4-part06d-logs-connections-and-flows.md
├── Single log creation flow (with type validation)
├── Bulk daily check-in flow (with upsert logic)
├── Flexible GET query flow (date vs range vs default)
├── Cache invalidation flow (Redis key deletion)
└── How logs feed into analytics and AI

KEY CONCEPTS: End-to-end flows, cache patterns, data pipeline to analytics
TIME: ~20 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI APPLICATION                                │
│                                                                              │
│  ┌─── AUTH ───┐    ┌─── HABITS ───┐    ┌─── LOGS (this module) ───────────┐ │
│  │ user_id    │    │ habits table  │    │                                   │ │
│  │ from JWT   │───>│ habit_type    │───>│ router.py: 5 endpoints            │ │
│  └────────────┘    │ target_value  │    │   POST /logs (single)             │ │
│                    └──────┬────────┘    │   POST /logs/bulk (daily check-in) │ │
│                           │             │   GET  /logs (date/range/habit)    │ │
│                           │ FK          │   PUT  /logs/:id (update)          │ │
│                           ▼             │   DELETE /logs/:id                 │ │
│                    ┌──────────────┐     │                                   │ │
│                    │ habit_logs   │     │ service.py:                        │ │
│                    │ table        │     │   validate type match              │ │
│                    │              │     │   prevent future dates             │ │
│                    │ user_id (FK) │     │   bulk upsert                     │ │
│                    │ habit_id (FK)│     │   invalidate analytics cache       │ │
│                    │ log_date     │     │                                   │ │
│                    │ value_numeric│     │ repository.py:                     │ │
│                    │ value_boolean│     │   date range queries              │ │
│                    │ value_scale  │     │   upsert (create or update)       │ │
│                    │ notes        │     │   user-scoped filters             │ │
│                    └──────────────┘     └───────────────────────────────────┘ │
│                           │                                                   │
│                           │ data flows to                                     │
│                           ▼                                                   │
│  ┌─── ANALYTICS (Part 07) ────────────────────────────────────────────────┐  │
│  │  SELECT AVG(value_numeric) FROM habit_logs                              │  │
│  │  WHERE habit_id = ? AND log_date BETWEEN ? AND ?                        │  │
│  │  → "Average water intake this week: 7.2 glasses"                        │  │
│  │  → "Sleep streak: 5 consecutive days"                                   │  │
│  │  → "Mood correlates with exercise (r=0.72)"                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Polymorphic value columns** | Three columns for three types — only one filled per row | `models.py` |
| 2 | **Composite UNIQUE constraint** | `UNIQUE(user_id, habit_id, log_date)` — one log per habit per day | `models.py` |
| 3 | **Two foreign keys** | References both `users.id` AND `habits.id` | `models.py` |
| 4 | **Bulk schema** | `BulkLogCreate` wraps multiple `BulkLogEntry` in one request | `schemas.py` |
| 5 | **Upsert logic** | Create if not exists, update if exists (for bulk endpoint) | `repository.py` |
| 6 | **Date range queries** | `WHERE log_date BETWEEN ? AND ?` | `repository.py` |
| 7 | **Cross-module validation** | Log service calls HabitRepository to check habit type | `service.py` |
| 8 | **Cache invalidation** | Delete Redis analytics cache when logs change | `service.py` |
| 9 | **Multiple query params** | `GET /logs?date=...&start=...&end=...&habit_id=...` | `router.py` |
| 10 | **Query aliases** | `Query(alias="start")` maps URL param `?start=` to Python `start_date` | `router.py` |
| 11 | **Idempotent bulk endpoint** | Saving twice doesn't create duplicates | `service.py` |
| 12 | **Hard delete** | Logs use actual DELETE (not soft delete) — unlike habits | `service.py` |

---

<a name="prerequisites"></a>
## 9. Prerequisites

| # | Prerequisite | Document | What It Gives You |
|---|-------------|----------|-------------------|
| 1 | Auth module complete | [Parts 04a–04f](./phase4-part04-auth-service-overview.md) | `get_current_user_id` dependency |
| 2 | Habits module complete | [Parts 05a–05e](./phase4-part05-habits-service-overview.md) | Habit model, HabitRepository (for type validation) |
| 3 | Shared utilities | [Part 03](./phase4-part03-shared-utilities-middleware.md) | BaseRepository, date_utils, logging |

---

<a name="design-decisions"></a>
## 10. Design Decisions Summary

### Decision 1: Three Value Columns vs Single Value Column

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Log Value Storage Strategy                        │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Three typed columns (value_numeric, value_boolean,         │
│          value_scale), one filled per row                           │
│                                                                     │
│  WHY:                                                               │
│  • Type-correct: boolean IS boolean in DB, not 1.0/0.0              │
│  • Queryable: AVG(value_numeric) works. AVG on booleans doesn't.    │
│  • Validatable: scale constraint (1-10) on integer column           │
│  • Clear: looking at a row, you see which type was logged           │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Single FLOAT column                                             │
│     ❌ Boolean as 1.0/0.0 is semantically wrong                   │
│     ❌ Can't enforce scale 1-10 constraint                         │
│  2. JSONB column                                                    │
│     ❌ Loses type safety, can't use AVG/SUM directly               │
│     ❌ No column-level constraints                                  │
│  3. Separate tables per type (numeric_logs, boolean_logs, ...)      │
│     ❌ 3x tables, 3x queries, 3x endpoints — over-engineered      │
│                                                                     │
│  TRADE-OFF: NULLs in 2 of 3 columns per row (~10 bytes wasted).    │
│  At our scale (millions of rows max), this is negligible.           │
│                                                                     │
│  INTERVIEW TIP: "We use three typed columns to preserve type        │
│  correctness while keeping a single table. Booleans are stored as   │
│  actual booleans, making analytics queries like 'percentage of      │
│  days exercised' straightforward. The NULL overhead is negligible." │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Bulk Endpoint with Upsert vs Separate Create/Update

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Daily Check-In Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: POST /logs/bulk that creates OR updates (upsert)           │
│                                                                     │
│  WHY:                                                               │
│  • UX: user fills the daily check-in page and hits "Save All"      │
│  • Idempotent: saving twice doesn't create duplicates               │
│  • Atomic: all entries saved or none (single transaction)           │
│  • Simple frontend: one API call instead of N individual calls      │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Individual POST /logs for each habit                            │
│     ❌ N API calls for N habits — slow, not atomic                 │
│  2. Reject duplicates on bulk (409 for existing logs)               │
│     ❌ User can't hit save twice — poor UX                         │
│                                                                     │
│  INTERVIEW TIP: "The bulk endpoint uses upsert logic — if a log    │
│  exists for that habit + date, it's updated; if not, it's created.  │
│  This makes the daily check-in idempotent and atomic."              │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: Hard Delete for Logs vs Soft Delete

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Log Deletion Strategy                             │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Hard delete (actual DELETE FROM) for log entries            │
│                                                                     │
│  WHY:                                                               │
│  • Logs are data points, not entities — deleting wrong data is fine │
│  • User explicitly wants to remove incorrect data                   │
│  • No other modules reference log IDs as foreign keys               │
│  • Soft delete would require filtering in every analytics query     │
│                                                                     │
│  CONTRAST WITH HABITS: Habits use soft delete (is_archived) because │
│  logs reference habit_id as FK. Deleting a habit would cascade.     │
│  Logs have no dependents — safe to hard delete.                     │
│                                                                     │
│  INTERVIEW TIP: "We chose hard delete for logs because they're      │
│  leaf data with no dependents. Habits use soft delete because logs   │
│  reference them. The deletion strategy depends on whether other      │
│  data depends on the resource."                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verification"></a>
## 11. Verification Checklist (After All Sub-Parts)

```bash
# 1. Create a log (need a habit first)
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"habit_id":"WATER_HABIT_ID","log_date":"2026-09-26","value_numeric":7.0}'
# Expected: 201

# 2. Bulk daily check-in
curl -X POST http://localhost/api/v1/logs/bulk \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"log_date":"2026-09-26","entries":[
    {"habit_id":"WATER_ID","value_numeric":8},
    {"habit_id":"SLEEP_ID","value_numeric":7.5},
    {"habit_id":"MOOD_ID","value_scale":7}
  ]}'
# Expected: 201 with array of logs

# 3. Get today's logs
curl "http://localhost/api/v1/logs?date=2026-09-26" \
  -H "Authorization: Bearer TOKEN"
# Expected: all logs for that date

# 4. Get date range
curl "http://localhost/api/v1/logs?start=2026-09-01&end=2026-09-30" \
  -H "Authorization: Bearer TOKEN"
# Expected: all logs for September

# 5. Test duplicate rejection (single endpoint)
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"habit_id":"WATER_ID","log_date":"2026-09-26","value_numeric":9}'
# Expected: 409 DUPLICATE_LOG

# 6. Test future date
curl -X POST http://localhost/api/v1/logs \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"habit_id":"WATER_ID","log_date":"2099-12-31","value_numeric":5}'
# Expected: 422 FUTURE_DATE
```

---

<a name="interview"></a>
## 12. Interview Q&A (Module Level)

### Q1: How does the daily check-in work?
**A:** "The user opens the check-in page, which loads all active habits via `GET /habits`. They fill in values for each habit and hit 'Save All'. The frontend sends a single `POST /logs/bulk` with the date and an array of entries — one per habit with the appropriate value field (numeric, boolean, or scale). The service validates each entry's value against the habit's type, then performs an upsert: creates new logs or updates existing ones. This makes the operation idempotent — users can save multiple times without duplicates."

### Q2: Why three value columns instead of one?
**A:** "Type correctness and queryable analytics. A single FLOAT column would store boolean as 1.0/0.0 — semantically wrong and makes queries like 'percentage of days exercised' awkward. With three columns (value_numeric, value_boolean, value_scale), each type is stored correctly. `AVG(value_numeric)` works for water intake, `COUNT(value_boolean = true)` works for exercise days, and we can enforce scale is 1-10 at the column level."

### Q3: How do you prevent duplicate logs?
**A:** "Two layers. First, the service checks before inserting. Second, the database has a `UNIQUE(user_id, habit_id, log_date)` constraint — even if the service check fails due to a race condition, the database prevents the duplicate. The single-log endpoint returns 409 with a helpful message: 'Use update instead.' The bulk endpoint handles duplicates gracefully by upserting."

### Q4: What is cache invalidation and why do you do it when logs change?
**A:** "The Analytics module caches computed results in Redis — weekly averages, streaks, correlations — because these queries are expensive (complex SQL with JOINs and aggregations). When a log is created, updated, or deleted, the underlying data changes, making the cache stale. We invalidate (delete) the relevant Redis cache keys so the next analytics request recalculates with fresh data. This is the 'write-through invalidation' pattern."

### Q5: Why hard delete for logs but soft delete for habits?
**A:** "Habits use soft delete because the habit_logs table references habit_id as a foreign key — hard deleting a habit would cascade-delete all its logs or violate the constraint. Logs are leaf data — no other table references log IDs. When a user deletes a log entry (wrong data), they want it gone. Soft-deleting logs would add an `is_deleted` filter to every analytics query — unnecessary complexity for data that has no dependents."

---

<a name="navigation"></a>
## 13. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 05e: Habits Connections & Flows](./phase4-part05e-habits-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 06a: Logs Models, Exceptions, Schemas & Migration](./phase4-part06a-logs-entities-migrations.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Sub-Part Quick Links

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 06a | [Logs Models, Schemas & Migration](./phase4-part06a-logs-entities-migrations.md) | models.py + exceptions.py + schemas.py + migration |
| 06b | [Logs Repository & Service](./phase4-part06b-logs-repository-service.md) | repository.py + service.py |
| 06c | [Logs Router](./phase4-part06c-logs-controller.md) | router.py with flexible filtering |
| 06d | [Logs Connections & Flows](./phase4-part06d-logs-connections-and-flows.md) | Flow diagrams |

---

**End of Phase 4 Part 06: Logs Module Overview**

*You now understand WHAT logs are, HOW the three value types work, and WHY the bulk endpoint uses upsert. Same layered architecture — router → service → repository → model. Next: start building the data layer.*
