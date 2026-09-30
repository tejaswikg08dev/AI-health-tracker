# ============================================================================
# Auth Module — Router (API Endpoints)
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines all HTTP endpoints for authentication.
#   Each function handles one endpoint — thin wrappers around the service.
#
# ENDPOINTS:
#   POST /api/v1/auth/signup    → Register a new user
#   POST /api/v1/auth/login     → Login, get JWT tokens
#   POST /api/v1/auth/refresh   → Refresh expired access token
#   POST /api/v1/auth/logout    → Blacklist current tokens
#   GET  /api/v1/auth/me        → Get current user profile
#   PUT  /api/v1/auth/me        → Update current user profile
#
# ROUTER VS SERVICE:
#   Router knows about HTTP: request bodies, status codes, headers.
#   Service knows about business: can this user register? is the password right?
#
#   Router is a thin translation layer:
#     HTTP request → extract data → call service → format HTTP response
# ============================================================================

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_async_session
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError
from app.modules.auth.schemas import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.modules.auth.security import decode_token
from app.modules.auth.service import AuthService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()

settings = get_settings()


# ── Dependency: Get Auth Service ──
# This creates a new AuthService instance for each request,
# injecting the current DB session and Redis client.
async def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AuthService:
    return AuthService(session, redis_client)


# ── Dependency: Get Current User ID from JWT Token ──
# This is the core auth dependency — used by ALL protected endpoints.
async def get_current_user_id(
    authorization: Annotated[str, Header(description="Bearer <access_token>")],
    redis_client: redis.Redis = Depends(get_redis_client),
) -> UUID:
    """
    Extract and validate user ID from the JWT token in the Authorization header.

    HOW IT WORKS:
    1. Frontend sends: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    2. We extract the token part (after "Bearer ")
    3. Decode and verify the JWT (signature, expiry, type)
    4. Check if token is blacklisted (user logged out)
    5. Return the user_id from the token payload

    This dependency is injected into any endpoint that needs authentication:
        @router.get("/me")
        async def get_profile(user_id: UUID = Depends(get_current_user_id)):
            ...

    Raises:
        TokenInvalidError: if no token, bad format, or tampered
        TokenExpiredError: if token has expired
    """
    # Extract token from "Bearer <token>" header value
    if not authorization.startswith("Bearer "):
        raise TokenInvalidError()

    token = authorization[7:]  # Skip "Bearer " (7 characters)

    # Decode and validate the JWT
    payload = decode_token(token, expected_type="access")

    # Check blacklist (logged-out tokens)
    is_blacklisted = await redis_client.get(f"token_blacklist:{token[:32]}")
    if is_blacklisted:
        raise TokenInvalidError()

    return UUID(payload["sub"])


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Register a new user account.

    - Validates email format and uniqueness
    - Hashes the password with bcrypt
    - Creates the user record in PostgreSQL
    - Returns the user profile (without password)

    After signup, the frontend should redirect to the login page.
    """
    user = await service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(
    data: UserLogin,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate with email and password, receive JWT tokens.

    Returns:
    - access_token: Send with every API request (expires in 30 min)
    - refresh_token: Use to get new access_token (expires in 7 days)

    Frontend usage:
        const response = await api.post("/auth/login", { email, password });
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("refresh_token", response.refresh_token);
        // Then on every request:
        api.defaults.headers.Authorization = `Bearer ${access_token}`;
    """
    tokens = await service.login(data.email, data.password)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh expired access token",
)
async def refresh_tokens(
    refresh_token: str,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Get new access + refresh tokens using a valid refresh token.

    Called automatically by the frontend when the access token expires.
    The old refresh token is blacklisted (can't be reused).

    Frontend usage:
        // When a request returns 401 (token expired):
        const newTokens = await api.post("/auth/refresh", {
            refresh_token: localStorage.getItem("refresh_token")
        });
        // Update stored tokens and retry the failed request
    """
    tokens = await service.refresh_tokens(refresh_token)
    return tokens


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout and blacklist tokens",
)
async def logout(
    user_id: UUID = Depends(get_current_user_id),
    authorization: str = Header(),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Logout — blacklist the current access token.

    After logout, the access token can no longer be used.
    The frontend should clear stored tokens and redirect to login.
    """
    token = authorization[7:]  # Extract token from "Bearer <token>"
    await service.logout(access_token=token)
    return SuccessResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Get the authenticated user's profile.

    Requires a valid access token in the Authorization header.
    Returns user info (never includes password).
    """
    user = await service.get_current_user(user_id)
    return UserResponse.model_validate(user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    data: UserUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Update the authenticated user's profile.

    Only provided fields are updated (partial update).
    Email and password changes are not supported here
    (would need separate endpoints with additional verification).
    """
    user = await service.update_profile(user_id, data)
    return UserResponse.model_validate(user)
