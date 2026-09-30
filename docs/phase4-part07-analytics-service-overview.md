# 📈 Phase 4 Part 07: Analytics Module — Overview & Roadmap

> **"Analytics is where raw data becomes knowledge. '7 glasses of water' is data. 'Your average is 7.4 glasses this week, up 10% from last week, and your water intake correlates with your mood' — that's analytics. This module makes the app intelligent."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07 (Analytics Module — Overview) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part06d-logs-connections-and-flows.md](./phase4-part06d-logs-connections-and-flows.md) |
| **Next** | [phase4-part07a-analytics-schemas.md](./phase4-part07a-analytics-schemas.md) |
| **Module Files** | 7 Python files (including dedicated cache layer) |
| **Endpoints** | 6 (ALL read-only GET endpoints, ALL cached) |
| **Sub-Parts** | 5 documents (07a through 07e) |
| **Time to Type** | ~5 hours (most complex module — advanced SQL) |
| **Difficulty** | ⭐ HARD (window functions, CTEs, Pearson correlation, caching layer) |

---

## 📖 Table of Contents

1. [What Is the Analytics Module?](#what-is-analytics)
2. [The Six Analytics — What Each Calculates](#six-analytics)
3. [Caching Strategy — Cache-Aside Pattern](#caching)
4. [Endpoints Overview](#endpoints)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Prerequisites](#prerequisites)
10. [Design Decisions Summary](#design-decisions)
11. [Interview Q&A](#interview)
12. [Navigation](#navigation)

---

<a name="what-is-analytics"></a>
## 1. What Is the Analytics Module?

The Analytics module transforms raw log entries into **insights**. It reads from the `habits` and `habit_logs` tables (never writes) and returns calculated data that powers dashboard widgets, charts, and AI context.

### Real-World Analogy

Think of a **fitness tracker dashboard** (like Fitbit or Apple Health):
- **Logs module** = the sensor recording your steps every minute
- **Analytics module** = the dashboard showing "10,432 steps today, 7-day average 8,200, you're 15% more active this week vs last week, and your sleep quality improves on days you exercise"

The raw data is useless without analytics. Analytics turns data into decisions.

### What Makes This Module Different

| Feature | Previous Modules | Analytics |
|---------|-----------------|-----------|
| Write operations | CREATE, UPDATE, DELETE | **NONE** — read-only |
| SQL complexity | Simple WHERE, JOIN | **Window functions, CTEs, GROUP BY, CASE, generate_series** |
| Caching | None (except log invalidation) | **Dedicated cache layer** (Redis) |
| Response format | Single objects or lists | **Aggregated calculations** (averages, percentages, correlations) |
| Repository style | ORM queries (SQLAlchemy) | **Raw SQL** (text()) for complex analytics |
| Python computation | Minimal | **Pearson correlation** calculated in Python |

---

<a name="six-analytics"></a>
## 2. The Six Analytics — What Each Calculates

### 1. Dashboard Overview

```
"Welcome back, Shreya! You've logged 4 of 6 habits today (67%).
 Your best current streak: Water Intake — 15 days straight!"
```

| Field | Calculation |
|-------|------------|
| `today_logged` | COUNT logs WHERE log_date = today |
| `today_total` | COUNT active habits |
| `today_completion_pct` | logged / total × 100 |
| `current_best_streak` | MAX streak across all habits |
| `week_completion_pct` | AVG daily completion this week |

### 2. Streaks

```
💧 Water Intake:  current 15 days, longest ever 30 days
🛌 Sleep Hours:   current 7 days,  longest ever 14 days
🧘 Meditation:    current 0 days,  longest ever 5 days (missed yesterday!)
```

**What is a streak?** Consecutive days where a habit was logged. Miss a day → reset to 0.

**SQL challenge:** Calculating streaks is a classic **window function** problem. You need to find "gaps" in dates and group consecutive sequences. This is one of the most commonly asked SQL interview questions.

### 3. Weekly Summary (This Week vs Last Week)

```
💧 Water:  This week avg 7.4 glasses ↑10% (last week: 6.7)
🛌 Sleep:  This week avg 6.8 hours   ↓5%  (last week: 7.2)
😊 Mood:   This week avg 7.1         ↑3%  (last week: 6.9)
```

Compares averages and counts between current week (Mon–Sun) and previous week. Shows improvement arrows (↑↓) and percentage change.

### 4. Monthly Trend (Chart Data)

```
Water Intake — Last 30 Days:
Day 1: 6 | Day 2: 8 | Day 3: 7 | Day 4: null (not logged) | Day 5: 9 | ...
```

Returns one data point per day per habit. Days without logs return `null` — the chart draws a gap. This powers the **line chart** on the analytics page.

### 5. Completion Rate

```
💧 Water:     28/30 days (93%)  ████████████████████░░
🧘 Meditation: 14/30 days (47%) █████████░░░░░░░░░░░░░
🏃 Exercise:  24/30 days (80%)  ████████████████░░░░░░
```

`days_logged / total_possible_days × 100` for each habit over a configurable period.

### 6. Correlations (★ The Crown Jewel)

```
🛌 Sleep ↔ 😊 Mood:    r = 0.72 (STRONG positive)
  → "Your mood is higher on days you sleep more"

🏃 Exercise ↔ 🛌 Sleep: r = 0.45 (MODERATE positive)
  → "You tend to sleep better on days you exercise"

📱 Screen Time ↔ 🛌 Sleep: r = -0.61 (STRONG negative)
  → "More screen time is associated with less sleep"
```

**Pearson correlation coefficient** measures how two habits move together. Calculated in Python (not SQL) because it involves pair-wise comparison across all habit combinations.

---

<a name="caching"></a>
## 3. Caching Strategy — Cache-Aside Pattern

### Why Cache?

```
WITHOUT CACHE:
  Dashboard load → 6 SQL queries → 6 × 50-200ms = 300-1200ms ← SLOW

WITH CACHE:
  Dashboard load → 6 Redis GETs → 6 × 0.5ms = 3ms ← FAST
  (Cache populated on first load, expires after TTL)
```

### Cache-Aside Pattern (Read-Through)

```
┌─────────────────────────────────────────────────────────────────┐
│  CLIENT REQUEST: GET /analytics/streaks                          │
│                                                                   │
│  1. Service checks cache:                                         │
│     cache.get_streaks(user_id)                                    │
│     → Redis GET "analytics:uuid-001:streaks"                      │
│                                                                   │
│  2a. CACHE HIT (data exists):                                     │
│      Return cached data immediately                               │
│      Response time: ~1ms                                          │
│                                                                   │
│  2b. CACHE MISS (no data or expired):                             │
│      → Query database (complex SQL with CTEs)                     │
│      → Transform results into response schema                     │
│      → Store in cache: cache.set_streaks(user_id, data)           │
│      → Return fresh data                                          │
│      Response time: ~100ms (SQL) + ~1ms (cache write)             │
│                                                                   │
│  3. CACHE INVALIDATION (when logs change):                        │
│     LogService._invalidate_cache(user_id)                         │
│     → Redis DELETE "analytics:uuid-001:*"                         │
│     → Next analytics request: cache miss → fresh calculation       │
└─────────────────────────────────────────────────────────────────┘
```

### TTL Values

| Analytics | TTL | Why |
|----------|-----|-----|
| Dashboard | 5 min | Changes often (today's progress) |
| Streaks | 30 min | Changes once per day (when user logs) |
| Weekly Summary | 30 min | Changes once per day |
| Monthly Trend | 1 hour | Historical data is stable |
| Completion Rate | 30 min | Changes once per day |
| Correlations | 1 hour | Expensive to calculate, stable |

---

<a name="endpoints"></a>
## 4. Endpoints Overview

**All endpoints are GET (read-only). All are cached. All require authentication.**

| # | Endpoint | Response | Cache TTL | What It Powers |
|---|----------|----------|-----------|---------------|
| 1 | `GET /analytics/dashboard` | `DashboardData` | 5 min | Main dashboard widgets |
| 2 | `GET /analytics/streaks` | `AllStreaksResponse` | 30 min | Streak cards |
| 3 | `GET /analytics/weekly-summary` | `WeeklySummaryResponse` | 30 min | This week vs last week |
| 4 | `GET /analytics/monthly-trend` | `MonthlyTrendResponse` | 1 hour | Line charts |
| 5 | `GET /analytics/completion-rate` | `CompletionRateResponse` | 30 min | Progress bars |
| 6 | `GET /analytics/correlations` | `CorrelationResponse` | 1 hour | Insight cards |

### Query Parameters

| Endpoint | Parameter | Default | Range |
|----------|-----------|---------|-------|
| `/monthly-trend` | `habit_id` | None (all habits) | Any valid UUID |
| `/monthly-trend` | `days` | 30 | 7–90 |
| `/completion-rate` | `days` | 30 | 7–90 |
| `/correlations` | `days` | 30 | 14–90 |

---

<a name="file-list"></a>
## 5. File List & Build Order

### Module File Structure

```
backend/app/modules/analytics/
├── __init__.py
├── schemas.py            ← Response schemas (dashboard, streaks, weekly, trend, completion, correlation)
├── exceptions.py         ← 2 exceptions (InsufficientData, InvalidDateRange)
├── cache.py              ← ★ NEW: Dedicated Redis cache layer
├── repository.py         ← ★★★ THE BIG FILE: Complex SQL (window functions, CTEs)
├── service.py            ← Cache-aside orchestration + Pearson correlation
└── router.py             ← 6 GET endpoints
```

### Build Order

| # | File | Doc | Why This Order |
|---|------|-----|---------------|
| 1 | `schemas.py` | Part 07a | Defines response shapes — everything else returns these |
| 2 | `exceptions.py` | Part 07a | Service raises these |
| 3 | `repository.py` | Part 07b | ★★★ The complex SQL — heart of the module |
| 4 | `cache.py` | Part 07c | Redis cache layer used by service |
| 5 | `service.py` | Part 07c | Cache-aside + Pearson correlation |
| 6 | `router.py` | Part 07d | 6 GET endpoints |

### What's Unique About This Module

1. **No models.py** — Analytics doesn't have its own table. It reads from `habits` + `habit_logs`
2. **No migrations** — Nothing to create in the database
3. **cache.py** — First module with a dedicated cache layer
4. **Raw SQL** — Repository uses `text()` for complex queries that ORM can't express
5. **Python computation** — Pearson correlation calculated in service, not SQL

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 07a: Analytics Schemas

```
📄 phase4-part07a-analytics-schemas.md
├── schemas.py      — 12 response schemas (DashboardData, StreakInfo, WeeklySummary, TrendDataPoint, etc.)
└── exceptions.py   — 2 exception classes

KEY CONCEPTS: Nested schemas, chart-ready data format, Pearson correlation fields
TIME: ~30 minutes
```

### Part 07b: Analytics Repository (★★★ THE BIG SQL FILE)

```
📄 phase4-part07b-analytics-repository-sql.md
└── repository.py   — 6 major query methods with raw SQL

KEY CONCEPTS: Window functions (ROW_NUMBER, LAG), CTEs, generate_series,
              GROUP BY with CASE, date_trunc, COALESCE
TIME: ~90 minutes (most complex doc in the project)
```

### Part 07c: Analytics Cache & Service

```
📄 phase4-part07c-analytics-cache-service.md
├── cache.py    — Redis cache with typed accessors and TTL
└── service.py  — Cache-aside pattern + Pearson correlation in Python

KEY CONCEPTS: Cache-aside pattern, JSON serialization, Pearson coefficient,
              itertools.combinations for habit pairs
TIME: ~60 minutes
```

### Part 07d: Analytics Router

```
📄 phase4-part07d-analytics-controller.md
└── router.py  — 6 GET endpoints with configurable parameters

KEY CONCEPTS: All-GET module, configurable days parameter (7-90)
TIME: ~20 minutes
```

### Part 07e: Analytics Connections & Flows

```
📄 phase4-part07e-analytics-connections-and-flows.md
├── Cache-aside flow for each endpoint
├── Correlation calculation walkthrough
├── How analytics feeds into the AI module
└── Performance: cached vs uncached response times

TIME: ~20 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ANALYTICS MODULE                                      │
│                                                                              │
│  ┌──────────┐     ┌──────────────────────────────────────────────────────┐  │
│  │  Router   │────>│  Service                                             │  │
│  │ 6 GET     │     │                                                      │  │
│  │ endpoints │     │  ┌────────────┐    ┌────────────────┐               │  │
│  └──────────┘     │  │   Check     │    │   Query DB      │               │  │
│                    │  │   Redis     │    │   (complex SQL) │               │  │
│                    │  │   Cache     │    │   Transform     │               │  │
│                    │  │            │    │   data           │               │  │
│                    │  │   Hit? ────┼──> │   Cache result   │               │  │
│                    │  │   Return!  │    │   Return         │               │  │
│                    │  └──────┬─────┘    └────────┬─────────┘               │  │
│                    │         │                    │                         │  │
│                    │         ▼                    ▼                         │  │
│                    │  ┌────────────┐    ┌────────────────┐                │  │
│                    │  │  cache.py   │    │ repository.py   │                │  │
│                    │  │  Redis      │    │ Raw SQL:        │                │  │
│                    │  │  get/set    │    │ • Window funcs  │                │  │
│                    │  │  TTL mgmt   │    │ • CTEs          │                │  │
│                    │  └──────┬─────┘    │ • GROUP BY      │                │  │
│                    │         │           │ • generate_series│                │  │
│                    │         ▼           └────────┬─────────┘               │  │
│                    │  ┌────────────┐              │                         │  │
│                    │  │   Redis     │              ▼                         │  │
│                    │  │   Server    │    ┌────────────────┐                │  │
│                    │  └────────────┘    │  PostgreSQL      │                │  │
│                    │                    │  habits +        │                │  │
│                    │                    │  habit_logs      │                │  │
│                    └────────────────────┴────────────────────────────────┘  │
│                                                                              │
│  INVALIDATION: LogService._invalidate_cache() deletes analytics:user:* keys │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **Window Functions** | SQL functions that operate across rows (ROW_NUMBER, LAG) | `repository.py` |
| 2 | **CTEs (WITH clauses)** | Named sub-queries for readable complex SQL | `repository.py` |
| 3 | **`generate_series()`** | PostgreSQL function that creates a sequence of dates | `repository.py` |
| 4 | **`date_trunc()`** | Truncate timestamp to day/week/month | `repository.py` |
| 5 | **GROUP BY + CASE** | Conditional aggregation in SQL | `repository.py` |
| 6 | **Raw SQL via `text()`** | SQLAlchemy's escape hatch for complex queries | `repository.py` |
| 7 | **Cache-Aside Pattern** | Check cache → if miss → query DB → cache → return | `service.py` |
| 8 | **TTL (Time-To-Live)** | Auto-expiring cache entries | `cache.py` |
| 9 | **JSON serialization** | Store Python dicts in Redis as JSON strings | `cache.py` |
| 10 | **Pearson Correlation** | Statistical measure of linear relationship (-1 to +1) | `service.py` |
| 11 | **`itertools.combinations`** | Generate all unique pairs from a list | `service.py` |
| 12 | **Typed cache accessors** | `get_streaks()`, `set_streaks()` with consistent key naming | `cache.py` |

---

<a name="prerequisites"></a>
## 9. Prerequisites

| # | Prerequisite | Document | What It Gives You |
|---|-------------|----------|-------------------|
| 1 | Auth complete | [Parts 04a–04f](./phase4-part04-auth-service-overview.md) | `get_current_user_id` dependency |
| 2 | Habits complete | [Parts 05a–05e](./phase4-part05-habits-service-overview.md) | Habit data (names, types, targets) |
| 3 | Logs complete | [Parts 06a–06d](./phase4-part06-logs-service-overview.md) | Log data + cache invalidation |
| 4 | Redis running | [Part 02](./phase4-part02-backend-foundation.md) | Redis connection for caching |

---

<a name="design-decisions"></a>
## 10. Design Decisions Summary

### Decision 1: Raw SQL vs ORM for Analytics

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Query Strategy for Analytics                      │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Raw SQL via text() for complex queries                     │
│                                                                     │
│  WHY:                                                               │
│  • Window functions (ROW_NUMBER, LAG) have limited ORM support      │
│  • CTEs are verbose and fragile in SQLAlchemy ORM                   │
│  • generate_series() is PostgreSQL-specific — no ORM equivalent     │
│  • Raw SQL is MORE readable for analytics than ORM builders         │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. SQLAlchemy ORM for everything                                   │
│     ❌ Window functions require subquery() nesting — unreadable    │
│  2. Pandas/NumPy (load all data, process in Python)                 │
│     ❌ Transfers entire dataset from DB to Python — wasteful        │
│     ❌ PostgreSQL is much faster at aggregations than Python        │
│  3. Materialized views (pre-computed in PostgreSQL)                  │
│     ⚠️ Good at scale but adds complexity (refresh scheduling)      │
│                                                                     │
│  RULE: Use ORM for simple CRUD. Use raw SQL for analytics.          │
│  Simple queries → repository uses select(Model).where(...)          │
│  Complex queries → repository uses text("SELECT ... WITH ...")      │
│                                                                     │
│  INTERVIEW TIP: "We use ORM for CRUD and raw SQL for analytics.     │
│  Window functions, CTEs, and generate_series are more readable and  │
│  performant in raw SQL. The key is keeping raw SQL in the            │
│  repository layer — the service never sees SQL."                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Dedicated Cache Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Cache Architecture                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Separate cache.py class with typed accessors               │
│                                                                     │
│  WHY:                                                               │
│  • Testable — mock AnalyticsCache in unit tests without Redis       │
│  • Typed — get_streaks/set_streaks vs generic get/set               │
│  • Consistent keys — _key() method ensures naming convention        │
│  • Swappable — could change to memcached without touching service   │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Cache logic inline in service methods                           │
│     ❌ Service becomes cluttered with Redis calls                  │
│     ❌ Hard to test service without Redis                          │
│  2. Decorator-based caching (@cache(ttl=300))                       │
│     ⚠️ Elegant but less control over invalidation and key naming   │
│                                                                     │
│  INTERVIEW TIP: "We separate cache logic into its own class for     │
│  testability and clean code. The service calls cache.get_streaks()  │
│  — if miss, it queries the DB and calls cache.set_streaks(). The    │
│  cache class handles JSON serialization and TTL management."        │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: Pearson Correlation in Python (Not SQL)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Correlation Computation Location                  │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Fetch paired data from SQL, compute Pearson in Python      │
│                                                                     │
│  WHY:                                                               │
│  • Need to compare ALL pairs of habits — N*(N-1)/2 pairs            │
│  • Python's itertools.combinations generates pairs cleanly          │
│  • Pearson formula is straightforward in Python (~20 lines)         │
│  • SQL correlation requires self-joins per pair — complex           │
│                                                                     │
│  HOW:                                                               │
│  1. SQL: Fetch all numeric log values grouped by (habit_id, date)   │
│  2. Python: Group by habit, find overlapping dates between pairs    │
│  3. Python: Calculate Pearson coefficient for each pair             │
│  4. Filter: Only show pairs with r > 0.3 and ≥ 5 data points      │
│                                                                     │
│  INTERVIEW TIP: "Correlations are computed in Python because we     │
│  need pairwise comparison across all habit combinations. SQL fetches │
│  the raw data efficiently, and Python handles the statistical       │
│  computation. The result is cached for 1 hour."                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 11. Interview Q&A (Module Level)

### Q1: How does the analytics caching work?
**A:** "We use the cache-aside pattern. When an analytics endpoint is called, the service checks Redis first. If the data is cached, it's returned in under 1ms. If not (cache miss), we run the SQL query (50-200ms), transform the results, cache them with a TTL, and return. Each analytics type has a different TTL: dashboard expires in 5 minutes (changes often), correlations expire in 1 hour (expensive to calculate, data is stable). Cache is invalidated when the Logs module creates, updates, or deletes a log entry."

### Q2: Why raw SQL instead of ORM for analytics?
**A:** "Analytics queries use PostgreSQL-specific features: window functions (ROW_NUMBER, LAG for streak calculation), CTEs (WITH clauses for multi-step queries), generate_series (to fill date gaps in chart data), and CASE expressions for conditional aggregation. These are either unsupported or extremely verbose in SQLAlchemy's ORM. Raw SQL via `text()` is more readable and maintainable for analytics. We keep raw SQL strictly in the repository layer — the service never sees SQL."

### Q3: How do you calculate habit streaks?
**A:** "It's a 'gaps and islands' problem — a classic SQL pattern. We use window functions: assign a row number to each log date, then subtract it from the date. Consecutive dates produce the same 'group_id' (island). We count the size of each island to get streak lengths. The current streak is the island that includes today (or yesterday). This runs as a CTE in PostgreSQL with ROW_NUMBER() and LAG()."

### Q4: How does Pearson correlation work in your app?
**A:** "We fetch daily values for all numeric habits over the requested period. In Python, we use itertools.combinations to generate all unique habit pairs. For each pair, we find dates where both habits were logged (overlapping days), then compute the Pearson coefficient: covariance divided by the product of standard deviations. The result is a number between -1 (perfect negative) and +1 (perfect positive). We filter to pairs with at least 5 data points and |r| > 0.3 (minimum moderate correlation). The insight text is generated from the direction and strength."

### Q5: What is the trade-off of your cache invalidation strategy?
**A:** "We delete ALL analytics cache keys for a user when any log changes. This is slightly wasteful — if the user logs water, we also invalidate the correlation cache even though it might not change. The trade-off: simplicity and correctness over efficiency. At our scale (single user, ~6 analytics keys), the cost is negligible. At larger scale, we'd switch to surgical invalidation — tracking which cache keys are affected by which habits."

---

<a name="navigation"></a>
## 12. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 06d: Logs Connections & Flows](./phase4-part06d-logs-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 07a: Analytics Schemas](./phase4-part07a-analytics-schemas.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Sub-Part Quick Links

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 07a | [Analytics Schemas](./phase4-part07a-analytics-schemas.md) | 12 response schemas + 2 exceptions |
| 07b | [Analytics Repository (★★★)](./phase4-part07b-analytics-repository-sql.md) | Complex SQL — window functions, CTEs |
| 07c | [Analytics Cache & Service](./phase4-part07c-analytics-cache-service.md) | Redis cache layer + Pearson correlation |
| 07d | [Analytics Router](./phase4-part07d-analytics-controller.md) | 6 GET endpoints |
| 07e | [Analytics Connections & Flows](./phase4-part07e-analytics-connections-and-flows.md) | Cache-aside flow diagrams |

---

**End of Phase 4 Part 07: Analytics Module Overview**

*This is the most technically complex module in the project. Window functions, CTEs, Pearson correlation, and a dedicated caching layer. If you can explain this module in an interview, you've demonstrated advanced SQL, caching patterns, and statistical thinking. Next: the schemas that define every response shape.*
