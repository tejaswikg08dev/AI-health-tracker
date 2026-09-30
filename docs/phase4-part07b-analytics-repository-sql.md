# 📈 Phase 4 Part 07b: Analytics — Repository (★★★ Complex SQL)

> **"Every query in this file is an interview question. Streaks? Window functions. Weekly comparison? CASE + GROUP BY. Chart data with no gaps? generate_series + LEFT JOIN. Correlations? Self-join. Master this file, and you can handle any SQL interview."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07b (Analytics Complex SQL — ★★★ HARDEST DOC) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part07a-analytics-schemas.md](./phase4-part07a-analytics-schemas.md) |
| **Next** | [phase4-part07c-analytics-cache-service.md](./phase4-part07c-analytics-cache-service.md) |
| **Files in This Doc** | 1 file (repository.py) — 6 SQL queries |
| **Time to Type** | ~90 minutes |
| **Difficulty** | ★★★ HARD (window functions, CTEs, generate_series, self-joins, CASE, COALESCE) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [SQL Concepts Primer](#sql-primer)
3. [File: repository.py — Full Source Code](#repository)
4. [Query 1: Streaks (Gaps and Islands)](#streaks)
5. [Query 2: Weekly Summary](#weekly)
6. [Query 3: Monthly Trend (generate_series)](#trend)
7. [Query 4: Completion Rates](#completion)
8. [Query 5: Correlation Data (Self-Join)](#correlations)
9. [Query 6: Dashboard Helpers](#dashboard)
10. [Design Decisions](#design-decisions)
11. [What You Learned](#what-you-learned)
12. [Interview Q&A](#interview)
13. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

The analytics repository contains **6 SQL queries** that are the most complex in the project. Unlike previous repositories (ORM-based), this one uses **raw SQL** via `text()` because these queries need PostgreSQL-specific features.

| # | Query | SQL Concepts Used |
|---|-------|------------------|
| 1 | `get_streaks()` | CTEs, ROW_NUMBER(), DISTINCT ON, LEFT JOIN, COALESCE |
| 2 | `get_weekly_summary()` | CASE WHEN, conditional AVG/COUNT, date arithmetic |
| 3 | `get_monthly_trend()` | generate_series(), CROSS JOIN, LEFT JOIN, COALESCE |
| 4 | `get_completion_rates()` | GREATEST(), date arithmetic, GROUP BY, ORDER BY expression |
| 5 | `get_correlation_data()` | Self-join (A < B trick), COALESCE for type normalization |
| 6 | `get_today_progress()` + `get_week_completion()` | Subqueries, CROSS JOIN, conditional AVG |

### Why This Repository Is Different

```
PREVIOUS REPOSITORIES:                    THIS REPOSITORY:
────────────────────                      ──────────────────
class UserRepository(BaseRepository):     class AnalyticsRepository:
    # Inherits CRUD                           # NO BaseRepository!
    # Uses ORM: select(User).where(...)       # Uses raw SQL: text("SELECT...")
    # Simple WHERE/ORDER BY                    # Window functions, CTEs, generate_series
```

---

<a name="sql-primer"></a>
## 2. SQL Concepts Primer

Before reading the queries, understand these building blocks:

### CTE (Common Table Expression) — `WITH ... AS`

A CTE is a **named sub-query** that makes complex SQL readable:

```sql
-- WITHOUT CTE (nested, hard to read):
SELECT * FROM (SELECT * FROM (SELECT * FROM habits WHERE ...) sub1 WHERE ...) sub2

-- WITH CTE (named steps, easy to read):
WITH step1 AS (
    SELECT * FROM habits WHERE ...
),
step2 AS (
    SELECT * FROM step1 WHERE ...
)
SELECT * FROM step2
```

Think of CTEs as **variables** in SQL — you compute something, give it a name, then use it later.

### Window Function — `ROW_NUMBER() OVER (...)`

A window function performs a calculation **across a set of rows** related to the current row:

```sql
SELECT
    name,
    log_date,
    ROW_NUMBER() OVER (PARTITION BY habit_id ORDER BY log_date) AS rn
FROM habit_logs

-- Result:
-- Water | Sep 20 | 1
-- Water | Sep 21 | 2
-- Water | Sep 22 | 3    ← ROW_NUMBER per habit, ordered by date
-- Sleep | Sep 20 | 1    ← Resets for each habit (PARTITION BY)
-- Sleep | Sep 21 | 2
```

- `PARTITION BY habit_id` — restart numbering for each habit
- `ORDER BY log_date` — number in chronological order

### `generate_series()` — Create a Date Sequence

```sql
SELECT generate_series('2026-09-01'::date, '2026-09-05'::date, '1 day'::interval)::date

-- Result:
-- 2026-09-01
-- 2026-09-02
-- 2026-09-03
-- 2026-09-04
-- 2026-09-05
```

This generates ALL dates in a range — used to fill gaps in chart data.

### `COALESCE()` — First Non-NULL Value

```sql
SELECT COALESCE(value_numeric, value_scale::float, 0.0)
-- If value_numeric is NOT NULL → use it
-- Else if value_scale is NOT NULL → use it (cast to float)
-- Else → use 0.0
```

### `CASE WHEN` — SQL If/Else

```sql
SELECT
    CASE
        WHEN value_boolean = true THEN 1.0
        WHEN value_boolean = false THEN 0.0
        ELSE NULL
    END AS normalized_value
```

---

<a name="repository"></a>
## 3. File: `repository.py` — Full Source Code

### Type This Code: `backend/app/modules/analytics/repository.py`

```python
# ============================================================================
# Analytics Module — Repository (Complex SQL Queries)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains the most complex SQL in the entire project.
#   Calculates: streaks, weekly summaries, monthly trends, completion rates,
#   and correlations between habits.
#
# SQL CONCEPTS YOU'LL LEARN:
#   1. Window Functions — ROW_NUMBER(), LAG(), running totals
#   2. CTEs (Common Table Expressions) — WITH clauses for readable sub-queries
#   3. GROUP BY with aggregations — SUM, AVG, COUNT, MIN, MAX
#   4. CASE expressions — conditional logic in SQL
#   5. Date arithmetic — intervals, date_trunc, generate_series
#   6. COALESCE — handle NULL values
#   7. LEFT JOIN — include days with no logs
#
# WHY RAW SQL (not ORM):
#   SQLAlchemy ORM is great for CRUD, but analytics queries need:
#   - Window functions (ORM support is limited)
#   - Complex CTEs (hard to express in ORM)
#   - Database-specific functions (date_trunc, generate_series)
#   Using raw SQL with text() gives us full PostgreSQL power.
#
# INTERVIEW GOLD:
#   Every query in this file is a potential interview question.
#   "How would you calculate streaks?" → _calculate_streaks()
#   "How do you compare this week vs last week?" → get_weekly_summary()
#   "How would you find correlations between habits?" → get_correlations()
# ============================================================================

import math
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.date_utils import (
    days_ago,
    end_of_week,
    start_of_week,
    today_utc,
)


class AnalyticsRepository:
    """
    Analytics-specific queries.

    NOT extending BaseRepository — analytics doesn't do CRUD.
    It only reads data and computes aggregations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
```

*(The full query methods follow in the deep-dive sections below. Type each section in order.)*

---

<a name="streaks"></a>
## 4. Query 1: Streaks (★★★ Gaps and Islands Problem)

### The Problem

Given these logged dates for "Water Intake":
```
Sep 20, Sep 21, Sep 22, [gap], Sep 24, Sep 25, Sep 26 (today)
```

Find:
- Current streak: **3 days** (Sep 24–26)
- Longest streak: **3 days** (tied — Sep 20–22 and Sep 24–26)

### The Algorithm (Step by Step)

```
STEP 1: Number each date with ROW_NUMBER()
  Sep 20 → rn=1
  Sep 21 → rn=2
  Sep 22 → rn=3
  Sep 24 → rn=4  (skipped Sep 23)
  Sep 25 → rn=5
  Sep 26 → rn=6

STEP 2: Subtract rn × 1 day from each date
  Sep 20 - 1 day = Sep 19   ← group A
  Sep 21 - 2 days = Sep 19  ← group A (same!)
  Sep 22 - 3 days = Sep 19  ← group A (same!)
  Sep 24 - 4 days = Sep 20  ← group B (different — gap detected!)
  Sep 25 - 5 days = Sep 20  ← group B
  Sep 26 - 6 days = Sep 20  ← group B

STEP 3: GROUP BY the computed group value
  Group A (Sep 19): 3 rows → streak length = 3
  Group B (Sep 20): 3 rows → streak length = 3

STEP 4: Current streak = group that includes today or yesterday
  Group B includes Sep 26 (today) → current streak = 3
```

### The SQL

Add this method to the AnalyticsRepository class:

```python
    async def get_streaks(self, user_id: UUID) -> list[dict]:
        """
        Calculate current and longest streaks for all active habits.
        Uses the "gaps and islands" algorithm with ROW_NUMBER().
        """
        query = text("""
            WITH habit_info AS (
                SELECT id AS habit_id, name, color, icon
                FROM habits
                WHERE user_id = :user_id AND is_archived = false
            ),
            logged_dates AS (
                SELECT
                    hl.habit_id,
                    hl.log_date,
                    ROW_NUMBER() OVER (
                        PARTITION BY hl.habit_id
                        ORDER BY hl.log_date
                    ) AS rn
                FROM habit_logs hl
                JOIN habit_info hi ON hl.habit_id = hi.habit_id
                WHERE hl.user_id = :user_id
                  AND (hl.value_numeric IS NOT NULL
                       OR hl.value_boolean = true
                       OR hl.value_scale IS NOT NULL)
            ),
            streaks AS (
                SELECT
                    habit_id,
                    log_date,
                    log_date - (rn * INTERVAL '1 day') AS grp
                FROM logged_dates
            ),
            streak_lengths AS (
                SELECT
                    habit_id,
                    MIN(log_date) AS streak_start,
                    MAX(log_date) AS streak_end,
                    COUNT(*) AS streak_length
                FROM streaks
                GROUP BY habit_id, grp
            ),
            current_streaks AS (
                SELECT
                    habit_id,
                    streak_length AS current_streak,
                    streak_end AS last_logged_date
                FROM streak_lengths
                WHERE streak_end >= CURRENT_DATE - INTERVAL '1 day'
            ),
            longest_streaks AS (
                SELECT DISTINCT ON (habit_id)
                    habit_id,
                    streak_length AS longest_streak
                FROM streak_lengths
                ORDER BY habit_id, streak_length DESC
            )
            SELECT
                hi.habit_id,
                hi.name AS habit_name,
                hi.color AS habit_color,
                hi.icon AS habit_icon,
                COALESCE(cs.current_streak, 0) AS current_streak,
                COALESCE(ls.longest_streak, 0) AS longest_streak,
                cs.last_logged_date
            FROM habit_info hi
            LEFT JOIN current_streaks cs ON hi.habit_id = cs.habit_id
            LEFT JOIN longest_streaks ls ON hi.habit_id = ls.habit_id
            ORDER BY COALESCE(cs.current_streak, 0) DESC
        """)

        result = await self.session.execute(query, {"user_id": str(user_id)})
        rows = result.mappings().all()
        return [dict(row) for row in rows]
```

### CTE-by-CTE Explanation

| CTE | What It Does |
|-----|-------------|
| `habit_info` | Get active habits for this user (name, color, icon) |
| `logged_dates` | Number each log date with ROW_NUMBER per habit |
| `streaks` | Subtract `rn × 1 day` from date — consecutive dates get same `grp` |
| `streak_lengths` | GROUP BY `grp` → count days in each streak |
| `current_streaks` | Filter: only streaks ending today or yesterday |
| `longest_streaks` | DISTINCT ON: pick the longest streak per habit |
| Final SELECT | LEFT JOIN everything — habits without streaks get 0 |

**`DISTINCT ON (habit_id)`** — PostgreSQL-specific. Keeps only the first row per `habit_id` after `ORDER BY streak_length DESC`. This gives us the longest streak per habit in one query.

**`WHERE streak_end >= CURRENT_DATE - INTERVAL '1 day'`** — "yesterday or today." If the user hasn't logged today yet, their streak from yesterday is still "current."

---

<a name="weekly"></a>
## 5. Query 2: Weekly Summary

Add this method:

```python
    async def get_weekly_summary(self, user_id: UUID) -> list[dict]:
        """
        Compare this week vs last week for all habits.
        Uses CASE WHEN for conditional aggregation — split data by week.
        """
        today = today_utc()
        this_week_start = start_of_week(today)
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(days=1)

        query = text("""
            WITH habit_info AS (
                SELECT id AS habit_id, name, color, habit_type
                FROM habits
                WHERE user_id = :user_id AND is_archived = false
            )
            SELECT
                hi.habit_id,
                hi.name AS habit_name,
                hi.color AS habit_color,
                hi.habit_type,

                AVG(CASE
                    WHEN hl.log_date >= :this_week_start THEN
                        COALESCE(hl.value_numeric, hl.value_scale::float,
                                 CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
                END) AS this_week_avg,

                AVG(CASE
                    WHEN hl.log_date >= :last_week_start AND hl.log_date <= :last_week_end THEN
                        COALESCE(hl.value_numeric, hl.value_scale::float,
                                 CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
                END) AS last_week_avg,

                COUNT(CASE WHEN hl.log_date >= :this_week_start THEN 1 END) AS this_week_count,

                COUNT(CASE
                    WHEN hl.log_date >= :last_week_start AND hl.log_date <= :last_week_end THEN 1
                END) AS last_week_count

            FROM habit_info hi
            LEFT JOIN habit_logs hl ON hi.habit_id = hl.habit_id
                AND hl.user_id = :user_id
                AND hl.log_date >= :last_week_start
            GROUP BY hi.habit_id, hi.name, hi.color, hi.habit_type
            ORDER BY hi.name
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id),
            "this_week_start": this_week_start,
            "last_week_start": last_week_start,
            "last_week_end": last_week_end,
        })
        rows = result.mappings().all()
        return [dict(row) for row in rows]
```

### Key Technique: Conditional Aggregation

```sql
AVG(CASE WHEN hl.log_date >= :this_week_start THEN value END) AS this_week_avg
```

This computes the average **only for rows in this week**. Rows from last week are NULL (CASE returns NULL when no WHEN matches), and AVG ignores NULLs. One query, two weeks of data — split by CASE.

### Value Normalization

```sql
COALESCE(hl.value_numeric, hl.value_scale::float,
         CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
```

- Numeric habits → use `value_numeric` directly
- Scale habits → cast `value_scale` to float (integer → float for AVG)
- Boolean habits → convert `true/false` to `1.0/0.0` so AVG makes sense (% of yes-days)

---

<a name="trend"></a>
## 6. Query 3: Monthly Trend (generate_series + CROSS JOIN)

Add this method:

```python
    async def get_monthly_trend(
        self, user_id: UUID, habit_id: UUID | None = None, days: int = 30,
    ) -> list[dict]:
        """
        Get daily values for the last N days.
        Uses generate_series + CROSS JOIN + LEFT JOIN to fill date gaps.
        """
        start_date = days_ago(days - 1)
        end_date = today_utc()
        habit_filter = "AND h.id = :habit_id" if habit_id else ""

        query = text(f"""
            WITH date_range AS (
                SELECT generate_series(
                    :start_date::date, :end_date::date, '1 day'::interval
                )::date AS d
            ),
            active_habits AS (
                SELECT id AS habit_id, name, color, habit_type
                FROM habits
                WHERE user_id = :user_id AND is_archived = false {habit_filter}
            ),
            habit_dates AS (
                SELECT ah.habit_id, ah.name, ah.color, ah.habit_type, dr.d AS log_date
                FROM active_habits ah
                CROSS JOIN date_range dr
            )
            SELECT
                hd.habit_id, hd.name AS habit_name, hd.color AS habit_color,
                hd.habit_type, hd.log_date,
                COALESCE(
                    hl.value_numeric, hl.value_scale::float,
                    CASE WHEN hl.value_boolean THEN 1.0
                         WHEN hl.value_boolean = false THEN 0.0 END
                ) AS value
            FROM habit_dates hd
            LEFT JOIN habit_logs hl ON hd.habit_id = hl.habit_id
                AND hd.log_date = hl.log_date AND hl.user_id = :user_id
            ORDER BY hd.habit_id, hd.log_date
        """)

        params = {"user_id": str(user_id), "start_date": start_date, "end_date": end_date}
        if habit_id:
            params["habit_id"] = str(habit_id)

        result = await self.session.execute(query, params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]
```

### How Gap-Filling Works

```
STEP 1: generate_series creates ALL dates
  Sep 1, Sep 2, Sep 3, Sep 4, Sep 5, ...Sep 30

STEP 2: CROSS JOIN creates every habit × date combination
  Water × Sep 1, Water × Sep 2, ..., Sleep × Sep 1, Sleep × Sep 2, ...

STEP 3: LEFT JOIN with actual logs
  Water × Sep 1 → value: 7.0 (logged)
  Water × Sep 2 → value: NULL (not logged — gap shown in chart)
  Water × Sep 3 → value: 8.0 (logged)
```

Without `generate_series`, days without logs simply wouldn't appear — the chart would connect Sep 1 directly to Sep 3, hiding the gap.

---

<a name="completion"></a>
## 7. Query 4: Completion Rates

Add this method:

```python
    async def get_completion_rates(self, user_id: UUID, days: int = 30) -> list[dict]:
        """
        Completion rate = days_logged / total_possible_days × 100.
        Uses GREATEST to handle habits created during the period.
        """
        start_date = days_ago(days - 1)
        end_date = today_utc()

        query = text("""
            SELECT
                h.id AS habit_id, h.name AS habit_name,
                h.color AS habit_color, h.icon AS habit_icon,
                COUNT(hl.id) AS days_logged,
                GREATEST(
                    (LEAST(:end_date, CURRENT_DATE) -
                     GREATEST(:start_date, h.created_at::date)) + 1,
                    1
                ) AS total_days
            FROM habits h
            LEFT JOIN habit_logs hl ON h.id = hl.habit_id
                AND hl.user_id = :user_id
                AND hl.log_date >= :start_date AND hl.log_date <= :end_date
            WHERE h.user_id = :user_id AND h.is_archived = false
            GROUP BY h.id, h.name, h.color, h.icon, h.created_at
            ORDER BY COUNT(hl.id)::float /
                GREATEST((LEAST(:end_date, CURRENT_DATE) -
                    GREATEST(:start_date, h.created_at::date)) + 1, 1) DESC
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id), "start_date": start_date, "end_date": end_date,
        })
        rows = result.mappings().all()
        return [dict(row) for row in rows]
```

### The GREATEST/LEAST Trick

```sql
GREATEST(:start_date, h.created_at::date)
```

If a habit was created Sep 15 but the period starts Sep 1, `total_days` should count from Sep 15 (not Sep 1). GREATEST picks the later date. LEAST does the opposite for the end date.

---

<a name="correlations"></a>
## 8. Query 5: Correlation Data (Self-Join)

Add this method:

```python
    async def get_correlation_data(self, user_id: UUID, days: int = 30) -> list[dict]:
        """
        Self-join to get paired values for all habit combinations on the same day.
        The A < B trick avoids duplicate pairs and self-pairs.
        """
        start_date = days_ago(days - 1)

        query = text("""
            WITH habit_values AS (
                SELECT hl.habit_id, h.name AS habit_name, hl.log_date,
                    COALESCE(hl.value_numeric, hl.value_scale::float,
                        CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END
                    ) AS value
                FROM habit_logs hl
                JOIN habits h ON hl.habit_id = h.id
                WHERE hl.user_id = :user_id AND h.is_archived = false
                  AND hl.log_date >= :start_date
                  AND (hl.value_numeric IS NOT NULL
                       OR hl.value_boolean IS NOT NULL
                       OR hl.value_scale IS NOT NULL)
            )
            SELECT
                a.habit_id AS habit_a_id, a.habit_name AS habit_a_name,
                b.habit_id AS habit_b_id, b.habit_name AS habit_b_name,
                a.log_date, a.value AS value_a, b.value AS value_b
            FROM habit_values a
            JOIN habit_values b ON a.log_date = b.log_date
                AND a.habit_id < b.habit_id
            ORDER BY a.habit_id, b.habit_id, a.log_date
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id), "start_date": start_date,
        })
        rows = result.mappings().all()
        return [dict(row) for row in rows]
```

### The `A < B` Trick

```sql
JOIN habit_values b ON a.log_date = b.log_date AND a.habit_id < b.habit_id
```

Without `<`, we'd get:
- (Water, Sleep), (Sleep, Water) — duplicate pair
- (Water, Water) — self-pair (meaningless)

With `<`, we only get (Water, Sleep) — each unique pair once. For 4 habits, that's 6 pairs instead of 16.

---

<a name="dashboard"></a>
## 9. Query 6: Dashboard Helpers

Add these methods:

```python
    async def get_today_progress(self, user_id: UUID) -> dict:
        """Count habits logged today vs total active habits."""
        today = today_utc()
        query = text("""
            SELECT
                (SELECT COUNT(*) FROM habits
                 WHERE user_id = :user_id AND is_archived = false) AS total_habits,
                (SELECT COUNT(DISTINCT habit_id) FROM habit_logs
                 WHERE user_id = :user_id AND log_date = :today) AS logged_today
        """)
        result = await self.session.execute(query, {"user_id": str(user_id), "today": today})
        row = result.mappings().one()
        return dict(row)

    async def get_week_completion(self, user_id: UUID) -> float:
        """Average daily completion percentage for the current week."""
        today = today_utc()
        week_start = start_of_week(today)
        query = text("""
            WITH daily_counts AS (
                SELECT hl.log_date, COUNT(DISTINCT hl.habit_id) AS logged_count
                FROM habit_logs hl
                WHERE hl.user_id = :user_id
                  AND hl.log_date >= :week_start AND hl.log_date <= :today
                GROUP BY hl.log_date
            ),
            total_habits AS (
                SELECT COUNT(*) AS cnt FROM habits
                WHERE user_id = :user_id AND is_archived = false
            )
            SELECT COALESCE(
                AVG(dc.logged_count::float / GREATEST(th.cnt, 1) * 100), 0
            ) AS week_completion_pct
            FROM daily_counts dc CROSS JOIN total_habits th
        """)
        result = await self.session.execute(query, {
            "user_id": str(user_id), "week_start": week_start, "today": today,
        })
        row = result.mappings().one()
        return float(row["week_completion_pct"])
```

### Key Pattern: `result.mappings().all()`

```python
result = await self.session.execute(query, params)
rows = result.mappings().all()
return [dict(row) for row in rows]
```

- `result.mappings()` — returns rows as dict-like objects (column name → value)
- `.all()` — fetches all rows
- `[dict(row) for row in rows]` — converts to plain dicts for JSON serialization

This is the raw SQL equivalent of the ORM's `result.scalars().all()`.

---

<a name="design-decisions"></a>
## 10. Design Decisions

### Design Decision: No BaseRepository Inheritance

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Analytics Repository Architecture                 │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Standalone class (NOT inheriting BaseRepository)           │
│                                                                     │
│  WHY:                                                               │
│  • Analytics has NO model (no table to do CRUD on)                  │
│  • BaseRepository provides create/get/update/delete — none needed   │
│  • Raw SQL queries don't use SQLAlchemy ORM models                  │
│  • Only needs: session + execute raw SQL + return dicts             │
│                                                                     │
│  PATTERN: Analytics reads from OTHER modules' tables (habits,       │
│  habit_logs) but doesn't own any table. It's a read-only consumer.  │
│                                                                     │
│  INTERVIEW TIP: "Analytics doesn't inherit BaseRepository because   │
│  it doesn't own a table — it reads from habits and habit_logs.      │
│  It uses raw SQL for complex aggregations that ORM can't express    │
│  cleanly."                                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="what-you-learned"></a>
## 11. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **CTE (`WITH ... AS`)** | Named sub-query for readable complex SQL | All queries |
| 2 | **`ROW_NUMBER() OVER`** | Number rows within partitions | Streak calculation |
| 3 | **Gaps and Islands** | Classic pattern: find consecutive sequences with gaps | Streaks |
| 4 | **`DISTINCT ON`** | PostgreSQL: keep first row per group | Longest streak |
| 5 | **`CASE WHEN`** | Conditional logic in SQL | Weekly: split by week |
| 6 | **Conditional AVG/COUNT** | `AVG(CASE WHEN ... THEN value END)` | Weekly summary |
| 7 | **`generate_series()`** | Create a sequence of dates (PostgreSQL-specific) | Monthly trend |
| 8 | **`CROSS JOIN`** | Every row from A × every row from B | Habit × date combos |
| 9 | **`LEFT JOIN`** | Include left-side rows even without matches | Fill date gaps |
| 10 | **`GREATEST() / LEAST()`** | Pick larger/smaller of two values | Completion rate |
| 11 | **Self-join** | Join a table with itself | Correlation pairs |
| 12 | **`A < B` trick** | Avoid duplicate and self pairs in self-join | Correlations |
| 13 | **`COALESCE()`** | First non-NULL argument | Value normalization |
| 14 | **`text()`** | SQLAlchemy raw SQL execution | All queries |
| 15 | **`result.mappings()`** | Get rows as dicts from raw SQL results | All queries |

---

<a name="interview"></a>
## 12. Interview Q&A

### Q1: How do you calculate streaks in SQL?
**A:** "It's the 'gaps and islands' problem. I number each log date per habit with ROW_NUMBER(), then subtract the row number (as days) from the date. Consecutive dates produce the same result — that's the 'island' group. I GROUP BY this computed value and COUNT rows to get streak lengths. The current streak is the island that includes today or yesterday. This runs as a 6-CTE query: get habits, number dates, compute groups, count lengths, find current, find longest, then LEFT JOIN to include habits with no streaks."

### Q2: How does generate_series help with chart data?
**A:** "Chart libraries need one data point per day, even for days without logs. Without generate_series, days with no logs simply don't appear — the chart connects Sep 1 directly to Sep 3, hiding the gap. generate_series creates ALL dates in the range. We CROSS JOIN with habits (every habit × every date), then LEFT JOIN with actual logs. Days without logs get NULL values — the chart renders them as gaps. The server fills gaps so the frontend doesn't have to."

### Q3: Explain the CASE WHEN technique for weekly comparison.
**A:** "One query computes both weeks. I load all logs from the last 2 weeks, then use conditional aggregation: `AVG(CASE WHEN log_date >= this_week_start THEN value END)` for this week, and a similar CASE for last week. AVG automatically ignores NULLs (rows from the other week). This avoids running two separate queries and joining — more efficient and atomic."

### Q4: Why the `A < B` trick in the correlation self-join?
**A:** "Without it, joining habit_values with itself produces duplicate pairs (Water,Sleep) and (Sleep,Water) plus self-pairs (Water,Water). The condition `a.habit_id < b.habit_id` ensures each unique pair appears exactly once. For N habits, this gives N×(N-1)/2 pairs instead of N². The service receives clean paired data and calculates Pearson correlation per pair."

### Q5: Why raw SQL instead of SQLAlchemy ORM for these queries?
**A:** "Three reasons: window functions (ROW_NUMBER, PARTITION BY) have limited ORM support; PostgreSQL-specific functions (generate_series, DISTINCT ON) have no ORM equivalent; and CTEs are more readable in raw SQL than in ORM query builders. I keep raw SQL strictly in the repository layer — the service never sees SQL, only typed dicts."

---

<a name="navigation"></a>
## 13. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 07a: Analytics Schemas](./phase4-part07a-analytics-schemas.md) |
| ➡️ Next | [Phase 4 Part 07c: Analytics Cache & Service](./phase4-part07c-analytics-cache-service.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Analytics Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 07a | ✅ Done | Analytics Schemas & Exceptions |
| **07b** | ✅ **You are here** | Analytics Repository (★★★ Complex SQL) |
| 07c | ⬜ Next | Analytics Cache & Service |
| 07d | ⬜ | Analytics Router |
| 07e | ⬜ | Analytics Connections & Flows |

---

**End of Phase 4 Part 07b: Analytics Repository**

*This is the hardest file in the project. If you can explain the streak algorithm, the generate_series gap-filling, and the self-join correlation query in an interview, you've demonstrated advanced SQL skills that most candidates lack. Next: the cache layer and service that orchestrate these queries.*
