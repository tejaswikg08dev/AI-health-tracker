# Phase 4 — Part 02e: Database Connection (database.py)

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 02e |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — FastAPI Foundation |
| **File** | `backend/app/database.py` |
| **Depends On** | Part 02d (config.py — needs DATABASE_URL) |
| **Next** | [Part 02f — redis_client.py](./phase4-part02f-redis-client.md) |
| **Difficulty** | 🟠 Hard |
| **Time to Type** | ~15 minutes |
| **Lines** | ~70 lines |

---

## What is a Database Connection Pool? Read This First

Every time your app queries the database, it needs a **connection** — like a phone call between your app and PostgreSQL. Opening a connection takes ~50ms (TCP handshake, authentication, SSL).

**Without a pool:** Every API request opens a new connection → 50ms overhead → connection closes after use.

**With a pool:** 20 connections are opened AT STARTUP and kept alive. When a request needs a connection, it BORROWS one from the pool (instant). When done, it RETURNS it (not closed, just recycled).

```
WITHOUT POOL:                      WITH POOL:
Request 1 → Open → Query → Close   Request 1 → Borrow → Query → Return
Request 2 → Open → Query → Close   Request 2 → Borrow → Query → Return
Request 3 → Open → Query → Close   Request 3 → Borrow → Query → Return
(50ms + 5ms + 5ms = 60ms each)     (0ms + 5ms + 0ms = 5ms each)
```

**Analogy:** Without pooling, it's like driving to the store for every ingredient. With pooling, the ingredients are already in your kitchen pantry — just grab what you need.

---

## What is Async SQLAlchemy?

**Synchronous (blocking):** While waiting for PostgreSQL to respond (~5ms), the Python thread is STUCK — it can't do anything else. If 100 requests come in, you need 100 threads.

**Asynchronous (non-blocking):** While waiting for PostgreSQL, Python handles OTHER requests. One thread handles hundreds of concurrent requests.

```python
# Sync (Django, Flask):
result = session.execute(query)  # Thread blocks for 5ms — idle CPU
# If 100 requests arrive, need 100 threads

# Async (FastAPI):
result = await session.execute(query)  # Thread freed during 5ms wait
# Other requests handled during that 5ms
# 100 requests, 1 thread!
```

---

## Source Code — Line by Line

> 📁 **File:** `backend/app/database.py`
> 📏 **Lines:** ~70
> ⏱️ **Type time:** ~15 minutes

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ── Create Async Engine ──
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # Keep 20 connections ready in the pool
    max_overflow=10,       # Allow 10 extra connections during traffic spikes
    pool_timeout=30,       # Wait up to 30s for a connection from pool
    pool_recycle=1800,     # Recycle connections every 30min (prevent stale connections)
    echo=settings.DEBUG,   # Log SQL queries in debug mode
)

# ── Session Factory ──
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ──
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# ── Session Dependency ──
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for a single request.

    1. Creates a new session from the pool
    2. Yields it to the route handler
    3. After the handler finishes, the session is closed
    4. The connection returns to the pool for reuse
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Line-by-line:**

### The Engine

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=settings.DEBUG,
)
```

- **`create_async_engine`** — Creates the connection pool. The engine is created ONCE at startup and shared for the entire app lifetime.
- **`pool_size=20`** — Always keep 20 connections open and ready. Like having 20 phone lines to the database.
- **`max_overflow=10`** — During traffic spikes, allow up to 10 EXTRA connections (30 total). These are closed when no longer needed.
- **`pool_timeout=30`** — If all 30 connections are busy, wait up to 30 seconds for one to free up. After 30s → raise error.
- **`pool_recycle=1800`** — Close and reopen connections every 30 minutes. PostgreSQL sometimes kills idle connections — recycling prevents "connection reset" errors.
- **`echo=settings.DEBUG`** — In debug mode, print every SQL query to the terminal. Invaluable for understanding what SQLAlchemy generates.

### The Session Factory

```python
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

