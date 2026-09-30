# ============================================================================
# Notifications Module — Database Model
# ============================================================================
# Stores each user's notification preferences.
# One row per user — created when user signs up.
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationSettings(Base):
    """
    User notification preferences.

    Controls: daily reminders, weekly reports, streak milestone alerts.
    Each setting can be independently toggled on/off.

    reminder_time: What time to send the daily reminder (in user's timezone).
    Default 08:00 — most people check habits in the morning.
    """

    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,       # One settings row per user
        index=True,
    )

    # Toggle settings
    daily_reminder: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send daily 'time to log' reminder email",
    )
    weekly_report: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send weekly AI-generated health report",
    )
    streak_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send milestone alerts (7-day, 30-day streaks)",
    )

    # Reminder time (user's local time)
    reminder_time: Mapped[str] = mapped_column(
        String(5), default="08:00", server_default="08:00",
        comment="Daily reminder time in HH:MM format (user's timezone)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None,
        onupdate=lambda: datetime.now(timezone.utc), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<NotificationSettings(user={self.user_id}, reminder={self.daily_reminder})>"
