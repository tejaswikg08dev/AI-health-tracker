# 🧪 Phase 5 Part 01: Testing — Overview & Infrastructure

> **"A test suite with 3 layers: conftest.py provides 6 reusable fixtures (test DB, async client, pre-authenticated headers), factories.py generates realistic fake data, and 3 mock files replace external services (LLM, email, S3) with in-memory fakes. Zero external dependencies needed to run unit tests."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 5 — Testing |
| **Previous** | [Phase 4 Part 16g: Frontend Flows](./phase4-part16g-frontend-entry-routing-flows.md) |
| **Next** | [Phase 5 Part 02: Unit Tests](./phase5-part02-unit-tests.md) |
| **Files in This Doc** | 5 files (conftest.py, factories.py, 3 mock files) |
| **Time to Type** | ~35 minutes |
| **Difficulty** | Medium (pytest fixtures, async test client, dependency injection override) |

---

## 1. Testing Strategy

### Three Types of Tests

```
┌─────────────────────────────────────────────────────────────┐
│                     TEST PYRAMID                             │
│                                                              │
│                    ╱  ╲          E2E Tests (curl commands)    │
│                   ╱────╲         Few, slow, test full flow   │
│                  ╱      ╲                                    │
│                 ╱────────╲      Integration Tests             │
│                ╱          ╲      Real DB, real HTTP, 3 files │
│               ╱────────────╲                                 │
│              ╱              ╲   Unit Tests                    │
│             ╱────────────────╲   No DB, no HTTP, 4 files     │
│            ╱                  ╲  Fast, many, test logic       │
│           └────────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

| Type | Files | Needs DB? | Needs Redis? | Speed | What It Tests |
|------|-------|-----------|-------------|-------|--------------|
| **Unit** | 4 | ❌ | ❌ | ~2 sec | Pure functions: JWT, hashing, chunking, agent loop |
| **Integration** | 3 | ✅ | ✅ | ~10 sec | Full HTTP: signup, login, CRUD habits, CRUD logs |
| **E2E** | curl scripts | ✅ | ✅ | ~30 sec | Manual: full user journey through the real API |

### Test File Structure

```
backend/tests/
├── conftest.py              ← Shared fixtures (DB session, test client, auth)
├── factories.py             ← Fake data generators (users, habits, logs)
├── __init__.py
│
├── mocks/                   ← In-memory replacements for external services
│   ├── mock_email_provider.py   ← Captures emails in a list
│   ├── mock_llm_client.py       ← Returns deterministic AI responses
│   ├── mock_storage.py          ← In-memory file storage (no S3)
│   └── __init__.py
│
├── unit/                    ← Tests that need NO external services
│   ├── test_auth_security.py    ← JWT + bcrypt tests
│   ├── test_date_utils.py       ← Date utility tests
│   ├── test_rag_chunker.py      ← Text chunking algorithm tests
│   ├── test_ai_agent.py         ← ReAct agent loop tests (mocked LLM)
│   └── __init__.py
│
└── integration/             ← Tests that hit real DB + real HTTP
    ├── test_auth_api.py         ← Signup, login, profile (10 tests)
    ├── test_habits_api.py       ← CRUD habits (7 tests)
    ├── test_logs_api.py         ← Create/list logs, bulk log (7 tests)
    └── __init__.py
```

---

## 2. `backend/tests/conftest.py` — Shared Fixtures

### Type This Code:

```python
# ============================================================================
# Test Configuration — Shared Fixtures
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
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

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
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

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
```

### How Fixtures Work (Visual)

```
test_create_habit(client, auth_headers)
                    │         │
                    │         └── auth_headers fixture:
                    │               └── depends on test_user fixture:
                    │                     └── depends on db_session fixture:
                    │                           └── depends on test_engine fixture
                    │                                 (creates tables once per session)
                    │
                    └── client fixture:
                          └── depends on db_session fixture (same instance!)
                                └── overrides FastAPI's get_async_session
                                    → all API calls use the TEST database
