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
        # First signup
        await client.post("/api/v1/auth/signup", json=data)
        # Duplicate
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
        """Login with unregistered email returns 401 (same as wrong password)."""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "anyPassword123",
        })
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProfile:
    async def test_get_profile_authenticated(self, client: AsyncClient, auth_headers: dict):
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

    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """User can update their profile."""
        response = await client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"},
        )

        assert response.status_code == 200
        assert response.json()["full_name"] == "Updated Name"
