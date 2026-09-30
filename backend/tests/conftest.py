# ============================================================================
# Test Configuration — Shared Fixtures
# ============================================================================
# WHAT THIS FILE DOES:
#   Provides reusable test fixtures for ALL tests.
#   Fixtures = pre-configured objects that tests can use.
#
# KEY FIXTURES:
#   db_session    — async SQLAlchemy session connected to test database
#   client        — httpx async test client for API integration tests
#   auth_headers  — pre-authenticated headers (skips login in every test)
#   test_user     — a pre-created user for tests that need one
#
# HOW FIXTURES WORK:
#   @pytest.fixture creates a reusable setup function.
#   Tests declare which fixtures they need via function parameters:
#
#     async def test_create_habit(client, auth_headers):
#         response = await client.post("/api/v1/habits", headers=auth_headers, json={...})
#
#   pytest automatically calls the fixture, passes the result, and cleans up after.
# ============================================================================

import asyncio
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database import Base, get_async_session
from app.main import app
from app.modules.auth.security import create_access_token, hash_password
from app.modules.auth.models import User

# ── Test Database URL ──
# Uses the test database (port 5433) started by docker-compose.test.yml
TEST_DATABASE_URL = "postgresql+asyncpg://testuser:testpass@localhost:5433/healthtracker_test"


# ── Async Event Loop ──
@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Test Database Engine ──
@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine and tables."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Database Session ──
@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session
        # Rollback after each test — keeps tests isolated
        await session.rollback()


# ── Override FastAPI Dependencies ──
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP test client for integration tests.

    Overrides the real database session with our test session.
    This means API calls in tests hit the test database, not the real one.
    """
    # Override the DB dependency
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    # Create test client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


# ── Test User ──
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        id=uuid4(),
        email=f"test_{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("TestPass123"),
        full_name="Test User",
        timezone="UTC",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── Auth Headers ──
@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """
    Pre-authenticated headers for integration tests.

    Creates a valid JWT token for the test user.
    Tests don't need to call /login first — just use these headers.
    """
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}
