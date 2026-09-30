# 📊 Phase 4 Part 05a: Habits — Models, Exceptions, Schemas & Migration

> **"The Habits module follows the exact same architecture as Auth. If you understood Part 04a, this will feel familiar — same patterns, new domain. That repetition is intentional: production codebases are consistent."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 05a (Habits Data Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.1 — Habit Management |
| **Previous** | [phase4-part05-habits-service-overview.md](./phase4-part05-habits-service-overview.md) |
| **Next** | [phase4-part05b-habits-repositories.md](./phase4-part05b-habits-repositories.md) |
| **Files in This Doc** | 4 files (models.py, exceptions.py, schemas.py, 002_migration.py) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (new concepts: foreign keys, Enum, field_validator, composite index) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: models.py — Habit Database Model](#models)
3. [File 2: exceptions.py — Habit-Specific Exceptions](#exceptions)
4. [File 3: schemas.py — Request/Response Schemas](#schemas)
5. [File 4: 002_create_habits_table.py — Migration](#migration)
6. [How These 4 Files Connect](#connections)
7. [Design Decisions](#design-decisions)
8. [How to Verify Your Work](#verify)
9. [What You Learned](#what-you-learned)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

Same pattern as Auth (Part 04a), but for a different domain:

| Auth (Part 04a) | Habits (Part 05a) |
|-----------------|-------------------|
| `User` model (8 columns) | `Habit` model (12 columns) |
| 5 exception classes | 4 exception classes |
| 5 schemas | 5 schemas + 1 Enum |
| 001_create_users_table.py | 002_create_habits_table.py |

### What's NEW in This Part (Not in Auth)

| Concept | What It Is | Where |
|---------|-----------|-------|
| **Foreign Key** | `user_id` links habits to users table | `models.py` |
| **`ondelete="CASCADE"`** | If user is deleted, their habits auto-delete | `models.py` |
| **Python Enum** | `HabitType(str, Enum)` — restricts to valid types | `schemas.py` |
| **`field_validator`** | Custom validation for hex color format | `schemas.py` |
| **Composite Index** | Index on `(user_id, is_archived)` — fast filtered queries | Migration |

### File Structure

```
backend/app/modules/habits/
├── __init__.py           ← Empty
├── models.py             ← File 1: Habit table (12 columns)
├── exceptions.py         ← File 2: 4 exception classes
├── schemas.py            ← File 3: 5 schemas + HabitType enum
└── (repository, service, router — later parts)

backend/alembic/versions/
└── 002_create_habits_table.py  ← File 4: Migration
```

---

<a name="models"></a>
## 2. File 1: `models.py` — Habit Database Model

### What Is a Foreign Key? Read This First

A **foreign key** connects two tables. It says "this column references a row in another table."

```
users table:                    habits table:
┌──────────┐                    ┌──────────────────────┐
│ id (PK)  │◄───────────────────│ user_id (FK → users) │
│ email    │                    │ id (PK)              │
│ ...      │                    │ name                 │
└──────────┘                    │ ...                  │
                                └──────────────────────┘

User "Shreya" (id=abc) has habits:
  habit_1: user_id=abc, name="Water"
  habit_2: user_id=abc, name="Sleep"

User "Raj" (id=def) has habits:
  habit_3: user_id=def, name="Exercise"
```

- **PK** = Primary Key (unique identifier for each row)
- **FK** = Foreign Key (references another table's PK)
- `ondelete="CASCADE"` = if the referenced user is deleted, their habits are auto-deleted too

### Type This Code: `backend/app/modules/habits/models.py`

```python
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
```

### Key Differences from User Model (What's New)

**Foreign Key — `user_id`**
```python
user_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
```
- `ForeignKey("users.id")` — this column references the `id` column in the `users` table. PostgreSQL enforces this: you can't insert a habit with a `user_id` that doesn't exist in `users`
- `ondelete="CASCADE"` — if a user row is deleted, PostgreSQL automatically deletes all their habits. Without this, deleting a user would fail (FK constraint violation) or leave orphaned habits
- `index=True` — creates an index on `user_id`. The most common query is "get all habits for user X" — without this index, PostgreSQL scans every row in the table. With it: O(log n) lookup

**Nullable Float — `target_value`**
```python
target_value: Mapped[float | None] = mapped_column(
    Float,
    nullable=True,
)
```
- `float | None` — this can be a number OR null
- Boolean habits ("Did I exercise?") don't have a numeric target — the target is just "yes"
- Scale habits might not have a target (mood doesn't have a "goal")
- Only numeric habits always have a target (8 glasses, 7 hours)

**Integer for Ordering — `sort_order`**
```python
sort_order: Mapped[int] = mapped_column(
    Integer,
    default=0,
    server_default="0",
)
```
- Controls display order on the dashboard. Lower number = higher position
- New habits get `sort_order = max + 1` (go at the end)
- When the user drags and drops, the frontend sends the new order and the service updates all `sort_order` values

**Soft Delete — `is_archived`**
```python
is_archived: Mapped[bool] = mapped_column(
    Boolean,
    default=False,
    server_default="false",
)
```
- Same concept as `is_active` on User, but inverted: `is_archived=True` means hidden
- Naming convention: `is_active` for things that should default to visible, `is_archived` for things that start visible and get hidden
- All queries filter `WHERE is_archived = false` by default

---

<a name="exceptions"></a>
## 3. File 2: `exceptions.py` — Habit-Specific Exceptions

### Type This Code: `backend/app/modules/habits/exceptions.py`

```python
# ============================================================================
# Habits Module — Custom Exceptions
# ============================================================================

from app.shared.exceptions import ConflictError, NotFoundError, ValidationError


class HabitNotFoundError(NotFoundError):
    """Habit does not exist or doesn't belong to this user — HTTP 404."""

    def __init__(self) -> None:
        super().__init__(
            message="Habit not found",
            error_code="HABIT_NOT_FOUND",
        )


class DuplicateHabitNameError(ConflictError):
    """User already has a habit with this name — HTTP 409."""

    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"You already have a habit named '{name}'",
            error_code="DUPLICATE_HABIT_NAME",
        )


class HabitLimitExceededError(ValidationError):
    """User has reached the maximum number of active habits — HTTP 422."""

    MAX_HABITS = 20

    def __init__(self) -> None:
        super().__init__(
            message=f"Maximum {self.MAX_HABITS} active habits allowed. Archive some to add more.",
            error_code="HABIT_LIMIT_EXCEEDED",
        )


class InvalidHabitTypeError(ValidationError):
    """Habit type is not one of: numeric, boolean, scale — HTTP 422."""

    def __init__(self, habit_type: str) -> None:
        super().__init__(
            message=f"Invalid habit type '{habit_type}'. Must be: numeric, boolean, or scale.",
            error_code="INVALID_HABIT_TYPE",
        )
```

### What's New Here (Compared to Auth Exceptions)

**Class-level constant:**
```python
class HabitLimitExceededError(ValidationError):
    MAX_HABITS = 20
```
- `MAX_HABITS = 20` is a **class attribute** — a constant stored on the class itself
- The service layer uses it: `if count >= HabitLimitExceededError.MAX_HABITS`
- Keeps the limit definition in ONE place — change it here, and both the message and the check update

**Dynamic message with f-string:**
```python
def __init__(self, name: str) -> None:
    super().__init__(
        message=f"You already have a habit named '{name}'",
    )
```
- `DuplicateHabitNameError("Water")` → message: "You already have a habit named 'Water'"
- The `name` parameter is included in the error message — helpful for the user

**Exception Hierarchy:**
```
BaseAppError (shared)
├── NotFoundError (404)
│   └── HabitNotFoundError → "Habit not found"
├── ConflictError (409)
│   └── DuplicateHabitNameError → "You already have a habit named '...'"
└── ValidationError (422)
    ├── HabitLimitExceededError → "Maximum 20 active habits"
    └── InvalidHabitTypeError → "Invalid habit type '...'"
```

---

<a name="schemas"></a>
## 4. File 3: `schemas.py` — Request/Response Schemas

### What Is a Python Enum? Read This First

An **Enum** (enumeration) restricts a value to a fixed set of options:

```python
class HabitType(str, Enum):
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    SCALE = "scale"

# Valid:
ht = HabitType("numeric")    # ✅
ht = HabitType.NUMERIC        # ✅

# Invalid:
ht = HabitType("invalid")    # ❌ ValueError!
```

**Why `str, Enum` (not just `Enum`)?**
- Without `str`: `HabitType.NUMERIC` is an Enum object. FastAPI can't serialize it to JSON
- With `str`: `HabitType.NUMERIC` is both a string AND an Enum. `str(HabitType.NUMERIC)` → `"numeric"`. JSON-serializable

### What Is `field_validator`? Read This First

Pydantic's `Field()` handles simple validation (min_length, max_length, ge, le). For **custom validation** that needs logic, use `@field_validator`:

```python
@field_validator("color")
@classmethod
def validate_color(cls, v: str) -> str:
    if not v.startswith("#") or len(v) != 7:
        raise ValueError("Color must be in #RRGGBB format")
    return v.upper()  # Normalize: "#3b82f6" → "#3B82F6"
```

- `@field_validator("color")` — runs when the `color` field is set
- `@classmethod` — required by Pydantic v2 (validator is a class method, not instance)
- `cls` — the class itself (not used, but required)
- `v` — the value to validate
- `raise ValueError(...)` — Pydantic catches this and includes it in the 422 response
- Return the (possibly modified) value — `v.upper()` normalizes case

### Type This Code: `backend/app/modules/habits/schemas.py`

```python
# ============================================================================
# Habits Module — Pydantic Schemas (Request/Response Models)
# ============================================================================
# WHAT THIS FILE DOES:
#   Validates incoming data and controls outgoing data for habit endpoints.
#
# VALIDATION EXAMPLES:
#   - name must be 1-100 characters
#   - habit_type must be one of: numeric, boolean, scale
#   - color must be a valid hex color (#RRGGBB)
#   - target_value required for numeric habits, optional for others
# ============================================================================

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.base_schemas import BaseSchema


class HabitType(str, Enum):
    """
    Valid habit types.

    Using an Enum gives us:
    1. Auto-validation — Pydantic rejects invalid types automatically
    2. Swagger docs — dropdown shows valid options
    3. Type safety — IDE autocomplete and error checking

    WHY str + Enum:
        Inheriting from str makes the enum JSON-serializable.
        Without str, FastAPI can't serialize it in responses.
    """

    NUMERIC = "numeric"     # Value is a number: 8 glasses, 7.5 hours, 10000 steps
    BOOLEAN = "boolean"     # Value is yes/no: Did I exercise? Did I meditate?
    SCALE = "scale"         # Value is 1-10: mood rating, energy level, pain level


class HabitCreate(BaseModel):
    """
    Schema for creating a new habit (POST /habits).

    Example request body:
    {
        "name": "Water Intake",
        "habit_type": "numeric",
        "unit": "glasses",
        "target_value": 8,
        "color": "#3B82F6",
        "icon": "💧"
    }
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Habit name displayed on dashboard",
        examples=["Water Intake", "Sleep Hours", "Exercise", "Mood"],
    )
    habit_type: HabitType = Field(
        ...,
        description="Type of tracking: numeric (number), boolean (yes/no), scale (1-10)",
        examples=["numeric"],
    )
    unit: str = Field(
        default="",
        max_length=50,
        description="Unit of measurement. Leave empty for boolean/scale.",
        examples=["glasses", "hours", "steps", "minutes"],
    )
    target_value: float | None = Field(
        default=None,
        ge=0,                  # ge = greater than or equal to 0
        le=100000,             # reasonable upper limit
        description="Daily target value. Required for numeric habits.",
        examples=[8, 7.5, 10000],
    )
    color: str = Field(
        default="#3B82F6",
        max_length=7,
        description="Hex color code for UI",
        examples=["#3B82F6", "#10B981", "#F59E0B", "#EF4444"],
    )
    icon: str = Field(
        default="⭐",
        max_length=50,
        description="Emoji or icon identifier",
        examples=["💧", "😴", "🏃", "😊", "📖"],
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate hex color format: must be #RRGGBB."""
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format (e.g., #3B82F6)")
        # Validate hex characters
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color code")
        return v.upper()

    @field_validator("target_value")
    @classmethod
    def validate_target_for_type(cls, v: float | None, info) -> float | None:
        """Warn if numeric habit has no target (but don't block — user might set later)."""
        return v


class HabitUpdate(BaseModel):
    """
    Schema for updating a habit (PUT /habits/:id).

    All fields optional — only update what's provided.
    Cannot change habit_type after creation (would break existing log data).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=50)
    target_value: float | None = Field(default=None, ge=0, le=100000)
    color: str | None = Field(default=None, max_length=7)
    icon: str | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be in #RRGGBB format")
        try:
            int(v[1:], 16)
        except ValueError:
            raise ValueError("Color must be a valid hex color code")
        return v.upper()


class HabitResponse(BaseSchema):
    """
    Schema for habit data in API responses.

    Example response:
    {
        "id": "550e8400-...",
        "name": "Water Intake",
        "habit_type": "numeric",
        "unit": "glasses",
        "target_value": 8.0,
        "color": "#3B82F6",
        "icon": "💧",
        "sort_order": 0,
        "is_archived": false,
        "created_at": "2026-09-26T10:00:00Z"
    }
    """

    id: UUID
    name: str
    habit_type: str
    unit: str
    target_value: float | None
    color: str
    icon: str
    sort_order: int
    is_archived: bool
    created_at: datetime


class HabitReorderRequest(BaseModel):
    """
    Schema for reordering habits (PUT /habits/reorder).

    The frontend sends the new order as a list of habit IDs.
    The position in the list = the new sort_order.

    Example request body:
    {
        "habit_ids": [
            "uuid-of-sleep",     ← sort_order = 0
            "uuid-of-water",     ← sort_order = 1
            "uuid-of-exercise"   ← sort_order = 2
        ]
    }
    """

    habit_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="Habit IDs in desired display order",
    )
```

### Key Schema Concepts Explained

**`HabitType(str, Enum)` — Type-safe string enum**
- The three values (`"numeric"`, `"boolean"`, `"scale"`) are the ONLY valid habit types
- If a client sends `"habit_type": "invalid"`, Pydantic rejects it automatically with a 422 error listing the valid options
- In Swagger docs (`/docs`), this shows as a dropdown — no guessing

**`ge=0, le=100000` in Field — Range constraints**
```python
target_value: float | None = Field(default=None, ge=0, le=100000)
```
- `ge` = "greater than or equal to" (≥ 0). No negative targets
- `le` = "less than or equal to" (≤ 100,000). Prevents absurd values. 100K steps is already extreme
- These generate automatic OpenAPI documentation with min/max values

**`@field_validator("color")` — Custom color validation**
```python
@field_validator("color")
@classmethod
def validate_color(cls, v: str) -> str:
    if not v.startswith("#") or len(v) != 7:
        raise ValueError("Color must be in #RRGGBB format")
    int(v[1:], 16)  # Verify hex characters
    return v.upper()  # Normalize: "#3b82f6" → "#3B82F6"
```
- `int(v[1:], 16)` — parses the hex string (after `#`) as base-16 integer. If it contains non-hex characters (e.g., `#GGHHII`), `int()` raises `ValueError`
- `return v.upper()` — normalizes case. Frontend might send lowercase, we store uppercase. Consistency

**`HabitUpdate` — No `habit_type` field**
```python
class HabitUpdate(BaseModel):
    name: str | None = ...
    unit: str | None = ...
    # NO habit_type field!
```
- `habit_type` is deliberately excluded from `HabitUpdate`. Once a habit is created as "numeric," it CANNOT become "boolean." Why? If you have 30 days of numeric log entries (6.5, 7.0, 8.0), changing to "boolean" makes them meaningless

**`HabitReorderRequest` — List of UUIDs**
```python
class HabitReorderRequest(BaseModel):
    habit_ids: list[UUID] = Field(..., min_length=1)
```
- The frontend sends habit IDs in the desired display order
- `min_length=1` — must have at least one ID (can't reorder nothing)
- Position in the array = new `sort_order` value (index 0 → sort_order 0)

**`HabitResponse` — What the client sees**
- Includes `is_archived` so the settings page can show archived habits differently
- Includes `sort_order` so the frontend knows the display order
- Does NOT include `user_id` — the client already knows who they are (from the JWT)
- Inherits from `BaseSchema` (has `from_attributes=True` for ORM → Pydantic conversion)

---

<a name="migration"></a>
## 5. File 4: `002_create_habits_table.py` — Migration

### Type This Code: `backend/alembic/versions/002_create_habits_table.py`

```python
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
```

### What's New in This Migration (vs 001)

**`down_revision = "001"`** — This migration runs AFTER 001. Alembic follows the chain.

**Foreign Key in migration:**
```python
sa.Column(
    "user_id", UUID(as_uuid=True),
    sa.ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
),
```
- Creates: `FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE`
- The users table (migration 001) must exist first — that's why the version chain matters

**Composite Index:**
```python
op.create_index(
    "ix_habits_user_active",
    "habits",
    ["user_id", "is_archived"],
)
```
- A **composite index** covers TWO columns. PostgreSQL can use it for queries that filter on BOTH:
  ```sql
  SELECT * FROM habits WHERE user_id = ? AND is_archived = false
  ```
- This is THE most common query — every dashboard load. Without this index, PostgreSQL would scan every habit row. With it: instant lookup
- **Index naming convention:** `ix_{table}_{column(s)}` — makes it clear what the index covers

**Downgrade drops indexes BEFORE the table:**
```python
def downgrade() -> None:
    op.drop_index("ix_habits_user_active")  # ← Drop indexes first
    op.drop_index("ix_habits_user_id")
    op.drop_table("habits")                  # ← Then drop table
```
- Indexes reference the table. Drop them first, then drop the table. Reverse order of creation

---

<a name="connections"></a>
## 6. How These 4 Files Connect

```
┌─────────────────────────────────────────────────────────────────┐
│  POST /api/v1/habits                                             │
│  Body: {"name":"Water","habit_type":"numeric","target_value":8}  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  schemas.py → HabitCreate                                         │
│  ✅ name: 1-100 chars                                            │
│  ✅ habit_type: "numeric" (valid HabitType enum value)            │
│  ✅ target_value: 8.0 (ge=0, le=100000)                          │
│  ✅ color: "#3B82F6" (default, validated by field_validator)      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  service.py (Part 05c)                                            │
│  1. Count active habits → under 20 limit ✅                       │
│  2. Check name "Water" not duplicate ✅                           │
│  3. Get next sort_order → 3                                       │
│  4. repo.create(user_id=..., name="Water", habit_type="numeric")  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  models.py → Habit                                                │
│  INSERT INTO habits (id, user_id, name, habit_type, ...)          │
│  Values auto-filled: id (uuid4), created_at (now), sort_order (3) │
│  FK constraint: user_id must exist in users table                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Response: HabitResponse.model_validate(habit)                    │
│  {"id":"uuid","name":"Water","habit_type":"numeric",              │
│   "target_value":8.0,"color":"#3B82F6","sort_order":3,...}       │
└──────────────────────────────────────────────────────────────────┘
```

---

<a name="design-decisions"></a>
## 7. Design Decisions

### Design Decision: Composite Index for Dashboard Query

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Index Strategy for Habits                         │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Composite index on (user_id, is_archived)                  │
│                                                                     │
│  WHY:                                                               │
│  • The dashboard query runs on EVERY page load:                     │
│    SELECT * FROM habits WHERE user_id=? AND is_archived=false       │
│  • Without index: full table scan (~100ms for 1M habits)            │
│  • With composite index: direct lookup (~1ms)                       │
│  • Single-column index on user_id would still scan all habits       │
│    for that user to filter is_archived                              │
│                                                                     │
│  AT SCALE: Add partial index for even faster queries:               │
│    CREATE INDEX ix_active_habits ON habits (user_id)                │
│    WHERE is_archived = false;                                       │
│  Partial index only indexes active habits — smaller, faster.        │
│                                                                     │
│  INTERVIEW TIP: "We use a composite index on (user_id, is_archived) │
│  because the dashboard query filters on both columns. PostgreSQL    │
│  can satisfy the entire WHERE clause from the index alone."         │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 8. How to Verify Your Work

```bash
# Run migration
docker-compose exec backend alembic upgrade head

# Check habits table
docker-compose exec postgres psql -U health_user -d health_tracker -c "\d habits"
# Expected: 12 columns, foreign key to users, indexes

# Verify imports
docker-compose exec backend python -c "
from app.modules.habits.models import Habit
from app.modules.habits.exceptions import HabitNotFoundError, DuplicateHabitNameError
from app.modules.habits.schemas import HabitCreate, HabitType, HabitResponse
print(f'Table: {Habit.__tablename__}')
print(f'Types: {[t.value for t in HabitType]}')
print('✅ All habits data layer imports OK')
"

# Test schema validation
docker-compose exec backend python -c "
from app.modules.habits.schemas import HabitCreate, HabitType
# Valid
h = HabitCreate(name='Water', habit_type='numeric', target_value=8)
print(f'Valid: {h.name}, type={h.habit_type}')

# Invalid type
try:
    HabitCreate(name='Bad', habit_type='invalid')
except Exception as e:
    print(f'Invalid type caught ✅')

# Invalid color
try:
    HabitCreate(name='Bad', habit_type='numeric', color='red')
except Exception as e:
    print(f'Invalid color caught ✅')

print('✅ Schema validation works')
"
```

---

<a name="what-you-learned"></a>
## 9. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Foreign Key** | Links habits to users — `ForeignKey("users.id")` | `models.py` |
| 2 | **`ondelete="CASCADE"`** | Auto-delete habits when user is deleted | `models.py` |
| 3 | **Nullable Float** | `float \| None` — for optional numeric values | `models.py` (target_value) |
| 4 | **`str, Enum`** | JSON-serializable enum — restricts to fixed values | `schemas.py` (HabitType) |
| 5 | **`@field_validator`** | Custom Pydantic validation with Python logic | `schemas.py` (color) |
| 6 | **`@classmethod`** | Required decorator for Pydantic v2 validators | `schemas.py` |
| 7 | **`int(v, 16)`** | Parse string as hexadecimal number | Color validation |
| 8 | **`ge=0, le=100000`** | Range constraints in `Field()` | `schemas.py` (target_value) |
| 9 | **Class attribute** | `MAX_HABITS = 20` on the exception class | `exceptions.py` |
| 10 | **Composite Index** | Index on two columns for combined WHERE clauses | Migration |
| 11 | **`down_revision`** | Links migrations in a chain (002 → 001 → None) | Migration |
| 12 | **Immutable field** | `habit_type` excluded from `HabitUpdate` — can't change after creation | `schemas.py` |

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: Why use a foreign key with CASCADE delete?
**A:** "The foreign key ensures referential integrity — you can't create a habit for a non-existent user. CASCADE delete means if a user account is deleted, their habits are automatically removed by PostgreSQL. Without CASCADE, deleting a user would either fail (FK violation) or leave orphaned habits with no owner. In practice, we use soft delete for users (is_active=False), so CASCADE rarely fires. But it's a safety net."

### Q2: Why is habit_type a string in the database but an Enum in Pydantic?
**A:** "Flexibility vs safety at different layers. In the database, a string column lets us add new habit types without an ALTER TYPE migration — just add a value to the Pydantic Enum and deploy. Validation happens at the API layer (Pydantic rejects invalid types) rather than at the database layer. A PostgreSQL ENUM type would require `ALTER TYPE habit_type ADD VALUE 'new_type'` migration for each new type — more friction."

### Q3: What is a composite index and when would you use one?
**A:** "A composite index covers multiple columns. PostgreSQL can use it when a query filters on those columns together. Our dashboard query is `WHERE user_id = ? AND is_archived = false` — a single-column index on user_id would find the user's habits but still scan all of them to check is_archived. The composite index on (user_id, is_archived) satisfies both conditions directly. Rule of thumb: if a WHERE clause always filters on the same columns together, create a composite index."

### Q4: Why can't habit_type be changed after creation?
**A:** "If a habit has 30 days of numeric log entries (7.5, 8.0, 6.5) and you change its type to boolean, those values become meaningless — what does 7.5 mean for a yes/no habit? The frontend charts would break, analytics would produce garbage, and the AI module couldn't interpret the data. We prevent this by excluding habit_type from the HabitUpdate schema entirely."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 05: Habits Module Overview](./phase4-part05-habits-service-overview.md) |
| ➡️ Next | [Phase 4 Part 05b: Habits Repository](./phase4-part05b-habits-repositories.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Habits Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **05a** | ✅ **You are here** | Habits Models, Exceptions, Schemas & Migration |
| 05b | ⬜ Next | Habits Repository |
| 05c | ⬜ | Habits Service |
| 05d | ⬜ | Habits Router |
| 05e | ⬜ | Habits Connections & Flows |

---

**End of Phase 4 Part 05a: Habits Models, Exceptions, Schemas & Migration**

*The data layer is done — 12-column model, 4 exception classes, 5 schemas with enum and custom validation, and a migration with composite indexes. Next: the repository layer with user-scoped queries.*
