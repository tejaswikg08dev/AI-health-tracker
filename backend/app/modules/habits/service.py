# ============================================================================
# Habits Module — Service Layer (Business Logic)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains all habit-related business logic.
#   Validates business rules before delegating to the repository.
#
# BUSINESS RULES:
#   - Maximum 20 active habits per user
#   - No duplicate habit names (per user)
#   - habit_type cannot change after creation (would break log data)
#   - "Delete" is actually soft-delete (archive)
#   - Reorder updates sort_order for all habits in the list
# ============================================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.exceptions import (
    DuplicateHabitNameError,
    HabitLimitExceededError,
    HabitNotFoundError,
)
from app.modules.habits.models import Habit
from app.modules.habits.repository import HabitRepository
from app.modules.habits.schemas import HabitCreate, HabitUpdate
from app.shared.logging import get_logger

logger = get_logger(__name__)


class HabitService:
    """
    Habit management service.

    Handles: creating habits with validation, updating, archiving,
    reordering, and listing with proper user scoping.
    """

    def __init__(self, session: AsyncSession):
        self.repo = HabitRepository(session)
        self.session = session

    async def create_habit(self, user_id: UUID, data: HabitCreate) -> Habit:
        """
        Create a new habit for the user.

        Validates:
        1. User hasn't exceeded the habit limit (20)
        2. No existing habit with the same name
        3. Assigns the next sort_order (goes at the end)

        Returns the created habit.
        """
        # Check habit limit
        active_count = await self.repo.count_active_habits(user_id)
        if active_count >= HabitLimitExceededError.MAX_HABITS:
            raise HabitLimitExceededError()

        # Check duplicate name
        if await self.repo.name_exists_for_user(user_id, data.name):
            raise DuplicateHabitNameError(data.name)

        # Get next sort order
        next_order = await self.repo.get_next_sort_order(user_id)

        # Create the habit
        habit = await self.repo.create(
            user_id=user_id,
            name=data.name,
            habit_type=data.habit_type.value,  # Enum → string for DB
            unit=data.unit,
            target_value=data.target_value,
            color=data.color,
            icon=data.icon,
            sort_order=next_order,
        )

        await self.session.commit()

        logger.info(
            "habit_created",
            user_id=str(user_id),
            habit_id=str(habit.id),
            habit_name=habit.name,
            habit_type=habit.habit_type,
        )
        return habit

    async def get_habits(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Habit]:
        """
        Get all habits for a user.

        By default returns only active habits (for dashboard).
        Pass include_archived=True for the management/settings page.
        """
        return await self.repo.get_user_habits(user_id, include_archived)

    async def get_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
        """
        Get a single habit by ID.

        Raises HabitNotFoundError if:
        - Habit doesn't exist
        - Habit belongs to a different user
        """
        habit = await self.repo.get_user_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()
        return habit

    async def update_habit(
        self, user_id: UUID, habit_id: UUID, data: HabitUpdate
    ) -> Habit:
        """
        Update a habit's properties.

        Only updates fields that were provided (non-None).
        Validates that the new name doesn't conflict with existing habits.

        NOTE: habit_type is NOT updatable. Changing "numeric" to "boolean"
        would make all existing numeric log entries invalid.
        """
        # Verify habit exists and belongs to user
        habit = await self.repo.get_user_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()

        # Build update dict with only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return habit  # Nothing to update

        # If name is being changed, check for duplicates
        if "name" in update_data and update_data["name"] != habit.name:
            if await self.repo.name_exists_for_user(
                user_id, update_data["name"], exclude_habit_id=habit_id
            ):
                raise DuplicateHabitNameError(update_data["name"])

        # Apply updates
        for key, value in update_data.items():
            setattr(habit, key, value)

        await self.session.flush()
        await self.session.refresh(habit)
        await self.session.commit()

        logger.info(
            "habit_updated",
            user_id=str(user_id),
            habit_id=str(habit_id),
            fields=list(update_data.keys()),
        )
        return habit

    async def delete_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
        """
        Soft delete (archive) a habit.

        Sets is_archived=True. The habit and its log data are preserved.
        User can potentially unarchive it later.
        """
        habit = await self.repo.archive_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()

        await self.session.commit()

        logger.info(
            "habit_archived",
            user_id=str(user_id),
            habit_id=str(habit_id),
            habit_name=habit.name,
        )
        return habit

    async def reorder_habits(self, user_id: UUID, habit_ids: list[UUID]) -> list[Habit]:
        """
        Reorder habits based on the provided list of IDs.

        The position in the list becomes the sort_order.
        Returns the updated habits in new order.
        """
        await self.repo.reorder_habits(user_id, habit_ids)
        await self.session.commit()

        logger.info(
            "habits_reordered",
            user_id=str(user_id),
            count=len(habit_ids),
        )

        # Return updated habits in new order
        return await self.repo.get_user_habits(user_id)
