# Phase 4 — Part 02f: Redis Client (redis_client.py)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02f |
| **File** | `backend/app/redis_client.py` |
| **Depends On** | Part 02d (config.py — needs REDIS_URL) |
| **Next** | [Part 02g — dependencies.py](./phase4-part02g-dependencies.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~8 minutes |
| **Lines** | ~40 lines |

---

## What is Redis? Read This First

Redis = **Remote Dictionary Server**. It's an in-memory data store — ALL data lives in RAM, not on disk.

**Why is that special?** RAM is 100x faster than disk:
- PostgreSQL (disk): read takes ~1-10 milliseconds
- Redis (RAM): read takes ~0.1 milliseconds

We use Redis for 4 things in this project:

| Use Case | Redis Command | TTL | Why Not PostgreSQL? |
|----------|-------------|-----|-------------------|
| **Analytics cache** | `SET key json EX 300` | 5-60 min | Dashboard loads 100x/day — Redis: 0.1ms, PG: 200ms |
| **Rate limiting** | `INCR key` | 60 sec | Checked on EVERY request — must be < 1ms |
| **JWT blacklist** | `SETEX key ttl value` | Until token expiry | Checked on EVERY request, auto-deletes |
| **Celery broker** | (managed internally) | — | Message queue for background tasks |

**Analogy:** PostgreSQL is your filing cabinet (organized, permanent, but takes time to walk there). Redis is your desk sticky notes (fast to read, limited space, temporary).

---

## Source Code — Line by Line

> 📁 **File:** `backend/app/redis_client.py`
> 📏 **Lines:** ~40
> ⏱️ **Type time:** ~8 minutes

```python
import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

# ── Create Redis Connection Pool ──
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)


def get_redis_client() -> redis.Redis:
    """
    Get a Redis client instance.
    Used as a FastAPI dependency — injected into route handlers.
    """
    return redis.Redis(connection_pool=redis_pool)


async def close_redis() -> None:
    """
    Close all Redis connections.
    Called during application shutdown (in main.py lifespan).
    """
    await redis_pool.disconnect()
```

**Line-by-line:**

- **`import redis.asyncio as redis`** — Import the ASYNC Redis client. The package name is `redis` but we import the async version. This matches FastAPI's async nature.

- **`redis_pool = redis.ConnectionPool.from_url(...)`** — Create a connection pool (same concept as PostgreSQL — pre-opened connections, reused).
  - `max_connections=20` — Keep up to 20 Redis connections alive
  - `decode_responses=True` — Return strings instead of bytes. Without this, `GET key` returns `b"hello"` (bytes), with it returns `"hello"` (string).

- **`get_redis_client()`** — Factory function that returns a Redis client using the shared pool. FastAPI calls this via `Depends()`.

- **`close_redis()`** — Called when the app shuts down. Closes all pool connections cleanly.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Redis | In-memory data store — 100x faster than disk-based databases |
| 2 | Connection pool | Same pattern as PostgreSQL — pre-open, reuse, return |
| 3 | decode_responses | Return strings instead of bytes (more convenient in Python) |
| 4 | 4 use cases | Cache, rate limiting, token blacklist, task broker |

---

## 🎤 Interview Q&A

### Q: "Why Redis instead of just using PostgreSQL for caching?"

> "Speed. Redis stores data in RAM — reads take 0.1ms. PostgreSQL stores data on disk — reads take 1-10ms. For analytics that are queried on every dashboard load, that's the difference between a 1ms response and a 200ms response. Redis also has built-in TTL — cache entries auto-expire without cleanup code. And it's excellent for rate limiting counters that need atomic INCR operations checked on every single request."

### Q: "What happens if Redis goes down?"

> "The app still works — just slower. I designed all Redis dependencies to fail gracefully: the rate limiter passes requests through (fail open), the cache returns misses (queries hit PostgreSQL directly), and the token blacklist fails open (already-logged-out tokens temporarily work until they expire naturally). No Redis failure should crash the application."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02e — database.py](./phase4-part02e-database.md) | | [Part 02g — dependencies.py](./phase4-part02g-dependencies.md) |