```

**Key design: `scope="session"` vs default scope**

| Fixture | Scope | Meaning |
|---------|-------|---------|
| `event_loop` | session | One event loop for ALL tests (not per-test) |
| `test_engine` | session | Create tables ONCE, drop ONCE (not per-test) |
| `db_session` | function (default) | Fresh session per test → rollback after each |
| `client` | function | Fresh HTTP client per test |
| `test_user` | function | New user per test (unique email) |

**`await session.rollback()`** — After each test, any database changes are rolled back. This means tests are **isolated** — one test's data doesn't affect another. No cleanup code needed.

**`app.dependency_overrides[get_async_session] = override_session`** — FastAPI's dependency injection allows replacing dependencies at test time. The real `get_async_session` connects to the production database. We swap it with our test session. The API code doesn't know it's being tested — it just gets a session object.

---

## 3. `backend/tests/factories.py` — Test Data Generators

### Type This Code:

```python
# ============================================================================
# Test Data Factories — Generate Realistic Fake Data
# ============================================================================

import random
from datetime import date, timedelta
from uuid import uuid4


def make_user_data(overrides: dict | None = None) -> dict:
    """Generate valid user registration data."""
    data = {
        "email": f"user_{uuid4().hex[:8]}@example.com",
        "password": "SecurePass123!",
        "full_name": random.choice(["Shreya", "Arjun", "Priya", "Rahul", "Ananya"]),
        "timezone": random.choice(["UTC", "Asia/Kolkata", "America/New_York"]),
    }
    if overrides:
        data.update(overrides)
    return data


def make_habit_data(overrides: dict | None = None) -> dict:
    """Generate valid habit creation data."""
    templates = [
        {"name": "Water Intake", "habit_type": "numeric", "unit": "glasses",
         "target_value": 8, "icon": "💧", "color": "#3B82F6"},
        {"name": "Sleep Hours", "habit_type": "numeric", "unit": "hours",
         "target_value": 7.5, "icon": "😴", "color": "#8B5CF6"},
        {"name": "Exercise", "habit_type": "boolean", "unit": "",
         "target_value": None, "icon": "🏃", "color": "#10B981"},
        {"name": "Mood", "habit_type": "scale", "unit": "",
         "target_value": None, "icon": "😊", "color": "#F59E0B"},
        {"name": "Reading", "habit_type": "numeric", "unit": "minutes",
         "target_value": 30, "icon": "📖", "color": "#EC4899"},
    ]
    data = random.choice(templates).copy()
    data["name"] = f"{data['name']} {uuid4().hex[:4]}"
    if overrides:
        data.update(overrides)
    return data


def make_log_data(
    habit_id: str, habit_type: str,
    log_date: str | None = None, overrides: dict | None = None,
) -> dict:
    """Generate valid log creation data matching the habit type."""
    data: dict = {
        "habit_id": habit_id,
        "log_date": log_date or str(date.today()),
    }
    if habit_type == "numeric":
        data["value_numeric"] = round(random.uniform(1, 10), 1)
    elif habit_type == "boolean":
        data["value_boolean"] = random.choice([True, False])
    elif habit_type == "scale":
        data["value_scale"] = random.randint(1, 10)
    if overrides:
        data.update(overrides)
    return data


def make_bulk_log_data(habits: list[dict], log_date: str | None = None) -> dict:
    """Generate bulk log data for multiple habits."""
    entries = []
    for h in habits:
        entry: dict = {"habit_id": h["id"]}
        if h["habit_type"] == "numeric":
            entry["value_numeric"] = round(random.uniform(1, 10), 1)
        elif h["habit_type"] == "boolean":
            entry["value_boolean"] = True
        elif h["habit_type"] == "scale":
            entry["value_scale"] = random.randint(1, 10)
        entries.append(entry)
    return {"log_date": log_date or str(date.today()), "entries": entries}
```

### Why Factories (Not Hardcoded Dicts)

```python
# WITHOUT factory — 15 lines per test, brittle:
data = {
    "name": "Water Intake",
    "habit_type": "numeric",
    "unit": "glasses",
    "target_value": 8,
    "color": "#3B82F6",
    "icon": "💧",
}

