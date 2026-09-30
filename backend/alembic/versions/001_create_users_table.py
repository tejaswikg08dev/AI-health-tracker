"""create users table

Revision ID: 001
Revises: None
Create Date: 2026-09-26

WHAT THIS MIGRATION DOES:
    Creates the 'users' table — the foundation for authentication.
    Also enables the pgvector extension (needed later for RAG embeddings).

NOTE:
    Normally Alembic auto-generates migrations with:
        alembic revision --autogenerate -m "create users table"
    We're writing this one manually so you can see exactly what's happening.
    Future migrations can be auto-generated.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# Revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply this migration — create the users table.

    This is the SQL that runs when you execute: alembic upgrade head
    """

    # Enable pgvector extension (needed for RAG embeddings later)
    # CREATE EXTENSION IF NOT EXISTS vector;
    # This adds the 'vector' data type to PostgreSQL
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Enable uuid-ossp extension (for UUID generation in SQL)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        "users",

        # Primary key — UUID auto-generated
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique user identifier",
        ),

        # Login credentials
        sa.Column(
            "email",
            sa.String(255),
            unique=True,
            nullable=False,
            index=True,
            comment="User email — used as login identifier",
        ),
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=False,
            comment="Bcrypt password hash — NEVER store plain text",
        ),

        # Profile
        sa.Column(
            "full_name",
            sa.String(100),
            nullable=False,
            comment="User display name",
        ),
        sa.Column(
            "timezone",
            sa.String(50),
            nullable=False,
            server_default="UTC",
            comment="IANA timezone (e.g., Asia/Kolkata)",
        ),

        # Account status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="False = account deactivated (soft delete)",
        ),

        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Account creation timestamp (UTC)",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Last profile update timestamp (UTC)",
        ),
    )


def downgrade() -> None:
    """
    Reverse this migration — drop the users table.

    This is the SQL that runs when you execute: alembic downgrade -1

    WARNING: This deletes ALL user data. Only use in development.
    In production, you'd never downgrade a migration with user data.
    """
    op.drop_table("users")

    # Note: We don't drop the pgvector extension here because
    # other migrations might depend on it.
