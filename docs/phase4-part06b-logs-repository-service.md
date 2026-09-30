# 📝 Phase 4 Part 06b: Logs — Repository & Service

> **"The Logs service is the most complex service so far. It validates value types against habit types, prevents future dates, handles bulk upserts, and invalidates the analytics cache. Three modules collaborate in a single request — Auth, Habits, and Logs."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 06b (Logs Business Layer) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.2 — Daily Logging |
| **Previous** | [phase4-part06a-logs-entities-migrations.md](./phase4-part06a-logs-entities-migrations.md) |
| **Next** | [phase4-part06c-logs-controller.md](./phase4-part06c-logs-controller.md) |
| **Files in This Doc** | 2 files (repository.py, service.py) |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Hard (upsert logic, cross-module validation, cache invalidation, bulk operations) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: repository.py — Full Source Code](#repository)
3. [File 2: service.py — Full Source Code](#service)
4. [Key Concepts Deep Dive](#concepts)
5. [Design Decisions](#design-decisions)
6. [How to Verify Your Work](#verify)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

### Repository — 8 Custom Methods

| # | Method | What It Does |
|---|--------|-------------|
| 1 | `get_logs_for_date(user_id, date)` | All logs for one day (check-in page) |
| 2 | `get_logs_for_range(user_id, start, end, habit_id?)` | Date range with optional habit filter |
| 3 | `get_existing_log(user_id, habit_id, date)` | Find duplicate (for upsert logic) |
| 4 | `get_user_log(user_id, log_id)` | Single log with user-scoping |
| 5 | `count_logs_for_date(user_id, date)` | "X of Y logged today" widget |
| 6 | `get_habit_log_dates(user_id, habit_id, start, end)` | Dates only (for streaks) |
| 7 | `delete_user_log(user_id, log_id)` | Hard delete with user-scoping |
| + 5 inherited | `create`, `get_by_id`, `get_all`, `update`, `delete` | From BaseRepository |

### Service — 6 Business Methods + 4 Private Helpers

| # | Method | What It Does | What's New |
|---|--------|-------------|-----------|
| 1 | `create_log()` | Single log with full validation | Cross-module type check |
| 2 | `bulk_create_logs()` | Daily check-in (upsert all) | Upsert logic |
| 3 | `get_logs_for_date()` | Get today's logs | Passthrough |
| 4 | `get_logs_for_range()` | Get date range | Passthrough with filter |
| 5 | `update_log()` | Update value/notes | Type re-validation |
| 6 | `delete_log()` | Hard delete | Cache invalidation |

### What's New Compared to HabitService

| Feature | HabitService | LogService |
|---------|-------------|-----------|
| Dependencies | session only | session + Redis (for cache) |
| Cross-module | None | Calls HabitRepository (type validation) |
| Bulk operation | None | `bulk_create_logs` (upsert array) |
| Cache | None | Invalidates analytics cache on write |
| Delete type | Soft (archive) | Hard (actual DELETE) |

---

<a name="repository"></a>
## 2. File 1: `repository.py` — Full Source Code

### Type This Code: `backend/app/modules/logs/repository.py`

```python
# ============================================================================
# Logs Module — Repository (Data Access Layer)
# ============================================================================
# WHAT THIS FILE DOES:
#   All database queries for habit log entries.
#   Handles: single/bulk insert, date range queries, daily summaries.
#
# KEY QUERIES:
#   - Get logs for a specific date (today's check-in status)
#   - Get logs for a date range (charts, analytics)
#   - Check if a log already exists (prevent duplicates)
#   - Bulk insert (daily check-in saves all habits at once)
#   - Get log by user+habit+date (for upsert logic)
# ============================================================================

from datetime import date
from uuid import UUID

from sqlalchemy import and_, delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.logs.models import HabitLog
from app.shared.base_repository import BaseRepository


class LogRepository(BaseRepository[HabitLog]):
    """
    HabitLog-specific database operations.

    Inherits CRUD from BaseRepository.
    Adds: date-scoped queries, duplicate detection, bulk operations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(HabitLog, session)

    async def get_logs_for_date(
        self,
        user_id: UUID,
        log_date: date,
    ) -> list[HabitLog]:
        """
        Get all log entries for a specific date.

        Used by: daily check-in page (show what's already logged today).

        Returns logs ordered by habit creation (consistent order).
        """
        result = await self.session.execute(
            select(HabitLog)
            .where(
                HabitLog.user_id == user_id,
                HabitLog.log_date == log_date,
            )
            .order_by(HabitLog.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_logs_for_range(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        habit_id: UUID | None = None,
    ) -> list[HabitLog]:
        """
        Get all log entries within a date range.

        Used by: charts (monthly trend), analytics (weekly summary), AI context.

        Optionally filter by a specific habit.
        If habit_id is None, returns logs for ALL habits in the range.

        Example:
            get_logs_for_range(user_id, date(2026, 9, 1), date(2026, 9, 30))
            → All September logs for all habits

            get_logs_for_range(user_id, start, end, habit_id=water_habit_id)
            → Only water intake logs for the range
        """
        query = select(HabitLog).where(
            HabitLog.user_id == user_id,
            HabitLog.log_date >= start_date,
            HabitLog.log_date <= end_date,
        )

        if habit_id:
            query = query.where(HabitLog.habit_id == habit_id)

        query = query.order_by(HabitLog.log_date.asc(), HabitLog.created_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_existing_log(
        self,
        user_id: UUID,
        habit_id: UUID,
        log_date: date,
    ) -> HabitLog | None:
        """
        Find an existing log for a specific user+habit+date combination.

        Used for:
        1. Duplicate detection (before creating a new log)
        2. Upsert logic (create if not exists, update if exists)

        The unique constraint (user_id, habit_id, log_date) guarantees
        at most one result.
        """
        result = await self.session.execute(
            select(HabitLog).where(
                HabitLog.user_id == user_id,
                HabitLog.habit_id == habit_id,
                HabitLog.log_date == log_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_log(self, user_id: UUID, log_id: UUID) -> HabitLog | None:
        """
        Get a single log entry — only if it belongs to this user.

        Same user-scoping pattern as habits: always filter by user_id
        to prevent users accessing each other's data.
        """
        result = await self.session.execute(
            select(HabitLog).where(
                HabitLog.id == log_id,
                HabitLog.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_logs_for_date(self, user_id: UUID, log_date: date) -> int:
        """
        Count how many habits were logged on a specific date.

        Used for: dashboard "X of Y habits logged today" progress.
        """
        result = await self.session.execute(
            select(func.count()).where(
                HabitLog.user_id == user_id,
                HabitLog.log_date == log_date,
            )
        )
        return result.scalar_one()

    async def get_habit_log_dates(
        self,
        user_id: UUID,
        habit_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        """
        Get all dates where a specific habit was logged within a range.

        Used for: streak calculation, contribution calendar (GitHub-style).

        Returns just dates (not full log objects) — lighter query.
        """
        result = await self.session.execute(
            select(HabitLog.log_date)
            .where(
                HabitLog.user_id == user_id,
                HabitLog.habit_id == habit_id,
                HabitLog.log_date >= start_date,
                HabitLog.log_date <= end_date,
            )
            .order_by(HabitLog.log_date.asc())
        )
        return list(result.scalars().all())

    async def delete_user_log(self, user_id: UUID, log_id: UUID) -> bool:
        """
        Delete a log entry (hard delete — log data is not critical to preserve).

        Unlike habits (soft delete), log entries can be truly deleted.
        The user just wants to remove an incorrect entry.
        """
        result = await self.session.execute(
            sa_delete(HabitLog).where(
                HabitLog.id == log_id,
                HabitLog.user_id == user_id,
            )
        )
        await self.session.flush()
        return result.rowcount > 0
```

### Key Repository Methods Explained

**`get_logs_for_range()` — Dynamic query with optional filter:**
```python
query = select(HabitLog).where(
    HabitLog.user_id == user_id,
    HabitLog.log_date >= start_date,
    HabitLog.log_date <= end_date,
)
if habit_id:
    query = query.where(HabitLog.habit_id == habit_id)
```
- `>=` and `<=` → SQL `BETWEEN` equivalent: `WHERE log_date >= '2026-09-01' AND log_date <= '2026-09-30'`
- Optional `habit_id` filter — if provided, narrows to one habit. If None, returns all habits
- This powers charts, analytics, AI context, and CSV exports

**`get_existing_log()` — The upsert helper:**
- Finds an existing log by the unique triple `(user_id, habit_id, log_date)`
- Returns the log object if found (service updates it), or None (service creates new)
- The UNIQUE constraint guarantees at most one result

**`get_habit_log_dates()` — Lightweight date list:**
```python
select(HabitLog.log_date)  # Only the date column, not the full row
```
- Returns just `list[date]` — not full HabitLog objects
- Used for streak calculation: "consecutive days with a log"
- Much lighter than loading full rows when you only need dates

**`delete_user_log()` — Hard delete:**
```python
sa_delete(HabitLog).where(HabitLog.id == log_id, HabitLog.user_id == user_id)
```
- Actual `DELETE FROM` SQL — row is permanently removed
- Still user-scoped: `HabitLog.user_id == user_id` prevents deleting other users' logs
- `result.rowcount > 0` — returns True if a row was actually deleted, False if log didn't exist

---

<a name="service"></a>
## 3. File 2: `service.py` — Full Source Code

### Type This Code: `backend/app/modules/logs/service.py`

```python
# ============================================================================
# Logs Module — Service Layer (Business Logic)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains all log-related business logic.
#   Validates values match habit types, prevents future dates,
#   handles bulk logging, and manages cache invalidation.
#
# BUSINESS RULES:
#   - Cannot log for future dates
#   - Value must match habit type (numeric → value_numeric, etc.)
#   - Scale values must be 1-10
#   - One log per habit per day (duplicate → error with "use update instead")
#   - Bulk log creates/updates all entries in a single transaction
#   - Creating/updating a log invalidates analytics cache (Redis)
# ============================================================================

from datetime import date
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.models import Habit
from app.modules.habits.repository import HabitRepository
from app.modules.habits.exceptions import HabitNotFoundError
from app.modules.logs.exceptions import (
    DuplicateLogError,
    FutureDateError,
    InvalidLogValueError,
    LogNotFoundError,
)
from app.modules.logs.models import HabitLog
from app.modules.logs.repository import LogRepository
from app.modules.logs.schemas import BulkLogCreate, LogCreate, LogUpdate
from app.shared.date_utils import today_utc
from app.shared.logging import get_logger

logger = get_logger(__name__)


class LogService:
    """
    Habit logging service.

    Handles: creating logs with type validation, bulk logging,
    updating, deleting, and querying by date range.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis | None = None):
        self.log_repo = LogRepository(session)
        self.habit_repo = HabitRepository(session)
        self.session = session
        self.redis = redis_client

    async def create_log(self, user_id: UUID, data: LogCreate) -> HabitLog:
        """
        Create a single log entry for a habit on a specific date.

        Validates:
        1. Date is not in the future
        2. Habit exists and belongs to this user
        3. No duplicate log for this habit+date
        4. Value matches the habit's type

        Returns the created log entry.
        """
        # Validate: no future dates
        if data.log_date > today_utc():
            raise FutureDateError()

        # Validate: habit exists and belongs to user
        habit = await self.habit_repo.get_user_habit(user_id, data.habit_id)
        if not habit:
            raise HabitNotFoundError()

        # Validate: no duplicate
        existing = await self.log_repo.get_existing_log(
            user_id, data.habit_id, data.log_date
        )
        if existing:
            raise DuplicateLogError(habit.name, str(data.log_date))

        # Validate and extract the correct value for this habit type
        value_fields = self._validate_and_extract_value(habit, data)

        # Create log entry
        log = await self.log_repo.create(
            user_id=user_id,
            habit_id=data.habit_id,
            log_date=data.log_date,
            notes=data.notes,
            **value_fields,
        )

        await self.session.commit()

        # Invalidate cached analytics (streaks, summaries may have changed)
        await self._invalidate_cache(user_id)

        logger.info(
            "log_created",
            user_id=str(user_id),
            habit_id=str(data.habit_id),
            log_date=str(data.log_date),
        )
        return log

    async def bulk_create_logs(
        self, user_id: UUID, data: BulkLogCreate
    ) -> list[HabitLog]:
        """
        Log multiple habits at once (daily check-in "Save All" button).

        For each entry:
        - If no log exists for that habit+date → creates one
        - If a log already exists → updates it (upsert behavior)

        This is more user-friendly than rejecting duplicates during bulk save.
        The user doesn't have to track what they already logged.

        All entries are saved in a SINGLE transaction — if any fail,
        none are saved (atomicity).
        """
        if data.log_date > today_utc():
            raise FutureDateError()

        created_logs = []

        for entry in data.entries:
            # Validate habit exists
            habit = await self.habit_repo.get_user_habit(user_id, entry.habit_id)
            if not habit:
                continue  # Skip invalid habits in bulk mode (don't fail entire batch)

            # Extract value fields
            value_fields = self._validate_and_extract_value_from_entry(habit, entry)

            # Check for existing log (upsert)
            existing = await self.log_repo.get_existing_log(
                user_id, entry.habit_id, data.log_date
            )

            if existing:
                # Update existing log
                for key, value in value_fields.items():
                    setattr(existing, key, value)
                if entry.notes is not None:
                    existing.notes = entry.notes
                await self.session.flush()
                await self.session.refresh(existing)
                created_logs.append(existing)
            else:
                # Create new log
                log = await self.log_repo.create(
                    user_id=user_id,
                    habit_id=entry.habit_id,
                    log_date=data.log_date,
                    notes=entry.notes,
                    **value_fields,
                )
                created_logs.append(log)

        await self.session.commit()
        await self._invalidate_cache(user_id)

        logger.info(
            "bulk_log_created",
            user_id=str(user_id),
            log_date=str(data.log_date),
            count=len(created_logs),
        )
        return created_logs

    async def get_logs_for_date(
        self, user_id: UUID, log_date: date
    ) -> list[HabitLog]:
        """Get all log entries for a specific date."""
        return await self.log_repo.get_logs_for_date(user_id, log_date)

    async def get_logs_for_range(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        habit_id: UUID | None = None,
    ) -> list[HabitLog]:
        """
        Get log entries within a date range.

        Optionally filter by a specific habit.
        Used by: charts, analytics, AI context building, CSV export.
        """
        return await self.log_repo.get_logs_for_range(
            user_id, start_date, end_date, habit_id
        )

    async def update_log(
        self, user_id: UUID, log_id: UUID, data: LogUpdate
    ) -> HabitLog:
        """
        Update an existing log entry's value or notes.

        Validates the new value against the habit's type.
        """
        log = await self.log_repo.get_user_log(user_id, log_id)
        if not log:
            raise LogNotFoundError()

        # Get the habit to validate the value type
        habit = await self.habit_repo.get_user_habit(user_id, log.habit_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return log

        # If any value field is being updated, validate it
        value_keys = {"value_numeric", "value_boolean", "value_scale"}
        if value_keys & set(update_data.keys()):
            # Validate value against habit type
            self._validate_value_for_type(habit, update_data)

        for key, value in update_data.items():
            setattr(log, key, value)

        await self.session.flush()
        await self.session.refresh(log)
        await self.session.commit()
        await self._invalidate_cache(user_id)

        logger.info(
            "log_updated",
            user_id=str(user_id),
            log_id=str(log_id),
            fields=list(update_data.keys()),
        )
        return log

    async def delete_log(self, user_id: UUID, log_id: UUID) -> None:
        """
        Delete a log entry (hard delete).

        Unlike habits, log entries are truly deleted — the user is
        correcting a mistake, not archiving for historical reference.
        """
        deleted = await self.log_repo.delete_user_log(user_id, log_id)
        if not deleted:
            raise LogNotFoundError()

        await self.session.commit()
        await self._invalidate_cache(user_id)

        logger.info("log_deleted", user_id=str(user_id), log_id=str(log_id))

    # ══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _validate_and_extract_value(
        self, habit: Habit, data: LogCreate
    ) -> dict:
        """
        Validate that the provided value matches the habit's type
        and return a dict with only the relevant value field.
        """
        return self._extract_value_dict(
            habit_type=habit.habit_type,
            value_numeric=data.value_numeric,
            value_boolean=data.value_boolean,
            value_scale=data.value_scale,
        )

    def _validate_and_extract_value_from_entry(
        self, habit: Habit, entry
    ) -> dict:
        """Same as above but for bulk log entries."""
        return self._extract_value_dict(
            habit_type=habit.habit_type,
            value_numeric=entry.value_numeric,
            value_boolean=entry.value_boolean,
            value_scale=entry.value_scale,
        )

    def _extract_value_dict(
        self,
        habit_type: str,
        value_numeric: float | None,
        value_boolean: bool | None,
        value_scale: int | None,
    ) -> dict:
        """
        Core validation logic — maps habit type to the correct value field.

        Returns a dict with all three value columns, setting the irrelevant ones to None.
        """
        if habit_type == "numeric":
            if value_numeric is None:
                raise InvalidLogValueError("Numeric habit requires value_numeric")
            return {
                "value_numeric": value_numeric,
                "value_boolean": None,
                "value_scale": None,
            }
        elif habit_type == "boolean":
            if value_boolean is None:
                raise InvalidLogValueError("Boolean habit requires value_boolean")
            return {
                "value_numeric": None,
                "value_boolean": value_boolean,
                "value_scale": None,
            }
        elif habit_type == "scale":
            if value_scale is None:
                raise InvalidLogValueError("Scale habit requires value_scale (1-10)")
            return {
                "value_numeric": None,
                "value_boolean": None,
                "value_scale": value_scale,
            }
        else:
            raise InvalidLogValueError(f"Unknown habit type: {habit_type}")

    @staticmethod
    def _validate_value_for_type(habit: Habit, update_data: dict) -> None:
        """Validate that update data matches the habit type."""
        if habit.habit_type == "numeric" and "value_boolean" in update_data:
            raise InvalidLogValueError("Cannot set boolean value on numeric habit")
        if habit.habit_type == "boolean" and "value_numeric" in update_data:
            raise InvalidLogValueError("Cannot set numeric value on boolean habit")
        if habit.habit_type == "scale" and "value_numeric" in update_data:
            raise InvalidLogValueError("Cannot set numeric value on scale habit")

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """
        Clear cached analytics when log data changes.

        WHY:
            Analytics (streaks, weekly summaries) are cached in Redis.
            When a log is created/updated/deleted, the cached data is stale.
            We delete the cache keys — next request recalculates fresh.

        This is called "cache invalidation" — one of the two hard problems
        in computer science (the other is naming things).
        """
        if self.redis:
            try:
                # Delete all analytics cache keys for this user
                pattern = f"analytics:{user_id}:*"
                keys = []
                async for key in self.redis.scan_iter(match=pattern, count=100):
                    keys.append(key)
                if keys:
                    await self.redis.delete(*keys)
            except Exception:
                # Cache invalidation failure is not critical — don't crash the request
                logger.warning("cache_invalidation_failed", user_id=str(user_id))
```

---

<a name="concepts"></a>
## 4. Key Concepts Deep Dive

### Cross-Module Dependency

```python
from app.modules.habits.repository import HabitRepository
from app.modules.habits.exceptions import HabitNotFoundError

class LogService:
    def __init__(self, session, redis_client):
        self.log_repo = LogRepository(session)
        self.habit_repo = HabitRepository(session)  # ← Cross-module!
```

The Log service creates BOTH a LogRepository AND a HabitRepository. Why?

When a user logs "8 glasses of water," the service must:
1. Verify the habit exists (`habit_repo.get_user_habit`)
2. Check the habit's type is "numeric" (to validate `value_numeric`)
3. Only then create the log entry

This is the first time one module uses another module's repository. The dependency flows: **Logs → Habits** (never the reverse).

### Upsert Logic (Bulk Endpoint)

```python
existing = await self.log_repo.get_existing_log(user_id, entry.habit_id, data.log_date)

if existing:
    # UPDATE existing log
    for key, value in value_fields.items():
        setattr(existing, key, value)
else:
    # CREATE new log
    log = await self.log_repo.create(user_id=..., habit_id=..., ...)
```

**Upsert** = "UPDATE if exists, INSERT if not." This makes the daily check-in idempotent:
- First save: creates all log entries
- Second save: updates existing entries (values might have changed)
- User never sees a "duplicate" error on the check-in page

### Type Validation Pattern

```python
def _extract_value_dict(self, habit_type, value_numeric, value_boolean, value_scale):
    if habit_type == "numeric":
        if value_numeric is None:
            raise InvalidLogValueError("Numeric habit requires value_numeric")
        return {"value_numeric": value_numeric, "value_boolean": None, "value_scale": None}
    elif habit_type == "boolean":
        if value_boolean is None:
            raise InvalidLogValueError("Boolean habit requires value_boolean")
        return {"value_numeric": None, "value_boolean": value_boolean, "value_scale": None}
    # ... scale ...
```

The pattern:
1. Check the habit's type (from the database, not from the request)
2. Verify the matching value field is provided
3. Return a dict with the correct field set and others explicitly NULL
4. Setting others to NULL prevents stale data if a log is updated

### Cache Invalidation

```python
async def _invalidate_cache(self, user_id: UUID) -> None:
    if self.redis:
        pattern = f"analytics:{user_id}:*"
        keys = []
        async for key in self.redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await self.redis.delete(*keys)
```

**When logs change, analytics cache is stale.** The Analytics module (Part 07) caches expensive calculations in Redis:
- `analytics:{user_id}:weekly_summary` → weekly averages
- `analytics:{user_id}:streaks` → consecutive day counts
- `analytics:{user_id}:correlations` → habit correlation data

When a log is created, updated, or deleted, we delete ALL analytics cache keys for that user. Next analytics request recalculates fresh.

**Why `scan_iter` not `keys`?**
- `KEYS pattern` blocks Redis for ALL clients while scanning (dangerous in production)
- `SCAN` is non-blocking — it iterates in batches (`count=100` per batch)
- `async for key in ...` — async iteration, doesn't block the event loop

**Why wrapped in try/except?**
- Cache invalidation is a "nice-to-have" — if Redis is down, we still want the log to be saved
- Worst case: analytics shows slightly stale data until cache expires naturally
- Same "fail open" philosophy as the rate limiter

### Bulk Error Handling — Skip vs Fail

```python
for entry in data.entries:
    habit = await self.habit_repo.get_user_habit(user_id, entry.habit_id)
    if not habit:
        continue  # Skip invalid habits (don't fail entire batch)
```

In bulk mode, if one habit_id is invalid, we **skip** it rather than failing the entire batch. Why?
- The user might have archived a habit after opening the check-in page
- The frontend might have a stale habit list
- Failing all 10 entries because 1 is invalid is poor UX

The single-log endpoint (`create_log`) DOES raise `HabitNotFoundError` — different error handling for different contexts.

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision 1: Cross-Module Repository Access

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: How Logs Validate Against Habits                  │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: LogService creates a HabitRepository for type validation   │
│                                                                     │
│  WHY:                                                               │
│  • Need to verify habit exists AND check its type                   │
│  • Repository pattern keeps all DB access in repositories           │
│  • Same session ensures both queries are in one transaction         │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Store habit_type in habit_logs table (denormalization)           │
│     ❌ Data duplication. If habit type changes, logs are stale.    │
│  2. Pass habit object from router to service                        │
│     ❌ Router shouldn't fetch habits — that's business logic       │
│  3. Call Habits API endpoint (HTTP call from Logs service)           │
│     ❌ Overkill — same process, same database. Network overhead.   │
│                                                                     │
│  RULE: Modules can import each other's REPOSITORIES (data layer)    │
│  but never each other's SERVICES (business layer). This prevents    │
│  circular dependencies while allowing data access.                  │
│                                                                     │
│  INTERVIEW TIP: "The Log service uses the Habit repository to       │
│  validate that the habit exists and check its type. They share the  │
│  same database session, so it's a single transaction. We access     │
│  the data layer cross-module, but never the business layer."        │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Cache Invalidation Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Analytics Cache Invalidation                      │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Delete all analytics keys for the user on any log change   │
│                                                                     │
│  WHY:                                                               │
│  • Simple — one pattern deletion covers all analytics               │
│  • Correct — stale data is never served after a log change          │
│  • Non-blocking — SCAN instead of KEYS, wrapped in try/except       │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Surgical invalidation (only delete affected cache keys)         │
│     ⚠️ More efficient but complex — need to track which keys are   │
│        affected by each log change. Easy to miss edge cases.        │
│  2. TTL-based expiry only (no explicit invalidation)                │
│     ❌ Stale data served until TTL expires (could be minutes)      │
│  3. No caching (recalculate on every request)                       │
│     ❌ Expensive SQL queries on every dashboard load               │
│                                                                     │
│  TRADE-OFF: We invalidate slightly more than necessary (delete ALL  │
│  analytics keys, not just the affected ones). At our scale, the     │
│  extra recalculation is negligible. At larger scale, switch to      │
│  surgical invalidation.                                             │
│                                                                     │
│  INTERVIEW TIP: "We use eager invalidation — delete all analytics   │
│  cache for the user when any log changes. It's simpler and correct. │
│  At scale, we'd switch to surgical invalidation to avoid            │
│  unnecessary recalculations."                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 6. How to Verify Your Work

```bash
docker-compose exec backend python -c "
from app.modules.logs.repository import LogRepository
from app.modules.logs.service import LogService
print('✅ repository.py imports OK')
print('✅ service.py imports OK')
print(f'Repo methods: {[m for m in dir(LogRepository) if not m.startswith(\"_\") and m not in dir(object)]}')
print(f'Service methods: {[m for m in dir(LogService) if not m.startswith(\"_\") and m not in dir(object)]}')
"
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Cross-module repository** | LogService uses HabitRepository for type validation | `service.__init__` |
| 2 | **Upsert pattern** | Check if exists → update or create | `bulk_create_logs` |
| 3 | **Type-value mapping** | habit_type determines which value column to fill | `_extract_value_dict` |
| 4 | **Cache invalidation** | Delete Redis keys when underlying data changes | `_invalidate_cache` |
| 5 | **`scan_iter`** | Non-blocking Redis key scanning (vs blocking `keys`) | `_invalidate_cache` |
| 6 | **`async for`** | Async iteration over Redis scan results | `_invalidate_cache` |
| 7 | **Fail-open cache** | Cache failure doesn't crash the request | try/except in invalidation |
| 8 | **Skip vs fail in bulk** | Invalid entries skipped, not rejected | `bulk_create_logs` |
| 9 | **Hard delete** | `DELETE FROM` — row permanently removed | `delete_user_log` |
| 10 | **Date range queries** | `WHERE log_date >= ? AND log_date <= ?` | `get_logs_for_range` |
| 11 | **Lightweight projection** | `select(HabitLog.log_date)` — only one column | `get_habit_log_dates` |
| 12 | **Idempotent bulk** | Saving twice produces same result (no duplicates) | `bulk_create_logs` |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: How does the upsert work in the bulk endpoint?
**A:** "For each entry in the bulk request, we check if a log already exists for that user+habit+date combination using `get_existing_log()`. If found, we update its value fields with `setattr()`. If not found, we create a new row. This makes the daily check-in idempotent — the user can hit 'Save' multiple times without duplicate errors. All operations happen in a single transaction, so either all succeed or all roll back."

### Q2: How does the Logs module validate against the Habits module?
**A:** "The LogService creates a HabitRepository alongside its own LogRepository, sharing the same database session. When creating a log, it fetches the habit to verify it exists and check its type. If the habit is type 'numeric' but the request provides `value_boolean`, it raises `InvalidLogValueError`. This cross-module data access stays at the repository layer — we never import another module's service to avoid circular dependencies."

### Q3: Explain your cache invalidation strategy.
**A:** "When a log is created, updated, or deleted, we delete all Redis analytics cache keys for that user using `SCAN` (non-blocking pattern match). This ensures analytics always reflects current data. We use SCAN instead of KEYS because KEYS blocks Redis for all clients. Cache invalidation failures are caught silently — if Redis is down, the log is still saved, and analytics serves slightly stale data until cache expires naturally."

### Q4: Why skip invalid habits in bulk mode but fail in single mode?
**A:** "Different user expectations. For single log creation, the user explicitly chose a habit — if it doesn't exist, that's a clear error. For the daily check-in page, the user fills in all habits and hits Save. If one habit was archived between page load and save, failing the entire batch (all 10 entries) because of one stale reference is poor UX. Skipping the invalid entry and saving the rest is the better experience."

### Q5: Why hard delete for logs but soft delete for habits?
**A:** "Logs are leaf data — no other table references them. When a user deletes a log (correcting a mistake), there's nothing to cascade. Habits use soft delete because `habit_logs` references `habit_id` — hard deleting a habit would cascade-delete all its logs. The deletion strategy depends on whether other data depends on the resource."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 06a: Logs Models, Schemas & Migration](./phase4-part06a-logs-entities-migrations.md) |
| ➡️ Next | [Phase 4 Part 06c: Logs Router](./phase4-part06c-logs-controller.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Logs Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 06a | ✅ Done | Logs Models, Exceptions, Schemas & Migration |
| **06b** | ✅ **You are here** | Logs Repository & Service |
| 06c | ⬜ Next | Logs Router |
| 06d | ⬜ | Logs Connections & Flows |

---

**End of Phase 4 Part 06b: Logs Repository & Service**

*The business layer is done — 8 repository methods, 6 service methods, cross-module type validation, upsert logic, and cache invalidation. Next: the router that exposes 5 endpoints with flexible date filtering.*
