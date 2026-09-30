# ============================================================================
# Agent Tool — Correlate Habits
# ============================================================================
# WHEN THE AGENT USES IT: "Does my sleep affect my mood?"
#   Agent thinks: "I need to check the correlation" → calls this tool
# ============================================================================

from uuid import UUID

import math
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.analytics.repository import AnalyticsRepository


class CorrelateTool(BaseTool):
    """Calculate correlation between two habits to find patterns."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    @property
    def name(self) -> str:
        return "correlate_habits"

    @property
    def description(self) -> str:
        return (
            "Calculate the correlation between two habits to find patterns. "
            "For example, does sleep affect mood? Does exercise affect energy? "
            "Use this when the user asks about relationships between habits, "
            "patterns, or cause-and-effect questions."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "habit_a": {
                    "type": "string",
                    "description": "First habit name (e.g., 'Sleep')",
                },
                "habit_b": {
                    "type": "string",
                    "description": "Second habit name (e.g., 'Mood')",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default: 30)",
                    "default": 30,
                },
            },
            "required": ["habit_a", "habit_b"],
        }

    async def execute(self, **kwargs) -> str:
        habit_a_name = kwargs.get("habit_a", "")
        habit_b_name = kwargs.get("habit_b", "")
        days = min(kwargs.get("days", 30), 90)

        repo = AnalyticsRepository(self.session)
        rows = await repo.get_correlation_data(self.user_id, days)

        if not rows:
            return "Not enough data to calculate correlations. Log more habits to see patterns."

        # Find the matching pair
        values_a = []
        values_b = []

        for row in rows:
            a_match = habit_a_name.lower() in row["habit_a_name"].lower()
            b_match = habit_b_name.lower() in row["habit_b_name"].lower()
            # Check both orderings (a,b) and (b,a)
            a_match_rev = habit_a_name.lower() in row["habit_b_name"].lower()
            b_match_rev = habit_b_name.lower() in row["habit_a_name"].lower()

            if a_match and b_match:
                values_a.append(float(row["value_a"]))
                values_b.append(float(row["value_b"]))
            elif a_match_rev and b_match_rev:
                values_a.append(float(row["value_b"]))
                values_b.append(float(row["value_a"]))

        if len(values_a) < 5:
            return (
                f"Not enough overlapping data for {habit_a_name} and {habit_b_name}. "
                f"Found only {len(values_a)} days where both were logged. Need at least 5."
            )

        # Calculate Pearson correlation
        r = self._pearson(values_a, values_b)
        if r is None:
            return "Could not calculate correlation (one habit has constant values)."

        # Interpret
        abs_r = abs(r)
        if abs_r < 0.3:
            strength = "weak"
        elif abs_r < 0.7:
            strength = "moderate"
        else:
            strength = "strong"

        direction = "positive" if r > 0.1 else ("negative" if r < -0.1 else "no clear")

        return (
            f"Correlation between {habit_a_name} and {habit_b_name} "
            f"(last {days} days, {len(values_a)} data points):\n"
            f"  Correlation coefficient: {r:.3f}\n"
            f"  Strength: {strength}\n"
            f"  Direction: {direction}\n"
            f"  Interpretation: {'Higher ' + habit_a_name + ' is associated with higher ' + habit_b_name if r > 0.1 else 'Higher ' + habit_a_name + ' is associated with lower ' + habit_b_name if r < -0.1 else 'No clear relationship found'}"
        )

    @staticmethod
    def _pearson(x: list[float], y: list[float]) -> float | None:
        n = len(x)
        if n < 2:
            return None
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        den = math.sqrt(
            sum((xi - mean_x) ** 2 for xi in x)
            * sum((yi - mean_y) ** 2 for yi in y)
        )
        return num / den if den != 0 else None
