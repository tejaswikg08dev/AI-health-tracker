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
