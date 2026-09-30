# ============================================================================
# Weekly Report — Step 1: Data Collector
# ============================================================================
# Gathers all habit data for the past week and formats it into a structured
# summary that the Analyzer step can work with.
# ============================================================================

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.habits.repository import HabitRepository
from app.modules.logs.repository import LogRepository
from app.shared.date_utils import start_of_week, today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)


class DataCollector:
    """
    Step 1 of the weekly report workflow.

    Collects: habit logs, streaks, weekly comparison, completion rates.
    Formats everything into a text summary for the LLM to analyze.
    """

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def collect(self) -> str:
        """
        Gather all relevant data for the weekly report.

        Returns a formatted text summary that can be sent to an LLM.
        """
        habit_repo = HabitRepository(self.session)
        log_repo = LogRepository(self.session)
        analytics_repo = AnalyticsRepository(self.session)

        today = today_utc()
        week_start = start_of_week(today)
        last_week_start = week_start - timedelta(days=7)

        # Get active habits
        habits = await habit_repo.get_user_habits(self.user_id)
        if not habits:
            return "No active habits found. The user hasn't created any habits yet."

        # Get this week's logs
        logs = await log_repo.get_logs_for_range(
            self.user_id, week_start, today
        )

        # Get streaks
        streaks = await analytics_repo.get_streaks(self.user_id)

        # Get weekly summary (this vs last)
        weekly = await analytics_repo.get_weekly_summary(self.user_id)

        # Get completion rates
        completion = await analytics_repo.get_completion_rates(self.user_id, days=7)

        # Format into structured text
        sections = []

        # Section 1: Habits overview
        sections.append(f"ACTIVE HABITS ({len(habits)}):")
        for h in habits:
            target = f", target: {h.target_value} {h.unit}" if h.target_value else ""
            sections.append(f"  - {h.name} ({h.habit_type}{target})")

        # Section 2: This week's data
        sections.append(f"\nTHIS WEEK'S LOGS ({week_start} to {today}):")
        habit_names = {str(h.id): h for h in habits}
        for log in logs:
            habit = habit_names.get(str(log.habit_id))
            name = habit.name if habit else "Unknown"
            unit = habit.unit if habit else ""
            value = log.value_numeric or log.value_scale or ("Yes" if log.value_boolean else "No")
            sections.append(f"  {log.log_date} | {name}: {value} {unit}")

        # Section 3: Streaks
        sections.append("\nCURRENT STREAKS:")
        for s in streaks:
            sections.append(
                f"  {s['habit_name']}: {s['current_streak']} days "
                f"(best: {s['longest_streak']})"
            )

        # Section 4: Weekly comparison
        sections.append("\nTHIS WEEK vs LAST WEEK:")
        for w in weekly:
            this_avg = f"{w['this_week_avg']:.1f}" if w['this_week_avg'] else "N/A"
            last_avg = f"{w['last_week_avg']:.1f}" if w['last_week_avg'] else "N/A"
            sections.append(
                f"  {w['habit_name']}: {this_avg} (this week) vs {last_avg} (last week)"
            )

        # Section 5: Completion rates
        sections.append("\nCOMPLETION RATES (this week):")
        for c in completion:
            pct = (c['days_logged'] / max(c['total_days'], 1)) * 100
            sections.append(f"  {c['habit_name']}: {pct:.0f}% ({c['days_logged']}/{c['total_days']} days)")

        summary = "\n".join(sections)

        logger.info(
            "weekly_data_collected",
            user_id=str(self.user_id),
            habits=len(habits),
            logs=len(logs),
        )

        return summary
