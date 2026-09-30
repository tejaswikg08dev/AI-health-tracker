# 🧪 Phase 5 Part 03: Integration Tests

> **"Three integration test files that hit the real API with a real test database: auth (signup, login, profile — 10 tests), habits (CRUD — 7 tests), logs (create, bulk, list — 7 tests). Each test uses the `client` and `auth_headers` fixtures from conftest.py."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase5-part02-unit-tests.md](./phase5-part02-unit-tests.md) |
| **Next** | [Phase 6: Docker Deep Dive](./phase6-part01-docker-deep-dive.md) |
| **Files in This Doc** | 3 integration test files |
| **Time to Type** | ~40 minutes |
| **Difficulty** | Medium (real HTTP calls, status code assertions, factory usage) |

---

## 1. `tests/integration/test_auth_api.py` — Signup, Login, Profile

### Type This Code:

```python
# ============================================================================
# Integration Tests — Auth API
# ============================================================================
# Tests the full HTTP request/response cycle for auth endpoints.
# Uses a real test database (via conftest.py fixtures).
# ============================================================================

import pytest
from httpx import AsyncClient

from tests.factories import make_user_data


@pytest.mark.asyncio
class TestSignup:
    async def test_signup_success(self, client: AsyncClient):
        """Successful signup returns user data with 201."""
        data = make_user_data()
        response = await client.post("/api/v1/auth/signup", json=data)

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == data["email"]
        assert body["full_name"] == data["full_name"]
        assert "id" in body
        # Password should NEVER be in the response
        assert "password" not in body
        assert "password_hash" not in body

    async def test_signup_duplicate_email(self, client: AsyncClient):
        """Signing up with an existing email returns 409."""
        data = make_user_data()
        await client.post("/api/v1/auth/signup", json=data)
        response = await client.post("/api/v1/auth/signup", json=data)

        assert response.status_code == 409
        assert response.json()["error_code"] == "EMAIL_ALREADY_EXISTS"

    async def test_signup_short_password(self, client: AsyncClient):
        """Password shorter than 8 chars returns 422."""
        data = make_user_data({"password": "short"})
        response = await client.post("/api/v1/auth/signup", json=data)
        assert response.status_code == 422

    async def test_signup_invalid_email(self, client: AsyncClient):
        """Invalid email format returns 422."""
        data = make_user_data({"email": "not-an-email"})
        response = await client.post("/api/v1/auth/signup", json=data)
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        """Successful login returns access and refresh tokens."""
        data = make_user_data()
        await client.post("/api/v1/auth/signup", json=data)

        response = await client.post("/api/v1/auth/login", json={
            "email": data["email"],
            "password": data["password"],
        })

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Wrong password returns 401."""
        data = make_user_data()
        await client.post("/api/v1/auth/signup", json=data)

        response = await client.post("/api/v1/auth/login", json={
            "email": data["email"],
            "password": "wrongPassword123",
        })

        assert response.status_code == 401
        assert response.json()["error_code"] == "INVALID_CREDENTIALS"

    async def test_login_nonexistent_email(self, client: AsyncClient):
        """Login with unregistered email returns 401."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "anyPassword123",
        })
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProfile:
    async def test_get_profile_authenticated(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Authenticated user can get their profile."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert "email" in body
        assert "full_name" in body
        assert "password_hash" not in body

    async def test_get_profile_no_token(self, client: AsyncClient):
        """Unauthenticated request returns 401 or 422."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code in (401, 422)

    async def test_update_profile(
        self, client: AsyncClient, auth_headers: dict
    ):
        """User can update their profile."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
```

### Key Patterns

**`client: AsyncClient` as a parameter** — pytest sees this and automatically calls the `client` fixture from conftest.py. The fixture creates an in-process HTTP client connected to the test database.

**Test both success AND failure paths:**
| Test | Status | What It Verifies |
|------|--------|-----------------|
| `test_signup_success` | 201 | Happy path works, password excluded from response |
| `test_signup_duplicate_email` | 409 | Unique constraint error handled properly |
| `test_signup_short_password` | 422 | Pydantic validation catches short passwords |
| `test_login_wrong_password` | 401 | Wrong password returns same error as nonexistent (security) |

**`assert "password_hash" not in body`** — Security test. The password hash should NEVER leak to the client. If a developer accidentally adds `password_hash` to the response schema, this test catches it.

