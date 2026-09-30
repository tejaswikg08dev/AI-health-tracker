# ============================================================================
# Auth Module — User Repository (Data Access Layer)
# ============================================================================
# WHAT THIS FILE DOES:
#   Handles all database queries related to users.
#   Extends BaseRepository with user-specific queries (get by email, etc.).
#
# WHY A REPOSITORY:
#   Service layer says: "Find the user with this email"
#   Repository translates that to: SELECT * FROM users WHERE email = :email
#
#   The service doesn't know (or care) about SQL.
#   If you switch databases, only the repository changes.
#
# LAYER RESPONSIBILITIES:
#   Router    → handles HTTP (request parsing, response formatting)
#   Service   → handles business logic (validation, rules)
#   Repository → handles data access (SQL queries)
#
#   Each layer has ONE job. This is called "Separation of Concerns."
# ============================================================================

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.shared.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User-specific database operations.

    Inherits from BaseRepository[User]:
        create(**kwargs) → create a new user
        get_by_id(id) → get user by UUID
        get_all(offset, limit) → list users with pagination
        update(id, **kwargs) → update user fields
        delete(id) → hard delete user
    """

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Find a user by email address.

        Used during:
        - Login (find user, then verify password)
        - Signup (check if email already exists)

        Returns None if no user found — service decides what to do:
        - Login: raise InvalidCredentialsError
        - Signup: proceed with creation

        WHY index on email column:
            Without an index, PostgreSQL scans ALL rows to find the email.
            With an index, it's like a book's index — jumps directly to the page.
            For 1 million users: without index ~100ms, with index ~1ms.
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: UUID) -> User | None:
        """
        Find an active user by ID.

        Different from get_by_id: this also checks is_active=True.
        Used by the auth dependency (get_current_user) to verify
        the token belongs to an active account.

        Deactivated users have valid tokens but can't access the API.
        """
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.

        Used during signup to return a friendly error message
        instead of crashing on the unique constraint violation.

        WHY not just catch the DB error:
            Database errors are vague ("unique constraint violated").
            Checking first gives us a specific error message
            ("A user with this email already exists").
        """
        user = await self.get_by_email(email)
        return user is not None
