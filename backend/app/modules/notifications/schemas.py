# ============================================================================
# Notifications Module — Schemas
# ============================================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.base_schemas import BaseSchema


class NotificationSettingsResponse(BaseSchema):
    """Current notification preferences."""

    id: UUID
    daily_reminder: bool
    weekly_report: bool
    streak_alerts: bool
    reminder_time: str
    created_at: datetime


class NotificationSettingsUpdate(BaseModel):
    """Update notification preferences — all fields optional."""

    daily_reminder: bool | None = None
    weekly_report: bool | None = None
    streak_alerts: bool | None = None
    reminder_time: str | None = Field(
        default=None,
        description="Daily reminder time in HH:MM format",
        examples=["08:00", "20:30"],
    )

    @field_validator("reminder_time")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except ValueError:
            raise ValueError("Time must be valid HH:MM (00:00 to 23:59)")
        return v


class TestEmailRequest(BaseModel):
    """Request to send a test email."""

    email_type: str = Field(
        default="daily_reminder",
        description="Type of test email: daily_reminder, weekly_report, streak_milestone",
    )