# WITH factory — 1 line, readable, unique:
data = make_habit_data({"habit_type": "numeric"})
```

**`uuid4().hex[:8]`** — Each call generates a unique suffix (`"a3f2b1c9"`). No two test users or habits have the same name. This prevents unique constraint violations when tests run in parallel.

**`overrides` pattern** — Defaults handle the common case. Tests override only what matters: `make_user_data({"password": "short"})` tests password validation without specifying every other field.

---

## 4. Mock Files (3 Files)

### 4.1 `tests/mocks/mock_email_provider.py`

```python
# Mock email provider — captures sent emails for assertion

from dataclasses import dataclass, field


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


class MockEmailProvider:
    """Fake email provider that stores emails in a list for testing."""

    def __init__(self):
        self.sent_emails: list[SentEmail] = []

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        self.sent_emails.append(SentEmail(to=to_email, subject=subject, body=html_body))
        return True

    @property
    def last_email(self) -> SentEmail | None:
        return self.sent_emails[-1] if self.sent_emails else None

    @property
    def email_count(self) -> int:
        return len(self.sent_emails)
```

**Usage in tests:**
```python
mock_email = MockEmailProvider()
await notification_service.send_daily_reminder(user, provider=mock_email)
assert mock_email.email_count == 1
assert "streaks alive" in mock_email.last_email.body
```

### 4.2 `tests/mocks/mock_llm_client.py`

```python
# Mock LLM client — returns deterministic responses for testing

from typing import AsyncGenerator
from app.modules.ai.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse, ToolCall


class MockLLMClient(BaseLLMClient):
    """
    Fake LLM for testing — no API calls, deterministic responses.

    Usage in tests:
        mock_llm = MockLLMClient(response_text="Your sleep averaged 7 hours")
        agent = BaseAgent(llm=mock_llm, tools=[], system_prompt="...")
        result = await agent.run("How's my sleep?")
        assert "7 hours" in result
    """

    def __init__(
        self,
        response_text: str = "This is a mock AI response.",
        tool_calls: list[ToolCall] | None = None,
    ):
        self.response_text = response_text
        self.tool_calls = tool_calls or []
        self.call_count = 0
        self.last_messages: list[LLMMessage] = []

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_messages = messages

        # First call returns tool calls (if any), subsequent calls return text
        if self.tool_calls and self.call_count == 1:
            return LLMResponse(
                content="",
                tool_calls=self.tool_calls,
                input_tokens=100,
                output_tokens=50,
                model="mock-model",
            )

        return LLMResponse(
            content=self.response_text,
            tool_calls=[],
            input_tokens=100,
            output_tokens=50,
            model="mock-model",
        )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        for word in self.response_text.split():
            yield word + " "

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(i % 10) / 10 for i in range(768)] for _ in texts]
```

**Why MockLLMClient extends `BaseLLMClient`:** It implements the same interface as OllamaClient, GroqClient, and OpenAIClient. The agent code doesn't know it's talking to a mock. This is the Strategy pattern working for testing — swap the real LLM with a fake that returns controlled responses.

**`self.call_count`** — Tracks how many times the LLM was called. For agent tests: first call returns a tool call, second call returns the final answer. This simulates the ReAct loop.

### 4.3 `tests/mocks/mock_storage.py`

```python
# Mock S3/MinIO storage — stores files in memory

class MockStorageProvider:
    """In-memory file storage for testing — no real S3/MinIO needed."""

    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload_file(self, key: str, content: bytes, content_type: str = "") -> str:
        self.files[key] = content
        return key

    async def download_file(self, key: str) -> bytes:
        if key not in self.files:
            raise FileNotFoundError(f"Key not found: {key}")
        return self.files[key]

    async def get_presigned_url(self, key: str, expires_in: int = 86400) -> str:
        return f"https://mock-s3.local/{key}?expires={expires_in}"

    async def delete_file(self, key: str) -> None:
        self.files.pop(key, None)

    async def ensure_bucket_exists(self) -> None:
        pass