---

## 2. `tests/integration/test_habits_api.py` — CRUD Habits

### Type This Code:

```python
# ============================================================================
# Integration Tests — Habits API
# ============================================================================

import pytest
from httpx import AsyncClient

from tests.factories import make_habit_data


@pytest.mark.asyncio
class TestCreateHabit:
    async def test_create_numeric_habit(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Create a numeric habit returns 201 with full habit data."""
        data = make_habit_data({
            "habit_type": "numeric", "unit": "glasses", "target_value": 8,
        })
        response = await client.post(
            "/api/v1/habits", headers=auth_headers, json=data,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["habit_type"] == "numeric"
        assert body["unit"] == "glasses"
        assert body["target_value"] == 8
        assert body["is_archived"] is False
        assert "id" in body

    async def test_create_boolean_habit(
        self, client: AsyncClient, auth_headers: dict
    ):
        data = make_habit_data({"habit_type": "boolean"})
        response = await client.post(
            "/api/v1/habits", headers=auth_headers, json=data,
        )
        assert response.status_code == 201
        assert response.json()["habit_type"] == "boolean"

    async def test_create_scale_habit(
        self, client: AsyncClient, auth_headers: dict
    ):
        data = make_habit_data({"habit_type": "scale"})
        response = await client.post(
            "/api/v1/habits", headers=auth_headers, json=data,
        )
        assert response.status_code == 201
        assert response.json()["habit_type"] == "scale"

    async def test_create_requires_auth(self, client: AsyncClient):
        """Creating a habit without auth returns error."""
        response = await client.post(
            "/api/v1/habits", json=make_habit_data(),
        )
        assert response.status_code in (401, 422)


@pytest.mark.asyncio
class TestListHabits:
    async def test_list_habits_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """New user has no habits."""
        response = await client.get("/api/v1/habits", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_habits_after_create(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Created habits appear in the list."""
        await client.post(
            "/api/v1/habits", headers=auth_headers, json=make_habit_data(),
        )
        await client.post(
            "/api/v1/habits", headers=auth_headers, json=make_habit_data(),
        )

        response = await client.get("/api/v1/habits", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


@pytest.mark.asyncio
class TestUpdateHabit:
    async def test_update_habit_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Update habit name."""
        create_res = await client.post(
            "/api/v1/habits", headers=auth_headers, json=make_habit_data(),
        )
        habit_id = create_res.json()["id"]

        response = await client.put(
            f"/api/v1/habits/{habit_id}",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
class TestDeleteHabit:
    async def test_archive_habit(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Deleting a habit archives it (soft delete)."""
        create_res = await client.post(
            "/api/v1/habits", headers=auth_headers, json=make_habit_data(),
        )
        habit_id = create_res.json()["id"]

        response = await client.delete(
            f"/api/v1/habits/{habit_id}", headers=auth_headers,
        )
        assert response.status_code == 200
        assert "archived" in response.json()["message"].lower()

        # Habit should not appear in default list
        list_res = await client.get("/api/v1/habits", headers=auth_headers)
        habit_ids = [h["id"] for h in list_res.json()]
        assert habit_id not in habit_ids
```

**`test_archive_habit`** — Tests the full soft-delete flow: create → delete → verify it's gone from the default list. This catches bugs where the archive flag isn't checked in the list query.

---

## 3. `tests/integration/test_logs_api.py` — Create & List Logs

### Type This Code:

