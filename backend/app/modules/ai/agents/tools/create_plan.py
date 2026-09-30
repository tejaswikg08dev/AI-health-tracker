# ============================================================================
# Agent Tool — Create Habit Improvement Plan
# ============================================================================
# WHEN THE AGENT USES IT: "Help me improve my sleep" / "Make a plan for me"
#   Agent uses data from other tools + this tool to generate a structured plan
# ============================================================================

from app.modules.ai.agents.tools.base_tool import BaseTool


class CreatePlanTool(BaseTool):
    """Generate a structured habit improvement plan based on user goals."""

    @property
    def name(self) -> str:
        return "create_plan"

    @property
    def description(self) -> str:
        return (
            "Generate a structured weekly improvement plan for a specific habit or goal. "
            "Use this when the user asks for help improving a habit, wants a plan, "
            "or asks 'what should I do to get better at X?'"
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "What the user wants to improve (e.g., 'sleep more', 'drink more water')",
                },
                "current_data": {
                    "type": "string",
                    "description": "Summary of user's current performance from other tools",
                },
            },
            "required": ["goal"],
        }

    async def execute(self, **kwargs) -> str:
        goal = kwargs.get("goal", "")
        current_data = kwargs.get("current_data", "No data available")

        # This tool returns a structured template that the LLM fills in
        # with personalized advice based on the goal and data
        return (
            f"PLAN GENERATION REQUEST:\n"
            f"Goal: {goal}\n"
            f"Current data: {current_data}\n\n"
            f"Generate a personalized 7-day improvement plan with:\n"
            f"1. A specific daily target for each day (gradual progression)\n"
            f"2. One actionable tip per day\n"
            f"3. A weekend check-in suggestion\n"
            f"4. Expected outcome if the plan is followed\n"
            f"Base the plan on the user's current performance data."
        )
