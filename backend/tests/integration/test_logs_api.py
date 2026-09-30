# ============================================================================
# Integration Tests — Logs API
# ============================================================================

import pytest
from httpx import AsyncClient
from datetime import date

from tests.factories import make_habit_data, make_log_data


@pytest.mark.asyncio
class TestCreateLog:
    async def _create_habit(self, client: AsyncClient, auth_headers: dict, habit_type: str = "numeric") -> dict:
        """Helper: create a habit and return its data."""
        data = make_habit_data({"habit_type": habit_type})
        res = await client.post("/api/v1/habits", headers=auth_headers, json=data)
        return res.json()

    async def test_create_numeric_log(self, client: AsyncClient, auth_headers: dict):
        """Log a numeric value for a habit."""
        habit = await self._create_habit(client, auth_headers, "numeric")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_numeric": 8.0,
        }
        response = await client.post("/api/v1/logs", headers=auth_headers, json=log_data)

        assert response.status_code == 201
        body = response.json()
        assert body["value_numeric"] == 8.0
        assert body["habit_id"] == habit["id"]

    async def test_create_boolean_log(self, client: AsyncClient, auth_headers: dict):
        habit = await self._create_habit(client, auth_headers, "boolean")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_boolean": True,
        }
        response = await client.post("/api/v1/logs", headers=auth_headers, json=log_data)
        assert response.status_code == 201
        assert response.json()["value_boolean"] is True

    async def test_create_scale_log(self, client: AsyncClient, auth_headers: dict):
        habit = await self._create_habit(client, auth_headers, "scale")
        log_data = {
            "habit_id": habit["id"],
            "log_date": str(date.today()),
            "value_scale": 7,
        }
        response = await client.post("/api/v1/logs", headers=auth_headers, json=log_data)
        assert response.status_code == 201
        assert response.json()["value_scale"] == 7

    async def test_reject_future_date(self, client: AsyncClient, auth_headers: dict):
        """Cannot log for a future date."""
        habit = await self._create_habit(client, auth_headers)
        log_data = {
            "habit_id": habit["id"],
            "log_date": "2099-12-31",
            "value_numeric": 5,
        }
        response = await client.post("/api/v1/logs", headers=auth_headers, json=log_data)
        assert response.status_code == 422
        assert "future" in response.json()["message"].lower()


@pytest.mark.asyncio
class TestGetLogs:
    async def test_get_logs_by_date(self, client: AsyncClient, auth_headers: dict):
        """Get logs for a specific date."""
        today = str(date.today())
        response = await client.get(
            "/api/v1/logs",
            headers=auth_headers,
            params={"date": today},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_logs_default_today(self, client: AsyncClient, auth_headers: dict):
        """No date param defaults to today."""
        response = await client.get("/api/v1/logs", headers=auth_headers)
        assert response.status_code == 200


@pytest.mark.asyncio
class TestBulkLog:
    async def test_bulk_create(self, client: AsyncClient, auth_headers: dict):
        """Bulk create logs for multiple habits."""
        # Create two habits
        h1 = make_habit_data({"habit_type": "numeric"})
        h2 = make_habit_data({"habit_type": "boolean"})
        r1 = await client.post("/api/v1/habits", headers=auth_headers, json=h1)
        r2 = await client.post("/api/v1/habits", headers=auth_headers, json=h2)

        bulk_data = {
            "log_date": str(date.today()),
            "entries": [
                {"habit_id": r1.json()["id"], "value_numeric": 8},
                {"habit_id": r2.json()["id"], "value_boolean": True},
            ],
        }

        response = await client.post("/api/v1/logs/bulk", headers=auth_headers, json=bulk_data)
        assert response.status_code == 201
        assert len(response.json()) == 2
