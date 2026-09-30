# ============================================================================
# Analytics Module — Service Layer
# ============================================================================
# WHAT THIS FILE DOES:
#   Orchestrates between the repository (SQL queries) and cache (Redis).
#   Transforms raw query results into structured response schemas.
#   Computes correlations in Python (not SQL).
#
# CACHE-ASIDE PATTERN (Read-Through):
#   1. Check cache → if hit, return cached data
#   2. If miss → query database → transform data → cache result → return
#
#   This is the most common caching pattern in production systems.
#   The service is the "single source of truth" for what gets cached.
#
# DATA TRANSFORMATION:
#   Repository returns raw dicts (from SQL rows).
#   Service transforms them into typed Pydantic schemas.
#   This separation keeps SQL in the repo and business logic in the service.
# ============================================================================

import math
from collections import defaultdict
from datetime import date, timedelta
from itertools import combinations
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.cache import AnalyticsCache
from app.modules.analytics.exceptions import InsufficientDataError
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import (
    AllStreaksResponse,
    CompletionRateResponse,
    CorrelationResponse,
    CorrelationResult,
    DashboardData,
    HabitCompletionRate,
    HabitTrendData,
    HabitWeeklySummary,
    MonthlyTrendResponse,
    StreakInfo,
    TrendDataPoint,
    WeeklySummaryResponse,
)
from app.shared.date_utils import (
    end_of_week,
    start_of_week,
    today_utc,
    days_ago,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    """
    Analytics service — computes and caches all analytics data.

    Every public method follows the cache-aside pattern:
    check cache → miss? → compute → cache → return.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.repo = AnalyticsRepository(session)
        self.cache = AnalyticsCache(redis_client)
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    # DASHBOARD
    # ══════════════════════════════════════════════════════════════════

    async def get_dashboard(self, user_id: UUID) -> DashboardData:
        """
        Get dashboard overview data — powers the main dashboard page.

        Combines: today's progress, best streak, weekly completion.
        Cached for 5 minutes (changes frequently during active logging).
        """
        uid = str(user_id)

        # Check cache
        cached = await self.cache.get_dashboard(uid)
        if cached:
            return DashboardData(**cached)

        # Compute fresh
        progress = await self.repo.get_today_progress(user_id)
        week_pct = await self.repo.get_week_completion(user_id)
        streaks_raw = await self.repo.get_streaks(user_id)

        total = progress["total_habits"]
        logged = progress["logged_today"]
        today_pct = round((logged / total * 100) if total > 0 else 0, 1)

        # Find best current streak
        best_streak = None
        if streaks_raw:
            top = max(streaks_raw, key=lambda s: s["current_streak"])
            if top["current_streak"] > 0:
                best_streak = StreakInfo(
                    habit_id=top["habit_id"],
                    habit_name=top["habit_name"],
                    habit_color=top["habit_color"],
                    habit_icon=top["habit_icon"],
                    current_streak=top["current_streak"],
                    longest_streak=top["longest_streak"],
                    last_logged_date=top["last_logged_date"],
                )

        dashboard = DashboardData(
            today_logged=logged,
            today_total=total,
            today_completion_pct=today_pct,
            total_active_habits=total,
            current_best_streak=best_streak,
            week_completion_pct=round(week_pct, 1),
        )

        # Cache
        await self.cache.set_dashboard(uid, dashboard.model_dump())

        return dashboard

    # ══════════════════════════════════════════════════════════════════
    # STREAKS
    # ══════════════════════════════════════════════════════════════════

    async def get_streaks(self, user_id: UUID) -> AllStreaksResponse:
        """
        Get current and longest streaks for all active habits.
        Cached for 30 minutes (streaks only change once per day max).
        """
        uid = str(user_id)

        cached = await self.cache.get_streaks(uid)
        if cached:
            return AllStreaksResponse(streaks=[StreakInfo(**s) for s in cached])

        rows = await self.repo.get_streaks(user_id)

        streaks = [
            StreakInfo(
                habit_id=row["habit_id"],
                habit_name=row["habit_name"],
                habit_color=row["habit_color"],
                habit_icon=row["habit_icon"],
                current_streak=row["current_streak"],
                longest_streak=row["longest_streak"],
                last_logged_date=row["last_logged_date"],
            )
            for row in rows
        ]

        response = AllStreaksResponse(streaks=streaks)
        await self.cache.set_streaks(uid, [s.model_dump() for s in streaks])

        return response

    # ══════════════════════════════════════════════════════════════════
    # WEEKLY SUMMARY
    # ══════════════════════════════════════════════════════════════════

    async def get_weekly_summary(self, user_id: UUID) -> WeeklySummaryResponse:
        """
        Compare this week vs last week for all habits.
        Cached for 30 minutes.
        """
        uid = str(user_id)

        cached = await self.cache.get_weekly(uid)
        if cached:
            return WeeklySummaryResponse(**cached)

        rows = await self.repo.get_weekly_summary(user_id)

        habits = []
        for row in rows:
            this_avg = float(row["this_week_avg"]) if row["this_week_avg"] else None
            last_avg = float(row["last_week_avg"]) if row["last_week_avg"] else None

            # Calculate percentage change
            change_pct = None
            if this_avg is not None and last_avg is not None and last_avg > 0:
                change_pct = round(((this_avg - last_avg) / last_avg) * 100, 1)

            habits.append(HabitWeeklySummary(
                habit_id=row["habit_id"],
                habit_name=row["habit_name"],
                habit_color=row["habit_color"],
                this_week_avg=round(this_avg, 1) if this_avg is not None else None,
                last_week_avg=round(last_avg, 1) if last_avg is not None else None,
                change_pct=change_pct,
                this_week_count=row["this_week_count"],
                last_week_count=row["last_week_count"],
            ))

        today = today_utc()
        response = WeeklySummaryResponse(
            week_start=start_of_week(today),
            week_end=end_of_week(today),
            habits=habits,
        )

        await self.cache.set_weekly(uid, response.model_dump())
        return response

    # ══════════════════════════════════════════════════════════════════
    # MONTHLY TREND
    # ══════════════════════════════════════════════════════════════════

    async def get_monthly_trend(
        self,
        user_id: UUID,
        habit_id: UUID | None = None,
        days: int = 30,
    ) -> MonthlyTrendResponse:
        """
        Get daily values for the last N days — powers the line chart.
        Cached for 1 hour (historical data doesn't change).
        """
        uid = str(user_id)
        hid = str(habit_id) if habit_id else None

        cached = await self.cache.get_monthly(uid, hid)
        if cached:
            return MonthlyTrendResponse(**cached)

        rows = await self.repo.get_monthly_trend(user_id, habit_id, days)

        # Group rows by habit
        habit_data: dict[str, list] = defaultdict(list)
        habit_meta: dict[str, dict] = {}

        for row in rows:
            hid_key = str(row["habit_id"])
            if hid_key not in habit_meta:
                habit_meta[hid_key] = {
                    "habit_id": row["habit_id"],
                    "habit_name": row["habit_name"],
                    "habit_color": row["habit_color"],
                    "habit_type": row["habit_type"],
                }
            habit_data[hid_key].append(
                TrendDataPoint(
                    date=row["log_date"],
                    value=round(float(row["value"]), 1) if row["value"] is not None else None,
                )
            )

        habits = [
            HabitTrendData(
                habit_id=meta["habit_id"],
                habit_name=meta["habit_name"],
                habit_color=meta["habit_color"],
                habit_type=meta["habit_type"],
                data_points=habit_data[hid_key],
            )
            for hid_key, meta in habit_meta.items()
        ]

        start_date = days_ago(days - 1)
        response = MonthlyTrendResponse(
            start_date=start_date,
            end_date=today_utc(),
            habits=habits,
        )

        await self.cache.set_monthly(uid, response.model_dump(), str(habit_id) if habit_id else None)
        return response

    # ══════════════════════════════════════════════════════════════════
    # COMPLETION RATE
    # ══════════════════════════════════════════════════════════════════

    async def get_completion_rates(
        self, user_id: UUID, days: int = 30
    ) -> CompletionRateResponse:
        """
        Calculate completion rate per habit over the last N days.
        Cached for 30 minutes.
        """
        uid = str(user_id)

        cached = await self.cache.get_completion(uid)
        if cached:
            return CompletionRateResponse(**cached)

        rows = await self.repo.get_completion_rates(user_id, days)

        habits = [
            HabitCompletionRate(
                habit_id=row["habit_id"],
                habit_name=row["habit_name"],
                habit_color=row["habit_color"],
                habit_icon=row["habit_icon"],
                days_logged=row["days_logged"],
                total_days=row["total_days"],
                completion_pct=round(
                    (row["days_logged"] / max(row["total_days"], 1)) * 100, 1
                ),
            )
            for row in rows
        ]

        start_date = days_ago(days - 1)
        response = CompletionRateResponse(
            period_start=start_date,
            period_end=today_utc(),
            habits=habits,
        )

        await self.cache.set_completion(uid, response.model_dump())
        return response

    # ══════════════════════════════════════════════════════════════════
    # CORRELATIONS
    # ══════════════════════════════════════════════════════════════════

    async def get_correlations(
        self, user_id: UUID, days: int = 30
    ) -> CorrelationResponse:
        """
        Calculate Pearson correlations between all habit pairs.

        WHAT IS PEARSON CORRELATION:
            Measures linear relationship between two variables.
            r = Σ((x-x̄)(y-ȳ)) / √(Σ(x-x̄)² × Σ(y-ȳ)²)

            r = +1.0 → perfect positive (both go up together)
            r = -1.0 → perfect negative (one up, other down)
            r = 0.0  → no linear relationship

        INTERPRETATION:
            |r| < 0.3  → weak
            |r| 0.3-0.7 → moderate
            |r| > 0.7  → strong

        Cached for 1 hour (expensive computation, stable results).
        """
        uid = str(user_id)

        cached = await self.cache.get_correlations(uid)
        if cached:
            return CorrelationResponse(correlations=[CorrelationResult(**c) for c in cached])

        rows = await self.repo.get_correlation_data(user_id, days)

        if not rows:
            return CorrelationResponse(correlations=[])

        # Group data by habit pairs
        pairs: dict[tuple, dict] = defaultdict(lambda: {
            "habit_a_name": "", "habit_b_name": "",
            "values_a": [], "values_b": [],
        })

        for row in rows:
            pair_key = (str(row["habit_a_id"]), str(row["habit_b_id"]))
            pairs[pair_key]["habit_a_id"] = row["habit_a_id"]
            pairs[pair_key]["habit_a_name"] = row["habit_a_name"]
            pairs[pair_key]["habit_b_id"] = row["habit_b_id"]
            pairs[pair_key]["habit_b_name"] = row["habit_b_name"]
            pairs[pair_key]["values_a"].append(float(row["value_a"]))
            pairs[pair_key]["values_b"].append(float(row["value_b"]))

        # Calculate Pearson correlation for each pair
        correlations = []
        for pair_key, pair_data in pairs.items():
            values_a = pair_data["values_a"]
            values_b = pair_data["values_b"]

            # Need at least 5 data points for a meaningful correlation
            if len(values_a) < 5:
                continue

            r = self._pearson_correlation(values_a, values_b)
            if r is None:
                continue

            # Interpret the correlation
            strength, direction = self._interpret_correlation(r)

            # Generate human-readable insight
            insight = self._generate_insight(
                pair_data["habit_a_name"],
                pair_data["habit_b_name"],
                r, strength, direction,
            )

            correlations.append(CorrelationResult(
                habit_a_id=pair_data["habit_a_id"],
                habit_a_name=pair_data["habit_a_name"],
                habit_b_id=pair_data["habit_b_id"],
                habit_b_name=pair_data["habit_b_name"],
                correlation=round(r, 3),
                strength=strength,
                direction=direction,
                data_points=len(values_a),
                insight=insight,
            ))

        # Sort by absolute correlation (strongest relationships first)
        correlations.sort(key=lambda c: abs(c.correlation), reverse=True)

        response = CorrelationResponse(correlations=correlations)
        await self.cache.set_correlations(uid, [c.model_dump() for c in correlations])

        return response

    # ══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
        """
        Calculate Pearson correlation coefficient between two lists.

        Formula: r = Σ((xi - x̄)(yi - ȳ)) / √(Σ(xi - x̄)² × Σ(yi - ȳ)²)

        Returns None if calculation is impossible (e.g., zero variance).

        INTERVIEW NOTE:
            This is a classic statistics formula. Knowing how to implement it
            from scratch (not just calling a library) shows deep understanding.
            In production, you might use numpy.corrcoef or scipy.stats.pearsonr.
            We implement it manually here for learning purposes.
        """
        n = len(x)
        if n != len(y) or n < 2:
            return None

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        # Numerator: sum of products of deviations
        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

        # Denominator: product of standard deviations (times n)
        sum_sq_x = sum((xi - mean_x) ** 2 for xi in x)
        sum_sq_y = sum((yi - mean_y) ** 2 for yi in y)

        denominator = math.sqrt(sum_sq_x * sum_sq_y)

        if denominator == 0:
            return None  # Zero variance — can't compute correlation

        return numerator / denominator

    @staticmethod
    def _interpret_correlation(r: float) -> tuple[str, str]:
        """Interpret correlation coefficient into strength and direction."""
        abs_r = abs(r)

        if abs_r < 0.3:
            strength = "weak"
        elif abs_r < 0.7:
            strength = "moderate"
        else:
            strength = "strong"

        if r > 0.1:
            direction = "positive"
        elif r < -0.1:
            direction = "negative"
        else:
            direction = "none"

        return strength, direction

    @staticmethod
    def _generate_insight(
        habit_a: str, habit_b: str,
        r: float, strength: str, direction: str,
    ) -> str:
        """Generate a human-readable insight about the correlation."""
        if direction == "none" or strength == "weak":
            return f"No clear relationship found between {habit_a} and {habit_b}"

        if direction == "positive":
            verb = "tends to be higher" if strength == "strong" else "may be slightly higher"
            return f"Your {habit_b} {verb} on days when {habit_a} is higher"
        else:
            verb = "tends to be lower" if strength == "strong" else "may be slightly lower"
            return f"Your {habit_b} {verb} on days when {habit_a} is higher"
