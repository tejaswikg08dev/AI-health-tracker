# ============================================================================
# Alembic — Migration Environment Configuration
# ============================================================================
# WHAT THIS FILE DOES:
#   Tells Alembic HOW to connect to the database and WHERE to find models.
#   This runs every time you execute an alembic command.
#
# KEY CONCEPT: target_metadata
#   Alembic needs to know about ALL your SQLAlchemy models to auto-generate
#   migrations. We import Base.metadata — which contains all models that
#   inherit from Base. When you add a new model, import it here.
#
# WHY SYNC (not async):
#   Alembic CLI runs synchronously. It can't use asyncpg.
#   So we use DATABASE_URL_SYNC (psycopg2) for migrations only.
#   The app itself uses DATABASE_URL (asyncpg) for async queries.
# ============================================================================

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.database import Base

# ── Import ALL models here ──
# Alembic can only auto-detect tables that are imported.
# As you add new modules, add their model imports here.
from app.modules.auth.models import User  # noqa: F401
from app.modules.habits.models import Habit  # noqa: F401
from app.modules.logs.models import HabitLog  # noqa: F401
from app.modules.ai.models import Document, DocumentChunk, AiChatMessage, AiInsight  # noqa: F401
from app.modules.notifications.models import NotificationSettings  # noqa: F401

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Setup logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Tell Alembic about our models ──
# This is the metadata that Alembic compares against the database
# to generate migration scripts automatically.
target_metadata = Base.metadata

# ── Override database URL from environment ──
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    Useful for: reviewing SQL before applying, running in CI without DB access.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Connects to the database and applies migrations directly.
    This is the normal mode used in development and production.

    Usage: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use connection pooling for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare server defaults — detect changes to default values
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Run the appropriate migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
