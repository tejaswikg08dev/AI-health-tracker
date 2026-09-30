# ============================================================================
# Auth Module — Service Layer (Business Logic)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains all authentication BUSINESS LOGIC.
#   Orchestrates between repository (data), security (crypto), and schemas.
#
# WHY A SERVICE LAYER:
#   Router handles HTTP concerns (parse request, format response).
#   Service handles BUSINESS concerns (can this user register? is the password right?)
#
#   This separation means:
#   1. Business logic is testable WITHOUT running a web server
#   2. Same logic can be reused (e.g., Celery task needs to verify a user)
#   3. Route handlers stay thin and clean
#
# BUSINESS RULES IN THIS SERVICE:
#   - Users cannot register with an existing email
#   - Passwords are hashed before storage
#   - Login returns both access and refresh tokens
#   - Refresh tokens can only be used to get new access tokens
#   - Logged-out tokens are blacklisted in Redis
# ============================================================================

from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.auth.exceptions import (
    AccountDeactivatedError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenResponse, UserCreate, UserUpdate
from app.modules.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """
    Authentication service — handles registration, login, token management.

    Each method represents a business operation.
    The service is instantiated per-request with the current DB session and Redis client.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.repo = UserRepository(session)
        self.session = session
        self.redis = redis_client

    async def register(self, data: UserCreate) -> User:
        """
        Register a new user.

        Business rules:
        1. Email must not already be registered
        2. Password must be hashed before storage
        3. Account is active by default

        Flow:
            Validate email is unique → Hash password → Create user in DB → Return user

        Raises:
            UserAlreadyExistsError: if email is taken
        """
        # Check if email already exists
        if await self.repo.email_exists(data.email):
            raise UserAlreadyExistsError()

        # Hash the password — NEVER store plain text
        hashed = hash_password(data.password)

        # Create user in database
        user = await self.repo.create(
            email=data.email,
            password_hash=hashed,
            full_name=data.full_name,
            timezone=data.timezone,
        )

        # Commit the transaction
        await self.session.commit()

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.

        Business rules:
        1. User must exist
        2. Password must match
        3. Account must be active
        4. Return both access and refresh tokens

        Flow:
            Find user by email → Verify password → Check active → Generate tokens

        Raises:
            InvalidCredentialsError: if email not found OR password wrong
            AccountDeactivatedError: if account is deactivated

        SECURITY NOTE:
            We use the SAME error for "email not found" and "wrong password".
            This prevents attackers from enumerating valid email addresses.
        """
        # Find user by email
        user = await self.repo.get_by_email(email)

        # User not found — raise generic "invalid credentials"
        if not user:
            raise InvalidCredentialsError()

        # Password doesn't match — same generic error (don't reveal which is wrong)
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # Account deactivated — different error (user knows they're blocked)
        if not user.is_active:
            raise AccountDeactivatedError()

        # Generate JWT tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        logger.info("user_logged_in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access + refresh tokens using a valid refresh token.

        WHY REFRESH:
            Access tokens expire every 30 minutes.
            Instead of forcing the user to login again,
            the frontend silently calls /auth/refresh with the refresh token
            to get a new access token. User never notices.

        Flow:
            Decode refresh token → Verify not blacklisted → Verify user active
            → Generate new tokens → Blacklist old refresh token

        Raises:
            TokenExpiredError: if refresh token is expired
            TokenInvalidError: if token is tampered or wrong type
            AccountDeactivatedError: if account was deactivated since last login
        """
        # Decode and validate the refresh token
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = UUID(payload["sub"])

        # Check if the token has been blacklisted (user logged out)
        is_blacklisted = await self.redis.get(f"token_blacklist:{refresh_token[:32]}")
        if is_blacklisted:
            raise InvalidCredentialsError()

        # Verify user still exists and is active
        user = await self.repo.get_active_by_id(user_id)
        if not user:
            raise AccountDeactivatedError()

        # Blacklist the old refresh token (prevent reuse)
        # TTL = remaining lifetime of the old token
        await self._blacklist_token(refresh_token)

        # Generate new tokens
        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)

        logger.info("tokens_refreshed", user_id=str(user.id))

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
        )

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """
        Logout — blacklist the current tokens.

        WHY BLACKLISTING:
            JWTs are stateless — the server doesn't track active sessions.
            When a user logs out, we can't "invalidate" the token because
            it's self-contained (carries its own expiry).

            Solution: maintain a BLACKLIST in Redis.
            On every request, check if the token is blacklisted.
            Blacklisted tokens = logged out.

        WHY Redis (not database):
            Token checks happen on EVERY request — must be fast (<1ms).
            Redis is perfect: in-memory, sub-millisecond reads.
            TTL auto-deletes entries when tokens expire (self-cleaning).
        """
        await self._blacklist_token(access_token)
        if refresh_token:
            await self._blacklist_token(refresh_token)

        logger.info("user_logged_out")

    async def get_current_user(self, user_id: UUID) -> User:
        """
        Get the currently authenticated user's profile.

        Called by the auth dependency after decoding the JWT token.

        Raises:
            AccountDeactivatedError: if account was deactivated
        """
        user = await self.repo.get_active_by_id(user_id)
        if not user:
            raise AccountDeactivatedError()
        return user

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
        """
        Update the current user's profile.

        Only updates fields that are provided (non-None).
        """
        # Build update dict with only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            # Nothing to update — return current user
            user = await self.repo.get_by_id(user_id)
            return user

        user = await self.repo.update(user_id, **update_data)
        await self.session.commit()

        logger.info("profile_updated", user_id=str(user_id), fields=list(update_data.keys()))
        return user

    async def _blacklist_token(self, token: str) -> None:
        """
        Add a token to the Redis blacklist.

        Uses first 32 chars of token as key (unique enough, saves memory).
        TTL is set to the token's remaining lifetime — auto-deletes when expired.
        No point blacklisting a token that's already expired.
        """
        try:
            payload = decode_token(token, expected_type="access")
        except Exception:
            try:
                payload = decode_token(token, expected_type="refresh")
            except Exception:
                return  # Token is already invalid — nothing to blacklist

        # Calculate remaining TTL
        from datetime import datetime, timezone

        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        ttl_seconds = int((exp_datetime - now).total_seconds())

        if ttl_seconds > 0:
            # Store in Redis with auto-expiry
            await self.redis.setex(
                f"token_blacklist:{token[:32]}",
                ttl_seconds,
                "blacklisted",
            )
