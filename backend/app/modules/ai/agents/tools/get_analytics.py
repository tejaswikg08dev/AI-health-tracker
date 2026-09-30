# ============================================================================
# Agent Tool — Get Analytics (Streaks, Averages, Trends)
# ============================================================================
# WHEN THE AGENT USES IT: "How are my streaks?" / "What's my weekly average?"
# ============================================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.analytics.repository import AnalyticsRepository


class GetAnalyticsTool(BaseTool):
    """Fetch calculated analytics: streaks, weekly summary, completion rates."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    @property
    def name(self) -> str:
        return "get_analytics"

    @property
    def description(self) -> str:
        return (
            "Get calculated analytics including habit streaks, weekly averages, "
            "and completion rates. Use this when the user asks about their progress, "
            "streaks, trends, or comparisons between time periods."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "metric_type": {
                    "type": "string",
                    "enum": ["streaks", "weekly_summary", "completion_rates"],
                    "description": "Type of analytics to fetch",
                },
            },
            "required": ["metric_type"],
        }

    async def execute(self, **kwargs) -> str:
        metric_type = kwargs.get("metric_type", "streaks")
        repo = AnalyticsRepository(self.session)

        if metric_type == "streaks":
            streaks = await repo.get_streaks(self.user_id)
            if not streaks:
                return "No streak data available yet. Start logging habits to build streaks!"
            lines = ["Current habit streaks:\n"]
            for s in streaks:
                lines.append(
                    f"  {s['habit_name']}: {s['current_streak']} days "
                    f"(best ever: {s['longest_streak']} days)"
                )
            return "\n".join(lines)

        elif metric_type == "weekly_summary":
            summary = await repo.get_weekly_summary(self.user_id)
            if not summary:
                return "No weekly data available yet."
            lines = ["This week vs last week:\n"]
            for s in summary:
                this_avg = f"{s['this_week_avg']:.1f}" if s['this_week_avg'] else "no data"
                last_avg = f"{s['last_week_avg']:.1f}" if s['last_week_avg'] else "no data"
                lines.append(
                    f"  {s['habit_name']}: {this_avg} (this week) vs {last_avg} (last week) "
                    f"| Logged {s['this_week_count']}/7 days"
                )
            return "\n".join(lines)

        elif metric_type == "completion_rates":
            rates = await repo.get_completion_rates(self.user_id)
            if not rates:
                return "No completion data available yet."
            lines = ["Habit completion rates (last 30 days):\n"]
            for r in rates:
                pct = (r['days_logged'] / max(r['total_days'], 1)) * 100
                lines.append(f"  {r['habit_name']}: {pct:.0f}% ({r['days_logged']}/{r['total_days']} days)")
            return "\n".join(lines)

        return f"Unknown metric type: {metric_type}"
