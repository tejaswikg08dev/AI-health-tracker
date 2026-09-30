# Phase 4 — Part 02g: Dependency Injection (dependencies.py)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02g |
| **File** | `backend/app/dependencies.py` |
| **Depends On** | Part 02d-f (config, database, redis — all injected) |
| **Next** | [Part 03 Overview — Shared + Middleware](./phase4-part03-shared-and-middleware-overview.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~5 minutes |
| **Lines** | ~25 lines |

---

## What is Dependency Injection? Read This First

Dependency Injection (DI) means: **"Don't create what you need — ask for it."**

```python
# ❌ WITHOUT DI: handler creates its own connection (hard to test, no cleanup)
async def get_habits():
    db = create_engine(...)  # Where does the URL come from? Who closes it?
    result = db.execute(query)
    return result

# ✅ WITH DI: handler DECLARES what it needs, FastAPI provides it
async def get_habits(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(query)  # Session provided, cleanup automatic
    return result
```

FastAPI sees `Depends(get_async_session)` and:
1. Calls `get_async_session()` (creates a session from the pool)
2. Passes the session to your handler as `db`
3. After the handler returns, runs cleanup (closes the session)

**Analogy:** In a restaurant, the waiter doesn't grow vegetables. The waiter ASKS the kitchen for ingredients. DI is the system where the kitchen provides ingredients to whoever asks.

### What is `Annotated`?

`Annotated` lets you attach metadata to a type hint. Combined with `Depends`, it creates reusable type aliases:

```python
# Long form (every handler repeats this):
async def get_habits(db: AsyncSession = Depends(get_async_session)): ...
async def get_logs(db: AsyncSession = Depends(get_async_session)): ...
async def get_user(db: AsyncSession = Depends(get_async_session)): ...

# Short form (define once, use everywhere):
DBSession = Annotated[AsyncSession, Depends(get_async_session)]

async def get_habits(db: DBSession): ...
async def get_logs(db: DBSession): ...
async def get_user(db: DBSession): ...
```

---

## Source Code — Line by Line

> 📁 **File:** `backend/app/dependencies.py`
> 📏 **Lines:** ~25
> ⏱️ **Type time:** ~5 minutes

```python
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_async_session
from app.redis_client import get_redis_client

DBSession = Annotated[AsyncSession, Depends(get_async_session)]
"""Database session — provides async SQLAlchemy session for the request lifecycle."""

RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
"""Redis client — provides async Redis connection for caching and rate limiting."""

AppSettings = Annotated[Settings, Depends(get_settings)]
"""App settings — provides access to all configuration values."""
```

**Line-by-line:**

- **`DBSession = Annotated[AsyncSession, Depends(get_async_session)]`**
  - `AsyncSession` = the TYPE (for IDE autocomplete and MyPy)
  - `Depends(get_async_session)` = HOW to get it (FastAPI calls this function)
  - Now any handler can write: `async def handler(db: DBSession)` — 12 characters instead of 55

- **`RedisClient`** — Same pattern for Redis connections.

- **`AppSettings`** — Same pattern for configuration. Rarely used directly (modules import `get_settings()` instead), but available for handlers that need settings.

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Dependency Injection | Don't create what you need — declare it, framework provides it |
| 2 | Depends() | FastAPI's DI mechanism — calls a function and passes the result |
| 3 | Annotated | Attach DI metadata to type hints — creates reusable aliases |
| 4 | Type aliases | `DBSession` = shorthand for `AsyncSession + Depends(...)` |

---

## 🎤 Interview Q&A

### Q: "How does dependency injection work in FastAPI?"

> "FastAPI uses `Depends()` — you declare what a handler needs in its function signature, and FastAPI provides it. For example, `async def get_habits(db: DBSession)` tells FastAPI to call `get_async_session()`, which creates a database session from the connection pool. The session is passed to the handler, and after the handler returns, the generator's cleanup code runs — closing the session and returning the connection to the pool. I define `Annotated` type aliases like `DBSession` so every handler uses a consistent, short syntax. For testing, I override the dependency with a test database session — the handler code doesn't change at all."

### Q: "How does DI help with testing?"

> "In tests, I override the dependency: `app.dependency_overrides[get_async_session] = test_session_factory`. Now every handler that declares `db: DBSession` receives a test database session instead of the production one. The handler code is identical in tests and production — only the infrastructure changes. This is the whole point of DI: decouple WHAT you need from WHERE it comes from."

---

## ✅ Release 1.1 Complete!

You've typed all 7 foundation files. Before moving on:

```bash
cd backend
python -c "
from app.config import get_settings
s = get_settings()
print(f'✅ Config: {s.APP_NAME} ({s.APP_ENV})')
print(f'✅ DB: {s.DATABASE_URL.split(\"@\")[-1]}')
print(f'✅ Redis: {s.REDIS_URL}')
print(f'✅ LLM: {s.LLM_PROVIDER}')
"
```

If this prints 4 lines → foundation is solid. Move to [Part 03 — Shared + Middleware](./phase4-part03-shared-and-middleware-overview.md) 🚀

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02f — redis_client.py](./phase4-part02f-redis-client.md) | | [Part 03 Overview — Shared + Middleware](./phase4-part03-shared-and-middleware-overview.md) |
