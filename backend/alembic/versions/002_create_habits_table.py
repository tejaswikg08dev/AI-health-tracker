"""create habits table

Revision ID: 002
Revises: 001
Create Date: 2026-09-26

WHAT THIS MIGRATION DOES:
    Creates the 'habits' table — stores user-defined trackable habits.
    Foreign key to users table with CASCADE delete.
    Composite index on (user_id, is_archived) for fast filtered lookups.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "habits",

        # Primary key
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),

        # Owner — foreign key to users
        sa.Column(
            "user_id", UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),

        # Habit definition
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("habit_type", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default=""),
        sa.Column("target_value", sa.Float, nullable=True),

        # UI customization
        sa.Column("color", sa.String(7), nullable=False, server_default="#3B82F6"),
        sa.Column("icon", sa.String(50), nullable=False, server_default="⭐"),

        # Ordering
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),

        # Soft delete
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Index: fast lookup for "get all active habits for user X"
    # This is the most common query — used on every dashboard load
    op.create_index(
        "ix_habits_user_id",
        "habits",
        ["user_id"],
    )

    # Composite index: user_id + is_archived — for filtered queries
    op.create_index(
        "ix_habits_user_active",
        "habits",
        ["user_id", "is_archived"],
    )


def downgrade() -> None:
    op.drop_index("ix_habits_user_active")
    op.drop_index("ix_habits_user_id")
    op.drop_table("habits")
