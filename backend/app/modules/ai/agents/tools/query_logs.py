# ============================================================================
# Agent Tool — Query Habit Logs
# ============================================================================
# WHAT: Fetches the user's habit log data for a date range.
# WHEN THE AGENT USES IT: "How much water did I drink this week?"
#   Agent thinks: "I need the user's water log data" → calls this tool
# ============================================================================

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.logs.repository import LogRepository
from app.modules.habits.repository import HabitRepository
from app.shared.date_utils import today_utc


class QueryLogsTool(BaseTool):
    """Fetch habit log data for a user within a date range."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    @property
    def name(self) -> str:
        return "query_logs"

    @property
    def description(self) -> str:
        return (
            "Get the user's habit log data for a specific date range. "
            "Returns daily values for the requested habit(s). "
            "Use this when the user asks about their data, progress, or specific numbers."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "habit_name": {
                    "type": "string",
                    "description": "Name of the habit to query (e.g., 'Water Intake', 'Sleep'). "
                                   "Use 'all' to get all habits.",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of past days to include (default: 7)",
                    "default": 7,
                },
            },
            "required": ["habit_name"],
        }

    async def execute(self, **kwargs) -> str:
        habit_name = kwargs.get("habit_name", "all")
        days = min(kwargs.get("days", 7), 90)  # Cap at 90 days

        log_repo = LogRepository(self.session)
        habit_repo = HabitRepository(self.session)

        start_date = today_utc() - timedelta(days=days - 1)
        end_date = today_utc()

        # Find the habit if a specific one is requested
        habit_id = None
        if habit_name.lower() != "all":
            habits = await habit_repo.get_user_habits(self.user_id)
            for h in habits:
                if habit_name.lower() in h.name.lower():
                    habit_id = h.id
                    break
            if not habit_id:
                return f"No habit found matching '{habit_name}'. Available habits: {', '.join(h.name for h in habits)}"

        logs = await log_repo.get_logs_for_range(
            self.user_id, start_date, end_date, habit_id
        )

        if not logs:
            return f"No log data found for the last {days} days."

        # Format results as readable text
        habits_data = await habit_repo.get_user_habits(self.user_id)
        habit_names = {str(h.id): h.name for h in habits_data}
        habit_units = {str(h.id): h.unit for h in habits_data}

        lines = [f"Habit log data for the last {days} days ({start_date} to {end_date}):\n"]
        for log in logs:
            name = habit_names.get(str(log.habit_id), "Unknown")
            unit = habit_units.get(str(log.habit_id), "")
            value = log.value_numeric or log.value_scale or ("Yes" if log.value_boolean else "No")
            lines.append(f"  {log.log_date} | {name}: {value} {unit}")

        return "\n".join(lines)
