"""create notification_settings table

Revision ID: 005
Revises: 004
Create Date: 2026-09-26

Creates the notification_settings table — one row per user
with toggles for daily reminders, weekly reports, and streak alerts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("daily_reminder", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("weekly_report", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("streak_alerts", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("reminder_time", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_settings_user_id", "notification_settings", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("notification_settings")
