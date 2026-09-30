# ============================================================================
# Auth Module — Pydantic Schemas (Request/Response Models)
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the EXACT shape of data going in and out of auth endpoints.
#   Pydantic validates EVERY incoming request against these schemas.
#
# WHY SEPARATE SCHEMAS:
#   - UserCreate: what the client sends (includes password)
#   - UserResponse: what the API returns (NEVER includes password_hash)
#   - UserInDB: internal use only (includes password_hash for verification)
#
#   This separation prevents accidentally exposing sensitive data.
#   If you return the SQLAlchemy User model directly, password_hash leaks.
#
# SCHEMA NAMING CONVENTION:
#   {Entity}Create   → POST request body
#   {Entity}Update   → PUT/PATCH request body
#   {Entity}Response → API response (what client sees)
#   {Entity}InDB     → Internal only (includes DB-only fields)
# ============================================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.shared.base_schemas import BaseSchema


class UserCreate(BaseModel):
    """
    Schema for user registration (POST /auth/signup).

    Validates:
    - email: must be a valid email format (Pydantic's EmailStr handles this)
    - password: minimum 8 characters (security best practice)
    - full_name: 1-100 characters
    - timezone: optional, defaults to UTC

    Example request body:
    {
        "email": "shreya@example.com",
        "password": "mySecurePass123",
        "full_name": "Shreya",
        "timezone": "Asia/Kolkata"
    }
    """

    email: EmailStr = Field(
        ...,                               # ... means required (no default)
        description="Valid email address — used for login",
        examples=["shreya@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,                      # Security: minimum 8 characters
        max_length=128,                    # Prevent DoS with huge passwords
        description="Password (min 8 characters)",
        examples=["mySecurePass123"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name",
        examples=["Shreya"],
    )
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="IANA timezone identifier",
        examples=["Asia/Kolkata", "America/New_York", "UTC"],
    )


class UserLogin(BaseModel):
    """
    Schema for login (POST /auth/login).

    Only email and password — nothing else needed.

    Example request body:
    {
        "email": "shreya@example.com",
        "password": "mySecurePass123"
    }
    """

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    Schema for profile update (PUT /auth/me).

    All fields optional — only update what's provided.
    Password update could be a separate endpoint for extra security.

    Example request body:
    {
        "full_name": "Shreya V",
        "timezone": "America/New_York"
    }
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)


class UserResponse(BaseSchema):
    """
    Schema for user data in API responses.

    CRITICAL: Does NOT include password_hash.
    This is what the client sees when they call GET /auth/me.

    Example response:
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "shreya@example.com",
        "full_name": "Shreya",
        "timezone": "Asia/Kolkata",
        "is_active": true,
        "created_at": "2026-09-26T10:00:00Z"
    }
    """

    id: UUID
    email: str
    full_name: str
    timezone: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """
    Schema for authentication tokens (returned on login and refresh).

    TWO TOKENS:
    - access_token: short-lived (30 min), sent with every API request
    - refresh_token: long-lived (7 days), used ONLY to get a new access_token

    WHY TWO TOKENS:
      If access_token is stolen, attacker has only 30 minutes.
      Refresh token is sent less often (only to /auth/refresh),
      so it's less likely to be intercepted.

    token_type is always "bearer" — tells the frontend to send it as:
      Authorization: Bearer <access_token>

    Example response:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
