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