```python
# ============================================================================
# Integration Tests — Logs API
# ============================================================================

import pytest
from httpx import AsyncClient
from datetime import date

from tests.factories import make_habit_data, make_log_data


@pytest.mark.asyncio
class TestCreateLog:
    async def _create_habit(
        self, client: AsyncClient, auth_headers: dict,
        habit_type: str = "numeric",
    ) -> dict:
        """Helper: create a habit and return its data."""
        data = make_habit_data({"habit_type": habit_type})
        res = await client.post(
            "/api/v1/habits", headers=auth_headers, json=data,
        )
        return res.json()

    async def test_create_numeric_log(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Log a numeric value for a habit."""
        habit = await self._create_habit(client, auth_headers, "numeric")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_numeric": 8.0,
        }
        response = await client.post(
            "/api/v1/logs", headers=auth_headers, json=log_data,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["value_numeric"] == 8.0
        assert body["habit_id"] == habit["id"]

    async def test_create_boolean_log(
        self, client: AsyncClient, auth_headers: dict
    ):
        habit = await self._create_habit(client, auth_headers, "boolean")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_boolean": True,
        }
        response = await client.post(
            "/api/v1/logs", headers=auth_headers, json=log_data,
        )
        assert response.status_code == 201
        assert response.json()["value_boolean"] is True

    async def test_create_scale_log(
        self, client: AsyncClient, auth_headers: dict
    ):
        habit = await self._create_habit(client, auth_headers, "scale")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_scale": 7,
        }
        response = await client.post(
            "/api/v1/logs", headers=auth_headers, json=log_data,
        )
        assert response.status_code == 201
        assert response.json()["value_scale"] == 7

    async def test_reject_future_date(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Cannot log for a future date."""
        habit = await self._create_habit(client, auth_headers)
        log_data = {
            "habit_id": habit["id"],
            "log_date": "2099-12-31",
            "value_numeric": 5,
        }
        response = await client.post(
            "/api/v1/logs", headers=auth_headers, json=log_data,
        )
        assert response.status_code == 422
        assert "future" in response.json()["message"].lower()


@pytest.mark.asyncio
class TestGetLogs:
    async def test_get_logs_by_date(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Get logs for a specific date."""
        today = str(date.today())
        response = await client.get(
            "/api/v1/logs", headers=auth_headers, params={"date": today},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_logs_default_today(
        self, client: AsyncClient, auth_headers: dict
    ):
        """No date param defaults to today."""
        response = await client.get("/api/v1/logs", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestBulkLog:
    async def test_bulk_create(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Bulk create logs for multiple habits."""
        h1 = make_habit_data({"habit_type": "numeric"})
        h2 = make_habit_data({"habit_type": "boolean"})
        r1 = await client.post(
            "/api/v1/habits", headers=auth_headers, json=h1,
        )
        r2 = await client.post(
            "/api/v1/habits", headers=auth_headers, json=h2,
        )

        bulk_data = {
            "log_date": str(date.today()),
            "entries": [
                {"habit_id": r1.json()["id"], "value_numeric": 8},
                {"habit_id": r2.json()["id"], "value_boolean": True},
            ],
        }

        response = await client.post(
            "/api/v1/logs/bulk", headers=auth_headers, json=bulk_data,
        )
        assert response.status_code == 201
        assert len(response.json()) == 2
```

### `_create_habit` Helper Pattern

```python
async def _create_habit(self, client, auth_headers, habit_type="numeric") -> dict:
    data = make_habit_data({"habit_type": habit_type})
    res = await client.post("/api/v1/habits", headers=auth_headers, json=data)
    return res.json()
```

Log tests need a habit to exist first. Instead of duplicating creation code in every test, `_create_habit` is a helper method (prefixed with `_` to indicate it's not a test itself). This is the **Arrange → Act → Assert** pattern: arrange (create habit), act (create log), assert (check response).

---

## 4. Test Summary Table

| File | Tests | What's Covered |
|------|-------|---------------|
| `test_auth_security.py` | 11 | bcrypt hash/verify, JWT create/decode, error cases |
| `test_date_utils.py` | 12 | timezone conversion, week/month boundaries, date ranges |
| `test_rag_chunker.py` | 7 | chunk splitting, overlap, page tracking, token count |
| `test_ai_agent.py` | 8 | ReAct loop, tool calling, max iterations, memory, unknown tools |
| `test_auth_api.py` | 10 | Signup (4), Login (3), Profile (3) |
| `test_habits_api.py` | 7 | Create (4), List (2), Update (1), Delete (1) — soft delete verified |
| `test_logs_api.py` | 7 | Create numeric/boolean/scale, reject future, get by date, bulk create |
| **Total** | **62** | All core flows covered |

---

## 5. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 5 Part 02: Unit Tests](./phase5-part02-unit-tests.md) |
| ➡️ Next | [Phase 6: Docker Deep Dive](./phase6-part01-docker-deep-dive.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |

---

**🎉 Phase 5 (Testing) is COMPLETE.**

*62 tests across 7 files: 4 unit test files (no DB, ~2 seconds), 3 integration test files (real API + test DB, ~10 seconds). Mocks replace LLM, email, and S3. Factories generate unique test data. conftest.py wires everything together with 6 fixtures. Next: Docker containerization.*
