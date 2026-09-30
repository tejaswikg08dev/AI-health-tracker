# ============================================================================
# Health Tracker — Redis Connection Manager
# ============================================================================
# WHAT THIS FILE DOES:
#   Creates and manages the Redis connection.
#   Used for: caching, rate limiting, JWT token blacklist, Celery broker.
#
# WHY REDIS:
#   Redis stores data in memory — reads/writes in <1 millisecond.
#   Compare: PostgreSQL reads from disk — takes 1-10 milliseconds.
#   For data that's read frequently (dashboard stats, user sessions),
#   Redis is 10-100x faster than hitting the database every time.
#
# REDIS DATA STRUCTURES YOU'LL USE:
#   String   → cache JSON data (analytics results, user profiles)
#   Hash     → store structured data (streak info per habit)
#   Set      → token blacklist (check if token is revoked)
#   Sorted Set → rate limiting (sliding window counter)
# ============================================================================

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

# ── Create Redis Connection Pool ──
# Like PostgreSQL, we use a connection pool.
# Multiple parts of the app share connections efficiently.
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,       # Max concurrent Redis connections
    decode_responses=True,    # Return strings instead of bytes (more convenient)
)


def get_redis_client() -> redis.Redis:
    """
    Get a Redis client instance.

    WHY a function (not a global variable):
      FastAPI's dependency injection expects a callable.
      Also allows us to mock Redis in tests easily.

    USAGE in route handlers:
      @router.get("/data")
      async def get_data(cache: redis.Redis = Depends(get_redis_client)):
          cached = await cache.get("my_key")
          if cached:
              return json.loads(cached)  # Cache hit — fast!
          # Cache miss — query DB, then cache the result
    """
    return redis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """
    Close all Redis connections.

    Called during application shutdown (in main.py lifespan).
    Ensures we don't leave dangling connections.
    """
    await redis_pool.disconnect()
