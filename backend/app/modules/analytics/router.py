# ============================================================================
# Analytics Module — Router (API Endpoints)
# ============================================================================
# ENDPOINTS:
#   GET /api/v1/analytics/dashboard       → Dashboard overview
#   GET /api/v1/analytics/streaks         → All habit streaks
#   GET /api/v1/analytics/weekly-summary  → This week vs last week
#   GET /api/v1/analytics/monthly-trend   → 30-day daily values (chart data)
#   GET /api/v1/analytics/completion-rate → Completion % per habit
#   GET /api/v1/analytics/correlations    → Habit-to-habit correlations
#
# ALL ENDPOINTS ARE READ-ONLY (GET only).
# ALL ENDPOINTS REQUIRE AUTHENTICATION.
# ALL RESPONSES ARE CACHED IN REDIS.
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query

import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.analytics.schemas import (
    AllStreaksResponse,
    CompletionRateResponse,
    CorrelationResponse,
    DashboardData,
    MonthlyTrendResponse,
    WeeklySummaryResponse,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.auth.router import get_current_user_id
from app.redis_client import get_redis_client

router = APIRouter()


# ── Dependency: Get Analytics Service ──
async def get_analytics_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AnalyticsService:
    return AnalyticsService(session, redis_client)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get(
    "/dashboard",
    response_model=DashboardData,
    summary="Get dashboard overview",
)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DashboardData:
    """
    Get the main dashboard data in a single request.

    Returns: today's progress, total habits, best current streak,
    and weekly completion percentage.

    Cached for 5 minutes. Invalidated when logs change.
    """
    return await service.get_dashboard(user_id)


@router.get(
    "/streaks",
    response_model=AllStreaksResponse,
    summary="Get all habit streaks",
)
async def get_streaks(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AllStreaksResponse:
    """
    Get current and longest streaks for all active habits.

    A streak is the number of consecutive days a habit was logged.
    Missing a day resets the current streak to 0.

    Ordered by current streak (longest first).
    Cached for 30 minutes.
    """
    return await service.get_streaks(user_id)


@router.get(
    "/weekly-summary",
    response_model=WeeklySummaryResponse,
    summary="Compare this week vs last week",
)
async def get_weekly_summary(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
) -> WeeklySummaryResponse:
    """
    Compare this week's habit data against last week.

    For each habit: average value, days logged, and percentage change.
    Useful for spotting improvements or declines.

    Cached for 30 minutes.
    """
    return await service.get_weekly_summary(user_id)


@router.get(
    "/monthly-trend",
    response_model=MonthlyTrendResponse,
    summary="Get 30-day trend data for charts",
)
async def get_monthly_trend(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    habit_id: UUID | None = Query(
        default=None,
        description="Filter to a specific habit (omit for all habits)",
    ),
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Number of days to include (7-90)",
    ),
) -> MonthlyTrendResponse:
    """
    Get daily values for the last N days — powers the line chart.

    Returns one data point per day per habit.
    Days without logs show as null (chart draws gaps).

    Optionally filter to a single habit.
    Cached for 1 hour.
    """
    return await service.get_monthly_trend(user_id, habit_id, days)


@router.get(
    "/completion-rate",
    response_model=CompletionRateResponse,
    summary="Get completion rate per habit",
)
async def get_completion_rate(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Period to calculate over (7-90 days)",
    ),
) -> CompletionRateResponse:
    """
    Get completion percentage for each habit over a period.

    Completion = days_logged / total_possible_days × 100.

    Ordered by completion rate (highest first).
    Cached for 30 minutes.
    """
    return await service.get_completion_rates(user_id, days)


@router.get(
    "/correlations",
    response_model=CorrelationResponse,
    summary="Find correlations between habits",
)
async def get_correlations(
    user_id: UUID = Depends(get_current_user_id),
    service: AnalyticsService = Depends(get_analytics_service),
    days: int = Query(
        default=30,
        ge=14,          # Need at least 14 days for meaningful correlations
        le=90,
        description="Period to analyze (14-90 days)",
    ),
) -> CorrelationResponse:
    """
    Discover correlations between habit pairs.

    Uses Pearson correlation coefficient to find relationships.
    Example: "Your mood tends to be higher on days you sleep more" (r=0.72)

    Requires at least 5 overlapping data points per pair.
    Ordered by correlation strength (strongest first).
    Cached for 1 hour.
    """
    return await service.get_correlations(user_id, days)
