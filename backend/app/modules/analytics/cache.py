# ============================================================================
# Analytics Module — Redis Cache Layer
# ============================================================================
# WHAT THIS FILE DOES:
#   Caches expensive analytics query results in Redis.
#   The dashboard loads faster because it reads from cache (< 1ms)
#   instead of running complex SQL queries (50-200ms).
#
# CACHING STRATEGY:
#   - Cache key format: "analytics:{user_id}:{query_type}"
#   - TTL (Time-To-Live): 30 min for most analytics, 5 min for dashboard
#   - Invalidation: cache is cleared when user creates/updates/deletes a log
#     (done in LogService._invalidate_cache)
#
# WHY CACHE ANALYTICS (not raw data):
#   Streak calculation runs 4 CTEs with window functions — ~100ms per query.
#   The dashboard calls 4 endpoints on load → 400ms just for analytics SQL.
#   With cache: 4 Redis GETs → ~4ms total.
#
# CACHE INVALIDATION STRATEGY:
#   "There are only two hard things in Computer Science:
#    cache invalidation and naming things." — Phil Karlton
#
#   Our approach: DELETE on write (simple, correct, slightly wasteful).
#   When a log is created/updated/deleted:
#   1. LogService calls _invalidate_cache(user_id)
#   2. That deletes ALL analytics:user_id:* keys from Redis
#   3. Next dashboard load recalculates fresh data
#   4. Fresh data is cached again for 30 minutes
#
#   Trade-off: First request after a log change is slow (100ms).
#   All subsequent requests are fast (1ms) until the next change.
#   For a personal health tracker, this is perfect.
# ============================================================================

import json
from typing import Any

import redis.asyncio as redis

from app.shared.logging import get_logger

logger = get_logger(__name__)

# Cache TTLs (seconds)
CACHE_TTL_DASHBOARD = 300       # 5 minutes — dashboard data changes often
CACHE_TTL_STREAKS = 1800        # 30 minutes — streaks only change once per day
CACHE_TTL_WEEKLY = 1800         # 30 minutes
CACHE_TTL_MONTHLY = 3600        # 1 hour — monthly trend is stable
CACHE_TTL_COMPLETION = 1800     # 30 minutes
CACHE_TTL_CORRELATION = 3600    # 1 hour — correlations are expensive + stable


class AnalyticsCache:
    """
    Redis cache for analytics results.

    Each method follows the same pattern:
    1. Build the cache key
    2. Try to GET from Redis
    3. If hit → return cached JSON (parsed back to Python)
    4. If miss → return None (caller computes fresh data and calls set_*)

    WHY a separate cache class (not inline in service):
    1. Testable — mock the cache in unit tests without mocking Redis
    2. Swappable — could change to memcached or in-memory cache
    3. Clean — service focuses on business logic, cache handles caching
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # ── Generic get/set ──

    async def get(self, key: str) -> Any | None:
        """
        Get a cached value by key.

        Returns parsed JSON or None if not found.
        Silently handles Redis errors (cache miss is fine, crash is not).
        """
        try:
            data = await self.redis.get(key)
            if data:
                logger.debug("cache_hit", key=key)
                return json.loads(data)
            logger.debug("cache_miss", key=key)
            return None
        except Exception:
            logger.warning("cache_get_error", key=key)
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store a value in cache with TTL (auto-expires).

        value is JSON-serialized. Redis stores it as a string.
        TTL ensures stale data is automatically cleaned up.
        """
        try:
            serialized = json.dumps(value, default=str)  # default=str handles UUID, date
            await self.redis.setex(key, ttl, serialized)
            logger.debug("cache_set", key=key, ttl=ttl)
        except Exception:
            # Cache write failure is not critical — don't crash the request
            logger.warning("cache_set_error", key=key)

    async def invalidate_user(self, user_id: str) -> None:
        """
        Delete ALL cached analytics for a user.

        Called when log data changes (create/update/delete).
        Uses SCAN to find matching keys — safer than KEYS (non-blocking).
        """
        try:
            pattern = f"analytics:{user_id}:*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await self.redis.delete(*keys)
                logger.debug("cache_invalidated", user_id=user_id, keys_deleted=len(keys))
        except Exception:
            logger.warning("cache_invalidate_error", user_id=user_id)

    # ── Typed accessors (build cache keys with consistent naming) ──

    def _key(self, user_id: str, query_type: str) -> str:
        return f"analytics:{user_id}:{query_type}"

    async def get_dashboard(self, user_id: str) -> dict | None:
        return await self.get(self._key(user_id, "dashboard"))

    async def set_dashboard(self, user_id: str, data: dict) -> None:
        await self.set(self._key(user_id, "dashboard"), data, CACHE_TTL_DASHBOARD)

    async def get_streaks(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "streaks"))

    async def set_streaks(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "streaks"), data, CACHE_TTL_STREAKS)

    async def get_weekly(self, user_id: str) -> dict | None:
        return await self.get(self._key(user_id, "weekly"))

    async def set_weekly(self, user_id: str, data: dict) -> None:
        await self.set(self._key(user_id, "weekly"), data, CACHE_TTL_WEEKLY)

    async def get_monthly(self, user_id: str, habit_id: str | None = None) -> dict | None:
        suffix = f"monthly:{habit_id}" if habit_id else "monthly:all"
        return await self.get(self._key(user_id, suffix))

    async def set_monthly(self, user_id: str, data: dict, habit_id: str | None = None) -> None:
        suffix = f"monthly:{habit_id}" if habit_id else "monthly:all"
        await self.set(self._key(user_id, suffix), data, CACHE_TTL_MONTHLY)

    async def get_completion(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "completion"))

    async def set_completion(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "completion"), data, CACHE_TTL_COMPLETION)

    async def get_correlations(self, user_id: str) -> list | None:
        return await self.get(self._key(user_id, "correlations"))

    async def set_correlations(self, user_id: str, data: list) -> None:
        await self.set(self._key(user_id, "correlations"), data, CACHE_TTL_CORRELATION)
