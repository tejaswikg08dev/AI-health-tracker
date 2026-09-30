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
