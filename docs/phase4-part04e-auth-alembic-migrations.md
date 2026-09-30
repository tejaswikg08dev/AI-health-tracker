# 🗃️ Phase 4 Part 04e: Auth — Alembic Migrations

> **"You can't just DROP and CREATE tables in production — you'd lose 100,000 users' data. Migrations apply incremental changes: add a column here, create an index there. Each change is versioned, reversible, and auditable."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04e (Auth Database Migrations) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04d-auth-controller-main-nginx.md](./phase4-part04d-auth-controller-main-nginx.md) |
| **Next** | [phase4-part04f-auth-connections-and-flows.md](./phase4-part04f-auth-connections-and-flows.md) |
| **Files in This Doc** | 3 files (alembic.ini, alembic/env.py, alembic/versions/001_create_users_table.py) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (new concept: database migrations, version chains) |

---

## 📖 Table of Contents

1. [What Are Database Migrations? Read This First](#what-are-migrations)
2. [File 1: alembic.ini — Configuration](#alembic-ini)
3. [File 2: alembic/env.py — Environment Setup](#env-py)
4. [File 3: 001_create_users_table.py — First Migration](#migration)
5. [How Alembic Fits in the Project](#connections)
6. [Design Decisions](#design-decisions)
7. [How to Verify Your Work](#verify)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="what-are-migrations"></a>
## 1. What Are Database Migrations? Read This First

### The Problem

Imagine you've deployed your app with a `users` table. 1,000 users have signed up. Now you need to add a `phone_number` column.

```
WITHOUT migrations:
  1. Write "ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"
  2. Run it manually on your laptop's database ✅
  3. Forget to run it on the staging server ❌
  4. Deploy to production — app crashes because column doesn't exist ❌
  5. Run it on production at 3 AM in a panic ❌
  6. Your colleague also needs to add a column — conflicting changes ❌

WITH migrations:
  1. Run: alembic revision --autogenerate -m "add phone_number to users"
  2. Alembic generates a Python file with upgrade() and downgrade()
  3. Commit to Git (everyone gets the migration)
  4. CI/CD runs: alembic upgrade head (applies all pending migrations)
  5. Every environment (dev, staging, prod) has the same schema ✅
  6. If something breaks: alembic downgrade -1 (rollback) ✅
```

### Real-World Analogy

Think of **Git, but for your database schema**:

| Git (code) | Alembic (database) |
|-----------|-------------------|
| `git commit` | `alembic revision` (create a migration) |
| `git push` | `alembic upgrade head` (apply to database) |
| `git revert` | `alembic downgrade -1` (rollback last change) |
| `git log` | `alembic history` (show all migrations) |
| Commit message | Migration message ("create users table") |
| Commit hash | Revision ID ("001", "002", ...) |

### How Alembic Works

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR MODELS (models.py)          CURRENT DATABASE               │
│                                                                   │
│  class User(Base):                 users table:                   │
│    id = ...                          id, email, password_hash,    │
│    email = ...                       full_name, timezone,         │
│    phone_number = ... ← NEW!         is_active, ...               │
│                                      (no phone_number!)           │
│                                                                   │
│  alembic revision --autogenerate                                  │
│  ↓                                                                │
│  Alembic compares model vs database → finds the difference        │
│  ↓                                                                │
│  Generates migration file:                                        │
│    def upgrade():                                                 │
│        op.add_column('users', sa.Column('phone_number', ...))     │
│    def downgrade():                                               │
│        op.drop_column('users', 'phone_number')                    │
│  ↓                                                                │
│  alembic upgrade head → runs upgrade() → adds column to DB       │
└─────────────────────────────────────────────────────────────────┘
```

### Migration Version Chain

Each migration points to the previous one, forming a chain:

```
None → 001_create_users_table → 002_create_habits_table → 003_create_habit_logs_table → ...

alembic upgrade head    → runs ALL pending migrations in order
alembic downgrade -1    → runs downgrade() of the latest migration
alembic upgrade 001     → runs migrations up to and including 001
```

### File Structure

```
backend/
├── alembic.ini                    ← File 1: Alembic configuration
├── alembic/
│   ├── env.py                     ← File 2: Database connection + model discovery
│   ├── script.py.mako             ← Template for new migration files
│   └── versions/
│       ├── 001_create_users_table.py    ← File 3: First migration (this part)
│       ├── 002_create_habits_table.py   ← Created in Part 05
│       ├── 003_create_habit_logs_table.py
│       ├── 004_create_ai_tables.py
│       └── 005_create_notification_settings.py
```

---

<a name="alembic-ini"></a>
## 2. File 1: `alembic.ini` — Configuration

### Type This Code: `backend/alembic.ini`

```ini
# ============================================================================
# Alembic Configuration
# ============================================================================
# WHAT IS ALEMBIC:
#   Database migration tool for SQLAlchemy.
#   When you change a model (add a column, create a table),
#   Alembic generates the ALTER TABLE / CREATE TABLE SQL for you.
#
# WHY MIGRATIONS:
#   You can't just drop and recreate tables in production — you'd lose data.
#   Migrations apply incremental changes: add column, rename, create index.
#   Each migration is versioned — you can upgrade or rollback.
#
# USAGE:
#   alembic revision --autogenerate -m "create users table"  → Generate migration
#   alembic upgrade head                                      → Apply all migrations
#   alembic downgrade -1                                      → Rollback last migration
#   alembic history                                           → Show migration history
# ============================================================================

[alembic]
# Path to migration scripts
script_location = alembic

# Template for new migration files
file_template = %%(rev)s_%%(slug)s

# Timezone for migration timestamps
timezone = UTC

# Database URL — overridden by env.py to use DATABASE_URL_SYNC from .env
# sqlalchemy.url is set programmatically in env.py, not here
sqlalchemy.url = driver://user:pass@localhost/dbname

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

### Key Settings Explained

| Setting | Value | Why |
|---------|-------|-----|
| `script_location = alembic` | Directory where migration files live | Alembic looks here for `env.py` and `versions/` |
| `file_template = %%(rev)s_%%(slug)s` | File naming pattern | Creates files like `001_create_users_table.py` |
| `timezone = UTC` | Migration timestamps in UTC | Consistent across team members in different timezones |
| `sqlalchemy.url = driver://...` | Placeholder — overridden by `env.py` | Real URL comes from `.env` (never hardcode credentials!) |

---

<a name="env-py"></a>
## 3. File 2: `alembic/env.py` — Environment Setup

### What Does env.py Do?

`env.py` runs every time you execute an Alembic command. It:
1. Loads the database URL from environment variables
2. Imports all SQLAlchemy models (so Alembic knows about all tables)
3. Connects to the database
4. Runs migrations

### Type This Code: `backend/alembic/env.py`

```python
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
```

### Line-by-Line Explanation: env.py

**Lines 23-24: Core Imports**
```python
from app.config import get_settings
from app.database import Base
```
- `get_settings` — loads `DATABASE_URL_SYNC` from `.env`
- `Base` — our SQLAlchemy declarative base. `Base.metadata` contains the schema of ALL models that inherit from `Base`

**Lines 27-33: Model Imports**
```python
from app.modules.auth.models import User  # noqa: F401
from app.modules.habits.models import Habit  # noqa: F401
```
- **CRITICAL:** You MUST import every model here. If you create a new model and forget to import it, `alembic revision --autogenerate` won't detect it
- `# noqa: F401` — tells the linter "I know this import looks unused, don't warn me." The imports have a side effect: they register the model in `Base.metadata`
- **When you add a new module** (e.g., Logs), add its model import here

**Lines 36-40: Alembic Config**
```python
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
```
- `context.config` — Alembic's configuration object (reads from `alembic.ini`)
- `fileConfig(...)` — sets up Python logging from `alembic.ini`'s logging section
- `target_metadata = Base.metadata` — tells Alembic: "Compare THIS metadata (from our models) against the actual database to find differences"

**Lines 43-44: Database URL Override**
```python
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)
```
- Overrides the placeholder URL in `alembic.ini` with the real URL from `.env`
- `DATABASE_URL_SYNC` — uses `psycopg2` (synchronous driver), NOT `asyncpg`. Alembic runs synchronously
- **Why two database URLs?**
  - App: `postgresql+asyncpg://...` (async, for FastAPI's async/await)
  - Alembic: `postgresql+psycopg2://...` (sync, for Alembic's CLI)
  - Same database, different drivers

**Lines 46-62: Offline Mode**
```python
def run_migrations_offline() -> None:
```
- Generates SQL without connecting to the database
- Use case: `alembic upgrade head --sql` outputs the SQL script. You can review it, send it to a DBA, or run it manually in production
- Good for environments where you can't connect directly (CI without DB access)

**Lines 64-84: Online Mode**
```python
def run_migrations_online() -> None:
    connectable = engine_from_config(...)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```
- `poolclass=pool.NullPool` — don't use connection pooling for migrations (one-off operation, not a long-running server)
- `compare_server_default=True` — detects changes to `server_default` values (e.g., changing `server_default="UTC"` to `server_default="America/New_York"`)
- `context.begin_transaction()` — wraps migrations in a transaction. If a migration fails, the entire thing rolls back
- `context.run_migrations()` — executes the pending migration files in order

---

<a name="migration"></a>
## 4. File 3: `001_create_users_table.py` — First Migration

### What's in a Migration File?

Every migration file has:
1. **Revision metadata** — ID, parent revision, creation date
2. **`upgrade()` function** — the forward migration (create table, add column)
3. **`downgrade()` function** — the reverse migration (drop table, remove column)

### Type This Code: `backend/alembic/versions/001_create_users_table.py`

```python
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
```

### Line-by-Line Explanation: Migration File

**Lines 1-14: Docstring**
```python
"""create users table

Revision ID: 001
Revises: None
Create Date: 2026-09-26
"""
```
- The docstring is the migration description. Shows in `alembic history` output
- `Revision ID: 001` — this migration's unique ID
- `Revises: None` — this is the FIRST migration (no parent)

**Lines 20-22: Imports**
```python
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID
```
- `sa` — SQLAlchemy module. `sa.Column()`, `sa.String()`, `sa.Boolean()` — define columns
- `op` — Alembic operations. `op.create_table()`, `op.drop_table()`, `op.add_column()` — the migration commands
- `UUID` — PostgreSQL-specific UUID type

**Lines 25-28: Revision Identifiers**
```python
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```
- `revision = "001"` — this migration's ID. Alembic uses this to track which migrations have been applied
- `down_revision = None` — the previous migration (None = this is the first). Migration 002 would have `down_revision = "001"`, creating the chain
- `branch_labels` and `depends_on` — for advanced branching (not needed for our project)

**Lines 31-38: PostgreSQL Extensions**
```python
op.execute("CREATE EXTENSION IF NOT EXISTS vector")
op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
```
- `op.execute()` — runs raw SQL directly
- `vector` — pgvector extension for vector similarity search. We enable it now so the database is ready when we build the RAG module later
- `uuid-ossp` — provides `uuid_generate_v4()` function for generating UUIDs in SQL
- `IF NOT EXISTS` — safe to run multiple times (idempotent)

**Lines 41-53: Primary Key**
```python
sa.Column(
    "id",
    UUID(as_uuid=True),
    primary_key=True,
    server_default=sa.text("uuid_generate_v4()"),
    comment="Unique user identifier",
),
```
- `server_default=sa.text("uuid_generate_v4()")` — PostgreSQL generates the UUID, not Python. This means INSERTs from raw SQL (not through the ORM) also get auto-generated UUIDs
- `sa.text(...)` — wraps raw SQL in a SQLAlchemy text object (prevents Alembic from treating it as a string literal)

**Lines 55-65: Email Column**
```python
sa.Column(
    "email",
    sa.String(255),
    unique=True,
    nullable=False,
    index=True,
    comment="User email — used as login identifier",
),
```
- `unique=True` — Alembic creates a UNIQUE constraint: `CONSTRAINT users_email_key UNIQUE (email)`
- `index=True` — Alembic creates an index: `CREATE INDEX ix_users_email ON users (email)`
- `comment=` — adds column comments visible in PostgreSQL: `COMMENT ON COLUMN users.email IS '...'`

**Lines 88-93: Boolean with Server Default**
```python
sa.Column(
    "is_active",
    sa.Boolean(),
    nullable=False,
    server_default=sa.text("true"),
    comment="False = account deactivated (soft delete)",
),
```
- `server_default=sa.text("true")` — the `sa.text()` wrapper is important. Without it, Alembic would generate `DEFAULT 'true'` (string), not `DEFAULT true` (boolean)

**Lines 95-101: Timestamp with `now()`**
```python
sa.Column(
    "created_at",
    sa.DateTime(timezone=True),
    nullable=False,
    server_default=sa.text("now()"),
),
```
- `sa.DateTime(timezone=True)` → `TIMESTAMP WITH TIME ZONE`
- `server_default=sa.text("now()")` — PostgreSQL's `now()` function returns current UTC time on INSERT

**Lines 109-114: downgrade()**
```python
def downgrade() -> None:
    op.drop_table("users")
```
- `op.drop_table("users")` — drops the entire table. ALL user data is lost
- In production, you'd almost NEVER run downgrade. It's there for development and testing
- We don't drop the pgvector extension — other tables might use it

---

<a name="connections"></a>
## 5. How Alembic Fits in the Project

```
┌─────────────────────────────────────────────────────────────────┐
│  DEVELOPMENT WORKFLOW                                            │
│                                                                   │
│  1. You change models.py (add a column, create a table)          │
│  2. Run: alembic revision --autogenerate -m "description"         │
│  3. Alembic generates a migration file in versions/               │
│  4. Review the generated file (fix if needed)                     │
│  5. Run: alembic upgrade head (apply to your local database)      │
│  6. Commit migration file to Git                                  │
│  7. Teammates pull → run alembic upgrade head → their DB matches  │
│                                                                   │
│  PRODUCTION DEPLOYMENT                                            │
│                                                                   │
│  1. CI/CD pipeline starts                                         │
│  2. Run: alembic upgrade head (apply pending migrations)          │
│  3. Deploy new code                                               │
│  4. If something breaks: alembic downgrade -1 (rollback)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MIGRATION VERSION CHAIN (our project)                           │
│                                                                   │
│  None                                                             │
│   └── 001_create_users_table         ← Auth module (this part)   │
│        └── 002_create_habits_table    ← Habits module (Part 05)  │
│             └── 003_create_habit_logs  ← Logs module (Part 06)   │
│                  └── 004_create_ai_tables  ← AI module           │
│                       └── 005_create_notification_settings        │
│                                                                   │
│  alembic upgrade head → runs ALL 5 in order                      │
│  alembic upgrade 002  → runs only 001 + 002                      │
│  alembic downgrade 001 → reverts 005, 004, 003, 002              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  ALEMBIC TRACKING TABLE (alembic_version)                        │
│                                                                   │
│  PostgreSQL automatically creates this table:                     │
│  ┌──────────────────┐                                            │
│  │ version_num      │                                            │
│  ├──────────────────┤                                            │
│  │ 005              │  ← Current version (all migrations applied)│
│  └──────────────────┘                                            │
│                                                                   │
│  Alembic checks this table to know which migrations               │
│  have already been applied and which are pending.                 │
└─────────────────────────────────────────────────────────────────┘
```

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision 1: Manual vs Auto-Generated Migrations

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Migration Generation Strategy                     │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: First migration manual, rest auto-generated                │
│                                                                     │
│  WHY MANUAL FOR THE FIRST:                                          │
│  • Learning: you see exactly what CREATE TABLE looks like           │
│  • Extensions: pgvector and uuid-ossp need manual op.execute()     │
│  • Control: auto-generate sometimes misses server_default details   │
│                                                                     │
│  WHY AUTO-GENERATE FOR THE REST:                                    │
│  • Faster: change model → run command → migration appears           │
│  • Less error-prone: Alembic detects differences automatically      │
│  • Still reviewable: always read the generated file before applying │
│                                                                     │
│  COMMAND: alembic revision --autogenerate -m "add phone to users"   │
│  ALWAYS REVIEW: auto-generated migrations may need manual tweaks    │
│                                                                     │
│  INTERVIEW TIP: "We use Alembic auto-generation for speed but      │
│  always review generated migrations before applying. The first      │
│  migration was written manually to include PostgreSQL extension      │
│  setup and ensure server defaults were correct."                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Sync Driver for Migrations

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Alembic Database Driver                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: psycopg2 (sync) for Alembic, asyncpg (async) for app      │
│                                                                     │
│  WHY:                                                               │
│  • Alembic CLI is synchronous — can't use asyncpg                   │
│  • Same database, different drivers                                 │
│  • psycopg2 is the most stable PostgreSQL driver for Python         │
│                                                                     │
│  HOW:                                                               │
│  .env has two URLs:                                                 │
│    DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/health       │
│    DATABASE_URL_SYNC=postgresql+psycopg2://user:pass@db:5432/health │
│                                                                     │
│  env.py uses: settings.DATABASE_URL_SYNC                            │
│  app uses:    settings.DATABASE_URL (async)                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 7. How to Verify Your Work

```bash
# 1. Run migrations
docker-compose exec backend alembic upgrade head
# Expected: "INFO  [alembic.runtime.migration] Running upgrade  -> 001, create users table"

# 2. Check migration history
docker-compose exec backend alembic history
# Expected:
# 001 -> 002 (head), create habits table
# <base> -> 001, create users table

# 3. Verify users table exists
docker-compose exec postgres psql -U health_user -d health_tracker -c "\d users"
# Expected: table with all 8 columns (id, email, password_hash, ...)

# 4. Check the alembic_version table
docker-compose exec postgres psql -U health_user -d health_tracker \
  -c "SELECT * FROM alembic_version"
# Expected: version_num = "005" (or latest migration)

# 5. Test downgrade (development only!)
docker-compose exec backend alembic downgrade -1
# Then upgrade again:
docker-compose exec backend alembic upgrade head

# 6. Check pgvector extension
docker-compose exec postgres psql -U health_user -d health_tracker \
  -c "SELECT extname FROM pg_extension WHERE extname = 'vector'"
# Expected: "vector"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Can't locate revision identified by '001'` | Migration not in versions/ | Check file exists at `alembic/versions/001_...py` |
| `FATAL: role "health_user" does not exist` | PostgreSQL not configured | Check Docker Compose postgres environment |
| `Target database is not up to date` | Pending migrations | Run `alembic upgrade head` |
| `Can't import app.modules.auth.models` | Module not found | Check `PYTHONPATH` includes backend directory |
| `ERROR: extension "vector" is not available` | pgvector not installed in PostgreSQL | Use `pgvector/pgvector:pg16` Docker image |

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Database Migrations** | Versioned, incremental schema changes (like Git for DB) | All 3 files |
| 2 | **Alembic** | Python migration tool for SQLAlchemy | All 3 files |
| 3 | **`alembic revision --autogenerate`** | Auto-detect model changes → generate migration | Development workflow |
| 4 | **`alembic upgrade head`** | Apply all pending migrations | Deployment |
| 5 | **`alembic downgrade -1`** | Rollback the last migration | Recovery |
| 6 | **`upgrade()` / `downgrade()`** | Forward and reverse migration functions | Migration files |
| 7 | **`op.create_table()`** | Alembic operation to create a table | Migration 001 |
| 8 | **`op.execute()`** | Run raw SQL in a migration | PostgreSQL extensions |
| 9 | **`target_metadata`** | Model metadata Alembic compares against DB | `env.py` |
| 10 | **Revision Chain** | `down_revision` links migrations in order | Migration headers |
| 11 | **`server_default`** | Default value in SQL (vs `default` in Python) | Column definitions |
| 12 | **`sa.text()`** | Wraps raw SQL expressions in SQLAlchemy | `server_default=sa.text("now()")` |
| 13 | **pgvector Extension** | Adds vector type to PostgreSQL for AI/RAG | Migration 001 |
| 14 | **Sync vs Async Driver** | Alembic uses psycopg2 (sync), app uses asyncpg | `env.py` config |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: What are database migrations and why are they important?
**A:** "Database migrations are versioned, incremental changes to the database schema — like Git for your database. Instead of manually running ALTER TABLE on each server, migrations are Python files committed to Git. The CI/CD pipeline runs `alembic upgrade head` during deployment, ensuring every environment has the same schema. Each migration has an upgrade (apply) and downgrade (rollback) function, making changes reversible. Without migrations, schema changes are manual, error-prone, and impossible to coordinate across a team."

### Q2: How does Alembic auto-generate migrations?
**A:** "Alembic compares `Base.metadata` (the current state of your models) against the actual database schema. It detects differences — new tables, added columns, changed defaults — and generates a migration file with the appropriate `op.create_table()`, `op.add_column()`, etc. You always review the generated file because auto-generation can miss some changes like column renames (it generates drop + add instead) or custom SQL functions."

### Q3: Why do you have both DATABASE_URL and DATABASE_URL_SYNC?
**A:** "Our FastAPI app uses asyncpg for async database operations — non-blocking I/O that lets one process handle thousands of concurrent requests. But Alembic's CLI is synchronous — it can't use asyncpg. So we have two database URLs pointing to the same database: one with asyncpg for the app and one with psycopg2 for Alembic. Same data, different drivers."

### Q4: Why enable pgvector in the first migration?
**A:** "pgvector adds the `vector` column type to PostgreSQL, which we need for RAG (Retrieval Augmented Generation) — storing document embeddings as vectors for similarity search. We enable it in migration 001 so the database is ready when the AI module is built later. CREATE EXTENSION IF NOT EXISTS is idempotent — safe to run multiple times."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04d: Auth Router, Main & Nginx](./phase4-part04d-auth-controller-main-nginx.md) |
| ➡️ Next | [Phase 4 Part 04f: Auth Connections & Flows](./phase4-part04f-auth-connections-and-flows.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 04a | ✅ Done | Auth Models, Exceptions & Schemas |
| 04b | ✅ Done | Auth Security — JWT & bcrypt |
| 04c | ✅ Done | Auth Repository & Service |
| 04d | ✅ Done | Auth Router, Main & Nginx |
| **04e** | ✅ **You are here** | Auth Alembic Migrations |
| 04f | ⬜ Next | Auth Connections & Flows |

---

**End of Phase 4 Part 04e: Auth Alembic Migrations**

*The database is now version-controlled. The users table exists, pgvector is enabled, and every future schema change will be tracked. Next: the final auth doc — sequence diagrams showing every auth flow end-to-end.*
