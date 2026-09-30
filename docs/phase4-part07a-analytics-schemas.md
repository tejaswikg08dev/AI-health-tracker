# 📈 Phase 4 Part 07a: Analytics — Schemas & Exceptions

> **"Analytics has no create or update schemas — it's purely read-only. Every schema here maps to a dashboard widget or chart. The frontend receives data ready to render: pass it to Recharts and you've got a line chart."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 07a (Analytics Data Shapes) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.3 — Analytics & Insights |
| **Previous** | [phase4-part07-analytics-service-overview.md](./phase4-part07-analytics-service-overview.md) |
| **Next** | [phase4-part07b-analytics-repository-sql.md](./phase4-part07b-analytics-repository-sql.md) |
| **Files in This Doc** | 2 files (schemas.py, exceptions.py) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (nested schemas, chart data format, correlation fields) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: schemas.py — All Analytics Response Schemas](#schemas)
3. [File 2: exceptions.py — Analytics Exceptions](#exceptions)
4. [Schema-to-Widget Mapping](#widget-mapping)
5. [What You Learned](#what-you-learned)
6. [Interview Q&A](#interview)
7. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Analytics schemas are different from previous modules:
- **No request schemas** — all endpoints are GET with query parameters (no body)
- **Response-only schemas** — define what each widget/chart receives
- **Nested schemas** — `WeeklySummaryResponse` contains a list of `HabitWeeklySummary`, etc.
- **Chart-ready format** — data maps directly to Recharts components

### Schema Count: 12 Response Schemas + 2 Exceptions

| Category | Schemas |
|----------|---------|
| Dashboard | `DashboardData`, `StreakInfo` |
| Streaks | `AllStreaksResponse`, `StreakInfo` (reused) |
| Weekly | `WeeklySummaryResponse`, `HabitWeeklySummary` |
| Monthly Trend | `MonthlyTrendResponse`, `HabitTrendData`, `TrendDataPoint` |
| Completion | `CompletionRateResponse`, `HabitCompletionRate` |
| Correlation | `CorrelationResponse`, `CorrelationResult` |

---

<a name="schemas"></a>
## 2. File 1: `schemas.py` — All Analytics Response Schemas

### Type This Code: `backend/app/modules/analytics/schemas.py`

```python
# ============================================================================
# Analytics Module — Pydantic Schemas
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the response shapes for all analytics endpoints.
#   These are READ-ONLY schemas — analytics has no create/update endpoints.
#
# SCHEMA DESIGN:
#   Each schema maps to a specific dashboard widget or chart.
#   The frontend receives data ready to render — minimal transformation needed.
#
# CHART DATA FORMAT:
#   We return data as lists of {label, value} points.
#   This maps directly to Recharts (React charting library) data format.
#   The frontend just passes it to <BarChart data={response.data_points} />.
# ============================================================================

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


# ── Dashboard Overview ──

class DashboardData(BaseModel):
    """
    Top-level dashboard summary — the first thing the user sees.

    Contains: today's progress, total active habits, top streaks.
    This is a single API call that powers multiple dashboard widgets.

    Example response:
    {
        "today_logged": 4,
        "today_total": 6,
        "today_completion_pct": 66.7,
        "total_active_habits": 6,
        "current_best_streak": {"habit_name": "Water", "days": 15},
        "week_completion_pct": 78.5
    }
    """

    today_logged: int = Field(description="Habits logged today")
    today_total: int = Field(description="Total active habits")
    today_completion_pct: float = Field(description="Today's completion percentage")
    total_active_habits: int = Field(description="Total active (non-archived) habits")
    current_best_streak: "StreakInfo | None" = Field(
        description="The longest currently active streak"
    )
    week_completion_pct: float = Field(
        description="Average completion percentage for the current week"
    )


# ── Streaks ──

class StreakInfo(BaseModel):
    """
    Streak information for a single habit.

    WHAT IS A STREAK:
        Consecutive days where the user logged a habit.
        If you log water for 7 days in a row, current_streak = 7.
        If you miss a day, the streak resets to 0.

    INTERVIEW GOLD:
        "How do you calculate streaks in SQL?"
        This is a classic window function problem.
        See repository.py for the implementation.

    Example:
    {
        "habit_id": "...",
        "habit_name": "Water Intake",
        "habit_color": "#3B82F6",
        "habit_icon": "💧",
        "current_streak": 15,
        "longest_streak": 30,
        "last_logged_date": "2026-09-26"
    }
    """

    habit_id: UUID
    habit_name: str
    habit_color: str
    habit_icon: str
    current_streak: int = Field(description="Current consecutive days")
    longest_streak: int = Field(description="All-time longest streak")
    last_logged_date: date | None = Field(description="Most recent log date")


class AllStreaksResponse(BaseModel):
    """Response containing streak data for all active habits."""

    streaks: list[StreakInfo]


# ── Weekly Summary ──

class HabitWeeklySummary(BaseModel):
    """
    Weekly summary for a single habit — this week vs last week.

    Powers the "comparison" view on the analytics page.
    The frontend shows side-by-side bars or percentage change arrows.

    Example:
    {
        "habit_id": "...",
        "habit_name": "Sleep Hours",
        "this_week_avg": 7.2,
        "last_week_avg": 6.5,
        "change_pct": 10.8,
        "this_week_count": 6,
        "last_week_count": 7
    }
    """

    habit_id: UUID
    habit_name: str
    habit_color: str
    this_week_avg: float | None = Field(description="Average value this week")
    last_week_avg: float | None = Field(description="Average value last week")
    change_pct: float | None = Field(
        description="Percentage change (positive = improvement for numeric)"
    )
    this_week_count: int = Field(description="Days logged this week")
    last_week_count: int = Field(description="Days logged last week")


class WeeklySummaryResponse(BaseModel):
    """Response containing weekly comparison for all habits."""

    week_start: date
    week_end: date
    habits: list[HabitWeeklySummary]


# ── Monthly Trend ──

class TrendDataPoint(BaseModel):
    """
    A single data point for a trend chart.

    Powers the line chart on the analytics page.
    Each point = one day's value for one habit.

    Example:
    {
        "date": "2026-09-01",
        "value": 8.0
    }
    """

    date: date
    value: float | None = Field(description="Logged value (null = not logged that day)")


class HabitTrendData(BaseModel):
    """
    Monthly trend data for a single habit.

    Contains 30 data points (one per day).
    Days without logs have value=null — the frontend draws gaps in the line.
    """

    habit_id: UUID
    habit_name: str
    habit_color: str
    habit_type: str
    data_points: list[TrendDataPoint]


class MonthlyTrendResponse(BaseModel):
    """Response containing 30-day trend for requested habits."""

    start_date: date
    end_date: date
    habits: list[HabitTrendData]


# ── Completion Rate ──

class HabitCompletionRate(BaseModel):
    """
    Completion rate for a single habit over a period.

    "How often does the user actually log this habit?"
    If they created the habit 30 days ago and logged 24 times: 80%.

    Example:
    {
        "habit_id": "...",
        "habit_name": "Exercise",
        "days_logged": 24,
        "total_days": 30,
        "completion_pct": 80.0
    }
    """

    habit_id: UUID
    habit_name: str
    habit_color: str
    habit_icon: str
    days_logged: int
    total_days: int
    completion_pct: float


class CompletionRateResponse(BaseModel):
    """Response containing completion rates for all habits."""

    period_start: date
    period_end: date
    habits: list[HabitCompletionRate]


# ── Correlation ──

class CorrelationResult(BaseModel):
    """
    Correlation between two habits.

    WHAT IS CORRELATION:
        A number between -1 and +1 that measures how two habits move together.
        +1.0 = perfect positive (when sleep goes up, mood goes up)
        -1.0 = perfect negative (when screen time goes up, sleep goes down)
         0.0 = no relationship

    Uses Pearson correlation coefficient — standard statistical measure.

    INTERVIEW NOTE:
        "How would you detect that poor sleep affects mood?"
        Answer: "Calculate Pearson correlation between daily sleep hours
        and mood scores. A coefficient > 0.5 suggests a strong positive relationship."

    Example:
    {
        "habit_a_name": "Sleep Hours",
        "habit_b_name": "Mood",
        "correlation": 0.72,
        "strength": "strong",
        "direction": "positive",
        "data_points": 28,
        "insight": "Your mood tends to be higher on days you sleep more"
    }
    """

    habit_a_id: UUID
    habit_a_name: str
    habit_b_id: UUID
    habit_b_name: str
    correlation: float = Field(ge=-1.0, le=1.0)
    strength: str = Field(description="weak, moderate, or strong")
    direction: str = Field(description="positive, negative, or none")
    data_points: int = Field(description="Number of days with both habits logged")
    insight: str = Field(description="Human-readable insight about the correlation")


class CorrelationResponse(BaseModel):
    """Response containing correlations between habit pairs."""

    correlations: list[CorrelationResult]
```

### Key Schema Concepts Explained

**Nested Schemas (Response wraps items)**

Every analytics response follows a consistent pattern — an outer wrapper containing a list of per-habit items:

```python
class WeeklySummaryResponse(BaseModel):     # Outer wrapper
    week_start: date
    week_end: date
    habits: list[HabitWeeklySummary]         # List of per-habit data

class HabitWeeklySummary(BaseModel):         # Per-habit data
    habit_id: UUID
    habit_name: str
    this_week_avg: float | None
    ...
```

This pattern is consistent across all analytics: `AllStreaksResponse.streaks`, `MonthlyTrendResponse.habits`, `CompletionRateResponse.habits`, `CorrelationResponse.correlations`.

**Forward Reference: `"StreakInfo | None"`**
```python
class DashboardData(BaseModel):
    current_best_streak: "StreakInfo | None" = Field(...)
```
- `"StreakInfo | None"` is a **forward reference** — a string containing the class name
- `StreakInfo` is defined AFTER `DashboardData` in the file. Python hasn't seen it yet
- Pydantic resolves the string to the actual class at validation time
- Without quotes: `StreakInfo | None` → `NameError: name 'StreakInfo' is not defined`

**Chart-Ready Format: `TrendDataPoint`**
```python
class TrendDataPoint(BaseModel):
    date: date
    value: float | None
```
- Maps directly to Recharts data format: `<LineChart data={habit.data_points} />`
- `value: float | None` — `None` for days without a log. The chart draws a gap
- 30 data points per habit (one per day). Frontend doesn't need to fill gaps — we do it server-side

**Correlation Fields**
```python
class CorrelationResult(BaseModel):
    correlation: float = Field(ge=-1.0, le=1.0)
    strength: str     # "weak", "moderate", "strong"
    direction: str    # "positive", "negative", "none"
    insight: str      # "Your mood tends to be higher on days you sleep more"
```
- `correlation` — raw Pearson coefficient. The math.
- `strength` — human-readable classification: |r| < 0.3 = weak, 0.3-0.6 = moderate, > 0.6 = strong
- `direction` — "positive" (both go up together) or "negative" (one goes up, other goes down)
- `insight` — natural language explanation generated by the service. Frontend displays it as-is

**No `BaseSchema` — Using `BaseModel` Instead**
```python
class DashboardData(BaseModel):    # NOT BaseSchema
```
Analytics schemas inherit from `BaseModel`, not our custom `BaseSchema`. Why?
- `BaseSchema` has `from_attributes=True` for converting SQLAlchemy objects to Pydantic
- Analytics schemas are constructed manually in the service layer from raw SQL results (dicts), not from ORM objects
- They don't need `from_attributes` because they're built from plain Python dicts

---

<a name="exceptions"></a>
## 3. File 2: `exceptions.py` — Analytics Exceptions

### Type This Code: `backend/app/modules/analytics/exceptions.py`

```python
# ============================================================================
# Analytics Module — Custom Exceptions
# ============================================================================

from app.shared.exceptions import ValidationError


class InsufficientDataError(ValidationError):
    """
    Not enough log data to generate meaningful analytics — HTTP 422.

    Raised when: user asks for weekly comparison but only has 2 days of data,
    or asks for correlation but only one habit has logs.

    The frontend should show a friendly "Log more data to see analytics" message.
    """

    def __init__(self, detail: str = "Not enough data for this analysis") -> None:
        super().__init__(
            message=detail,
            error_code="INSUFFICIENT_DATA",
        )


class InvalidDateRangeError(ValidationError):
    """Start date is after end date — HTTP 422."""

    def __init__(self) -> None:
        super().__init__(
            message="Start date must be before or equal to end date",
            error_code="INVALID_DATE_RANGE",
        )
```

### What's Special About These Exceptions

**Only 2 exceptions — the lightest module so far.** Analytics is read-only: no creating, no updating, no deleting. The only things that can "go wrong" are:
1. Not enough data to analyze (user just signed up, has 2 days of logs)
2. Invalid date range (start after end — programming error, not user error)

**`InsufficientDataError` takes a custom detail:**
```python
InsufficientDataError("Need at least 14 days of data for correlations")
InsufficientDataError("No logs found for this period")
```
Different messages depending on which analytics function hit the minimum threshold.

---

<a name="widget-mapping"></a>
## 4. Schema-to-Widget Mapping

Each schema maps to a specific frontend component:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS DASHBOARD (React)                    │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐│
│  │ Today's        │  │ Best Streak    │  │ Week Completion       ││
│  │ Progress       │  │                │  │                       ││
│  │ 4/6 (67%)     │  │ 💧 Water       │  │ Mon ██████ 100%      ││
│  │ ████████░░░   │  │ 15 days 🔥    │  │ Tue ████░░ 67%       ││
│  │               │  │                │  │ Wed █████░ 83%        ││
│  │ DashboardData │  │ DashboardData. │  │ DashboardData.        ││
│  │ .today_*      │  │ best_streak    │  │ week_completion_pct   ││
│  └───────────────┘  └───────────────┘  └───────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Weekly Comparison                                            ││
│  │ Sleep: This week 7.2h ↑10% | Last week 6.5h                ││
│  │ Water: This week 7.4  ↑5%  | Last week 7.0                 ││
│  │                                                              ││
│  │ WeeklySummaryResponse → habits[] → HabitWeeklySummary        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 30-Day Trend (Line Chart)                                    ││
│  │    8 ─── ●                      ● ──── ●                    ││
│  │    7 ──● ─── ● ──── ● ──── ● ─── ●                         ││
│  │    6 ────────── ● ─────                                      ││
│  │    Sep 1    Sep 7    Sep 14    Sep 21    Sep 28              ││
│  │                                                              ││
│  │ MonthlyTrendResponse → habits[] → data_points[]              ││
│  │ Frontend: <LineChart data={habit.data_points} />              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────┐  ┌───────────────────────────────────┐│
│  │ Completion Rates      │  │ Correlations                      ││
│  │ Water  93% ██████████│  │ Sleep ↔ Mood: r=0.72 (strong +)  ││
│  │ Exercise 80% ████████│  │ "Mood higher on days you sleep    ││
│  │ Meditation 47% █████ │  │  more"                            ││
│  │                       │  │                                    ││
│  │ CompletionRateResponse│  │ CorrelationResponse               ││
│  └──────────────────────┘  └───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Why Return Chart-Ready Data?

```python
# BAD: Frontend has to do date math
{"logs": [{"date": "Sep-1", "value": 7}, {"date": "Sep-3", "value": 8}]}
# Frontend: "Wait, where's Sep 2? I need to fill the gap!"

# GOOD: Server fills gaps, returns complete series
{"data_points": [
    {"date": "Sep-1", "value": 7},
    {"date": "Sep-2", "value": null},  ← Server filled the gap
    {"date": "Sep-3", "value": 8}
]}
# Frontend: Just render it. Done.
```

The server does the heavy lifting (SQL + gap filling). The frontend just renders.

---

<a name="what-you-learned"></a>
## 5. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Response-only schemas** | No Create/Update — read-only module | All schemas |
| 2 | **Nested schemas** | Wrapper contains list of item schemas | All response types |
| 3 | **Forward reference** | `"StreakInfo \| None"` — string for class not yet defined | `DashboardData` |
| 4 | **Chart-ready data** | Return data matching frontend chart format directly | `TrendDataPoint` |
| 5 | **`float \| None` for gaps** | `None` = no data for this day (chart draws gap) | `TrendDataPoint.value` |
| 6 | **Correlation fields** | `correlation`, `strength`, `direction`, `insight` | `CorrelationResult` |
| 7 | **`ge=-1.0, le=1.0`** | Pearson coefficient bounded to [-1, +1] | `CorrelationResult` |
| 8 | **BaseModel vs BaseSchema** | BaseModel for manual dicts, BaseSchema for ORM objects | All analytics schemas |
| 9 | **Descriptive Field()** | Every field has `description=` for Swagger docs | All fields |
| 10 | **Minimal exceptions** | Read-only module = only 2 things can go wrong | `exceptions.py` |

---

<a name="interview"></a>
## 6. Interview Q&A

### Q1: Why are analytics schemas response-only?
**A:** "Analytics is purely read-only — it computes insights from existing data, it never creates or modifies data. All endpoints are GET with query parameters (days, habit_id), no request body. There's no `AnalyticsCreate` because there's nothing to create. The schemas define what each dashboard widget and chart receives."

### Q2: Why return chart-ready data instead of raw log data?
**A:** "Server-side data transformation means the frontend does minimal work. The monthly trend returns 30 data points per habit with null for days without logs — the frontend passes this directly to `<LineChart data={...} />`. If we returned raw logs, the frontend would need to fill date gaps, calculate averages, and handle missing data. Doing it server-side is also more efficient — one SQL query with generate_series fills gaps instead of N client-side iterations."

### Q3: What does the CorrelationResult schema tell the frontend?
**A:** "It provides four levels of information: the raw coefficient (for data-savvy users), strength/direction classifications (for labeling — 'strong positive'), data point count (confidence indicator — more data = more reliable), and a natural language insight ('Your mood tends to be higher on days you sleep more'). The frontend can show as little or as much as the user wants — from a simple insight card to a detailed statistical view."

### Q4: Why use BaseModel instead of BaseSchema for analytics?
**A:** "BaseSchema has `from_attributes=True` which enables creating Pydantic models from SQLAlchemy ORM objects. Analytics schemas are constructed manually from raw SQL result dicts and Python calculations — they're never created from ORM objects. Using BaseModel avoids the unnecessary from_attributes overhead and makes it clear these schemas are hand-constructed."

---

<a name="navigation"></a>
## 7. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 07: Analytics Module Overview](./phase4-part07-analytics-service-overview.md) |
| ➡️ Next | [Phase 4 Part 07b: Analytics Repository (★★★ Complex SQL)](./phase4-part07b-analytics-repository-sql.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Analytics Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **07a** | ✅ **You are here** | Analytics Schemas & Exceptions |
| 07b | ⬜ Next | Analytics Repository (★★★ Complex SQL) |
| 07c | ⬜ | Analytics Cache & Service |
| 07d | ⬜ | Analytics Router |
| 07e | ⬜ | Analytics Connections & Flows |

---

**End of Phase 4 Part 07a: Analytics Schemas & Exceptions**

*The response shapes are defined — 12 schemas mapping to dashboard widgets, charts, and insight cards. Next: the repository — the most complex SQL in the entire project. Window functions, CTEs, generate_series, and streak calculations.*
