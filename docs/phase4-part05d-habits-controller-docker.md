# 📊 Phase 4 Part 05d: Habits — Router

> **"Every endpoint in this router is 3-5 lines. Parse the request, call the service, format the response. That's it. If your route handler is more than 10 lines, you've put business logic in the wrong place."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 05d (Habits HTTP Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.1 — Habit Management |
| **Previous** | [phase4-part05c-habits-service-tests.md](./phase4-part05c-habits-service-tests.md) |
| **Next** | [phase4-part05e-habits-connections-and-flows.md](./phase4-part05e-habits-connections-and-flows.md) |
| **Files in This Doc** | 1 file (router.py) — 6 endpoints |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (path parameters, query parameters, list responses, reuse of auth dependency) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File: router.py — Full Source Code](#router)
3. [Endpoint-by-Endpoint Walkthrough](#walkthrough)
4. [What's New Compared to Auth Router](#whats-new)
5. [How to Verify Your Work](#verify)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

The Habits router is the HTTP layer — 6 thin endpoints that translate HTTP requests into service calls. The key difference from Auth's router: every endpoint uses `get_current_user_id` from the **Auth module** — demonstrating cross-module dependency.

### Endpoint Summary

| # | Method | Path | Auth | What It Does |
|---|--------|------|:----:|-------------|
| 1 | `POST` | `/api/v1/habits` | ✅ | Create a habit |
| 2 | `GET` | `/api/v1/habits` | ✅ | List all habits |
| 3 | `PUT` | `/api/v1/habits/reorder` | ✅ | Reorder dashboard |
| 4 | `GET` | `/api/v1/habits/{habit_id}` | ✅ | Get one habit |
| 5 | `PUT` | `/api/v1/habits/{habit_id}` | ✅ | Update a habit |
| 6 | `DELETE` | `/api/v1/habits/{habit_id}` | ✅ | Archive a habit |

### Route Ordering Matters

Notice `PUT /habits/reorder` is defined BEFORE `GET /habits/{habit_id}`. This is important — FastAPI matches routes in definition order. If `{habit_id}` came first, a request to `/habits/reorder` would match `{habit_id}` with the string "reorder" and fail.

---

<a name="router"></a>
## 2. File: `router.py` — Full Source Code

### Type This Code: `backend/app/modules/habits/router.py`

```python
# ============================================================================
# Habits Module — Router (API Endpoints)
# ============================================================================
# ENDPOINTS:
#   POST   /api/v1/habits           → Create a new habit
#   GET    /api/v1/habits           → List user's habits
#   GET    /api/v1/habits/:id       → Get a single habit
#   PUT    /api/v1/habits/:id       → Update a habit
#   DELETE /api/v1/habits/:id       → Archive (soft delete) a habit
#   PUT    /api/v1/habits/reorder   → Reorder habits
#
# ALL ENDPOINTS REQUIRE AUTHENTICATION (get_current_user_id dependency).
# A user can ONLY access their own habits.
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.auth.router import get_current_user_id
from app.modules.habits.schemas import (
    HabitCreate,
    HabitReorderRequest,
    HabitResponse,
    HabitUpdate,
)
from app.modules.habits.service import HabitService
from app.shared.base_schemas import SuccessResponse

router = APIRouter()


# ── Dependency: Get Habit Service ──
async def get_habit_service(
    session: AsyncSession = Depends(get_async_session),
) -> HabitService:
    return HabitService(session)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "",
    response_model=HabitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new habit",
)
async def create_habit(
    data: HabitCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> HabitResponse:
    """
    Create a new trackable habit.

    - Validates habit type (numeric, boolean, scale)
    - Checks for duplicate names
    - Enforces maximum 20 active habits
    - Assigns next display order automatically

    After creating, the habit appears on the dashboard and daily check-in page.
    """
    habit = await service.create_habit(user_id, data)
    return HabitResponse.model_validate(habit)


@router.get(
    "",
    response_model=list[HabitResponse],
    summary="List user's habits",
)
async def list_habits(
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
    include_archived: bool = Query(
        default=False,
        description="Include archived habits (for settings page)",
    ),
) -> list[HabitResponse]:
    """
    Get all habits for the current user.

    Returns active habits ordered by sort_order (user's preferred display order).
    Pass include_archived=true to also see archived habits.
    """
    habits = await service.get_habits(user_id, include_archived)
    return [HabitResponse.model_validate(h) for h in habits]


@router.put(
    "/reorder",
    response_model=list[HabitResponse],
    summary="Reorder habits",
)
async def reorder_habits(
    data: HabitReorderRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> list[HabitResponse]:
    """
    Reorder habits on the dashboard.

    Send the habit IDs in the desired order.
    The position in the array becomes the new sort_order.

    Called after drag-and-drop on the frontend.
    """
    habits = await service.reorder_habits(user_id, data.habit_ids)
    return [HabitResponse.model_validate(h) for h in habits]


@router.get(
    "/{habit_id}",
    response_model=HabitResponse,
    summary="Get a single habit",
)
async def get_habit(
    habit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> HabitResponse:
    """
    Get detailed information about a single habit.

    Returns 404 if the habit doesn't exist or belongs to another user.
    """
    habit = await service.get_habit(user_id, habit_id)
    return HabitResponse.model_validate(habit)


@router.put(
    "/{habit_id}",
    response_model=HabitResponse,
    summary="Update a habit",
)
async def update_habit(
    habit_id: UUID,
    data: HabitUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> HabitResponse:
    """
    Update a habit's properties.

    Only provided fields are updated (partial update).
    Note: habit_type cannot be changed after creation.
    """
    habit = await service.update_habit(user_id, habit_id, data)
    return HabitResponse.model_validate(habit)


@router.delete(
    "/{habit_id}",
    response_model=SuccessResponse,
    summary="Archive (soft delete) a habit",
)
async def delete_habit(
    habit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> SuccessResponse:
    """
    Archive a habit (soft delete).

    The habit is hidden from the dashboard but its data is preserved.
    Historical analytics that reference this habit still work.
    """
    habit = await service.delete_habit(user_id, habit_id)
    return SuccessResponse(message=f"Habit '{habit.name}' archived successfully")
```

---

<a name="walkthrough"></a>
## 3. Endpoint-by-Endpoint Walkthrough

### Cross-Module Import

```python
from app.modules.auth.router import get_current_user_id
```
- This is the **cross-module dependency** — the Habits module imports the auth dependency
- Every endpoint uses `user_id: UUID = Depends(get_current_user_id)`
- The Auth module is the ONLY module imported by Habits — clean dependency direction

### Habit Service Dependency — Simpler Than Auth

```python
async def get_habit_service(
    session: AsyncSession = Depends(get_async_session),
) -> HabitService:
    return HabitService(session)
```
- Only needs `session` — no Redis (habits don't use caching or blacklisting)
- Compare with Auth's dependency: `get_auth_service(session, redis_client)` — auth needs Redis for tokens

### POST `/habits` — Create

```python
@router.post("", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
async def create_habit(
    data: HabitCreate,
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
) -> HabitResponse:
    habit = await service.create_habit(user_id, data)
    return HabitResponse.model_validate(habit)
```
- `""` as path — means the bare prefix (`/api/v1/habits`). No trailing slash
- `data: HabitCreate` — Pydantic validates the JSON body (name, habit_type, etc.)
- `user_id` — extracted from JWT by the auth dependency. The habit is created for THIS user
- `HabitResponse.model_validate(habit)` — converts SQLAlchemy Habit to Pydantic response

### GET `/habits` — List with Query Parameter

```python
@router.get("", response_model=list[HabitResponse])
async def list_habits(
    user_id: UUID = Depends(get_current_user_id),
    service: HabitService = Depends(get_habit_service),
    include_archived: bool = Query(default=False, description="Include archived habits"),
) -> list[HabitResponse]:
    habits = await service.get_habits(user_id, include_archived)
    return [HabitResponse.model_validate(h) for h in habits]
```
- `response_model=list[HabitResponse]` — returns a LIST of habits (not a single one)
- `Query(default=False)` — reads from the URL query string: `GET /habits?include_archived=true`
- `[HabitResponse.model_validate(h) for h in habits]` — list comprehension: converts each SQLAlchemy Habit to Pydantic. This is different from auth where we return a single object

**What is `Query()`?**
- Extracts parameters from the URL query string (after the `?`)
- `GET /habits?include_archived=true&page=2`
- `Query(default=False)` — if not provided, defaults to `False`
- Shows in Swagger docs as a parameter with a checkbox

### PUT `/habits/reorder` — BEFORE `/{habit_id}`

```python
@router.put("/reorder", response_model=list[HabitResponse])
async def reorder_habits(data: HabitReorderRequest, ...):
```
- **Route order matters:** This is defined BEFORE `/{habit_id}`. If `/{habit_id}` came first, FastAPI would try to parse `"reorder"` as a UUID — and fail with a 422 error
- Takes `HabitReorderRequest` body: `{"habit_ids": ["uuid1", "uuid2", "uuid3"]}`
- Returns the full updated habit list so the frontend can verify the new order

### GET `/habits/{habit_id}` — Path Parameter

```python
@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(
    habit_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    ...
):
```
- `{habit_id}` — a **path parameter**. FastAPI extracts it from the URL: `GET /habits/550e8400-...`
- `habit_id: UUID` — FastAPI auto-converts the string to a Python `UUID`. If the string isn't a valid UUID, Pydantic returns 422
- Both `habit_id` (from URL) and `user_id` (from JWT) are passed to the service — ensuring ownership

### DELETE `/habits/{habit_id}` — Archive with Message

```python
@router.delete("/{habit_id}", response_model=SuccessResponse)
async def delete_habit(habit_id: UUID, ...):
    habit = await service.delete_habit(user_id, habit_id)
    return SuccessResponse(message=f"Habit '{habit.name}' archived successfully")
```
- The service returns the archived habit object — we use `habit.name` to build a friendly message
- `SuccessResponse` (from shared schemas) = `{"message": "Habit 'Water Intake' archived successfully"}`
- The HTTP method is DELETE but the implementation is soft delete — the client doesn't need to know

---

<a name="whats-new"></a>
## 4. What's New Compared to Auth Router

| Feature | Auth Router | Habits Router |
|---------|-------------|---------------|
| Auth dependency | Defines `get_current_user_id` | Imports it from auth |
| Service dependency | Needs session + Redis | Needs session only |
| Path parameters | None | `{habit_id}` on 3 endpoints |
| Query parameters | None | `include_archived` on list |
| List response | None | `list[HabitResponse]` on 2 endpoints |
| Route ordering | No conflicts | `/reorder` must come before `/{habit_id}` |
| f-string in response | None | `f"Habit '{habit.name}' archived"` |
| List comprehension | None | `[HabitResponse.model_validate(h) for h in habits]` |

### Registration in main.py

The habits router is already registered in `main.py` (Part 04d):

```python
# In _register_routers():
from app.modules.habits.router import router as habits_router
app.include_router(habits_router, prefix="/api/v1/habits", tags=["Habits"])
```

No changes needed to main.py — it was set up to include all module routers.

---

<a name="verify"></a>
## 5. How to Verify Your Work

```bash
# 1. Login first (get a token)
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}' | jq -r '.access_token')

# 2. Create a habit
curl -X POST http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Water Intake","habit_type":"numeric","unit":"glasses","target_value":8,"color":"#3B82F6","icon":"💧"}'
# Expected: 201 with habit data

# 3. Create another habit
curl -X POST http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Sleep Hours","habit_type":"numeric","unit":"hours","target_value":7}'

# 4. List habits
curl http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 with array of 2 habits, ordered by sort_order

# 5. Test duplicate name
curl -X POST http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Water Intake","habit_type":"boolean"}'
# Expected: 409 DUPLICATE_HABIT_NAME

# 6. Archive a habit
curl -X DELETE http://localhost/api/v1/habits/HABIT_ID \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 "Habit 'Water Intake' archived successfully"

# 7. Verify archived is hidden
curl http://localhost/api/v1/habits \
  -H "Authorization: Bearer $TOKEN"
# Expected: only 1 habit (archived one hidden)

# 8. Include archived
curl "http://localhost/api/v1/habits?include_archived=true" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 2 habits (including archived one)

# 9. Check Swagger docs
# Open http://localhost/docs — "Habits" section should show all 6 endpoints
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Cross-module dependency** | Importing `get_current_user_id` from Auth module | All endpoints |
| 2 | **Path parameters** | `/{habit_id}` — UUID extracted from URL | GET/PUT/DELETE by ID |
| 3 | **`Query()` parameter** | Extract value from URL query string (`?key=value`) | `include_archived` |
| 4 | **`list[HabitResponse]`** | Returning an array of objects | List + reorder |
| 5 | **List comprehension for response** | `[Model.validate(h) for h in habits]` | List + reorder |
| 6 | **Route definition order** | Static routes (`/reorder`) before dynamic (`/{id}`) | Prevents matching conflicts |
| 7 | **f-string in response** | Dynamic success message with habit name | Delete endpoint |
| 8 | **`""` as route path** | Bare prefix path — no trailing content | POST + GET list |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: Why does `PUT /reorder` come before `GET /{habit_id}` in the route definitions?
**A:** "FastAPI matches routes in definition order. If `/{habit_id}` were defined first, a request to `/habits/reorder` would match with `habit_id='reorder'`. FastAPI would try to parse 'reorder' as a UUID and fail with a 422 error. By placing the static route `/reorder` first, it matches exactly. The dynamic `/{habit_id}` only matches requests that didn't match earlier routes. This is the same in Flask, Express, and most web frameworks."

### Q2: How does the Habits module reuse the Auth module's authentication?
**A:** "The Habits router imports `get_current_user_id` from `app.modules.auth.router`. Every endpoint declares `user_id: UUID = Depends(get_current_user_id)` as a parameter. FastAPI automatically calls this dependency function — which decodes the JWT, verifies the signature, checks the Redis blacklist, and returns the user_id — before the endpoint handler runs. If the token is invalid, the handler never executes. This is the only cross-module import — clean dependency direction from Habits → Auth."

### Q3: What is the difference between path parameters and query parameters?
**A:** "Path parameters are part of the URL path: `/habits/{habit_id}` — the habit_id is required and identifies a specific resource. Query parameters come after the `?`: `/habits?include_archived=true` — they're optional filters or modifiers. In REST conventions, path parameters identify resources, query parameters filter or paginate them. FastAPI auto-extracts both and validates their types."

### Q4: Why return `list[HabitResponse]` instead of a paginated response?
**A:** "Users have at most 20 habits (our limit), so pagination is unnecessary. Returning a simple array keeps the API clean for this small, bounded dataset. The Logs module, which can have thousands of entries, uses `PaginatedResponse[LogResponse]` with page/page_size parameters. The right approach depends on the data size — small bounded sets get simple arrays, large unbounded sets get pagination."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 05c: Habits Service](./phase4-part05c-habits-service-tests.md) |
| ➡️ Next | [Phase 4 Part 05e: Habits Connections & Flows](./phase4-part05e-habits-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Habits Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 05a | ✅ Done | Habits Models, Exceptions, Schemas & Migration |
| 05b | ✅ Done | Habits Repository |
| 05c | ✅ Done | Habits Service |
| **05d** | ✅ **You are here** | Habits Router |
| 05e | ⬜ Next | Habits Connections & Flows |

---

**End of Phase 4 Part 05d: Habits Router**

*All 6 habits endpoints are live. Users can create, list, get, update, archive, and reorder habits. Next: the final Habits doc — flow diagrams showing how everything connects.*
