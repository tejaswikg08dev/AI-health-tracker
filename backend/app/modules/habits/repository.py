# ============================================================================
# Habits Module — Repository (Data Access Layer)
# ============================================================================
# WHAT THIS FILE DOES:
#   All database queries for habits. Extends BaseRepository with
#   habit-specific queries: get by user, check duplicates, reorder.
#
# KEY QUERIES:
#   - Get all active habits for a user (filtered, ordered)
#   - Check if user already has a habit with the same name
#   - Count active habits (for limit enforcement)
#   - Reorder habits (update sort_order for multiple rows)
#   - Soft delete (archive) instead of hard delete
# ============================================================================

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.models import Habit
from app.shared.base_repository import BaseRepository


class HabitRepository(BaseRepository[Habit]):
    """
    Habit-specific database operations.

    Inherits CRUD from BaseRepository: create, get_by_id, update, delete.
    Adds: user-scoped queries, duplicate checks, reordering, soft delete.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Habit, session)

    async def get_user_habits(
        self,
        user_id: UUID,
        include_archived: bool = False,
    ) -> list[Habit]:
        """
        Get all habits for a user, ordered by sort_order.

        By default, excludes archived habits (soft-deleted).
        Pass include_archived=True for settings/management views.

        The ORDER BY sort_order ensures habits display in the user's
        preferred order (after drag-and-drop reordering).
        """
        query = select(Habit).where(Habit.user_id == user_id)

        if not include_archived:
            query = query.where(Habit.is_archived.is_(False))

        query = query.order_by(Habit.sort_order.asc(), Habit.created_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_habit(self, user_id: UUID, habit_id: UUID) -> Habit | None:
        """
        Get a specific habit — only if it belongs to this user.

        WHY user_id check:
            Without it, user A could access user B's habit by guessing the UUID.
            Always scope queries to the current user. This is called
            "row-level security" at the application layer.
        """
        result = await self.session.execute(
            select(Habit).where(
                Habit.id == habit_id,
                Habit.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def name_exists_for_user(
        self,
        user_id: UUID,
        name: str,
        exclude_habit_id: UUID | None = None,
    ) -> bool:
        """
        Check if user already has an active habit with this name.

        exclude_habit_id is used during updates — don't flag the habit's
        own name as a duplicate when renaming.

        Example:
            User has "Water Intake" and "Sleep".
            Creating "Water Intake" → returns True (duplicate).
            Updating "Sleep" to "Sleep Hours" → exclude_habit_id=sleep_id.
        """
        query = select(func.count()).where(
            Habit.user_id == user_id,
            Habit.name == name,
            Habit.is_archived.is_(False),
        )

        if exclude_habit_id:
            query = query.where(Habit.id != exclude_habit_id)

        result = await self.session.execute(query)
        return result.scalar_one() > 0

    async def count_active_habits(self, user_id: UUID) -> int:
        """
        Count user's active (non-archived) habits.

        Used to enforce the maximum habit limit (20).
        Archived habits don't count toward the limit.
        """
        result = await self.session.execute(
            select(func.count()).where(
                Habit.user_id == user_id,
                Habit.is_archived.is_(False),
            )
        )
        return result.scalar_one()

    async def get_next_sort_order(self, user_id: UUID) -> int:
        """
        Get the next available sort_order value for a new habit.

        If user has habits with sort_order 0, 1, 2 → returns 3.
        New habits go at the end of the list.
        """
        result = await self.session.execute(
            select(func.coalesce(func.max(Habit.sort_order), -1)).where(
                Habit.user_id == user_id,
                Habit.is_archived.is_(False),
            )
        )
        return result.scalar_one() + 1

    async def reorder_habits(self, user_id: UUID, habit_ids: list[UUID]) -> None:
        """
        Update sort_order for multiple habits based on the provided order.

        The index in the list becomes the new sort_order:
            habit_ids[0] → sort_order = 0
            habit_ids[1] → sort_order = 1
            habit_ids[2] → sort_order = 2

        WHY not a single UPDATE:
            Each habit gets a DIFFERENT sort_order value.
            We batch this with individual updates in a single transaction.
            All updates commit together — if one fails, none apply.
        """
        for index, habit_id in enumerate(habit_ids):
            await self.session.execute(
                update(Habit)
                .where(Habit.id == habit_id, Habit.user_id == user_id)
                .values(sort_order=index)
            )
        await self.session.flush()

    async def archive_habit(self, user_id: UUID, habit_id: UUID) -> Habit | None:
        """
        Soft delete — set is_archived=True instead of actually deleting.

        The habit's log data is preserved. User can potentially unarchive later.
        This is the standard approach for data-heavy applications.
        """
        habit = await self.get_user_habit(user_id, habit_id)
        if not habit:
            return None

        habit.is_archived = True
        await self.session.flush()
        await self.session.refresh(habit)
        return habit