- **`async_sessionmaker`** — A factory that creates database sessions. Each API request gets its own session.
- **`expire_on_commit=False`** — After `session.commit()`, the objects remain usable. Without this, accessing `user.email` after commit would trigger a NEW database query (lazy loading).

### The Base Class

```python
class Base(DeclarativeBase):
    pass
```

Every SQLAlchemy model inherits from `Base`. When Alembic runs migrations, it finds ALL classes that inherit from `Base` and creates/updates their tables.

### The Session Dependency

```python
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

- **`AsyncGenerator[AsyncSession, None]`** — This function is a generator. It `yield`s a session (gives it to the route handler) and then cleans up.
- **`yield session`** — The route handler receives the session here. When the handler finishes, execution resumes AFTER the yield.
- **`finally: await session.close()`** — The connection returns to the pool. This runs whether the handler succeeded or raised an exception.
- **`async with`** — Context manager that automatically handles cleanup if an error occurs.

---

## How This Connects

```
config.py (DATABASE_URL)
    │
    ▼
database.py
    ├── engine (connection pool — created once at startup)
    ├── async_session_factory (creates sessions)
    ├── Base (all models inherit from this)
    └── get_async_session() (FastAPI dependency)
         │
         │ used by dependencies.py:
         │   DBSession = Annotated[AsyncSession, Depends(get_async_session)]
         │
         │ used by every router:
         │   async def get_habits(db: DBSession):
         │       result = await db.execute(select(Habit))
         │
         └── Connection from pool → execute query → return to pool
```

---

## What You Learned

| # | Concept | Summary |
|---|---------|---------|
| 1 | Connection pool | Pre-opened connections reused across requests (pool_size=20) |
| 2 | Async engine | Non-blocking — handles other requests while waiting for DB |
| 3 | Session factory | Creates per-request database sessions |
| 4 | Base class | All ORM models inherit from Base (Alembic discovers them) |
| 5 | Generator dependency | `yield session` → handler uses it → `finally` cleans up |
| 6 | expire_on_commit | Keep objects usable after commit (no surprise queries) |
| 7 | pool_recycle | Prevent stale connection errors by recycling every 30 min |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `connection refused` | PostgreSQL not running | `docker-compose up postgres -d` |
| `QueuePool limit of 20 overflow 10 reached` | Too many concurrent queries | Increase pool_size or fix connection leak (missing session.close) |
| `Connection reset by peer` | PostgreSQL killed idle connection | Set `pool_recycle=1800` |
| `Can't use await outside of async function` | Using sync code in async context | Ensure ALL database functions use `await` |

---

## 🎤 Interview Q&A

### Q: "Explain your database connection strategy"

> "Async SQLAlchemy with a connection pool. The engine is created once at startup with a pool of 20 connections and 10 overflow connections. Each API request gets its own session via a FastAPI dependency that yields a session and ensures cleanup in a `finally` block — the connection returns to the pool whether the request succeeds or raises an exception. I use `pool_recycle=1800` to prevent stale connections that PostgreSQL might terminate."

### Q: "What is a connection pool and why is it important?"

> "A connection pool pre-opens database connections at startup and keeps them alive. When a request needs a database query, it borrows a connection from the pool (instant — 0ms), uses it, and returns it. Without a pool, every request opens a new TCP connection (~50ms), authenticates, queries, and closes. For 100 requests/second, that's 5,000ms wasted just on connection setup. With a pool of 20 connections, those 100 requests share the 20 pre-opened connections."

### Q: "What does `yield` do in get_async_session?"

> "It makes the function a generator — used by FastAPI's dependency injection. When a route handler declares `db: DBSession`, FastAPI calls `get_async_session()`. The function creates a session, `yield`s it to the handler (handler uses it for queries), and when the handler finishes — whether successfully or with an exception — execution resumes after `yield` and the `finally` block closes the session. This is Python's equivalent of try-with-resources in Java or `using` in C#."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 02d — config.py](./phase4-part02d-config.md) | | [Part 02f — redis_client.py](./phase4-part02f-redis-client.md) |
