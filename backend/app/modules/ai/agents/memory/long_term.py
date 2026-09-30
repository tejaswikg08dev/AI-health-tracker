# ============================================================================
# Agent Memory — Long-Term (Persistent Key Insights)
# ============================================================================
# WHAT THIS FILE DOES:
#   Stores important insights about the user that persist across sessions.
#   "Shreya is vegetarian" "Shreya is trying to improve sleep" "Shreya runs 3x/week"
#
# WHY LONG-TERM MEMORY:
#   Short-term memory is cleared after each conversation.
#   But some information is valuable across all conversations:
#   - User's dietary preferences (from uploaded docs)
#   - Health goals they've mentioned
#   - Recurring patterns the agent has noticed
#
#   Without long-term memory:
#     Session 1: "I'm vegetarian" → agent knows
#     Session 2: "What should I eat for iron?" → agent doesn't know they're vegetarian
#
#   With long-term memory:
#     Session 2: agent recalls "user is vegetarian" → recommends plant-based iron sources
#
# STORAGE: Redis (fast access) + Database (permanent backup)
#   Redis: current active insights (fast, 24h TTL, refreshed on access)
#   DB: all insights ever generated (permanent, for weekly reports)
#
# THIS IS A SIMPLIFIED VERSION:
#   Production systems use vector-based memory retrieval (embed insights,
#   search by relevance). We use keyword-based storage for simplicity.
#   The concept is the same — persistent knowledge about the user.
# ============================================================================

import json
from uuid import UUID

import redis.asyncio as redis

from app.shared.logging import get_logger

logger = get_logger(__name__)

MAX_INSIGHTS = 20  # Keep the 20 most recent insights per user
REDIS_TTL = 86400  # 24 hours — refreshed on every access


class LongTermMemory:
    """
    Persistent memory that survives across conversation sessions.

    Stores key-value insights about the user:
    - "dietary_preference": "vegetarian"
    - "health_goal": "improve sleep to 8 hours"
    - "pattern_noticed": "mood drops on days with < 6 hours sleep"

    Usage:
        memory = LongTermMemory(redis_client)
        await memory.save_insight(user_id, "dietary_preference", "vegetarian")
        insights = await memory.get_all_insights(user_id)
        # → {"dietary_preference": "vegetarian", "health_goal": "..."}
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def save_insight(
        self,
        user_id: UUID,
        key: str,
        value: str,
    ) -> None:
        """
        Save a key insight about the user.

        If the key already exists, it's overwritten with the new value.
        Insights are stored as a Redis hash (key-value map).
        """
        redis_key = f"memory:{user_id}:insights"

        try:
            await self.redis.hset(redis_key, key, value)
            await self.redis.expire(redis_key, REDIS_TTL)

            # Trim to MAX_INSIGHTS if too many
            count = await self.redis.hlen(redis_key)
            if count > MAX_INSIGHTS:
                # Remove oldest entries (Redis hash doesn't track order,
                # so we just remove the first ones returned)
                all_keys = await self.redis.hkeys(redis_key)
                to_remove = all_keys[: count - MAX_INSIGHTS]
                if to_remove:
                    await self.redis.hdel(redis_key, *to_remove)

            logger.debug("insight_saved", user_id=str(user_id), key=key)

        except Exception:
            logger.warning("insight_save_error", user_id=str(user_id), key=key)

    async def get_all_insights(self, user_id: UUID) -> dict[str, str]:
        """
        Get all stored insights for a user.

        Returns a dict of key-value pairs.
        Refreshes the TTL on access (keeps active users' data alive).
        """
        redis_key = f"memory:{user_id}:insights"

        try:
            insights = await self.redis.hgetall(redis_key)
            if insights:
                # Refresh TTL on access
                await self.redis.expire(redis_key, REDIS_TTL)
            return insights or {}
        except Exception:
            logger.warning("insight_get_error", user_id=str(user_id))
            return {}

    async def get_insight(self, user_id: UUID, key: str) -> str | None:
        """Get a specific insight by key."""
        redis_key = f"memory:{user_id}:insights"

        try:
            return await self.redis.hget(redis_key, key)
        except Exception:
            return None

    async def remove_insight(self, user_id: UUID, key: str) -> None:
        """Remove a specific insight."""
        redis_key = f"memory:{user_id}:insights"

        try:
            await self.redis.hdel(redis_key, key)
        except Exception:
            pass

    async def format_for_prompt(self, user_id: UUID) -> str:
        """
        Format all insights into a string for the LLM prompt.

        This is injected into the system prompt so the agent
        "remembers" things about the user across sessions.

        Output:
            KNOWN FACTS ABOUT THIS USER:
            - dietary_preference: vegetarian
            - health_goal: improve sleep to 8 hours
            - pattern_noticed: mood drops on days with < 6 hours sleep
        """
        insights = await self.get_all_insights(user_id)

        if not insights:
            return ""

        lines = ["KNOWN FACTS ABOUT THIS USER:"]
        for key, value in insights.items():
            lines.append(f"- {key}: {value}")

        return "\n".join(lines)
