# 📝 Phase 4 Part 06a: Logs — Models, Exceptions, Schemas & Migration

> **"The habit_logs table is the data engine of the entire application. Every chart, every streak, every AI insight comes from these rows. One entry per habit per day — simple structure, massive analytical power."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 06a (Logs Data Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.2 — Daily Logging |
| **Previous** | [phase4-part06-logs-service-overview.md](./phase4-part06-logs-service-overview.md) |
| **Next** | [phase4-part06b-logs-repository-service.md](./phase4-part06b-logs-repository-service.md) |
| **Files in This Doc** | 4 files (models.py, exceptions.py, schemas.py, 003_migration.py) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (new concepts: composite UNIQUE, polymorphic columns, bulk schema, Date type) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: models.py — HabitLog Database Model](#models)
3. [File 2: exceptions.py — Log-Specific Exceptions](#exceptions)
4. [File 3: schemas.py — Request/Response Schemas](#schemas)
5. [File 4: 003_create_habit_logs_table.py — Migration](#migration)
6. [How These Files Connect](#connections)
7. [Design Decisions](#design-decisions)
8. [How to Verify Your Work](#verify)
9. [What You Learned](#what-you-learned)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

The data layer for the Logs module — same pattern as Auth (04a) and Habits (05a), with three new concepts:

| What's New | What It Is | Where |
|-----------|-----------|-------|
| **Composite UNIQUE constraint** | `UNIQUE(user_id, habit_id, log_date)` — one log per habit per day | `models.py` |
| **Polymorphic value columns** | Three typed columns, one filled per row | `models.py` |
| **Two foreign keys** | References both `users.id` AND `habits.id` | `models.py` |
| **Bulk schema** | `BulkLogCreate` wraps an array of `BulkLogEntry` | `schemas.py` |
| **Date type (not DateTime)** | `log_date: date` — just the calendar day, no time | `models.py` |

### File Structure

```
backend/app/modules/logs/
├── __init__.py
├── models.py             ← File 1: HabitLog (10 columns, 2 FKs, UNIQUE)
├── exceptions.py         ← File 2: 4 exception classes
├── schemas.py            ← File 3: 6 schemas (LogCreate, BulkLogCreate, BulkLogEntry, LogUpdate, LogResponse, DailyLogSummary)
└── (repository, service, router — later parts)

backend/alembic/versions/
└── 003_create_habit_logs_table.py  ← File 4: Migration with 3 indexes + UNIQUE
```

---

<a name="models"></a>
## 2. File 1: `models.py` — HabitLog Database Model

### What Is a Composite UNIQUE Constraint? Read This First

A **composite UNIQUE constraint** spans MULTIPLE columns. It says: "The combination of these columns must be unique."

```
Single-column UNIQUE (email on users):
  "shreya@test.com" can only appear ONCE in the email column

Composite UNIQUE (user_id + habit_id + log_date on habit_logs):
  The COMBINATION must be unique:
  ✅ (user-1, water, Sep-26)    ← first log
  ❌ (user-1, water, Sep-26)    ← DUPLICATE! same user + habit + date
  ✅ (user-1, water, Sep-27)    ← different date — OK
  ✅ (user-1, sleep, Sep-26)    ← different habit — OK
  ✅ (user-2, water, Sep-26)    ← different user — OK
```

This guarantees: **one log entry per habit per day per user**. The database enforces it even if the application logic has a bug.

### What Is `__table_args__`?

SQLAlchemy's `__table_args__` is where you put **table-level** constraints — things that span multiple columns:

```python
class HabitLog(Base):
    __table_args__ = (
        UniqueConstraint("user_id", "habit_id", "log_date", name="uq_user_habit_date"),
    )
```

- Column-level constraints (single column): defined on the column itself (`unique=True`, `index=True`)
- Table-level constraints (multiple columns): defined in `__table_args__`
- The name `"uq_user_habit_date"` lets you identify the constraint in error messages

### Type This Code: `backend/app/modules/logs/models.py`

```python
# ============================================================================
# Logs Module — HabitLog Database Model
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the 'habit_logs' table — each row is one daily check-in value.
#   "On September 26, Shreya drank 7 glasses of water."
#
# DESIGN:
#   One row per habit per day per user.
#   The UNIQUE constraint (user_id, habit_id, log_date) prevents
#   duplicate logs — you can only log "Water" once per day.
#
# THREE VALUE COLUMNS:
#   value_numeric  → for "numeric" habits (8.0 glasses, 7.5 hours)
#   value_boolean  → for "boolean" habits (True = did it, False = didn't)
#   value_scale    → for "scale" habits (7 out of 10 mood)
#
#   Only ONE of these is filled per row, based on the habit's type.
#   This is called "polymorphic storage" — one table handles multiple types.
#
# TABLE SCHEMA:
#   habit_logs
#   ├── id              UUID (primary key)
#   ├── user_id         UUID (FK → users.id)
#   ├── habit_id        UUID (FK → habits.id)
#   ├── log_date        DATE (the day this log is for)
#   ├── value_numeric   FLOAT (nullable — only for numeric habits)
#   ├── value_boolean   BOOLEAN (nullable — only for boolean habits)
#   ├── value_scale     INTEGER (nullable — only for scale habits, 1-10)
#   ├── notes           TEXT (optional user notes: "felt tired today")
#   ├── created_at      TIMESTAMP
#   └── updated_at      TIMESTAMP
#
#   UNIQUE(user_id, habit_id, log_date) — one log per habit per day
# ============================================================================

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HabitLog(Base):
    """
    Daily habit log entry.

    Each row represents: "User X logged value Y for habit Z on date D."

    UNIQUE CONSTRAINT:
        (user_id, habit_id, log_date) ensures one entry per habit per day.
        If a user tries to log "Water" twice on Sept 26, the second attempt
        should update the existing row, not create a duplicate.
    """

    __tablename__ = "habit_logs"

    # Enforce one log per habit per day per user at the database level
    __table_args__ = (
        UniqueConstraint(
            "user_id", "habit_id", "log_date",
            name="uq_user_habit_date",
        ),
    )

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique log entry identifier",
    )

    # ── Foreign Keys ──
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user ID",
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Which habit this log is for",
    )

    # ── Log Date ──
    # This is the DATE the log is for, not when it was created.
    # User might log yesterday's sleep today — log_date = yesterday.
    log_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,     # Indexed for fast date range queries
        comment="The date this log entry is for (not when it was created)",
    )

    # ── Values (one per habit type) ──
    # Only one of these will be filled per row, based on the habit's type.
    value_numeric: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Value for numeric habits (e.g., 8.0 glasses, 7.5 hours)",
    )
    value_boolean: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Value for boolean habits (True = completed, False = missed)",
    )
    value_scale: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Value for scale habits (1-10 rating)",
    )

    # ── Optional Notes ──
    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional notes (e.g., 'felt tired today', 'ran 5K')",
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

    def __repr__(self) -> str:
        return (
            f"<HabitLog(id={self.id}, habit_id={self.habit_id}, "
            f"date={self.log_date}, num={self.value_numeric}, "
            f"bool={self.value_boolean}, scale={self.value_scale})>"
        )
```

### Key Differences from Habit Model

**`Date` type (not `DateTime`)**
```python
log_date: Mapped[date] = mapped_column(Date, ...)
```
- `Date` → PostgreSQL `DATE` type — stores `2026-09-26` (no time component)
- `DateTime` → PostgreSQL `TIMESTAMP` — stores `2026-09-26T22:00:00Z`
- We use `Date` because a log is for a CALENDAR DAY, not a specific moment. "I drank 7 glasses today" — the specific time doesn't matter

**`__table_args__` with UniqueConstraint**
```python
__table_args__ = (
    UniqueConstraint("user_id", "habit_id", "log_date", name="uq_user_habit_date"),
)
```
- Tuple with a trailing comma `(constraint,)` — Python requires the comma for a single-element tuple
- `name="uq_user_habit_date"` — PostgreSQL constraint name. Visible in error messages: `"violates unique constraint uq_user_habit_date"`

**Two Foreign Keys**
```python
user_id → ForeignKey("users.id", ondelete="CASCADE")
habit_id → ForeignKey("habits.id", ondelete="CASCADE")
```
- `user_id` — who logged this entry
- `habit_id` — which habit was logged
- Both have `ondelete="CASCADE"` — if the user or habit is deleted, the logs are cleaned up automatically

**Three nullable value columns**
```python
value_numeric: Mapped[float | None]   # For numeric habits
value_boolean: Mapped[bool | None]    # For boolean habits
value_scale: Mapped[int | None]       # For scale habits (1-10)
```
- All three are nullable. Only ONE is filled per row
- The service layer validates which one should be filled based on the habit's `habit_type`

---

<a name="exceptions"></a>
## 3. File 2: `exceptions.py` — Log-Specific Exceptions

### Type This Code: `backend/app/modules/logs/exceptions.py`

```python
# ============================================================================
# Logs Module — Custom Exceptions
# ============================================================================

from app.shared.exceptions import ConflictError, NotFoundError, ValidationError


class LogNotFoundError(NotFoundError):
    """Log entry not found or doesn't belong to this user — HTTP 404."""

    def __init__(self) -> None:
        super().__init__(
            message="Log entry not found",
            error_code="LOG_NOT_FOUND",
        )


class DuplicateLogError(ConflictError):
    """
    A log already exists for this habit on this date — HTTP 409.

    The frontend should use the update endpoint instead.
    """

    def __init__(self, habit_name: str, log_date: str) -> None:
        super().__init__(
            message=f"A log for '{habit_name}' already exists on {log_date}. Use update instead.",
            error_code="DUPLICATE_LOG",
        )


class FutureDateError(ValidationError):
    """
    Cannot log for a future date — HTTP 422.

    You can log for today or past dates (backfilling), but not the future.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Cannot log for a future date",
            error_code="FUTURE_DATE",
        )


class InvalidLogValueError(ValidationError):
    """
    Log value doesn't match the habit type — HTTP 422.

    Examples:
    - Numeric habit but value is negative
    - Scale habit but value is 15 (must be 1-10)
    - Boolean habit but a numeric value was provided
    """

    def __init__(self, detail: str) -> None:
        super().__init__(
            message=f"Invalid log value: {detail}",
            error_code="INVALID_LOG_VALUE",
        )
```

### What's New Here

**`DuplicateLogError` takes TWO parameters:**
```python
def __init__(self, habit_name: str, log_date: str) -> None:
    super().__init__(
        message=f"A log for '{habit_name}' already exists on {log_date}. Use update instead.",
    )
```
- Includes BOTH the habit name and date — very specific: "A log for 'Water Intake' already exists on 2026-09-26. Use update instead."
- The "Use update instead" hint tells the frontend what to do

**`FutureDateError` — no parameters:**
- Always the same message. You can log today or past dates (backfilling yesterday's sleep), but not December 2027

**`InvalidLogValueError` takes a `detail` string:**
- Different messages depending on the mismatch: "Numeric habit requires value_numeric", "Scale habit requires value_scale (1-10)", etc.

---

<a name="schemas"></a>
## 4. File 3: `schemas.py` — Request/Response Schemas

### Type This Code: `backend/app/modules/logs/schemas.py`

```python
# ============================================================================
# Logs Module — Pydantic Schemas (Request/Response Models)
# ============================================================================
# WHAT THIS FILE DOES:
#   Validates daily check-in data. Handles three different value types
#   (numeric, boolean, scale) in a single schema using optional fields.
#
# HOW THE VALUE FIELDS WORK:
#   The client sends ONE of: value_numeric, value_boolean, or value_scale.
#   Which one depends on the habit's type.
#   The service layer validates that the correct field is provided.
#
# EXAMPLE REQUESTS:
#   Numeric: {"habit_id": "...", "log_date": "2026-09-26", "value_numeric": 8.0}
#   Boolean: {"habit_id": "...", "log_date": "2026-09-26", "value_boolean": true}
#   Scale:   {"habit_id": "...", "log_date": "2026-09-26", "value_scale": 7}
# ============================================================================

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.base_schemas import BaseSchema


class LogCreate(BaseModel):
    """
    Schema for creating a single log entry (POST /logs).

    The client provides the habit_id, date, and the value.
    Only ONE value field should be filled (matching the habit's type).

    Example request bodies:
        Numeric: {"habit_id": "...", "log_date": "2026-09-26", "value_numeric": 8.0}
        Boolean: {"habit_id": "...", "log_date": "2026-09-26", "value_boolean": true}
        Scale:   {"habit_id": "...", "log_date": "2026-09-26", "value_scale": 7}
    """

    habit_id: UUID = Field(
        ...,
        description="ID of the habit to log",
    )
    log_date: date = Field(
        ...,
        description="Date to log for (today or past dates, not future)",
        examples=["2026-09-26"],
    )

    # ── Value Fields (only one should be provided) ──
    value_numeric: float | None = Field(
        default=None,
        ge=0,                      # Must be non-negative
        le=100000,                 # Reasonable upper limit
        description="Numeric value (for numeric habits: glasses, hours, steps)",
        examples=[8.0, 7.5, 10000],
    )
    value_boolean: bool | None = Field(
        default=None,
        description="Boolean value (for boolean habits: did it or not)",
        examples=[True, False],
    )
    value_scale: int | None = Field(
        default=None,
        ge=1,                      # Minimum 1
        le=10,                     # Maximum 10
        description="Scale value 1-10 (for scale habits: mood, energy)",
        examples=[7, 5, 9],
    )

    # ── Optional Notes ──
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional notes for this entry",
        examples=["Felt great today!", "Missed morning workout"],
    )


class BulkLogCreate(BaseModel):
    """
    Schema for logging multiple habits at once (POST /logs/bulk).

    This is used by the daily check-in page where the user fills in
    ALL their habits at once and hits "Save All".

    Example request body:
    {
        "log_date": "2026-09-26",
        "entries": [
            {"habit_id": "uuid-water", "value_numeric": 8},
            {"habit_id": "uuid-exercise", "value_boolean": true},
            {"habit_id": "uuid-mood", "value_scale": 7}
        ]
    }
    """

    log_date: date = Field(
        ...,
        description="Date for all entries (typically today)",
    )
    entries: list["BulkLogEntry"] = Field(
        ...,
        min_length=1,
        max_length=30,          # Max 30 habits in one bulk request
        description="List of habit values to log",
    )


class BulkLogEntry(BaseModel):
    """Single entry within a bulk log request."""

    habit_id: UUID
    value_numeric: float | None = Field(default=None, ge=0, le=100000)
    value_boolean: bool | None = None
    value_scale: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=500)


class LogUpdate(BaseModel):
    """
    Schema for updating a log entry (PUT /logs/:id).

    Only value fields and notes can be updated.
    habit_id and log_date cannot change (create a new entry instead).
    """

    value_numeric: float | None = Field(default=None, ge=0, le=100000)
    value_boolean: bool | None = None
    value_scale: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = Field(default=None, max_length=500)


class LogResponse(BaseSchema):
    """
    Schema for log data in API responses.

    Example response:
    {
        "id": "550e8400-...",
        "habit_id": "660e8400-...",
        "log_date": "2026-09-26",
        "value_numeric": 8.0,
        "value_boolean": null,
        "value_scale": null,
        "notes": "Drank extra water today",
        "created_at": "2026-09-26T10:00:00Z"
    }
    """

    id: UUID
    habit_id: UUID
    log_date: date
    value_numeric: float | None
    value_boolean: bool | None
    value_scale: int | None
    notes: str | None
    created_at: datetime


class DailyLogSummary(BaseModel):
    """
    Summary of a single day's logs — used on the dashboard.

    Example:
    {
        "date": "2026-09-26",
        "logged_count": 4,
        "total_habits": 6,
        "completion_percentage": 66.7
    }
    """

    date: date
    logged_count: int
    total_habits: int
    completion_percentage: float
```

### Key Schema Concepts

**`log_date: date` — Date type in Pydantic**
- Pydantic accepts date strings in ISO format: `"2026-09-26"` → Python `date(2026, 9, 26)`
- `date` (no time) vs `datetime` (with time) — logs are for a calendar day, not a moment

**Three optional value fields with constraints:**
```python
value_numeric: float | None = Field(default=None, ge=0, le=100000)
value_scale: int | None = Field(default=None, ge=1, le=10)
value_boolean: bool | None = Field(default=None)
```
- All three are optional (default `None`). The service validates that exactly ONE is provided (matching the habit type)
- `ge=1, le=10` on `value_scale` — Pydantic rejects values outside 1-10 before the service even runs
- `ge=0` on `value_numeric` — no negative values (you can't drink -3 glasses of water)

**`BulkLogCreate` — Nested schema:**
```python
class BulkLogCreate(BaseModel):
    log_date: date
    entries: list["BulkLogEntry"]
```
- `log_date` at the top level — shared by all entries (user is logging "today" for everything)
- `entries` is a list of `BulkLogEntry` objects — each with its own `habit_id` and value
- `max_length=30` — reasonable cap. Max 20 habits + some buffer

**`LogResponse` includes `habit_id`:**
- Unlike HabitResponse (doesn't include user_id), LogResponse DOES include habit_id
- The frontend needs to know which habit each log belongs to (for rendering on the check-in page)

**`DailyLogSummary` — Dashboard widget:**
- Shows "4 of 6 habits logged (67%)" on the dashboard
- Calculated by the service layer, not stored in the database

---

<a name="migration"></a>
## 5. File 4: `003_create_habit_logs_table.py` — Migration

### Type This Code: `backend/alembic/versions/003_create_habit_logs_table.py`

```python
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
        sa.UniqueConstraint("user_id", "habit_id", "log_date", name="uq_user_habit_date"),
    )

    # ── Indexes ──

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
```

### Index Strategy Explained

Each index serves a specific query pattern:

| Index | Columns | Query Pattern | Used By |
|-------|---------|--------------|---------|
| `ix_habit_logs_user_date` | `(user_id, log_date)` | "All logs for today" | Daily check-in page |
| `ix_habit_logs_habit_date` | `(habit_id, log_date)` | "This habit's history" | Streak calculation, charts |
| `ix_habit_logs_user_id` | `(user_id)` | "All logs for this user" | General scoping |
| `uq_user_habit_date` | `(user_id, habit_id, log_date)` | Duplicate prevention | Unique constraint (also acts as index) |

**Why not index everything?** Each index:
- Speeds up reads ✅
- Slows down writes ❌ (index must be updated on INSERT/UPDATE)
- Uses disk space ❌

For a health tracker, reads vastly outnumber writes (dashboard loads every time the user opens the app, logs are created once per day), so indexing for read performance is the right trade-off.

---

<a name="connections"></a>
## 6. How These Files Connect

```
POST /api/v1/logs
Body: {"habit_id":"water-id","log_date":"2026-09-26","value_numeric":7}
         │
         ▼
  schemas.py → LogCreate
    ✅ habit_id: valid UUID
    ✅ log_date: "2026-09-26" → date object
    ✅ value_numeric: 7.0 (ge=0, le=100000)
    ✅ value_boolean: None (not provided)
    ✅ value_scale: None (not provided)
         │
         ▼
  service.py (Part 06b)
    1. log_date > today? → FutureDateError (422)
    2. Habit exists for this user? → HabitNotFoundError (404)
    3. Existing log for this habit+date? → DuplicateLogError (409)
    4. Habit type is "numeric" → value_numeric must be provided ✅
         │
         ▼
  models.py → HabitLog
    INSERT INTO habit_logs (user_id, habit_id, log_date, value_numeric, ...)
    UNIQUE constraint: (user_id, habit_id, log_date) — database-level safety net
         │
         ▼
  schemas.py → LogResponse
    {"id":"log-001","habit_id":"water-id","log_date":"2026-09-26",
     "value_numeric":7.0,"value_boolean":null,"value_scale":null,...}
```

---

<a name="design-decisions"></a>
## 7. Design Decisions

### Design Decision: Index Per Query Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Index Strategy for habit_logs                     │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: One index per major query pattern (3 indexes + UNIQUE)     │
│                                                                     │
│  WHY:                                                               │
│  • (user_id, log_date) — daily check-in: THE most frequent query    │
│  • (habit_id, log_date) — streak/chart: second most frequent       │
│  • (user_id) — general scoping: covers broad user queries          │
│  • UNIQUE constraint also acts as an index on all 3 columns        │
│                                                                     │
│  NOT INDEXED:                                                       │
│  • value_numeric, value_boolean, value_scale — never filtered on    │
│  • notes — text search would need full-text index (overkill)       │
│                                                                     │
│  AT SCALE:                                                          │
│  • Add partial indexes: WHERE value_boolean = true (only log        │
│    dates where habit was completed — smaller index for streaks)     │
│  • Partition by month: PARTITION BY RANGE (log_date) for tables     │
│    with millions of rows                                            │
│                                                                     │
│  INTERVIEW TIP: "We index based on actual query patterns. The daily │
│  check-in loads all logs for a user+date, so (user_id, log_date)   │
│  is our primary composite index. Streak calculation needs            │
│  (habit_id, log_date). We avoid over-indexing to keep writes fast." │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 8. How to Verify Your Work

```bash
# Run migration
docker-compose exec backend alembic upgrade head

# Verify table
docker-compose exec postgres psql -U health_user -d health_tracker -c "\d habit_logs"

# Verify unique constraint
docker-compose exec postgres psql -U health_user -d health_tracker \
  -c "SELECT conname FROM pg_constraint WHERE conname = 'uq_user_habit_date'"

# Verify imports
docker-compose exec backend python -c "
from app.modules.logs.models import HabitLog
from app.modules.logs.exceptions import DuplicateLogError, FutureDateError
from app.modules.logs.schemas import LogCreate, BulkLogCreate, LogResponse
print(f'Table: {HabitLog.__tablename__}')
print(f'Constraints: {[c.name for c in HabitLog.__table__.constraints]}')
print('✅ All logs data layer imports OK')
"
```

---

<a name="what-you-learned"></a>
## 9. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Composite UNIQUE** | Multiple columns must be unique together | `models.py` `__table_args__` |
| 2 | **`__table_args__`** | Table-level constraints in SQLAlchemy | `models.py` |
| 3 | **`Date` vs `DateTime`** | Calendar day (no time) vs specific moment | `log_date` column |
| 4 | **Polymorphic columns** | Multiple typed columns, one filled per row | Three value columns |
| 5 | **Two foreign keys** | References both users AND habits | `user_id`, `habit_id` |
| 6 | **Bulk schema (nested)** | `BulkLogCreate` contains `list[BulkLogEntry]` | `schemas.py` |
| 7 | **Forward reference** | `list["BulkLogEntry"]` — string for class not yet defined | `schemas.py` |
| 8 | **Index per query pattern** | Design indexes based on actual queries, not guessing | Migration |
| 9 | **UNIQUE as index** | UNIQUE constraints automatically create an index | Migration |
| 10 | **`ge=1, le=10`** | Range constraints for scale values | `schemas.py` |

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: Why a composite UNIQUE constraint instead of checking in the service?
**A:** "Defense in depth. The service checks for duplicates before inserting, but race conditions can slip through — two concurrent requests checking simultaneously both find no duplicate, then both insert. The database UNIQUE constraint catches this: one insert succeeds, the other fails with an IntegrityError that we convert to a friendly DuplicateLogError. The service check gives a nice error message; the database constraint guarantees correctness."

### Q2: Why three value columns instead of a JSONB column?
**A:** "Type safety and query performance. With three columns, PostgreSQL knows `value_numeric` is a FLOAT — we can use `AVG()`, `SUM()`, `MIN()`, `MAX()` directly. A JSONB column would require casting (`(value->>'numeric')::float`) which is slower and loses column-level constraints like `ge=0` or `le=10`. The trade-off is two NULL columns per row (~10 bytes), which is negligible compared to the query and type-safety benefits."

### Q3: How does the Date type differ from DateTime and why use it here?
**A:** "Date stores just the calendar day (2026-09-26) without time. DateTime stores a specific moment (2026-09-26T22:00:00Z). We use Date because a log represents a whole day — 'I drank 7 glasses today.' The time the user entered it doesn't affect which day it belongs to. Using DateTime would add timezone complexity: did the user mean September 26th in their timezone or UTC? Date eliminates this ambiguity."

### Q4: What is the index strategy and why these specific indexes?
**A:** "Each index maps to a real query: (user_id, log_date) for the daily check-in page — the most frequent query. (habit_id, log_date) for streak calculations and habit-specific charts. (user_id) alone for general scoping. We don't index value columns because they're never in WHERE clauses — they're only in SELECT. Over-indexing slows writes without benefiting reads."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 06: Logs Module Overview](./phase4-part06-logs-service-overview.md) |
| ➡️ Next | [Phase 4 Part 06b: Logs Repository & Service](./phase4-part06b-logs-repository-service.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Logs Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **06a** | ✅ **You are here** | Logs Models, Exceptions, Schemas & Migration |
| 06b | ⬜ Next | Logs Repository & Service |
| 06c | ⬜ | Logs Router |
| 06d | ⬜ | Logs Connections & Flows |

---

**End of Phase 4 Part 06a: Logs Models, Exceptions, Schemas & Migration**

*The data layer is done — 10-column model with composite UNIQUE, 4 exceptions, 6 schemas including bulk, and a migration with 3 targeted indexes. Next: the repository and service with upsert logic, type validation, and cache invalidation.*
