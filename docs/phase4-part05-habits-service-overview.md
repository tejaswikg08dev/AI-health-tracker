# 📊 Phase 4 Part 05: Habits Module — Overview & Roadmap

> **"Habits are the heart of this application. Auth tells us WHO you are. Habits tell us WHAT you're tracking. Everything else — logs, analytics, AI insights — flows from the habits you define here."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 05 (Habits Module — Overview) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.1 — Habit Management |
| **Previous** | [phase4-part04f-auth-connections-and-flows.md](./phase4-part04f-auth-connections-and-flows.md) |
| **Next** | [phase4-part05a-habits-entities-migrations.md](./phase4-part05a-habits-entities-migrations.md) |
| **Module Files** | 7 Python files + 1 Alembic migration |
| **Endpoints** | 6 (create, list, get, update, delete/archive, reorder) |
| **Sub-Parts** | 5 documents (05a through 05e) |
| **Time to Type** | ~3 hours (across all 5 sub-parts) |
| **Difficulty** | Medium (builds on auth patterns — same architecture, new domain) |

---

## 📖 Table of Contents

1. [What Is the Habits Module?](#what-is-habits)
2. [Why Habits Are the Foundation](#why-habits)
3. [Habit Types — Three Ways to Track](#habit-types)
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

<a name="what-is-habits"></a>
## 1. What Is the Habits Module?

The Habits module manages the **things users want to track** — water intake, sleep hours, exercise, mood, meditation, steps, and anything else they define. A habit is a template: "I want to track Water Intake, measured in glasses, with a daily goal of 8."

The actual daily values ("I drank 6 glasses today") go in the **Logs module** (Part 06). The Habits module defines WHAT to track; the Logs module records HOW MUCH.

### Real-World Analogy

Think of a **fitness journal**:
- **Habits** = the column headers you write at the top of each page: "Water", "Sleep", "Steps", "Mood"
- **Logs** = the daily entries you write in each column: "8 glasses", "7.5 hours", "12,000", "😊 (8/10)"
- **Analytics** = the summary page where you see trends: "Average sleep this week: 7.2 hours"

You first define the headers (habits), then fill in daily values (logs), then analyze patterns (analytics).

### What a Habit Looks Like

```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "abc-123",
    "name": "Water Intake",
    "habit_type": "numeric",
    "unit": "glasses",
    "target_value": 8.0,
    "color": "#3B82F6",
    "icon": "💧",
    "sort_order": 0,
    "is_archived": false,
    "created_at": "2026-09-26T10:00:00Z"
}
```

---

<a name="why-habits"></a>
## 2. Why Habits Are the Foundation

Every other module depends on habits:

```
┌──────────────┐
│   HABITS     │ ← You are here
│  "Water"     │
│  "Sleep"     │
│  "Mood"      │
└──────┬───────┘
       │ defines what to track
       ▼
┌──────────────┐
│    LOGS      │ ← Part 06
│  "8 glasses" │
│  "7.5 hours" │
│  "mood: 8"   │
└──────┬───────┘
       │ provides data for
       ▼
┌──────────────┐
│  ANALYTICS   │ ← Part 07
│  "avg: 7.2h" │
│  "streak: 5" │
│  "trend: ↑"  │
└──────┬───────┘
       │ feeds into
       ▼
┌──────────────┐
│    AI        │ ← Parts 08-12
│  "You sleep  │
│   better on  │
│   days you   │
│   exercise"  │
└──────────────┘
```

Without habits, there's nothing to log, nothing to analyze, and nothing for the AI to learn from.

---

<a name="habit-types"></a>
## 3. Habit Types — Three Ways to Track

| Type | What It Measures | Example | Log Value | Target |
|------|-----------------|---------|-----------|--------|
| **numeric** | A quantity (number) | Water: 8 glasses | `6.0` | `8.0` |
| **boolean** | Yes/No (did or didn't) | Exercise: yes | `true` | — (just "yes") |
| **scale** | Rating 1–10 | Mood: 7/10 | `7.0` | — (optional) |

### Why Three Types?

Not everything is a number. Some habits are binary ("Did I meditate today?"), some are subjective ("How's my mood on a scale of 1-10?"), and some are measurable ("How many glasses of water?"). The type determines:
- **How the frontend renders the input** (number field, toggle switch, or slider)
- **How analytics calculates averages** (boolean → percentage of "yes" days, numeric → average value)
- **What validation rules apply** (scale must be 1-10, numeric must be positive)

### Example Habits Per Type

```
NUMERIC habits:
  💧 Water Intake    → 8 glasses/day
  🛌 Sleep Hours     → 7 hours/day
  🏃 Steps           → 10,000 steps/day
  📖 Reading         → 30 pages/day

BOOLEAN habits:
  🧘 Meditated?      → yes/no
  🏋️ Exercised?      → yes/no
  💊 Took Vitamins?   → yes/no
  📓 Journaled?       → yes/no

SCALE habits:
  😊 Mood            → 1-10 rating
  ⚡ Energy Level    → 1-10 rating
  😰 Stress Level    → 1-10 rating
  😴 Sleep Quality   → 1-10 rating
```

---

<a name="endpoints"></a>
## 4. Endpoints Overview

All endpoints require authentication (`get_current_user_id` dependency from Auth module).

| # | Method | Endpoint | Request Body | Response | Status | Purpose |
|---|--------|----------|-------------|----------|--------|---------|
| 1 | `POST` | `/api/v1/habits` | `HabitCreate` | `HabitResponse` | `201` | Create a new habit |
| 2 | `GET` | `/api/v1/habits` | — | `list[HabitResponse]` | `200` | List all habits |
| 3 | `GET` | `/api/v1/habits/{id}` | — | `HabitResponse` | `200` | Get one habit |
| 4 | `PUT` | `/api/v1/habits/{id}` | `HabitUpdate` | `HabitResponse` | `200` | Update a habit |
| 5 | `DELETE` | `/api/v1/habits/{id}` | — | `SuccessResponse` | `200` | Archive (soft delete) |
| 6 | `PUT` | `/api/v1/habits/reorder` | `HabitReorderRequest` | `list[HabitResponse]` | `200` | Reorder dashboard |

### Error Responses

| Scenario | Status | Error Code | Triggered By |
|----------|--------|------------|-------------|
| Habit not found (or belongs to another user) | `404` | `HABIT_NOT_FOUND` | GET/PUT/DELETE with wrong ID |
| Duplicate habit name for this user | `409` | `DUPLICATE_HABIT_NAME` | POST with existing name |
| Too many active habits (>20) | `422` | `HABIT_LIMIT_EXCEEDED` | POST when at 20 habits |
| Invalid habit type | `422` | `INVALID_HABIT_TYPE` | POST with wrong type |
| Invalid request body | `422` | `VALIDATION_ERROR` | Missing fields, bad format |
| Not authenticated | `401` | `TOKEN_INVALID` | No/bad token |

### Key Business Rules

1. **Max 20 active habits** — prevents UI clutter and keeps daily logging manageable
2. **No duplicate names per user** — "Water" can't be created twice (but different users can each have "Water")
3. **Habit type is immutable** — once created as "numeric", can't change to "boolean" (would break existing log data)
4. **Delete = archive** — setting `is_archived=True`. Historical data preserved for analytics
5. **Sort order for drag-and-drop** — users arrange habits in their preferred order on the dashboard

---

<a name="file-list"></a>
## 5. File List & Build Order

### Module File Structure

```
backend/app/modules/habits/
├── __init__.py           ← Empty
├── models.py             ← Habit database model (12 columns)
├── exceptions.py         ← 4 habit-specific exception classes
├── schemas.py            ← 5 schemas (HabitCreate, HabitUpdate, HabitResponse, HabitType enum, HabitReorderRequest)
├── repository.py         ← HabitRepository (inherits BaseRepository + 5 custom queries)
├── service.py            ← HabitService (create, list, get, update, delete, reorder)
└── router.py             ← 6 endpoint definitions
```

### Build Order

| # | File | Doc | Why This Order |
|---|------|-----|---------------|
| 1 | `models.py` | Part 05a | Table definition must exist first |
| 2 | `exceptions.py` | Part 05a | Service raises these |
| 3 | `schemas.py` | Part 05a | Router uses for validation/response |
| 4 | `002_create_habits_table.py` | Part 05a | Migration to create the table |
| 5 | `repository.py` | Part 05b | Service calls for DB access |
| 6 | `service.py` | Part 05c | Business logic |
| 7 | `router.py` | Part 05d | HTTP endpoints |

### Layer Architecture (Same as Auth)

```
┌────────────────────────────────────────────────────────┐
│  router.py — 6 endpoints, uses get_current_user_id     │
│  schemas.py — HabitCreate, HabitResponse, HabitType     │
├────────────────────────────────────────────────────────┤
│  service.py — create, list, get, update, delete, reorder│
│  exceptions.py — HabitNotFound, DuplicateName, Limit    │
├────────────────────────────────────────────────────────┤
│  repository.py — SQL queries (by user, by name, count)  │
│  models.py — Habit table (12 columns, FK to users)      │
├────────────────────────────────────────────────────────┤
│  PostgreSQL (habits table)                               │
└────────────────────────────────────────────────────────┘
```

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 05a: Habits Models, Exceptions, Schemas & Migration

```
📄 phase4-part05a-habits-entities-migrations.md
├── models.py         — Habit database model (12 columns, FK to users, soft delete)
├── exceptions.py     — 4 habit-specific exceptions
├── schemas.py        — HabitType enum, HabitCreate, HabitUpdate, HabitResponse, HabitReorderRequest
└── 002_create_habits_table.py — Alembic migration

KEY CONCEPTS: Foreign keys, Enum type, field_validator, composite uniqueness
TIME: ~45 minutes
```

### Part 05b: Habits Repository

```
📄 phase4-part05b-habits-repositories.md
└── repository.py     — HabitRepository (get_by_user, count_active, get_by_name, get_next_order)

KEY CONCEPTS: Filtered queries (WHERE user_id AND NOT archived), counting, ordering
TIME: ~30 minutes
```

### Part 05c: Habits Service

```
📄 phase4-part05c-habits-service-tests.md
└── service.py        — HabitService (create, list, get, update, delete, reorder)

KEY CONCEPTS: Business rule enforcement (max 20, no duplicates, immutable type), soft delete
TIME: ~45 minutes
```

### Part 05d: Habits Router

```
📄 phase4-part05d-habits-controller-docker.md
└── router.py         — 6 endpoints + HabitService dependency + register in main.py

KEY CONCEPTS: Path parameters ({habit_id}), query parameters (?include_archived), list responses
TIME: ~30 minutes
```

### Part 05e: Habits Connections & Flows

```
📄 phase4-part05e-habits-connections-and-flows.md
├── Create habit flow (with validation chain)
├── Reorder flow (drag-and-drop → sort_order update)
├── Soft delete flow (archive → hide from dashboard, keep for analytics)
└── Cross-module: how Logs and Analytics reference habits

KEY CONCEPTS: End-to-end flows, error paths, how habits connect to logs/analytics
TIME: ~20 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

### How the Habits Module Fits in the System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI APPLICATION                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        AUTH MODULE (Part 04)                            │  │
│  │  get_current_user_id → extracts user_id from JWT                       │  │
│  └───────────────────────────────────┬────────────────────────────────────┘  │
│                                      │ provides user_id                      │
│                                      ▼                                       │
│  ┌────────────────────── HABITS MODULE (Part 05) ────────────────────────┐  │
│  │                                                                        │  │
│  │  router.py ──→ service.py ──→ repository.py ──→ models.py             │  │
│  │      │              │              │                                    │  │
│  │      │              │              └── PostgreSQL (habits table)        │  │
│  │      │              │                  FK → users.id                    │  │
│  │      │              │                                                  │  │
│  │      │              └── exceptions.py (HabitNotFound, DuplicateName)   │  │
│  │      │                                                                 │  │
│  │      └── schemas.py (HabitCreate, HabitResponse, HabitType enum)       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                                      │ habits referenced by                  │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  LOGS MODULE (Part 06)              ANALYTICS MODULE (Part 07)          │  │
│  │  habit_logs table:                  Queries join habits + logs:          │  │
│  │    habit_id FK → habits.id          "avg sleep this week"               │  │
│  │    value: 7.5                       "streak for Water: 5 days"          │  │
│  │    log_date: 2026-09-26             "mood correlates with exercise"     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Database Relationship

```
users (1) ──── (many) habits (1) ──── (many) habit_logs

User "Shreya" has habits:
  ├── 💧 Water Intake (numeric, target: 8 glasses)
  ├── 🛌 Sleep Hours  (numeric, target: 7 hours)
  ├── 🧘 Meditated?   (boolean)
  └── 😊 Mood         (scale, 1-10)

Each habit has daily logs:
  💧 Water Intake:
    ├── Sep 25: 7 glasses
    ├── Sep 26: 8 glasses ✅ (hit target)
    └── Sep 27: 6 glasses
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Foreign Key** | `user_id` references `users.id` — links habits to users | `models.py` |
| 2 | **`ondelete="CASCADE"`** | If a user is deleted, their habits are auto-deleted | `models.py` |
| 3 | **Python Enum** | `HabitType(str, Enum)` — restricts values to defined options | `schemas.py` |
| 4 | **`field_validator`** | Pydantic custom validation (hex color format, etc.) | `schemas.py` |
| 5 | **Filtered Queries** | `WHERE user_id = ? AND is_archived = false` | `repository.py` |
| 6 | **Business Rule Validation** | Max 20 habits, no duplicates, immutable type | `service.py` |
| 7 | **Soft Delete** | Set `is_archived=True` instead of `DELETE FROM` | `service.py` |
| 8 | **Sort Order (Reorder)** | Batch update `sort_order` for drag-and-drop UI | `service.py` |
| 9 | **Path Parameters** | `/{habit_id}` — UUID from the URL path | `router.py` |
| 10 | **Query Parameters** | `?include_archived=true` — optional filter | `router.py` |
| 11 | **List Response** | Return `list[HabitResponse]` instead of single object | `router.py` |

---

<a name="prerequisites"></a>
## 9. Prerequisites

| # | Prerequisite | Document | What It Gives You |
|---|-------------|----------|-------------------|
| 1 | Auth module complete | [Parts 04a–04f](./phase4-part04-auth-service-overview.md) | `get_current_user_id` dependency, User model, users table |
| 2 | Shared utilities | [Part 03](./phase4-part03-shared-utilities-middleware.md) | BaseRepository, base_schemas, exceptions, logging |
| 3 | Backend foundation | [Part 02](./phase4-part02-backend-foundation.md) | database.py, dependencies.py, config.py |

### Quick Verification

```bash
# Auth module works (can signup + login)
curl -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test123!@#","full_name":"Test"}'

# Users table exists
docker-compose exec postgres psql -U health_user -d health_tracker \
  -c "SELECT count(*) FROM users"
```

---

<a name="design-decisions"></a>
## 10. Design Decisions Summary

### Decision 1: Habit Type as String vs Database Enum

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Habit Type Storage                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: String column validated by Pydantic Enum                   │
│                                                                     │
│  WHY:                                                               │
│  • Adding new types doesn't require a migration                     │
│  • Pydantic Enum validates on input (rejects invalid types)         │
│  • String is portable — works with any database                     │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. PostgreSQL ENUM type                                            │
│     ❌ Adding a value requires ALTER TYPE migration (complex)       │
│  2. Integer mapping (1=numeric, 2=boolean, 3=scale)                 │
│     ❌ Not self-documenting — what does type=2 mean?               │
│                                                                     │
│  INTERVIEW TIP: "We store habit types as strings validated by       │
│  a Pydantic Enum. This avoids ALTER TYPE migrations when adding     │
│  new types while still enforcing valid values at the API layer."    │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Max 20 Habits Limit

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Habit Count Limit                                 │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Maximum 20 active habits per user                          │
│                                                                     │
│  WHY:                                                               │
│  • UX: Daily check-in with 50+ habits is overwhelming               │
│  • Performance: Dashboard loads all active habits at once            │
│  • Focus: Research shows tracking 5-10 habits is most effective     │
│  • Prevention: Stops abuse (bot creating thousands of habits)        │
│                                                                     │
│  ENFORCEMENT: Service layer checks count before create.             │
│  Archived habits don't count — user can archive old ones            │
│  and create new ones.                                               │
│                                                                     │
│  INTERVIEW TIP: "We enforce a 20-habit limit at the service layer   │
│  for UX and performance. The count query excludes archived habits,  │
│  so users can archive old tracking and start new ones."             │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: Soft Delete (is_archived) vs Hard Delete

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Habit Deletion Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Soft delete — set is_archived=True, keep all data          │
│                                                                     │
│  WHY:                                                               │
│  • Historical analytics preserved: "Your average sleep when you     │
│    tracked it was 7.2 hours" — still works after archiving          │
│  • habit_logs table has FK to habits.id — hard delete would         │
│    cascade-delete all log entries or violate FK constraint           │
│  • User can un-archive (restore) a habit later                      │
│  • AI insights can reference archived habit data                    │
│                                                                     │
│  HOW: DELETE endpoint sets is_archived=True.                        │
│  All queries filter WHERE is_archived = false by default.           │
│  ?include_archived=true parameter for settings page.                │
│                                                                     │
│  INTERVIEW TIP: "We soft-delete habits to preserve referential      │
│  integrity with the logs table and enable historical analytics.     │
│  The AI module can still analyze patterns from archived habits."    │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verification"></a>
## 11. Verification Checklist (After All Sub-Parts)

```bash
# 1. Create a habit
curl -X POST http://localhost/api/v1/habits \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Water Intake","habit_type":"numeric","unit":"glasses","target_value":8,"color":"#3B82F6","icon":"💧"}'
# Expected: 201 with habit data

# 2. List habits
curl http://localhost/api/v1/habits \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 with array of habits

# 3. Update a habit
curl -X PUT http://localhost/api/v1/habits/HABIT_ID \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_value":10}'
# Expected: 200 with updated target_value

# 4. Archive a habit
curl -X DELETE http://localhost/api/v1/habits/HABIT_ID \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 with success message

# 5. Verify archived habit is hidden
curl http://localhost/api/v1/habits \
  -H "Authorization: Bearer TOKEN"
# Expected: archived habit NOT in the list

# 6. Show archived habits
curl "http://localhost/api/v1/habits?include_archived=true" \
  -H "Authorization: Bearer TOKEN"
# Expected: archived habit IS in the list

# 7. Test duplicate name
curl -X POST http://localhost/api/v1/habits \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Water Intake","habit_type":"numeric","unit":"glasses","target_value":8}'
# Expected: 409 DUPLICATE_HABIT_NAME
```

---

<a name="interview"></a>
## 12. Interview Q&A (Module Level)

### Q1: How did you design the habits feature?
**A:** "The Habits module follows the same layered architecture as Auth — router → service → repository → model. It supports three habit types: numeric (water, sleep), boolean (exercise, meditation), and scale (mood 1-10). The type determines frontend rendering and analytics calculations. We enforce business rules in the service layer: max 20 active habits, no duplicate names per user, and immutable habit type after creation to prevent breaking existing log data."

### Q2: Why three habit types instead of just numeric?
**A:** "User experience. Asking 'How many?' for meditation doesn't make sense — it's binary (did/didn't). Mood isn't a count — it's a subjective rating. The type drives the frontend input component (number field, toggle, slider) and analytics logic (numeric → average, boolean → percentage of yes-days, scale → average). This also maps well to real health tracking apps like Apple Health and Fitbit."

### Q3: How does soft delete work and why use it?
**A:** "When a user 'deletes' a habit, we set `is_archived=True` instead of running a SQL DELETE. The habit is hidden from the dashboard but preserved in the database. This is critical because the `habit_logs` table has a foreign key to `habits.id` — hard deleting a habit would either cascade-delete all log entries (losing data) or violate the foreign key constraint. Archived habit data remains available for analytics: 'Your average sleep when you tracked it was 7.2 hours.' The user can also un-archive a habit to start tracking again."

### Q4: How does the reorder feature work?
**A:** "Users drag and drop habits on the dashboard to arrange them in their preferred order. The frontend sends a `PUT /habits/reorder` request with an array of habit IDs in the desired order. The service loops through the array and sets `sort_order = index` for each habit. All habits are fetched ordered by `sort_order ASC`, so the dashboard respects the user's arrangement. This is a batch update wrapped in a single transaction."

### Q5: How do you ensure a user can only see their own habits?
**A:** "Every query includes `WHERE user_id = ?` using the authenticated user's ID from the JWT token. The `get_current_user_id` dependency (from the Auth module) extracts the user_id from the token BEFORE the handler runs. The repository methods all accept `user_id` as a parameter and include it in every query. Even if someone guesses a habit UUID from another user, the query returns no rows (filtered by user_id), and the service raises `HabitNotFoundError` — indistinguishable from a non-existent habit."

---

<a name="navigation"></a>
## 13. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04f: Auth Connections & Flows](./phase4-part04f-auth-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 05a: Habits Models, Exceptions, Schemas & Migration](./phase4-part05a-habits-entities-migrations.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Sub-Part Quick Links

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 05a | [Habits Models, Schemas & Migration](./phase4-part05a-habits-entities-migrations.md) | models.py + exceptions.py + schemas.py + migration |
| 05b | [Habits Repository](./phase4-part05b-habits-repositories.md) | repository.py |
| 05c | [Habits Service](./phase4-part05c-habits-service-tests.md) | service.py |
| 05d | [Habits Router](./phase4-part05d-habits-controller-docker.md) | router.py + main.py registration |
| 05e | [Habits Connections & Flows](./phase4-part05e-habits-connections-and-flows.md) | Flow diagrams |

---

**End of Phase 4 Part 05: Habits Module Overview**

*You now understand WHAT habits are, WHY three types, and HOW the module is structured. Same architecture as Auth — you already know the pattern. Next: start building — Part 05a covers the data layer.*
