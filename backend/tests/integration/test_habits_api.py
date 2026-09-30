# ============================================================================
# Integration Tests — Habits API
# ============================================================================

import pytest
from httpx import AsyncClient

from tests.factories import make_habit_data


@pytest.mark.asyncio
class TestCreateHabit:
    async def test_create_numeric_habit(self, client: AsyncClient, auth_headers: dict):
        """Create a numeric habit returns 201 with full habit data."""
        data = make_habit_data({"habit_type": "numeric", "unit": "glasses", "target_value": 8})
        response = await client.post("/api/v1/habits", headers=auth_headers, json=data)

        assert response.status_code == 201
        body = response.json()
        assert body["habit_type"] == "numeric"
        assert body["unit"] == "glasses"
        assert body["target_value"] == 8
        assert body["is_archived"] is False
        assert "id" in body

    async def test_create_boolean_habit(self, client: AsyncClient, auth_headers: dict):
        data = make_habit_data({"habit_type": "boolean"})
        response = await client.post("/api/v1/habits", headers=auth_headers, json=data)
        assert response.status_code == 201
        assert response.json()["habit_type"] == "boolean"

    async def test_create_scale_habit(self, client: AsyncClient, auth_headers: dict):
        data = make_habit_data({"habit_type": "scale"})
        response = await client.post("/api/v1/habits", headers=auth_headers, json=data)
        assert response.status_code == 201
        assert response.json()["habit_type"] == "scale"

    async def test_create_requires_auth(self, client: AsyncClient):
        """Creating a habit without auth returns error."""
        response = await client.post("/api/v1/habits", json=make_habit_data())
        assert response.status_code in (401, 422)


@pytest.mark.asyncio
class TestListHabits:
    async def test_list_habits_empty(self, client: AsyncClient, auth_headers: dict):
        """New user has no habits."""
        response = await client.get("/api/v1/habits", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_habits_after_create(self, client: AsyncClient, auth_headers: dict):
        """Created habits appear in the list."""
        await client.post("/api/v1/habits", headers=auth_headers, json=make_habit_data())
        await client.post("/api/v1/habits", headers=auth_headers, json=make_habit_data())

        response = await client.get("/api/v1/habits", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2


@pytest.mark.asyncio
class TestUpdateHabit:
    async def test_update_habit_name(self, client: AsyncClient, auth_headers: dict):
        """Update habit name."""
        create_res = await client.post("/api/v1/habits", headers=auth_headers, json=make_habit_data())
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
    async def test_archive_habit(self, client: AsyncClient, auth_headers: dict):
        """Deleting a habit archives it (soft delete)."""
        create_res = await client.post("/api/v1/habits", headers=auth_headers, json=make_habit_data())
        habit_id = create_res.json()["id"]

        response = await client.delete(f"/api/v1/habits/{habit_id}", headers=auth_headers)
        assert response.status_code == 200
        assert "archived" in response.json()["message"].lower()

        # Habit should not appear in default list
        list_res = await client.get("/api/v1/habits", headers=auth_headers)
        habit_ids = [h["id"] for h in list_res.json()]
        assert habit_id not in habit_ids
