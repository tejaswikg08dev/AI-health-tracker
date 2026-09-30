# ============================================================================
# Agent — Health Coach Agent
# ============================================================================
# WHAT THIS FILE DOES:
#   Creates a pre-configured Health Coach agent with all the right tools,
#   system prompt, and memory. This is the agent the user chats with.
#
# WHY A SEPARATE CLASS (not just using BaseAgent directly):
#   BaseAgent is generic — it doesn't know about health tracking.
#   HealthCoachAgent:
#   1. Sets up health-specific tools (query_logs, analytics, docs, etc.)
#   2. Uses a health coach system prompt
#   3. Injects long-term memory (user preferences, past insights)
#   4. Handles the full agent lifecycle (create → run → save memory)
#
# USAGE:
#   agent = await HealthCoachAgent.create(session, redis, user_id, user)
#   response = await agent.chat("How's my sleep this week?")
# ============================================================================

from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.agents.base_agent import BaseAgent
from app.modules.ai.agents.memory.long_term import LongTermMemory
from app.modules.ai.agents.memory.short_term import ShortTermMemory
from app.modules.ai.agents.tools.base_tool import BaseTool
from app.modules.ai.agents.tools.correlate import CorrelateTool
from app.modules.ai.agents.tools.create_plan import CreatePlanTool
from app.modules.ai.agents.tools.get_analytics import GetAnalyticsTool
from app.modules.ai.agents.tools.query_logs import QueryLogsTool
from app.modules.ai.agents.tools.search_docs import SearchDocsTool
from app.modules.ai.llm.factory import get_llm_client
from app.modules.ai.llm.prompt_templates import AGENT_SYSTEM
from app.modules.habits.repository import HabitRepository
from app.shared.logging import get_logger

logger = get_logger(__name__)


class HealthCoachAgent:
    """
    Pre-configured health coach AI agent.

    Wraps BaseAgent with health-specific tools, prompts, and memory.
    This is the main entry point for the AI chat feature.

    TOOLS AVAILABLE TO THE AGENT:
    1. query_logs       — fetch habit data for any date range
    2. get_analytics    — get streaks, weekly summaries, completion rates
    3. search_documents — RAG search across uploaded health documents
    4. correlate_habits — find correlations between two habits
    5. create_plan      — generate a structured improvement plan

    The agent decides WHICH tools to use based on the user's question.
    It can use multiple tools in sequence for complex questions.
    """

    def __init__(
        self,
        agent: BaseAgent,
        long_term_memory: LongTermMemory,
        user_id: UUID,
    ):
        self.agent = agent
        self.long_term_memory = long_term_memory
        self.user_id = user_id

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        redis_client: redis.Redis,
        user_id: UUID,
        user_name: str,
        user_timezone: str = "UTC",
    ) -> "HealthCoachAgent":
        """
        Factory method — creates a fully configured Health Coach agent.

        This is the FACTORY METHOD PATTERN (different from the factory function
        in llm/factory.py). A classmethod that creates instances with complex setup.

        Steps:
        1. Initialize all tools with the user's context
        2. Build the system prompt with user info and long-term memory
        3. Create the BaseAgent with tools, prompt, and memory
        4. Return a HealthCoachAgent wrapper
        """
        # Get LLM client
        llm = get_llm_client()

        # Initialize tools — each tool gets the DB session and user_id
        tools: list[BaseTool] = [
            QueryLogsTool(session, user_id),
            GetAnalyticsTool(session, user_id),
            SearchDocsTool(session, user_id),
            CorrelateTool(session, user_id),
            CreatePlanTool(),
        ]

        # Count active habits for context
        habit_repo = HabitRepository(session)
        habits = await habit_repo.get_user_habits(user_id)
        habit_count = len(habits)

        # Build system prompt with user context
        system_prompt = AGENT_SYSTEM.render(
            user_name=user_name,
            habit_count=habit_count,
            tools=tools,
        )

        # Load long-term memory and append to system prompt
        long_term = LongTermMemory(redis_client)
        memory_context = await long_term.format_for_prompt(user_id)
        if memory_context:
            system_prompt += f"\n\n{memory_context}"

        # Add active habits list to system prompt
        if habits:
            habit_list = "\n".join(
                f"  - {h.name} ({h.habit_type}, {h.unit or 'no unit'})"
                for h in habits
            )
            system_prompt += f"\n\nACTIVE HABITS:\n{habit_list}"

        # Create the base agent
        short_term = ShortTermMemory(max_messages=20)
        agent = BaseAgent(
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            memory=short_term,
            max_iterations=5,
        )

        logger.info(
            "health_coach_created",
            user_id=str(user_id),
            tools=len(tools),
            habits=habit_count,
            has_long_term_memory=bool(memory_context),
        )

        return cls(agent=agent, long_term_memory=long_term, user_id=user_id)

    async def chat(self, message: str) -> str:
        """
        Send a message to the health coach and get a response.

        The agent will:
        1. Analyze the question
        2. Decide which tools to use
        3. Fetch real data from the database
        4. Generate a personalized response

        Returns the agent's text response.
        """
        response = await self.agent.run(message)

        # Extract and save any new insights to long-term memory
        await self._extract_and_save_insights(message, response)

        return response

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed by this agent across all interactions."""
        return self.agent.total_tokens

    async def _extract_and_save_insights(self, user_message: str, response: str) -> None:
        """
        Attempt to save relevant insights from the conversation to long-term memory.

        Simple heuristic: if the user mentions personal facts, save them.
        A production system would use a separate LLM call to extract facts.
        We use keyword matching for simplicity and zero cost.
        """
        message_lower = user_message.lower()

        # Detect dietary preferences
        for keyword in ["vegetarian", "vegan", "keto", "gluten-free", "dairy-free"]:
            if keyword in message_lower:
                await self.long_term_memory.save_insight(
                    self.user_id, "dietary_preference", keyword
                )

        # Detect health goals
        goal_phrases = ["i want to", "my goal is", "i'm trying to", "help me"]
        for phrase in goal_phrases:
            if phrase in message_lower:
                # Save a summary of their goal
                goal = user_message[:200]  # First 200 chars as the goal
                await self.long_term_memory.save_insight(
                    self.user_id, "health_goal", goal
                )
                break
