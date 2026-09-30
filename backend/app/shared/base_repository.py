# ============================================================================
# Health Tracker — Generic Base Repository
# ============================================================================
# WHAT THIS FILE DOES:
#   Provides reusable CRUD (Create, Read, Update, Delete) database operations.
#   Every module's repository inherits from this — no more rewriting
#   the same SELECT, INSERT, UPDATE queries in every module.
#
# WHAT IS THE REPOSITORY PATTERN:
#   A layer between your service (business logic) and database (SQL queries).
#
#   Service says: "Give me user with id=5"
#   Repository does: SELECT * FROM users WHERE id = 5
#   Service never writes SQL directly.
#
# WHY:
#   1. Reusable — CRUD operations written once, used by all modules
#   2. Testable — mock the repository in unit tests, no real DB needed
#   3. Swappable — if you switch from PostgreSQL to MongoDB, only repos change
#   4. Clean — services contain business logic, repos contain data access
#
# THIS IS THE SAME PATTERN AS:
#   Spring Boot: JpaRepository<T, ID>
#   .NET: Repository<T>
#   Django: Manager (queryset)
# ============================================================================

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

# ModelType is a placeholder for any SQLAlchemy model
# When you do BaseRepository[User], ModelType becomes User
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD repository.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            # Add custom queries specific to users
            async def get_by_email(self, email: str) -> User | None:
                ...

    The base class gives you: create, get_by_id, get_all, update, delete
    You only write custom queries in the subclass.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        Initialize with the model class and a database session.

        Args:
            model: The SQLAlchemy model class (e.g., User, Habit)
            session: The async database session for this request
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record in the database.

        Example:
            user = await user_repo.create(email="a@b.com", full_name="Shreya")

        HOW IT WORKS:
            1. Creates a model instance with the given fields
            2. Adds it to the session (marks for insert)
            3. Flushes to DB (executes INSERT, assigns id)
            4. Refreshes the object (loads DB-generated fields like created_at)
            5. Returns the created object

        WHY flush + refresh (not commit):
            Commit happens at the route handler level.
            This allows multiple repo operations in a single transaction.
            If any operation fails, everything rolls back.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()       # Execute INSERT, get generated id
        await self.session.refresh(instance)  # Load DB defaults (created_at, etc.)
        return instance

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """
        Get a single record by its primary key (UUID).

        Returns None if not found — the service layer decides whether to raise 404.

        Example:
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User not found")
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Example:
            habits = await habit_repo.get_all(offset=0, limit=20)  # First 20

        WHY offset/limit (not page/page_size):
            SQL uses OFFSET and LIMIT directly.
            The PaginationParams schema converts page to offset.
        """
        result = await self.session.execute(
            select(self.model)
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at.desc())  # Newest first
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """
        Count total records — used for pagination metadata.

        Example:
            total = await habit_repo.count()
            # Returns: 47
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def update(self, id: UUID, **kwargs) -> ModelType | None:
        """
        Update a record by ID with the given fields.

        Only updates fields that are provided — doesn't overwrite other fields.

        Example:
            updated_user = await user_repo.update(
                user_id,
                full_name="New Name",
                timezone="Asia/Kolkata"
            )

        Returns None if record doesn't exist.
        """
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Returns True if deleted, False if not found.

        NOTE: For most resources (habits, logs), we use SOFT DELETE
        (set is_archived=True) instead of real delete. This preserves
        data for analytics. Hard delete is used for things like
        expired tokens or test data.
        """
        result = await self.session.execute(
            sa_delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0
