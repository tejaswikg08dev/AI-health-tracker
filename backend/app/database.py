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
