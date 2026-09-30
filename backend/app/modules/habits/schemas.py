# ============================================================================
# Habits Module — Pydantic Schemas (Request/Response Models)
# ============================================================================
# WHAT THIS FILE DOES:
#   Validates incoming data and controls outgoing data for habit endpoints.
#
# VALIDATION EXAMPLES:
#   - name must be 1-100 characters
#   - habit_type must be one of: numeric, boolean, scale
#   - color must be a valid hex color (#RRGGBB)
#   - target_value required for numeric habits, optional for others
# ============================================================================

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.base_schemas import BaseSchema


class HabitType(str, Enum):
    """
    Valid habit types.

    Using an Enum gives us:
    1. Auto-validation — Pydantic rejects invalid types automatically
    2. Swagger docs — dropdown shows valid options
    3. Type safety — IDE autocomplete and error checking

    WHY str + Enum:
        Inheriting from str makes the enum JSON-serializable.
        Without str, FastAPI can't serialize it in responses.
    """

    NUMERIC = "numeric"     # Value is a number: 8 glasses, 7.5 hours, 10000 steps
    BOOLEAN = "boolean"     # Value is yes/no: Did I exercise? Did I meditate?
    SCALE = "scale"         # Value is 1-10: mood rating, energy level, pain level


class HabitCreate(BaseModel):
    """
    Schema for creating a new habit (POST /habits).

    Example request body:
    {
        "name": "Water Intake",
        "habit_type": "numeric",
        "unit": "glasses",
        "target_value": 8,
        "color": "#3B82F6",
        "icon": "💧"
    }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Habit name displayed on dashboard",
        examples=["Water Intake", "Sleep Hours", "Exercise", "Mood"],
    )
    habit_type: HabitType = Field(
        ...,
        description="Type of tracking: numeric (number), boolean (yes/no), scale (1-10)",
        examples=["numeric"],
    )
    unit: str = Field(
        default="",
        max_length=50,
        description="Unit of measurement. Leave empty for boolean/scale.",
        examples=["glasses", "hours", "steps", "minutes"],
    )
    target_value: float | None = Field(
        default=None,
        ge=0,                  # ge = greater than or equal to 0
        le=100000,             # reasonable upper limit
        description="Daily target value. Required for numeric habits.",
        examples=[8, 7.5, 10000],
    )
    color: str = Field(
        default="#3B82F6",
        max_length=7,
        description="Hex color code for UI",
        examples=["#3B82F6", "#10B981", "#F59E0B", "#EF4444"],
    )
    icon: str = Field(
        default="⭐",
        max_length=50,
        description="Emoji or icon identifier",
        examples=["💧", "😴", "🏃", "😊", "📖"],
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate hex color format: must be #RRGGBB."""
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format (e.g., #3B82F6)")
        # Validate hex characters
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color code")
        return v.upper()

    @field_validator("target_value")
    @classmethod
    def validate_target_for_type(cls, v: float | None, info) -> float | None:
        """Warn if numeric habit has no target (but don't block — user might set later)."""
        return v


class HabitUpdate(BaseModel):
    """
    Schema for updating a habit (PUT /habits/:id).

    All fields optional — only update what's provided.
    Cannot change habit_type after creation (would break existing log data).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=50)
    target_value: float | None = Field(default=None, ge=0, le=100000)
    color: str | None = Field(default=None, max_length=7)
    icon: str | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color code")
        return v.upper()


class HabitResponse(BaseSchema):
    """
    Schema for habit data in API responses.

    Example response:
    {
        "id": "550e8400-...",
        "name": "Water Intake",
        "habit_type": "numeric",
        "unit": "glasses",
        "target_value": 8.0,
        "color": "#3B82F6",
        "icon": "💧",
        "sort_order": 0,
        "is_archived": false,
        "created_at": "2026-09-26T10:00:00Z"
    }
    """

    id: UUID
    name: str
    habit_type: str
    unit: str
    target_value: float | None
    color: str
    icon: str
    sort_order: int
    is_archived: bool
    created_at: datetime


class HabitReorderRequest(BaseModel):
    """
    Schema for reordering habits (PUT /habits/reorder).

    The frontend sends the new order as a list of habit IDs.
    The position in the list = the new sort_order.

    Example request body:
    {
        "habit_ids": [
            "uuid-of-sleep",     ← sort_order = 0
            "uuid-of-water",     ← sort_order = 1
            "uuid-of-exercise"   ← sort_order = 2
        ]
    }
    """

    habit_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="Habit IDs in desired display order",
    )
