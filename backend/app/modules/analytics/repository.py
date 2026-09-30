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

    # ══════════════════════════════════════════════════════════════════
    # STREAKS
    # ══════════════════════════════════════════════════════════════════

    async def get_streaks(self, user_id: UUID) -> list[dict]:
        """
        Calculate current and longest streaks for all active habits.

        ALGORITHM (Gaps and Islands problem):
        ──────────────────────────────────────
        This is a classic SQL interview problem called "gaps and islands."

        Given logged dates: Sep 20, 21, 22, 24, 25, 26 (gap on Sep 23)
        We need to find: streak 1 = Sep 20-22 (3 days), streak 2 = Sep 24-26 (3 days)

        HOW IT WORKS:
        1. Number each log date with ROW_NUMBER() (1, 2, 3, 4, 5, 6)
        2. Subtract row_number from the date:
           Sep 20 - 1 = Sep 19
           Sep 21 - 2 = Sep 19  ← same group!
           Sep 22 - 3 = Sep 19  ← same group!
           Sep 24 - 4 = Sep 20  ← different group (gap detected)
           Sep 25 - 5 = Sep 20
           Sep 26 - 6 = Sep 20
        3. GROUP BY the computed group value
        4. COUNT(*) in each group = streak length

        The "current" streak is the one that includes today (or yesterday).
        """
        query = text("""
            WITH habit_info AS (
                -- Get active habits for this user
                SELECT id AS habit_id, name, color, icon
                FROM habits
                WHERE user_id = :user_id AND is_archived = false
            ),
            logged_dates AS (
                -- Get all log dates per habit (only where something was actually logged)
                SELECT
                    hl.habit_id,
                    hl.log_date,
                    -- Number each date per habit, ordered chronologically
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
                -- The magic: subtract row_number from date to find consecutive groups
                SELECT
                    habit_id,
                    log_date,
                    -- Dates in consecutive groups will have the same grp value
                    log_date - (rn * INTERVAL '1 day') AS grp
                FROM logged_dates
            ),
            streak_lengths AS (
                -- Count consecutive days in each group
                SELECT
                    habit_id,
                    MIN(log_date) AS streak_start,
                    MAX(log_date) AS streak_end,
                    COUNT(*) AS streak_length
                FROM streaks
                GROUP BY habit_id, grp
            ),
            current_streaks AS (
                -- Current streak: must include today or yesterday
                -- (yesterday counts because user might not have logged today yet)
                SELECT
                    habit_id,
                    streak_length AS current_streak,
                    streak_end AS last_logged_date
                FROM streak_lengths
                WHERE streak_end >= CURRENT_DATE - INTERVAL '1 day'
            ),
            longest_streaks AS (
                -- Longest streak ever per habit
                SELECT DISTINCT ON (habit_id)
                    habit_id,
                    streak_length AS longest_streak
                FROM streak_lengths
                ORDER BY habit_id, streak_length DESC
            )
            -- Final: join everything together
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

    # ══════════════════════════════════════════════════════════════════
    # WEEKLY SUMMARY
    # ══════════════════════════════════════════════════════════════════

    async def get_weekly_summary(self, user_id: UUID) -> list[dict]:
        """
        Compare this week vs last week for all habits.

        For numeric habits: compares averages (7.2 hrs sleep vs 6.5 hrs)
        For boolean habits: compares completion count (5/7 vs 6/7)
        For scale habits: compares averages (mood 7.1 vs 6.3)

        USES:
        - CASE WHEN for conditional aggregation (split by week)
        - FILTER clause (PostgreSQL-specific, cleaner than CASE)
        - Date arithmetic to define "this week" and "last week"
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

                -- This week: average value
                AVG(CASE
                    WHEN hl.log_date >= :this_week_start THEN
                        COALESCE(hl.value_numeric, hl.value_scale::float,
                                 CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
                END) AS this_week_avg,

                -- Last week: average value
                AVG(CASE
                    WHEN hl.log_date >= :last_week_start AND hl.log_date <= :last_week_end THEN
                        COALESCE(hl.value_numeric, hl.value_scale::float,
                                 CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END)
                END) AS last_week_avg,

                -- This week: days logged
                COUNT(CASE WHEN hl.log_date >= :this_week_start THEN 1 END) AS this_week_count,

                -- Last week: days logged
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

    # ══════════════════════════════════════════════════════════════════
    # MONTHLY TREND
    # ══════════════════════════════════════════════════════════════════

    async def get_monthly_trend(
        self,
        user_id: UUID,
        habit_id: UUID | None = None,
        days: int = 30,
    ) -> list[dict]:
        """
        Get daily values for the last N days — powers the line chart.

        Returns one row per habit per day.
        Days without logs are included with value=NULL (the chart shows gaps).

        USES:
        - generate_series() to create a complete date range (no missing days)
        - LEFT JOIN to include days with no logs
        - CROSS JOIN to create habit×date combinations
        """
        start_date = days_ago(days - 1)
        end_date = today_utc()

        habit_filter = "AND h.id = :habit_id" if habit_id else ""

        query = text(f"""
            WITH date_range AS (
                -- Generate all dates in the range (no gaps)
                SELECT generate_series(
                    :start_date::date,
                    :end_date::date,
                    '1 day'::interval
                )::date AS d
            ),
            active_habits AS (
                SELECT id AS habit_id, name, color, habit_type
                FROM habits
                WHERE user_id = :user_id
                  AND is_archived = false
                  {habit_filter}
            ),
            -- Cross join: every habit × every date
            habit_dates AS (
                SELECT ah.habit_id, ah.name, ah.color, ah.habit_type, dr.d AS log_date
                FROM active_habits ah
                CROSS JOIN date_range dr
            )
            SELECT
                hd.habit_id,
                hd.name AS habit_name,
                hd.color AS habit_color,
                hd.habit_type,
                hd.log_date,
                -- Pick the correct value column based on habit type
                COALESCE(
                    hl.value_numeric,
                    hl.value_scale::float,
                    CASE WHEN hl.value_boolean THEN 1.0 WHEN hl.value_boolean = false THEN 0.0 END
                ) AS value
            FROM habit_dates hd
            LEFT JOIN habit_logs hl ON hd.habit_id = hl.habit_id
                AND hd.log_date = hl.log_date
                AND hl.user_id = :user_id
            ORDER BY hd.habit_id, hd.log_date
        """)

        params = {
            "user_id": str(user_id),
            "start_date": start_date,
            "end_date": end_date,
        }
        if habit_id:
            params["habit_id"] = str(habit_id)

        result = await self.session.execute(query, params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════════════
    # COMPLETION RATE
    # ══════════════════════════════════════════════════════════════════

    async def get_completion_rates(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[dict]:
        """
        Calculate completion rate per habit over the last N days.

        Completion = days_logged / total_days_in_period × 100

        A habit created 10 days ago with a 30-day period:
        total_days = 10 (not 30 — only count from creation date).
        """
        start_date = days_ago(days - 1)
        end_date = today_utc()

        query = text("""
            SELECT
                h.id AS habit_id,
                h.name AS habit_name,
                h.color AS habit_color,
                h.icon AS habit_icon,
                -- Days logged in the period
                COUNT(hl.id) AS days_logged,
                -- Total possible days (from habit creation or period start, whichever is later)
                GREATEST(
                    (LEAST(:end_date, CURRENT_DATE) -
                     GREATEST(:start_date, h.created_at::date)) + 1,
                    1  -- At least 1 day to avoid division by zero
                ) AS total_days
            FROM habits h
            LEFT JOIN habit_logs hl ON h.id = hl.habit_id
                AND hl.user_id = :user_id
                AND hl.log_date >= :start_date
                AND hl.log_date <= :end_date
            WHERE h.user_id = :user_id
              AND h.is_archived = false
            GROUP BY h.id, h.name, h.color, h.icon, h.created_at
            ORDER BY COUNT(hl.id)::float /
                GREATEST(
                    (LEAST(:end_date, CURRENT_DATE) -
                     GREATEST(:start_date, h.created_at::date)) + 1, 1
                ) DESC
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id),
            "start_date": start_date,
            "end_date": end_date,
        })
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════════════
    # CORRELATIONS
    # ══════════════════════════════════════════════════════════════════

    async def get_correlation_data(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> list[dict]:
        """
        Get paired daily values for all habit combinations.

        Returns rows where BOTH habits have a value on the same day.
        The service layer calculates Pearson correlation from this data.

        WHY not calculate correlation in SQL:
            PostgreSQL has corr() aggregate, but:
            1. We need to handle different value types (numeric vs boolean vs scale)
            2. We want to calculate it for ALL pairs (combinatorial)
            3. Python's math is easier to test and debug
            So we fetch paired data and compute in Python.
        """
        start_date = days_ago(days - 1)

        query = text("""
            WITH habit_values AS (
                -- Normalize all habit types to a single float value per day
                SELECT
                    hl.habit_id,
                    h.name AS habit_name,
                    hl.log_date,
                    COALESCE(
                        hl.value_numeric,
                        hl.value_scale::float,
                        CASE WHEN hl.value_boolean THEN 1.0 ELSE 0.0 END
                    ) AS value
                FROM habit_logs hl
                JOIN habits h ON hl.habit_id = h.id
                WHERE hl.user_id = :user_id
                  AND h.is_archived = false
                  AND hl.log_date >= :start_date
                  AND (hl.value_numeric IS NOT NULL
                       OR hl.value_boolean IS NOT NULL
                       OR hl.value_scale IS NOT NULL)
            )
            -- Self-join to get pairs of habits on the same day
            SELECT
                a.habit_id AS habit_a_id,
                a.habit_name AS habit_a_name,
                b.habit_id AS habit_b_id,
                b.habit_name AS habit_b_name,
                a.log_date,
                a.value AS value_a,
                b.value AS value_b
            FROM habit_values a
            JOIN habit_values b ON a.log_date = b.log_date
                AND a.habit_id < b.habit_id  -- Avoid duplicates (A,B) and (B,A) and (A,A)
            ORDER BY a.habit_id, b.habit_id, a.log_date
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id),
            "start_date": start_date,
        })
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    # ══════════════════════════════════════════════════════════════════
    # DASHBOARD HELPERS
    # ══════════════════════════════════════════════════════════════════

    async def get_today_progress(self, user_id: UUID) -> dict:
        """
        Count how many habits the user logged today vs total active habits.

        Powers the dashboard "4 of 6 habits logged" progress ring.
        """
        today = today_utc()

        query = text("""
            SELECT
                (SELECT COUNT(*) FROM habits
                 WHERE user_id = :user_id AND is_archived = false) AS total_habits,
                (SELECT COUNT(DISTINCT habit_id) FROM habit_logs
                 WHERE user_id = :user_id AND log_date = :today) AS logged_today
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id),
            "today": today,
        })
        row = result.mappings().one()
        return dict(row)

    async def get_week_completion(self, user_id: UUID) -> float:
        """
        Calculate average daily completion percentage for the current week.

        If the user has 6 habits and logged 4 on Mon, 5 on Tue, 6 on Wed:
        Mon = 66.7%, Tue = 83.3%, Wed = 100%
        Average = 83.3%
        """
        today = today_utc()
        week_start = start_of_week(today)

        query = text("""
            WITH daily_counts AS (
                SELECT
                    hl.log_date,
                    COUNT(DISTINCT hl.habit_id) AS logged_count
                FROM habit_logs hl
                WHERE hl.user_id = :user_id
                  AND hl.log_date >= :week_start
                  AND hl.log_date <= :today
                GROUP BY hl.log_date
            ),
            total_habits AS (
                SELECT COUNT(*) AS cnt
                FROM habits
                WHERE user_id = :user_id AND is_archived = false
            )
            SELECT
                COALESCE(
                    AVG(dc.logged_count::float / GREATEST(th.cnt, 1) * 100),
                    0
                ) AS week_completion_pct
            FROM daily_counts dc
            CROSS JOIN total_habits th
        """)

        result = await self.session.execute(query, {
            "user_id": str(user_id),
            "week_start": week_start,
            "today": today,
        })
        row = result.mappings().one()
        return float(row["week_completion_pct"])
