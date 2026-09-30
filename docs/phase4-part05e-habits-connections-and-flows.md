# 🔄 Phase 4 Part 05e: Habits — Connections & Flows

> **"The Habits module is the bridge between identity (Auth) and data (Logs, Analytics, AI). Understanding how habits connect to every other module is understanding the application's architecture."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 05e (Habits Flows & Architecture) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.1 — Habit Management |
| **Previous** | [phase4-part05d-habits-controller-docker.md](./phase4-part05d-habits-controller-docker.md) |
| **Next** | [phase4-part06-logs-service-overview.md](./phase4-part06-logs-service-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only — no new code) |
| **Time to Read** | ~15 minutes |

---

## 📖 Table of Contents

1. [Habits Module — Complete File Map](#file-map)
2. [Flow 1: Create Habit (with Validation Chain)](#create-flow)
3. [Flow 2: Daily Dashboard Load](#dashboard-flow)
4. [Flow 3: Reorder via Drag-and-Drop](#reorder-flow)
5. [Flow 4: Soft Delete (Archive)](#archive-flow)
6. [Flow 5: Error Paths](#error-flows)
7. [Cross-Module Dependency Map](#cross-module)
8. [Habits Module Summary](#summary)
9. [Navigation](#navigation)

---

<a name="file-map"></a>
## 1. Habits Module — Complete File Map

```
backend/app/modules/habits/
├── models.py          ─── Part 05a ── Habit table (12 columns, FK → users)
├── exceptions.py      ─── Part 05a ── 4 exception classes
├── schemas.py         ─── Part 05a ── HabitType enum + 4 schemas
├── repository.py      ─── Part 05b ── 7 custom queries (user-scoped)
├── service.py         ─── Part 05c ── 6 business methods (validate-then-act)
├── router.py          ─── Part 05d ── 6 endpoints
└── __init__.py

backend/alembic/versions/
└── 002_create_habits_table.py ─── Part 05a ── Migration with composite index

Dependency chain:
  router.py → service.py → repository.py → models.py
       │           │
       │           └── exceptions.py, schemas.py (validation)
       └── auth/router.py (get_current_user_id)
```

---

<a name="create-flow"></a>
## 2. Flow 1: Create Habit (with Validation Chain)

```
STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Browser              POST /api/v1/habits
                           Headers: Authorization: Bearer eyJ...
                           Body: {"name":"Water Intake","habit_type":"numeric",
                                  "unit":"glasses","target_value":8,
                                  "color":"#3B82F6","icon":"💧"}

 2    Nginx                Rate check: api_limit (30 req/s) → OK
                           Forward to backend:8000

 3    Middleware            CORS → Logging (request_id: a1b2) → Rate Limiter → OK

 4    FastAPI              Match: POST /api/v1/habits

 5    Pydantic             Validate body → HabitCreate schema:
                             ✅ name: "Water Intake" (1-100 chars)
                             ✅ habit_type: "numeric" (valid HabitType enum)
                             ✅ target_value: 8 (ge=0, le=100000)
                             ✅ color: "#3B82F6" (field_validator: hex format)
                             ✅ icon: "💧" (max 50 chars)

 6    get_current_user_id  Decode JWT → user_id = uuid-001
                           Check Redis blacklist → not blacklisted ✅

 7    get_habit_service    Create HabitService(session)

 8    service.create_habit:
        a) repo.count_active_habits(uuid-001)
           → SELECT COUNT(*) FROM habits
             WHERE user_id = 'uuid-001' AND is_archived = false
           → 3 (under 20 limit ✅)

        b) repo.name_exists_for_user(uuid-001, "Water Intake")
           → SELECT COUNT(*) FROM habits
             WHERE user_id = 'uuid-001' AND name = 'Water Intake'
             AND is_archived = false
           → 0 (no duplicate ✅)

        c) repo.get_next_sort_order(uuid-001)
           → SELECT COALESCE(MAX(sort_order), -1) FROM habits
             WHERE user_id = 'uuid-001' AND is_archived = false
           → 2 (next = 3)

        d) repo.create(user_id=uuid-001, name="Water Intake",
                       habit_type="numeric", sort_order=3, ...)
           → INSERT INTO habits (...) VALUES (...)
           → Habit(id=habit-001)

        e) session.commit()

 9    Router               HabitResponse.model_validate(habit)

10    Response             HTTP 201 Created
                           {"id":"habit-001","name":"Water Intake",
                            "habit_type":"numeric","unit":"glasses",
                            "target_value":8.0,"color":"#3B82F6",
                            "icon":"💧","sort_order":3,
                            "is_archived":false,"created_at":"..."}
```

---

<a name="dashboard-flow"></a>
## 3. Flow 2: Daily Dashboard Load

This is the MOST FREQUENT request — every time a user opens the app.

```
STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Browser              GET /api/v1/habits
                           Headers: Authorization: Bearer eyJ...

 2    get_current_user_id  Decode JWT → user_id = uuid-001 ✅

 3    service.get_habits(uuid-001, include_archived=False)

 4    repo.get_user_habits(uuid-001, False)
        → SELECT * FROM habits
          WHERE user_id = 'uuid-001' AND is_archived = false
          ORDER BY sort_order ASC, created_at ASC
        → Uses composite index: ix_habits_user_active
        → [Habit(Water, order=0), Habit(Sleep, order=1),
           Habit(Mood, order=2), Habit(Exercise, order=3)]

 5    Response             HTTP 200 OK
                           [
                             {"name":"Water Intake","sort_order":0,...},
                             {"name":"Sleep Hours","sort_order":1,...},
                             {"name":"Mood","sort_order":2,...},
                             {"name":"Exercise","sort_order":3,...}
                           ]

PERFORMANCE:
  Without composite index: ~50ms (full table scan)
  With composite index: ~1ms (direct lookup)
  This query runs on EVERY dashboard load — index matters.
```

---

<a name="reorder-flow"></a>
## 4. Flow 3: Reorder via Drag-and-Drop

```
USER ACTION:
  User drags "Mood" from position 2 to position 0 (top of dashboard)

  BEFORE:          AFTER (desired):
  0: Water         0: Mood        ← moved up
  1: Sleep         1: Water       ← shifted down
  2: Mood          2: Sleep       ← shifted down
  3: Exercise      3: Exercise    ← unchanged

STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Frontend             User drops "Mood" at position 0
                           Build new order: [mood_id, water_id, sleep_id, exercise_id]

 2    Browser              PUT /api/v1/habits/reorder
                           Body: {"habit_ids":["mood-id","water-id","sleep-id","exercise-id"]}

 3    service.reorder_habits(uuid-001, [mood, water, sleep, exercise])

 4    repo.reorder_habits:
        UPDATE habits SET sort_order = 0 WHERE id = 'mood-id'    AND user_id = 'uuid-001'
        UPDATE habits SET sort_order = 1 WHERE id = 'water-id'   AND user_id = 'uuid-001'
        UPDATE habits SET sort_order = 2 WHERE id = 'sleep-id'   AND user_id = 'uuid-001'
        UPDATE habits SET sort_order = 3 WHERE id = 'exercise-id' AND user_id = 'uuid-001'
        flush()  ← all 4 UPDATEs sent as batch

 5    session.commit()  ← all-or-nothing transaction

 6    repo.get_user_habits(uuid-001)  ← fetch updated list

 7    Response             HTTP 200 OK
                           [
                             {"name":"Mood","sort_order":0,...},
                             {"name":"Water Intake","sort_order":1,...},
                             {"name":"Sleep Hours","sort_order":2,...},
                             {"name":"Exercise","sort_order":3,...}
                           ]
```

---

<a name="archive-flow"></a>
## 5. Flow 4: Soft Delete (Archive)

```
STEP  COMPONENT            ACTION
────  ────────             ──────
 1    Browser              DELETE /api/v1/habits/water-id
                           Headers: Authorization: Bearer eyJ...

 2    get_current_user_id  → uuid-001

 3    service.delete_habit(uuid-001, water-id)

 4    repo.archive_habit(uuid-001, water-id):
        a) SELECT * FROM habits WHERE id = 'water-id' AND user_id = 'uuid-001'
           → Habit(name="Water Intake", is_archived=false)

        b) habit.is_archived = True

        c) flush() → UPDATE habits SET is_archived = true WHERE id = 'water-id'

 5    session.commit()

 6    Response             HTTP 200 OK
                           {"message": "Habit 'Water Intake' archived successfully"}

AFTER ARCHIVE:
  GET /habits              → Water NOT in list (filtered by is_archived=false)
  GET /habits?include_archived=true → Water IS in list (is_archived=true)
  GET /logs (for Water)    → Historical logs STILL EXIST (not deleted)
  Analytics queries         → Still include Water's data for past analysis
```

---

<a name="error-flows"></a>
## 6. Flow 5: Error Paths

### Duplicate Name
```
POST /habits {"name":"Water Intake","habit_type":"boolean"}
  → service.create_habit()
    → repo.name_exists_for_user(uuid-001, "Water Intake") → True
    → raise DuplicateHabitNameError("Water Intake")
      → HTTP 409: {"error_code":"DUPLICATE_HABIT_NAME",
                    "message":"You already have a habit named 'Water Intake'"}
```

### Habit Limit Exceeded
```
POST /habits {"name":"Habit #21",...}  (user already has 20 active habits)
  → service.create_habit()
    → repo.count_active_habits(uuid-001) → 20
    → raise HabitLimitExceededError()
      → HTTP 422: {"error_code":"HABIT_LIMIT_EXCEEDED",
                    "message":"Maximum 20 active habits allowed. Archive some to add more."}
```

### Habit Not Found (or Wrong User)
```
GET /habits/nonexistent-uuid
  → service.get_habit(uuid-001, nonexistent-uuid)
    → repo.get_user_habit(uuid-001, nonexistent-uuid) → None
    → raise HabitNotFoundError()
      → HTTP 404: {"error_code":"HABIT_NOT_FOUND","message":"Habit not found"}

GET /habits/other-users-habit-id  (habit exists but belongs to user B)
  → Same flow: WHERE id=? AND user_id=? returns None
    → SAME error: HTTP 404 "Habit not found"
    → Attacker can't tell if habit exists or belongs to someone else
```

### Invalid Habit Type
```
POST /habits {"name":"Test","habit_type":"invalid"}
  → Pydantic rejects BEFORE reaching service
    → HTTP 422: {"error_code":"VALIDATION_ERROR",
                  "detail":["body → habit_type: Input should be 'numeric', 'boolean' or 'scale'"]}
```

---

<a name="cross-module"></a>
## 7. Cross-Module Dependency Map

```
┌─────────────── AUTH MODULE ───────────────┐
│  get_current_user_id (dependency)         │
│  User model (FK reference)                │
└────────────────────┬──────────────────────┘
                     │ provides user_id
                     ▼
┌─────────────── HABITS MODULE ─────────────┐
│  models.py: Habit (user_id FK → users.id) │
│  router.py: uses get_current_user_id      │
│  6 endpoints, 7 repo methods, 6 service   │
└────────────────────┬──────────────────────┘
                     │ habits referenced by
                     ▼
┌─────────────── LOGS MODULE (Part 06) ─────┐
│  habit_logs.habit_id FK → habits.id       │
│  "On Sep 26, Water Intake = 7 glasses"    │
│  One log per habit per day (UNIQUE)       │
└────────────────────┬──────────────────────┘
                     │ logs aggregated by
                     ▼
┌─────────── ANALYTICS MODULE (Part 07) ────┐
│  JOIN habits + habit_logs                  │
│  "Average water this week: 7.2 glasses"   │
│  "Sleep streak: 5 consecutive days"       │
│  "Mood correlates with exercise (r=0.72)" │
└────────────────────┬──────────────────────┘
                     │ insights feed into
                     ▼
┌──────────── AI MODULE (Parts 08-12) ──────┐
│  RAG: documents about user's habits       │
│  Agent: "You sleep better on days you     │
│          exercise. Consider a 30-min walk  │
│          before bed."                      │
│  Weekly report: AI-generated summary      │
└───────────────────────────────────────────┘
```

### What Other Modules Need from Habits

| Module | What It Needs | How It Gets It |
|--------|-------------|---------------|
| **Logs** | `habit_id` FK, `habit_type` for validation | FK reference + join query |
| **Analytics** | Habit names, types, targets for dashboards | JOIN habits ON habit_logs.habit_id |
| **AI Agent** | Habit list for context ("user tracks water, sleep, mood") | Query habits table |
| **Notifications** | Habit schedule for reminders ("remind at 8 PM to log water") | Query habits table |
| **Export** | Habit metadata for CSV headers | Query habits table |

---

<a name="summary"></a>
## 8. Habits Module Summary

### What You Built (Parts 05a–05e)

| Part | Files | What It Does |
|------|-------|-------------|
| **05a** | models.py, exceptions.py, schemas.py, migration | Data layer — table, errors, API shapes, DB migration |
| **05b** | repository.py | Data access — 7 user-scoped queries |
| **05c** | service.py | Business logic — validate-then-act pattern |
| **05d** | router.py | HTTP layer — 6 endpoints |
| **05e** | (this doc) | Architecture — flows, connections, error paths |

### By the Numbers

| Metric | Count |
|--------|-------|
| Python files | 7 |
| Endpoints | 6 |
| Exception classes | 4 |
| Pydantic schemas | 4 + 1 Enum |
| Repository methods | 7 custom + 5 inherited |
| Service methods | 6 |
| Database columns | 12 |
| Business rules | 5 (limit, duplicate, immutable type, soft delete, ordering) |

### Pattern Comparison: Auth vs Habits

| Aspect | Auth | Habits |
|--------|------|--------|
| External services | Redis (blacklist), bcrypt, JWT | None (pure DB) |
| Endpoints | 6 | 6 |
| Model columns | 8 | 12 |
| Custom exceptions | 5 | 4 |
| Schemas | 5 | 4 + enum |
| Key feature | Token management | Soft delete + reorder |
| Difficulty | Hard (crypto) | Medium (CRUD + rules) |

The same architecture pattern — router → service → repository → model — works for both simple and complex modules. You now know the pattern. Every future module (Logs, Analytics, AI) follows it.

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 05d: Habits Router](./phase4-part05d-habits-controller-docker.md) |
| ➡️ Next | [Phase 4 Part 06: Logs Module Overview](./phase4-part06-logs-service-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Habits Module — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 05a | ✅ Done | Habits Models, Exceptions, Schemas & Migration |
| 05b | ✅ Done | Habits Repository |
| 05c | ✅ Done | Habits Service |
| 05d | ✅ Done | Habits Router |
| **05e** | ✅ **Done** | Habits Connections & Flows |

---

**End of Phase 4 Part 05e: Habits Connections & Flows**

**🎉 The Habits module is COMPLETE.**

*Users can create, list, update, archive, and reorder habits. Every query is user-scoped, every business rule is enforced, and the data flows cleanly through all layers. Next: the Logs module — daily check-in values for each habit.*