```

**`self.files: dict[str, bytes]`** — A Python dict replaces S3. Upload stores bytes, download retrieves them, delete removes the key. Tests can verify file content was uploaded correctly without any AWS credentials.

---

## 5. `pyproject.toml` — pytest Configuration

```toml
# ── Pytest ──
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-v",                             # Verbose output (show test names)
    "--tb=short",                     # Short traceback on failure
    "--strict-markers",               # Error if unknown markers used
]
markers = [
    "unit: Unit tests (no external dependencies)",
    "integration: Integration tests (needs DB + Redis)",
    "slow: Slow tests (AI calls, large data)",
]
asyncio_mode = "auto"

# ── Coverage ──
[tool.coverage.run]
source = ["app"]
omit = ["app/tasks/*", "alembic/*"]

[tool.coverage.report]
show_missing = true
fail_under = 70
```

**`asyncio_mode = "auto"`** — Automatically detects `async def test_*` functions and runs them with asyncio. Without this, every async test would need `@pytest.mark.asyncio` explicitly.

**`fail_under = 70`** — CI fails if test coverage drops below 70%. This prevents merging code that isn't tested.

---

## 6. Running Tests

```bash
# Start test databases (different ports to avoid conflicts)
docker-compose -f docker-compose.test.yml up -d

# Run all tests
cd backend && python -m pytest -v

# Run only unit tests (no DB needed)
python -m pytest tests/unit -v

# Run only integration tests
python -m pytest tests/integration -v

# Run with coverage report
python -m pytest --cov=app --cov-report=html

# Or use the Makefile shortcuts
make test          # Full suite with test DB
make test-unit     # Unit tests only
make test-int      # Integration tests only
```

---

## 7. What You Learned

| # | Concept | Where |
|---|---------|-------|
| 1 | **Test pyramid** | Unit (many, fast) → Integration (fewer) → E2E (few, slow) |
| 2 | **pytest fixtures** | conftest.py — reusable setup/teardown with dependency injection |
| 3 | **Fixture scopes** | session (once) vs function (per-test) |
| 4 | **`dependency_overrides`** | Swap real DB session with test session |
| 5 | **`ASGITransport`** | In-process HTTP client — no real server needed |
| 6 | **`await session.rollback()`** | Test isolation — undo changes after each test |
| 7 | **Factory pattern** | Generate unique test data with defaults + overrides |
| 8 | **Mock objects** | Replace external services (LLM, email, S3) with fakes |
| 9 | **Strategy pattern in testing** | MockLLMClient implements BaseLLMClient interface |
| 10 | **`asyncio_mode = "auto"`** | Auto-detect async tests without manual markers |

---

## 8. Interview Questions

### Q1: "How do you ensure test isolation?"

**A:** Three mechanisms: (1) Each test gets its own database session via the `db_session` fixture, and `await session.rollback()` undoes all changes after the test. (2) Factory functions generate unique data (`uuid4()` in emails/names) so tests don't conflict. (3) FastAPI's `dependency_overrides` routes all API calls to the test database. Tests can run in any order without affecting each other.

### Q2: "Why mock the LLM instead of calling it?"

**A:** Real LLM calls are slow (2-5 seconds), non-deterministic (different responses each time), and expensive (token costs). Unit tests need to run in under 5 seconds and produce the same result every time. MockLLMClient returns controlled responses — we test that the agent LOOP works correctly (tool calling, memory, iteration limits), not that the LLM generates good text. LLM output quality is tested separately via integration tests or manual review.

### Q3: "What's the difference between `pytest.fixture` and `pytest_asyncio.fixture`?"

**A:** `pytest_asyncio.fixture` is needed for fixtures that use `async/await`. Our database session and HTTP client are async (SQLAlchemy async, httpx async), so they need `pytest_asyncio.fixture`. The `event_loop` fixture uses regular `pytest.fixture` because it creates the loop synchronously. Without `pytest_asyncio.fixture`, async fixtures would raise "coroutine was never awaited" errors.

---

## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 16g: Frontend Flows](./phase4-part16g-frontend-entry-routing-flows.md) |
| ➡️ Next | [Phase 5 Part 02: Unit Tests](./phase5-part02-unit-tests.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**End of Phase 5 Part 01: Testing Overview & Infrastructure**
