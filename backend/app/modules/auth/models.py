# ============================================================================
# Auth Module — User Database Model
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the 'users' table in PostgreSQL using SQLAlchemy ORM.
#   Each class attribute = a column in the database table.
#
# WHY ORM (Object-Relational Mapping):
#   Instead of writing raw SQL:
#     "INSERT INTO users (email, password_hash) VALUES ('a@b.com', '$2b$...')"
#   You write Python:
#     user = User(email="a@b.com", password_hash="$2b$...")
#     session.add(user)
#
#   Benefits:
#   1. Type safety — Python catches typos, SQL doesn't
#   2. Migrations — Alembic auto-generates ALTER TABLE from model changes
#   3. Relationships — user.habits gives you all habits, no manual JOIN
#   4. Security — ORM auto-escapes values, preventing SQL injection
#
# TABLE SCHEMA:
#   users
#   ├── id           UUID (primary key, auto-generated)
#   ├── email        VARCHAR(255) (unique, indexed — login identifier)
#   ├── password_hash VARCHAR(255) (bcrypt hash, NEVER plain text)
#   ├── full_name    VARCHAR(100)
#   ├── timezone     VARCHAR(50) (IANA timezone, e.g., "Asia/Kolkata")
#   ├── is_active    BOOLEAN (soft delete — deactivate instead of delete)
#   ├── created_at   TIMESTAMP (auto-set on creation)
#   └── updated_at   TIMESTAMP (auto-set on every update)
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    User database model.

    IMPORTANT DESIGN DECISIONS:

    1. UUID primary key (not auto-increment integer):
       - UUIDs are globally unique — safe to expose in URLs and APIs
       - Auto-increment IDs leak information (competitor can guess user count)
       - UUIDs allow future database sharding (split data across servers)

    2. password_hash (not password):
       - We NEVER store plain text passwords
       - bcrypt hash is one-way — even if database is stolen, passwords are safe
       - The column name reminds developers: this is a hash, not a password

    3. is_active (soft delete):
       - Deleting a user account doesn't remove their row
       - We set is_active=False — preserves data for analytics and legal compliance
       - User can potentially reactivate their account

    4. timezone:
       - Stored per user, not globally
       - Used to show dates/times in the user's local time
       - Used for daily reminder scheduling (8 AM in THEIR timezone)
    """

    __tablename__ = "users"

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,    # Auto-generate UUID on creation
        comment="Unique user identifier",
    )

    # ── Login Credentials ──
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,           # No duplicate emails
        index=True,            # Index for fast lookup on login
        nullable=False,
        comment="User email — used as login identifier",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt password hash — NEVER store plain text",
    )

    # ── Profile ──
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's display name",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        server_default="UTC",
        nullable=False,
        comment="IANA timezone (e.g., Asia/Kolkata, America/New_York)",
    )

    # ── Account Status ──
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="False = account deactivated (soft delete)",
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Account creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="Last profile update timestamp (UTC)",
    )

    def __repr__(self) -> str:
        """String representation for debugging — NEVER include password_hash."""
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"
