"""create habit_logs table

Revision ID: 003
Revises: 002
Create Date: 2026-09-26

WHAT THIS MIGRATION DOES:
    Creates the 'habit_logs' table — daily check-in entries.
    One row per habit per day per user.

    KEY INDEXES:
    - (user_id, log_date) — "show me everything I logged today"
    - (habit_id, log_date) — "show me this habit's history" (for streaks)
    - UNIQUE(user_id, habit_id, log_date) — prevent duplicate logs

    INDEX STRATEGY:
    We create indexes based on actual query patterns, not guessing.
    Every index speeds up reads but slows down writes (index must be updated).
    For a health tracker, reads >> writes (dashboard loads 100x more than logs created).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "habit_logs",

        # Primary key
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),

        # Foreign keys
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "habit_id", UUID(as_uuid=True),
            sa.ForeignKey("habits.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # The date this log is for
        sa.Column("log_date", sa.Date, nullable=False),

        # Value columns (only one filled per row, based on habit type)
        sa.Column("value_numeric", sa.Float, nullable=True),
        sa.Column("value_boolean", sa.Boolean, nullable=True),
        sa.Column("value_scale", sa.Integer, nullable=True),

        # Optional notes
        sa.Column("notes", sa.String(500), nullable=True),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),

        # ── Unique Constraint ──
        # Prevents: two log entries for the same habit on the same day
        # If violated, PostgreSQL raises IntegrityError — we catch this
        # in the service layer and return a friendly DuplicateLogError
        sa.UniqueConstraint("user_id", "habit_id", "log_date", name="uq_user_habit_date"),
    )

    # ── Indexes ──
    # Each index is designed for a specific query pattern:

    # Index 1: "Get all logs for user X on date Y" — daily check-in page
    op.create_index(
        "ix_habit_logs_user_date",
        "habit_logs",
        ["user_id", "log_date"],
    )

    # Index 2: "Get all logs for habit X between dates" — streak calculation, charts
    op.create_index(
        "ix_habit_logs_habit_date",
        "habit_logs",
        ["habit_id", "log_date"],
    )

    # Index 3: user_id alone — for broad user-scoped queries
    op.create_index(
        "ix_habit_logs_user_id",
        "habit_logs",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_habit_logs_user_id")
    op.drop_index("ix_habit_logs_habit_date")
    op.drop_index("ix_habit_logs_user_date")
    op.drop_table("habit_logs")
