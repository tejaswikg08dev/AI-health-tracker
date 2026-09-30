# ============================================================================
# LLM — Token Usage Tracker
# ============================================================================
# WHAT THIS FILE DOES:
#   Tracks how many tokens each user consumes per day.
#   Used for: cost monitoring, rate limiting AI usage, analytics.
#
# WHY TRACK TOKENS:
#   Even with free providers (Ollama, Groq), tracking tokens teaches you
#   the production skill of cost management. In production with OpenAI:
#   - GPT-4: $0.03 per 1K input tokens
#   - A user sending 100 messages/day = $3-10/day = $100-300/month
#   - Without tracking, one abusive user could cost you thousands
#
# STORAGE: Redis (fast writes, auto-expiry for daily counters)
# ============================================================================

from datetime import date

import redis.asyncio as redis

from app.shared.date_utils import today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Daily token limits per user (adjustable)
DAILY_TOKEN_LIMIT = 50000  # ~50 conversations per day with context


class TokenTracker:
    """
    Tracks token usage per user per day in Redis.

    Key format: "tokens:{user_id}:{date}"
    Value: total tokens used today
    TTL: 48 hours (auto-cleanup, keeps yesterday for reference)
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def track_usage(
        self,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
    ) -> int:
        """
        Record token usage for a request.

        Returns the updated total for today.
        """
        today = str(today_utc())
        key = f"tokens:{user_id}:{today}"
        total = input_tokens + output_tokens

        try:
            new_total = await self.redis.incrby(key, total)
            # Set expiry if this is the first request today
            if new_total == total:
                await self.redis.expire(key, 172800)  # 48 hours
            return new_total
        except Exception:
            logger.warning("token_tracking_error", user_id=user_id)
            return 0

    async def get_usage_today(self, user_id: str) -> int:
        """Get total tokens used today by this user."""
        today = str(today_utc())
        key = f"tokens:{user_id}:{today}"

        try:
            usage = await self.redis.get(key)
            return int(usage) if usage else 0
        except Exception:
            return 0

    async def check_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user has exceeded their daily token limit.

        Returns:
            (is_allowed, tokens_remaining)
        """
        usage = await self.get_usage_today(user_id)
        remaining = max(0, DAILY_TOKEN_LIMIT - usage)
        return remaining > 0, remaining
