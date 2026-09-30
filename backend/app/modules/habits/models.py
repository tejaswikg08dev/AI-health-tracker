# ============================================================================
# Habits Module — Habit Database Model
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the 'habits' table — each row is one habit a user tracks.
#   A user can have multiple habits (e.g., Water, Sleep, Exercise, Mood).
#
# HABIT TYPES:
#   numeric  → value is a number (e.g., 8 glasses of water, 7.5 hours sleep)
#   boolean  → yes/no (e.g., "Did I exercise today?")
#   scale    → 1-10 rating (e.g., mood, energy level)
#
# TABLE SCHEMA:
#   habits
#   ├── id            UUID (primary key)
#   ├── user_id       UUID (foreign key → users.id)
#   ├── name          VARCHAR(100) ("Water Intake", "Sleep Hours")
#   ├── habit_type    VARCHAR(20) (numeric / boolean / scale)
#   ├── unit          VARCHAR(50) ("glasses", "hours", "")
#   ├── target_value  FLOAT (daily goal: 8 glasses, 7 hours)
#   ├── color         VARCHAR(7) (hex color for UI: "#3B82F6")
#   ├── icon          VARCHAR(50) (emoji or icon name: "💧", "🏃")
#   ├── sort_order    INTEGER (display order on dashboard)
#   ├── is_archived   BOOLEAN (soft delete — hide but keep data)
#   ├── created_at    TIMESTAMP
#   └── updated_at    TIMESTAMP
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Habit(Base):
    """
    Habit database model.

    DESIGN DECISIONS:

    1. habit_type as string (not enum):
       In the database, we store "numeric", "boolean", "scale" as strings.
       Using a DB enum makes adding new types require a migration.
       Strings are more flexible — validation happens in Pydantic schemas.

    2. target_value is nullable:
       Boolean habits don't have a numeric target.
       "Did I exercise?" → target is just "yes" (True), not a number.

    3. sort_order for drag-and-drop:
       Users can reorder habits on their dashboard.
       Without sort_order, you'd order by created_at (not user-friendly).

    4. is_archived (soft delete):
       When a user "deletes" a habit, we set is_archived=True.
       The habit's historical log data is preserved for analytics.
       "Your average sleep was 7.2 hours when you tracked it" — still works.

    5. color and icon for personalization:
       Each habit gets a color and icon displayed on the dashboard.
       Makes the UI visually appealing and habits easily distinguishable.
    """

    __tablename__ = "habits"

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique habit identifier",
    )

    # ── Owner ──
    # Foreign key to users table — each habit belongs to one user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,          # Index for fast lookup: "get all habits for user X"
        comment="Owner user ID",
    )

    # ── Habit Definition ──
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Habit display name (e.g., 'Water Intake')",
    )
    habit_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type: numeric, boolean, or scale",
    )
    unit: Mapped[str] = mapped_column(
        String(50),
        default="",
        server_default="",
        nullable=False,
        comment="Unit of measurement (e.g., 'glasses', 'hours', 'steps')",
    )
    target_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Daily target (e.g., 8 glasses, 7 hours). Null for boolean habits.",
    )

    # ── UI Customization ──
    color: Mapped[str] = mapped_column(
        String(7),
        default="#3B82F6",           # Default: blue
        server_default="#3B82F6",
        nullable=False,
        comment="Hex color code for UI display",
    )
    icon: Mapped[str] = mapped_column(
        String(50),
        default="⭐",
        server_default="⭐",
        nullable=False,
        comment="Emoji or icon name for UI display",
    )

    # ── Ordering ──
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        comment="Display order on dashboard (lower = higher position)",
    )

    # ── Status ──
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="True = soft-deleted, hidden from active view but data preserved",
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

    # ── Relationships ──
    # This allows: habit.logs → list of all log entries for this habit
    # lazy="selectin" means: when we load a habit, also load its logs efficiently
    # We won't always want this, so it's optional — use it when needed
    # logs = relationship("HabitLog", back_populates="habit", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Habit(id={self.id}, name={self.name}, type={self.habit_type})>"
