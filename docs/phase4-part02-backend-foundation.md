# 🏗️ Phase 4 Part 02: Backend Foundation

> **"The foundation is invisible but holds everything up. Get it wrong and every module wobbles."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 02 |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — Backend Infrastructure |
| **Previous** | [phase4-part01-project-setup-docker.md](./phase4-part01-project-setup-docker.md) |
| **Next** | [phase4-part03-shared-utilities-middleware.md](./phase4-part03-shared-utilities-middleware.md) |
| **Files in This Doc** | 7 files (requirements.txt, pyproject.toml, Dockerfile, config.py, database.py, redis_client.py, dependencies.py) |
| **Endpoints** | 0 (infrastructure only — no routes yet) |
| **Time to Type** | ~90 minutes |
| **Difficulty** | Medium (new concepts: connection pooling, async, dependency injection) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [File 1: requirements.txt — Python Dependencies](#requirements)
3. [File 2: pyproject.toml — Tool Configuration](#pyproject)
4. [File 3: Dockerfile — Multi-Stage Build](#dockerfile)
5. [File 4: config.py — Pydantic Settings](#config)
6. [File 5: database.py — Async SQLAlchemy](#database)
7. [File 6: redis_client.py — Redis Connection](#redis)
8. [File 7: dependencies.py — FastAPI DI](#dependencies)
9. [How All 7 Files Connect](#connections)
10. [How to Verify Your Work](#verify)
11. [What You Learned](#what-you-learned)
12. [Interview Q&A](#interview)

---

<a name="overview"></a>
## 1. What We're Building in This Part

Before you can build any feature (auth, habits, AI), you need the **infrastructure** — the plumbing that every module shares. This part creates that plumbing.

**Real-world analogy:** Before a restaurant opens, it needs:
- A grocery list (requirements.txt = what ingredients/packages to buy)
- Kitchen equipment standards (pyproject.toml = tool configurations)
- A building plan (Dockerfile = how to construct the kitchen)
- A recipe binder (config.py = all settings in one place)
- A pantry system (database.py = where to store/retrieve ingredients)
- A fridge (redis_client.py = fast access to frequently used items)
- A waiter protocol (dependencies.py = who provides what to whom)

**File structure after this part:**

```
backend/
├── requirements.txt         ← File 1: 20+ Python packages
├── pyproject.toml           ← File 2: ruff, mypy, pytest config
├── Dockerfile               ← File 3: multi-stage Docker build
├── app/
│   ├── __init__.py          ← (already exists — created as empty file)
│   ├── config.py            ← File 4: Pydantic Settings
│   ├── database.py          ← File 5: async SQLAlchemy engine
│   ├── redis_client.py      ← File 6: Redis connection pool
│   └── dependencies.py      ← File 7: FastAPI DI type aliases
```

---

<a name="config"></a>
## 5. File 4: config.py — Application Configuration (Pydantic Settings)

### What is This File?

This file reads ALL configuration from environment variables (`.env` file) into a single, typed, validated Python object. Instead of `os.environ.get("DATABASE_URL")` scattered everywhere (untyped, unchecked, error-prone), you have one `Settings` class that:

1. **Reads** from `.env` file automatically
2. **Validates types** (`DEBUG=true` string → `True` boolean)
3. **Provides defaults** (if not in `.env`, uses the default value)
4. **Fails fast** (if a required var is missing, app crashes AT STARTUP with a clear message — not at 3 AM in production)

### Concepts You Need to Know First

**What is `@lru_cache`?**

`@lru_cache` is a **decorator** — a function that wraps another function to add behavior. `lru_cache` (Least Recently Used cache) memorizes the function's return value:

```python
# WITHOUT @lru_cache:
get_settings()  # Reads .env file (I/O operation) — 5ms
get_settings()  # Reads .env file AGAIN — 5ms
get_settings()  # Reads .env file AGAIN — 5ms
# 1000 calls × 5ms = 5,000ms wasted

# WITH @lru_cache:
get_settings()  # Reads .env file — 5ms (first call)
get_settings()  # Returns cached result — 0.001ms (instant!)
get_settings()  # Returns cached result — 0.001ms
# 1 read + 999 cache hits = 5ms total
```

**What is `Literal["a", "b", "c"]`?**

`Literal` restricts a field to SPECIFIC values. If `.env` has `LLM_PROVIDER=claude`, Pydantic raises an error AT STARTUP:

```python
LLM_PROVIDER: Literal["ollama", "groq", "openai"] = "ollama"
# ✅ LLM_PROVIDER=ollama  — valid
# ✅ LLM_PROVIDER=groq    — valid
# ❌ LLM_PROVIDER=claude  — ERROR at startup: "unexpected value 'claude'"
```

**What is `@property`?**

`@property` makes a method look like a field. You call `settings.cors_origins_list` (no parentheses) but it runs code:

```python
@property
def cors_origins_list(self) -> list[str]:
    return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

# Usage: settings.cors_origins_list → ["http://localhost:3000", "http://localhost:5173"]
```

### Create Folders First

```bash
# Make sure the folder structure exists:
mkdir -p backend/app

# Create the __init__.py (empty file — makes 'app' a Python package):
echo '__version__ = "1.0.0"' > backend/app/__init__.py
```

### Type This File: `backend/app/config.py`

```python
# ============================================================================
# Health Tracker — Application Configuration
# ============================================================================
# WHAT THIS FILE DOES:
#   Reads ALL configuration from environment variables (or .env file).
#   Uses Pydantic Settings — validates types, provides defaults, errors on missing.
#
# WHY:
#   - Never hardcode secrets (DB password, API keys) in code
#   - Same code runs in dev, staging, production — only env vars change
#   - Pydantic validates everything at startup — fail fast if config is wrong
#
# HOW COMPANIES DO IT:
#   Same pattern. Config from env vars, validated at startup.
#   Some use AWS Secrets Manager or HashiCorp Vault for secrets,
#   but the code pattern is identical — read from env, validate, use.
# ============================================================================

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic Settings automatically:
    1. Reads from environment variables (case-insensitive)
    2. Reads from .env file if it exists
    3. Validates types (str, int, bool, etc.)
    4. Raises clear errors if required vars are missing
    """

    # ── App ──
    APP_NAME: str = "Health Tracker"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Database ──
    # postgresql+asyncpg:// = async driver for FastAPI
    DATABASE_URL: str = "postgresql+asyncpg://healthuser:healthpass@localhost:5432/healthtracker"
    # postgresql:// = sync driver for Alembic migrations
    DATABASE_URL_SYNC: str = "postgresql://healthuser:healthpass@localhost:5432/healthtracker"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Security ──
    SECRET_KEY: str = "change-me-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Algorithm used for JWT signing — HS256 is HMAC with SHA-256
    JWT_ALGORITHM: str = "HS256"

    # ── LLM ──
    LLM_PROVIDER: Literal["ollama", "groq", "openai"] = "ollama"
    LLM_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Embeddings ──
    EMBEDDING_PROVIDER: Literal["ollama", "openai"] = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # ── Object Storage (S3 / MinIO) ──
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_BUCKET: str = "health-tracker"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGION: str = "us-east-1"

    # ── Email ──
    EMAIL_PROVIDER: Literal["console", "resend", "ses"] = "console"
    RESEND_API_KEY: str = ""
    SES_FROM_EMAIL: str = "noreply@healthtracker.app"

    # ── CORS ──
    # Comma-separated list of allowed origins for frontend
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── AWS ──
    AWS_REGION: str = "us-east-1"
    SQS_EXPORT_QUEUE_URL: str = ""
    SQS_STREAK_QUEUE_URL: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    # Tell Pydantic Settings where to find the .env file
    model_config = SettingsConfigDict(
        env_file=".env",           # Read from .env file in project root
        env_file_encoding="utf-8",
        case_sensitive=False,      # DATABASE_URL and database_url both work
        extra="ignore",            # Ignore unknown env vars (don't crash)
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).

    WHY @lru_cache:
      Settings are read from env vars and .env file. This is I/O.
      We only need to do it ONCE — then reuse the same Settings object.
      lru_cache ensures get_settings() is called once, result is cached forever.

    This is a common pattern in FastAPI applications.
    """
    return Settings()
```

### Line-by-Line Explanation of Key Parts

**Line 1: `from functools import lru_cache`**
- `functools` is a Python standard library module with utility functions
- `lru_cache` is a decorator that caches function return values
- "LRU" = Least Recently Used — when cache is full, oldest items are removed
- We use `@lru_cache()` with empty parentheses (no size limit — just cache forever)

**Line 2: `from typing import Literal`**
- `Literal` restricts a type to specific allowed values
- `Literal["a", "b", "c"]` means ONLY "a", "b", or "c" are valid
- If any other value is provided, Pydantic raises a validation error at startup

**Line 3: `from pydantic_settings import BaseSettings, SettingsConfigDict`**
- `BaseSettings` is the base class for settings classes (reads from environment)
- `SettingsConfigDict` configures HOW Pydantic reads settings (file path, encoding, etc.)
- This comes from the `pydantic-settings` package (separate from `pydantic`)

**Line 6: `class Settings(BaseSettings):`**
- `Settings` is our custom class that inherits from `BaseSettings`
- `BaseSettings` automatically reads values from environment variables
- Every field like `APP_NAME: str = "Health Tracker"` becomes a setting:
  - Type: `str` (must be a string)
  - Default: `"Health Tracker"` (if env var `APP_NAME` is not set)
  - Pydantic reads `APP_NAME` from `.env` or environment variables

**Lines 90-95: `model_config = SettingsConfigDict(...)`**
- `env_file=".env"` — look for a `.env` file in the project root
- `case_sensitive=False` — `DATABASE_URL` and `database_url` both work
- `extra="ignore"` — if `.env` has variables we don't define (like `RANDOM_VAR`), just ignore them (don't crash)

**Lines 98-109: `@lru_cache()` + `def get_settings()`**
- `@lru_cache()` is a **decorator** — it wraps `get_settings` to add caching
- First call: creates a `Settings()` object (reads `.env` file — I/O)
- Every subsequent call: returns the cached object (no I/O, instant)
- This is important because `get_settings()` is called from MANY files (config, database, redis, every module)
- Without caching: each call re-reads `.env` from disk
- With caching: read once, reuse forever

---

<a name="database"></a>
## 6. File 5: database.py — Async SQLAlchemy Engine

### Concepts You Need to Know First

**What is a Connection Pool?**

Every database query needs a **connection** — like a phone call between your app and PostgreSQL. Opening a connection takes ~50ms (TCP handshake, authentication, SSL).

```
WITHOUT pool: Open connection (50ms) → Query (5ms) → Close → repeat
              100 requests × 55ms = 5,500ms wasted on connections

WITH pool:    Borrow from pool (0ms) → Query (5ms) → Return to pool
              100 requests × 5ms = 500ms total
              Pool opened 20 connections at startup and keeps them alive
```

**What is `async`/`await`?**

Normal (synchronous) code BLOCKS while waiting:
```python
# SYNC: Thread is STUCK for 5ms while waiting for PostgreSQL
result = session.execute(query)  # Thread does NOTHING during the wait
```

Async code FREES the thread while waiting:
```python
# ASYNC: Thread handles OTHER requests during the 5ms wait
result = await session.execute(query)  # "await" = "I'll wait, but others can go"
```

FastAPI is async. Using sync database calls would block the event loop, making the server handle only 1 request at a time.

**What is `yield` in `get_async_session()`?**

`yield` makes a function a **generator** — it "pauses" and gives you a value, then resumes for cleanup:

```python
async def get_async_session():
    session = create_session()   # Setup
    yield session                 # Give session to the route handler (PAUSE here)
    session.close()              # Cleanup (runs AFTER the handler finishes)
```

FastAPI's dependency injection system uses this pattern to ensure resources are always cleaned up, even if the handler raises an exception.

### Type This File: `backend/app/database.py`

```python
# ============================================================================
# Health Tracker — Database Connection (Async SQLAlchemy)
# ============================================================================
# WHAT THIS FILE DOES:
#   Creates the database engine (connection pool) and session factory.
#   Everything is ASYNC — non-blocking database queries.
#
# WHY ASYNC:
#   FastAPI is async. If database queries block the event loop,
#   your API can only handle 1 request at a time.
#   With async queries, the server handles thousands of requests concurrently.
#
# KEY CONCEPTS:
#   Engine   = connection pool (manages multiple DB connections)
#   Session  = a single "conversation" with the DB (start, query, commit, close)
#   Base     = parent class for all SQLAlchemy models
#
# HOW COMPANIES DO IT:
#   Same pattern. Connection pool with limits, async sessions,
#   dependency injection to provide sessions to route handlers.
# ============================================================================

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
# The engine manages a POOL of database connections.
# Instead of opening a new connection for every request (slow),
# connections are reused from the pool (fast).
engine = create_async_engine(
    settings.DATABASE_URL,
    # Pool settings — tune these based on your server capacity
    pool_size=20,          # Keep 20 connections ready in the pool
    max_overflow=10,       # Allow 10 extra connections during traffic spikes
    pool_timeout=30,       # Wait up to 30s for a connection from pool
    pool_recycle=1800,     # Recycle connections every 30min (prevent stale connections)
    echo=settings.DEBUG,   # Log SQL queries in debug mode (helpful for learning!)
)

# ── Session Factory ──
# Creates new database sessions. Each API request gets its own session.
# expire_on_commit=False: after commit, objects remain usable
#   (without this, accessing user.email after commit would trigger a new DB query)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ──
# All SQLAlchemy models inherit from this.
# Example: class User(Base): ...
class Base(DeclarativeBase):
    """
    Base class for all database models.

    WHY a base class:
      SQLAlchemy uses this to discover all your models.
      When you run Alembic migrations, it finds all classes
      that inherit from Base and creates/updates their tables.
    """

    pass


# ── Session Dependency ──
# This function is used as a FastAPI dependency.
# It provides a database session to route handlers and ensures cleanup.
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for a single request.

    HOW IT WORKS:
      1. Creates a new session from the pool
      2. Yields it to the route handler (handler uses it for queries)
      3. After the handler finishes (success OR error), the session is closed
      4. The connection returns to the pool for reuse

    WHY AsyncGenerator:
      The 'yield' keyword makes this a generator.
      Code before yield = setup (create session)
      Code after yield = cleanup (close session)
      FastAPI's dependency injection system handles this automatically.

    USAGE in route handlers:
      @router.get("/users")
      async def get_users(db: AsyncSession = Depends(get_async_session)):
          result = await db.execute(select(User))
          return result.scalars().all()
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Line-by-Line Explanation of Key Parts

**`engine = create_async_engine(settings.DATABASE_URL, pool_size=20, ...)`**

This creates the connection pool. It's created ONCE when the module loads (when Python first imports `database.py`). The pool opens `pool_size` connections to PostgreSQL and keeps them alive.

- `pool_size=20` — 20 connections always ready. Like having 20 phone lines to the database.
- `max_overflow=10` — During traffic spikes, allow 10 MORE connections temporarily (30 total). These extra ones are closed when no longer needed.
- `pool_timeout=30` — If all 30 connections are busy, a new request waits up to 30 seconds. After 30s: raises an error (better than hanging forever).
- `pool_recycle=1800` — Close and reopen each connection every 30 minutes. PostgreSQL sometimes kills idle connections — recycling prevents "connection reset" errors.
- `echo=settings.DEBUG` — When `DEBUG=true`, print every SQL query to the terminal. Invaluable for learning what SQLAlchemy generates.

**`async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`**

This is a FACTORY — a function that creates database sessions on demand. Each API request gets its own session (isolation — one request's uncommitted changes don't leak to another).

`expire_on_commit=False` is critical: without it, after `await session.commit()`, accessing `user.email` would trigger ANOTHER database query (lazy loading). With it, the object stays usable in memory.

**`async def get_async_session() -> AsyncGenerator[AsyncSession, None]:`**

This is a **generator dependency**. FastAPI calls it automatically when a route handler declares `db: AsyncSession = Depends(get_async_session)`:

1. FastAPI calls `get_async_session()`
2. The function creates a session (borrows a connection from the pool)
3. `yield session` — FastAPI receives the session and passes it to the handler
4. The handler uses the session for queries
5. The handler returns (or raises an exception)
6. Execution resumes after `yield` — the `finally` block runs
7. `session.close()` returns the connection to the pool

This guarantees cleanup even if the handler crashes.

---

<a name="redis"></a>
## 7. File 6: redis_client.py — Redis Connection

### What is Redis?

Redis = **Re**mote **Di**ctionary **S**erver. An in-memory data store. ALL data lives in RAM, making it 100x faster than disk-based databases:

- PostgreSQL (disk): read takes ~1-10 milliseconds
- Redis (RAM): read takes ~0.1 milliseconds

We use Redis for 4 things:

| Use Case | Redis Command | Why Not PostgreSQL? |
|----------|-------------|-------------------|
| **Analytics cache** | `SET key json EX 300` | 200x faster reads for dashboard |
| **Rate limiting** | `INCR key` + `EXPIRE key 60` | Checked on EVERY request — must be < 1ms |
| **JWT blacklist** | `SETEX key ttl "blacklisted"` | Checked on EVERY request, auto-expires |
| **Celery broker** | (managed by Celery) | Built-in message queue support |

### Type This File: `backend/app/redis_client.py`

```python
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
```

---

<a name="dependencies"></a>
## 8. File 7: dependencies.py — FastAPI Dependency Injection

### What is Dependency Injection?

Dependency Injection (DI) means: **"Don't create what you need — ask for it."**

```python
# ❌ WITHOUT DI: handler creates its own connection (hard to test, no cleanup)
async def get_habits():
    db = create_engine(...)  # Where does URL come from? Who closes it?
    result = db.execute(query)
    return result

# ✅ WITH DI: handler DECLARES what it needs, FastAPI provides it
async def get_habits(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(query)  # Session provided and cleaned up automatically
    return result
```

### What is `Annotated`?

`Annotated` attaches extra info to a type hint. With `Depends`, it creates reusable type aliases:

```python
# Long form (every handler repeats this):
async def get_habits(db: AsyncSession = Depends(get_async_session)):
async def get_logs(db: AsyncSession = Depends(get_async_session)):
async def get_user(db: AsyncSession = Depends(get_async_session)):

# Short form (define ONCE, use everywhere):
DBSession = Annotated[AsyncSession, Depends(get_async_session)]
async def get_habits(db: DBSession):
async def get_logs(db: DBSession):
async def get_user(db: DBSession):
```

### Type This File: `backend/app/dependencies.py`

```python
# ============================================================================
# Health Tracker — Shared Dependencies
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines reusable dependencies that are injected into route handlers.
#   Dependencies are a core FastAPI concept — they provide shared resources
#   (DB sessions, Redis, current user) to any endpoint that needs them.
#
# WHY DEPENDENCY INJECTION:
#   Instead of each route handler creating its own DB connection:
#     db = create_connection()  # BAD — repeated everywhere, hard to test
#
#   We declare what we need, and FastAPI provides it:
#     async def handler(db: AsyncSession = Depends(get_db)):  # GOOD
#
#   Benefits:
#   1. DRY — write connection logic once, use everywhere
#   2. Testable — swap real DB with test DB by overriding the dependency
#   3. Clean — route handlers focus on business logic, not infrastructure
#
# HOW COMPANIES DO IT:
#   This is the same pattern in Spring Boot (@Autowired), NestJS (@Inject),
#   and .NET (services.AddScoped). FastAPI just uses Python type hints.
# ============================================================================

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_async_session
from app.redis_client import get_redis_client

# ── Type Aliases for Dependency Injection ──
# These make route handler signatures cleaner and more readable.
#
# Instead of:
#   async def create_habit(db: AsyncSession = Depends(get_async_session)):
#
# You write:
#   async def create_habit(db: DBSession):
#
# Annotated[Type, Depends(provider)] tells FastAPI:
#   "This parameter is of type Type, and get it by calling provider"

DBSession = Annotated[AsyncSession, Depends(get_async_session)]
"""Database session — provides async SQLAlchemy session for the request lifecycle."""

RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
"""Redis client — provides async Redis connection for caching and rate limiting."""

AppSettings = Annotated[Settings, Depends(get_settings)]
"""App settings — provides access to all configuration values."""
```

---

<a name="connections"></a>
## 9. How All 7 Files Connect

```
.env file (secrets)
    │
    │ read by
    ▼
config.py ──────── Settings class (@lru_cache singleton)
    │
    ├──────────────► database.py ──── engine (connection pool)
    │                     │            session_factory
    │                     │            Base (model parent)
    │                     │            get_async_session() ─────┐
    │                     │                                      │
    ├──────────────► redis_client.py ── redis_pool               │
    │                     │              get_redis_client() ─────┤
    │                     │              close_redis()            │
    │                     │                                      │
    └──────────────► dependencies.py ── DBSession ◄──────────────┤
                          │              RedisClient ◄────────────┘
                          │              AppSettings
                          │
                          │ imported by EVERY module's router:
                          ▼
                    async def get_habits(db: DBSession):
                        result = await db.execute(select(Habit))
```

**The dependency chain:**
1. `.env` → `config.py` reads it
2. `config.py` → `database.py` needs `DATABASE_URL`
3. `config.py` → `redis_client.py` needs `REDIS_URL`
4. `database.py` + `redis_client.py` → `dependencies.py` creates type aliases
5. `dependencies.py` → every router uses `DBSession` and `RedisClient`

---

<a name="verify"></a>
## 10. How to Verify Your Work

```bash
cd backend

# Create virtual environment (if not done)
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Test config loads correctly
python -c "
from app.config import get_settings
s = get_settings()
print(f'✅ App: {s.APP_NAME}')
print(f'✅ Env: {s.APP_ENV}')
print(f'✅ LLM: {s.LLM_PROVIDER}')
print(f'✅ DB:  {s.DATABASE_URL.split(\"@\")[-1]}')
print(f'✅ Redis: {s.REDIS_URL}')
print(f'✅ CORS: {s.cors_origins_list}')
"

# Expected:
# ✅ App: Health Tracker
# ✅ Env: development
# ✅ LLM: ollama
# ✅ DB:  localhost:5432/healthtracker
# ✅ Redis: redis://localhost:6379/0
# ✅ CORS: ['http://localhost:3000', 'http://localhost:5173']
```

If all 6 lines print ✅ → Part 02 is complete!

**Note:** You can't run the app yet — that needs `main.py` which comes in Part 04 (Auth module). But the infrastructure is ready.

---

<a name="what-you-learned"></a>
## 11. What You Learned

| # | Concept | Key Takeaway |
|---|---------|-------------|
| 1 | `requirements.txt` | Shopping list of Python packages with pinned versions |
| 2 | `pyproject.toml` | One file configuring all dev tools (ruff, mypy, pytest) |
| 3 | Multi-stage Dockerfile | 3 stages (builder → dev → prod) for smaller, safer images |
| 4 | Pydantic Settings | Typed, validated config from env vars + .env file |
| 5 | `@lru_cache` | Cache function result — read .env once, reuse forever |
| 6 | `Literal["a", "b"]` | Restrict field to specific allowed values |
| 7 | `@property` | Method that looks like a field (no parentheses) |
| 8 | Connection pool | Pre-opened DB connections reused across requests |
| 9 | `async`/`await` | Non-blocking — handle other requests while waiting for DB |
| 10 | `yield` in generators | Setup → yield value → cleanup (guaranteed even on error) |
| 11 | Redis | In-memory store — 100x faster than PostgreSQL for reads |
| 12 | `decode_responses=True` | Redis returns strings not bytes (more convenient) |
| 13 | `Annotated[Type, Depends()]` | DI type alias — defines both type AND provider |
| 14 | Dependency injection | Don't create what you need — declare it, framework provides it |

---

<a name="interview"></a>
## 12. Interview Q&A

### Q: "How do you handle configuration in your application?"

> "Pydantic Settings — a single `Settings` class that reads ALL environment variables from a `.env` file, validates their types, and provides defaults. If a required variable is missing, the app fails at startup with a clear error — fail fast. The Settings object is cached with `@lru_cache` so the `.env` file is read once. I use `Literal` types to restrict certain fields — `LLM_PROVIDER` can only be 'ollama', 'groq', or 'openai'. This catches misconfigurations at startup, not at 3 AM in production."

### Q: "Explain your database connection strategy"

> "Async SQLAlchemy with a connection pool. The engine is created once at startup with 20 connections and 10 overflow. Each API request gets its own session via a FastAPI dependency that `yield`s a session and closes it in a `finally` block — the connection returns to the pool whether the request succeeds or raises an exception. I use `pool_recycle=1800` to prevent stale connections."

### Q: "What is dependency injection and why do you use it?"

> "DI means 'don't create what you need — declare it.' In FastAPI, `Depends()` provides resources like DB sessions and Redis clients to route handlers automatically. The handler writes `db: DBSession` and FastAPI creates the session, passes it in, and cleans it up after. Benefits: DRY (write connection logic once), testable (swap real DB for test DB by overriding the dependency), clean (handlers focus on business logic, not infrastructure)."

### Q: "Why Redis instead of just caching in Python?"

> "Three reasons. First, a Python dict lives in one process — 4 Gunicorn workers = 4 separate caches. Redis is shared across all workers. Second, Redis has TTL — cache entries auto-expire without cleanup code. Third, Redis persists across restarts. Plus we use Redis for 3 other things: rate limiting (INCR), token blacklist (SETEX), and Celery message broker."

### Q: "What does @lru_cache do?"

> "It's a decorator that memorizes a function's return value. First call: execute the function, store the result. Subsequent calls: return the stored result without executing. I use it on `get_settings()` because Settings initialization reads the `.env` file from disk. With caching: read once at startup, return the same object for the entire process lifetime."

---

## 📚 Document Index

| Phase | Document | Status |
|-------|----------|--------|
| 0-3 | Phase 0-3 (Overview, Setup, Design) | ✅ All complete |
| **4.01** | [Project Setup + Docker](./phase4-part01-project-setup-docker.md) | ✅ |
| **4.02** | **Backend Foundation** | **← You are here** |
| 4.03 | [Shared Utilities + Middleware](./phase4-part03-shared-utilities-middleware.md) | ⬜ Next |
| 4.04 | [Auth Module Overview](./phase4-part04-auth-module-overview.md) | ⬜ |

---
*End of Phase 4 Part 02: Backend Foundation*
*Next: [Phase 4 Part 03: Shared Utilities + Middleware →](./phase4-part03-shared-utilities-middleware.md)*
