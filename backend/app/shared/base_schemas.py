# ============================================================================
# Health Tracker — Base Pydantic Schemas
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines reusable request/response schemas used across all modules.
#   These are the building blocks — every module's schemas build on these.
#
# WHAT IS A SCHEMA (in this context):
#   A Pydantic model that defines the SHAPE of data going in/out of the API.
#   - Request schema: validates what the client sends
#   - Response schema: controls what the API returns (hides internal fields)
#
# WHY SEPARATE SCHEMAS FROM MODELS:
#   SQLAlchemy Model = database table structure (has password_hash, internal IDs)
#   Pydantic Schema  = API contract (never exposes password_hash to the client)
#   This separation is a security best practice.
# ============================================================================

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# TypeVar for generic pagination — works with any response type
T = TypeVar("T")


class BaseSchema(BaseModel):
    """
    Base schema that all other schemas inherit from.

    model_config with from_attributes=True tells Pydantic:
    "You can create this schema from a SQLAlchemy model object"

    Without this:
        user = User(id=1, email="a@b.com")
        UserResponse(**user.__dict__)  # Works but ugly

    With this:
        UserResponse.model_validate(user)  # Clean, automatic
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """
    Adds created_at and updated_at to response schemas.
    Most database records have these timestamps.
    """

    created_at: datetime
    updated_at: datetime | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    Every error from the API looks like this — consistent for frontend parsing.

    Example:
        {
            "error_code": "HABIT_NOT_FOUND",
            "message": "Habit with id 123 not found",
            "detail": null
        }
    """

    error_code: str
    message: str
    detail: str | None = None


class SuccessResponse(BaseModel):
    """
    Generic success response for operations that don't return data.

    Example:
        {"message": "Habit deleted successfully"}
    """

    message: str


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.

    Usage in route handler:
        @router.get("/habits")
        async def list_habits(pagination: PaginationParams = Depends()):
            # pagination.page = 1, pagination.page_size = 20

    WHY PAGINATION:
        Without it, GET /logs returns ALL logs — could be thousands of rows.
        With pagination: GET /logs?page=1&page_size=20 returns just 20 rows.
        The frontend shows a "Load More" button or page numbers.
    """

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate SQL OFFSET from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size — used in SQL LIMIT clause."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response wrapper.
    Wraps any list of items with pagination metadata.

    Example response:
        {
            "items": [...],
            "total": 150,
            "page": 1,
            "page_size": 20,
            "total_pages": 8
        }

    Generic[T] means this works with ANY item type:
        PaginatedResponse[HabitResponse]
        PaginatedResponse[LogResponse]
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class IDResponse(BaseModel):
    """Response containing just an ID — returned after creating a resource."""

    id: UUID
