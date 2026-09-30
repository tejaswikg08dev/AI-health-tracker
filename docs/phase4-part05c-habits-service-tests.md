# 📊 Phase 4 Part 05c: Habits — Service Layer

> **"The service is the referee. It checks the rules before every play: Is the habit limit reached? Does this name already exist? Is the user allowed to touch this habit? Only after all rules pass does it call the repository to do the actual work."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 05c (Habits Business Logic) |
| **Sprint** | Sprint 2 — Core Tracking |
| **Release** | Release 2.1 — Habit Management |
| **Previous** | [phase4-part05b-habits-repositories.md](./phase4-part05b-habits-repositories.md) |
| **Next** | [phase4-part05d-habits-controller-docker.md](./phase4-part05d-habits-controller-docker.md) |
| **Files in This Doc** | 1 file (service.py) — 6 business methods |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (business rule orchestration, enum-to-string conversion, partial updates) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File: service.py — Full Source Code](#service)
3. [Method-by-Method Walkthrough](#walkthrough)
4. [Business Rules Summary](#rules)
5. [Design Decisions](#design-decisions)
6. [How to Verify Your Work](#verify)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

The `HabitService` sits between the router (HTTP) and the repository (SQL). It enforces every business rule before data touches the database.

### Service Methods Overview

| # | Method | What It Does | Business Rules Checked |
|---|--------|-------------|----------------------|
| 1 | `create_habit()` | Create a new habit | Max 20 limit, no duplicate names, assign sort_order |
| 2 | `get_habits()` | List user's habits | Filter archived by default |
| 3 | `get_habit()` | Get single habit | Must belong to this user |
| 4 | `update_habit()` | Update habit fields | No duplicate names (excluding self), user ownership |
| 5 | `delete_habit()` | Archive (soft delete) | Must belong to this user |
| 6 | `reorder_habits()` | Reorder dashboard | Batch update sort_order |

### Comparison with AuthService

| Feature | AuthService | HabitService |
|---------|-------------|-------------|
| Dependencies | session + Redis | session only (no Redis needed) |
| CRUD operations | register, login, refresh, logout | create, list, get, update, delete |
| External services | JWT creation, bcrypt, Redis blacklist | None (pure DB + business rules) |
| Complexity | High (crypto + token management) | Medium (validation + CRUD orchestration) |

The Habits service is simpler than Auth because there's no cryptography or token management — it's pure business logic on top of database operations.

---

<a name="service"></a>
## 2. File: `service.py` — Full Source Code

### Type This Code: `backend/app/modules/habits/service.py`

```python
# ============================================================================
# Habits Module — Service Layer (Business Logic)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains all habit-related business logic.
#   Validates business rules before delegating to the repository.
#
# BUSINESS RULES:
#   - Maximum 20 active habits per user
#   - No duplicate habit names (per user)
#   - habit_type cannot change after creation (would break log data)
#   - "Delete" is actually soft-delete (archive)
#   - Reorder updates sort_order for all habits in the list
# ============================================================================

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.exceptions import (
    DuplicateHabitNameError,
    HabitLimitExceededError,
    HabitNotFoundError,
)
from app.modules.habits.models import Habit
from app.modules.habits.repository import HabitRepository
from app.modules.habits.schemas import HabitCreate, HabitUpdate
from app.shared.logging import get_logger

logger = get_logger(__name__)


class HabitService:
    """
    Habit management service.

    Handles: creating habits with validation, updating, archiving,
    reordering, and listing with proper user scoping.
    """

    def __init__(self, session: AsyncSession):
        self.repo = HabitRepository(session)
        self.session = session

    async def create_habit(self, user_id: UUID, data: HabitCreate) -> Habit:
        """
        Create a new habit for the user.

        Validates:
        1. User hasn't exceeded the habit limit (20)
        2. No existing habit with the same name
        3. Assigns the next sort_order (goes at the end)

        Returns the created habit.
        """
        # Check habit limit
        active_count = await self.repo.count_active_habits(user_id)
        if active_count >= HabitLimitExceededError.MAX_HABITS:
            raise HabitLimitExceededError()

        # Check duplicate name
        if await self.repo.name_exists_for_user(user_id, data.name):
            raise DuplicateHabitNameError(data.name)

        # Get next sort order
        next_order = await self.repo.get_next_sort_order(user_id)

        # Create the habit
        habit = await self.repo.create(
            user_id=user_id,
            name=data.name,
            habit_type=data.habit_type.value,  # Enum → string for DB
            unit=data.unit,
            target_value=data.target_value,
            color=data.color,
            icon=data.icon,
            sort_order=next_order,
        )

        await self.session.commit()

        logger.info(
            "habit_created",
            user_id=str(user_id),
            habit_id=str(habit.id),
            habit_name=habit.name,
            habit_type=habit.habit_type,
        )
        return habit

    async def get_habits(
        self, user_id: UUID, include_archived: bool = False
    ) -> list[Habit]:
        """
        Get all habits for a user.

        By default returns only active habits (for dashboard).
        Pass include_archived=True for the management/settings page.
        """
        return await self.repo.get_user_habits(user_id, include_archived)

    async def get_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
        """
        Get a single habit by ID.

        Raises HabitNotFoundError if:
        - Habit doesn't exist
        - Habit belongs to a different user
        """
        habit = await self.repo.get_user_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()
        return habit

    async def update_habit(
        self, user_id: UUID, habit_id: UUID, data: HabitUpdate
    ) -> Habit:
        """
        Update a habit's properties.

        Only updates fields that were provided (non-None).
        Validates that the new name doesn't conflict with existing habits.

        NOTE: habit_type is NOT updatable. Changing "numeric" to "boolean"
        would make all existing numeric log entries invalid.
        """
        # Verify habit exists and belongs to user
        habit = await self.repo.get_user_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()

        # Build update dict with only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return habit  # Nothing to update

        # If name is being changed, check for duplicates
        if "name" in update_data and update_data["name"] != habit.name:
            if await self.repo.name_exists_for_user(
                user_id, update_data["name"], exclude_habit_id=habit_id
            ):
                raise DuplicateHabitNameError(update_data["name"])

        # Apply updates
        for key, value in update_data.items():
            setattr(habit, key, value)

        await self.session.flush()
        await self.session.refresh(habit)
        await self.session.commit()

        logger.info(
            "habit_updated",
            user_id=str(user_id),
            habit_id=str(habit_id),
            fields=list(update_data.keys()),
        )
        return habit

    async def delete_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
        """
        Soft delete (archive) a habit.

        Sets is_archived=True. The habit and its log data are preserved.
        User can potentially unarchive it later.
        """
        habit = await self.repo.archive_habit(user_id, habit_id)
        if not habit:
            raise HabitNotFoundError()

        await self.session.commit()

        logger.info(
            "habit_archived",
            user_id=str(user_id),
            habit_id=str(habit_id),
            habit_name=habit.name,
        )
        return habit

    async def reorder_habits(self, user_id: UUID, habit_ids: list[UUID]) -> list[Habit]:
        """
        Reorder habits based on the provided list of IDs.

        The position in the list becomes the sort_order.
        Returns the updated habits in new order.
        """
        await self.repo.reorder_habits(user_id, habit_ids)
        await self.session.commit()

        logger.info(
            "habits_reordered",
            user_id=str(user_id),
            count=len(habit_ids),
        )

        # Return updated habits in new order
        return await self.repo.get_user_habits(user_id)
```

---

<a name="walkthrough"></a>
## 3. Method-by-Method Walkthrough

### Constructor — Simpler Than AuthService

```python
def __init__(self, session: AsyncSession):
    self.repo = HabitRepository(session)
    self.session = session
```

- **Only needs `session`** — no Redis client. Habits don't use Redis (no caching, no blacklisting)
- Compare with AuthService: `def __init__(self, session, redis_client)` — auth needs Redis for token blacklists
- One instance per request, same as AuthService

### `create_habit()` — Three Checks Before Creating

```python
async def create_habit(self, user_id: UUID, data: HabitCreate) -> Habit:
    # Check 1: Habit limit
    active_count = await self.repo.count_active_habits(user_id)
    if active_count >= HabitLimitExceededError.MAX_HABITS:
        raise HabitLimitExceededError()

    # Check 2: Duplicate name
    if await self.repo.name_exists_for_user(user_id, data.name):
        raise DuplicateHabitNameError(data.name)

    # Check 3: Get next position
    next_order = await self.repo.get_next_sort_order(user_id)

    # Create
    habit = await self.repo.create(
        user_id=user_id,
        name=data.name,
        habit_type=data.habit_type.value,  # ← Enum → string
        ...
        sort_order=next_order,
    )

    await self.session.commit()
    return habit
```

**Step-by-step:**

1. **Count active habits** — `count_active_habits` returns the number of non-archived habits. If it's ≥ 20, raise `HabitLimitExceededError` (422)

2. **Check duplicate name** — `name_exists_for_user` checks if the user already has an active habit with this name. If yes, raise `DuplicateHabitNameError("Water Intake")` (409)

3. **Get next sort_order** — new habits go at the END of the dashboard list. If the user has habits with `sort_order` 0, 1, 2, the new one gets 3

4. **Create via repository** — passes all fields as keyword arguments. Note: `data.habit_type.value` — the `.value` converts the Pydantic Enum (`HabitType.NUMERIC`) to a plain string (`"numeric"`) for the database

5. **Commit** — finalizes the transaction. If anything fails between the checks and the commit, everything rolls back

6. **Log** — structured log with user_id, habit_id, name, type. Searchable in ELK: "how many habits were created today?"

### `get_habits()` — Thin Passthrough

```python
async def get_habits(self, user_id: UUID, include_archived: bool = False) -> list[Habit]:
    return await self.repo.get_user_habits(user_id, include_archived)
```

- No business rules to check — just pass through to the repository
- The `include_archived` parameter comes from the query string: `GET /habits?include_archived=true`
- Why have a service method for a simple passthrough? **Consistency**. All routes call service methods. If you later add business logic (e.g., "also load today's log count for each habit"), it goes here without changing the router

### `get_habit()` — Ownership Check

```python
async def get_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
    habit = await self.repo.get_user_habit(user_id, habit_id)
    if not habit:
        raise HabitNotFoundError()
    return habit
```

- `get_user_habit` queries with BOTH `habit_id` AND `user_id`
- If the habit doesn't exist OR belongs to another user → returns `None`
- Service converts `None` to `HabitNotFoundError` (404)
- The client can't tell if the habit doesn't exist or belongs to someone else — by design (security)

### `update_habit()` — Partial Update with Duplicate Check

```python
async def update_habit(self, user_id: UUID, habit_id: UUID, data: HabitUpdate) -> Habit:
    # 1. Verify ownership
    habit = await self.repo.get_user_habit(user_id, habit_id)
    if not habit:
        raise HabitNotFoundError()

    # 2. Extract only provided fields
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return habit

    # 3. Check name uniqueness (if name is changing)
    if "name" in update_data and update_data["name"] != habit.name:
        if await self.repo.name_exists_for_user(
            user_id, update_data["name"], exclude_habit_id=habit_id
        ):
            raise DuplicateHabitNameError(update_data["name"])

    # 4. Apply updates field by field
    for key, value in update_data.items():
        setattr(habit, key, value)

    await self.session.flush()
    await self.session.refresh(habit)
    await self.session.commit()
    return habit
```

**Key details:**

- `data.model_dump(exclude_unset=True)` — only includes fields the client sent. If client sends `{"target_value": 10}`, the dict is `{"target_value": 10}` — name, color, icon are NOT overwritten with None

- **Name uniqueness check** — only runs if the name is actually changing. `update_data["name"] != habit.name` prevents the check when the name stays the same. The `exclude_habit_id=habit_id` prevents the habit from conflicting with itself

- `setattr(habit, key, value)` — dynamically sets attributes: `habit.target_value = 10`. SQLAlchemy tracks these changes and generates the UPDATE SQL on flush

- **Notice: no `habit_type` update.** `HabitUpdate` schema doesn't include `habit_type` (Part 05a), so it never appears in `update_data`. The immutability is enforced at the schema level — cleanest approach

### `delete_habit()` — Soft Delete

```python
async def delete_habit(self, user_id: UUID, habit_id: UUID) -> Habit:
    habit = await self.repo.archive_habit(user_id, habit_id)
    if not habit:
        raise HabitNotFoundError()

    await self.session.commit()
    return habit
```

- `archive_habit` sets `is_archived=True` — the habit is hidden from the dashboard but preserved
- Returns the archived habit so the router can include its name in the success message: "Habit 'Water Intake' archived successfully"
- No hard delete anywhere in the habits flow

### `reorder_habits()` — Batch Update + Return Updated List

```python
async def reorder_habits(self, user_id: UUID, habit_ids: list[UUID]) -> list[Habit]:
    await self.repo.reorder_habits(user_id, habit_ids)
    await self.session.commit()

    return await self.repo.get_user_habits(user_id)
```

- `reorder_habits` updates `sort_order` for each habit based on its position in the array
- After committing, we fetch the updated habit list — the response shows the new order
- The frontend can verify the reorder succeeded by checking the returned order matches what it sent

---

<a name="rules"></a>
## 4. Business Rules Summary

| Rule | Enforcement | Error |
|------|-------------|-------|
| Max 20 active habits | `count_active_habits() >= 20` | `HabitLimitExceededError` (422) |
| No duplicate names (per user) | `name_exists_for_user()` | `DuplicateHabitNameError` (409) |
| Habit type immutable | `HabitUpdate` schema excludes `habit_type` | Field simply doesn't exist in update |
| User can only access own habits | `get_user_habit(user_id, habit_id)` | `HabitNotFoundError` (404) |
| Delete = archive | `archive_habit()` sets `is_archived=True` | No actual DELETE SQL |
| Archived don't count toward limit | `count_active_habits` filters `is_archived=False` | User can archive + create |
| New habits go at end | `get_next_sort_order()` | `sort_order = max + 1` |

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision: Immutability via Schema Exclusion

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Enforcing Immutable Fields                        │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Exclude immutable fields from the Update schema            │
│                                                                     │
│  WHY:                                                               │
│  • Cleanest enforcement — field literally doesn't exist in input    │
│  • No runtime check needed — Pydantic ignores unknown fields        │
│  • Self-documenting — looking at HabitUpdate, you immediately see   │
│    what CAN be changed (everything listed) and what CAN'T           │
│    (everything missing)                                             │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Runtime check in service ("if habit_type in update_data: raise")│
│     ❌ Easy to forget. Silent if someone adds it later.            │
│  2. Database trigger (BEFORE UPDATE, check OLD.type = NEW.type)     │
│     ❌ Obscure — hard to debug, not visible in application code    │
│  3. Read-only field in schema (frozen=True)                         │
│     ⚠️ Works but Pydantic's approach is to just not include it     │
│                                                                     │
│  INTERVIEW TIP: "We enforce immutability by excluding habit_type    │
│  from the HabitUpdate schema. The field can't be sent in the update │
│  request at all — Pydantic ignores it. This is schema-level         │
│  enforcement, the cleanest approach."                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision: Validate-Then-Act Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Service Method Pattern                            │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Check all rules first, then perform the operation          │
│                                                                     │
│  PATTERN:                                                           │
│    1. Check limit (count query)                                     │
│    2. Check duplicate (name query)                                  │
│    3. Get next order (max query)                                    │
│    4. Create (insert)                                               │
│    5. Commit                                                        │
│                                                                     │
│  WHY:                                                               │
│  • All validation runs before any mutation — fail fast              │
│  • If any check fails, no data has been changed                     │
│  • Error messages are specific ("habit limit exceeded", not         │
│    "database constraint violated")                                  │
│  • Easy to test: mock repo methods, verify service calls them       │
│                                                                     │
│  ALTERNATIVE: Try to create, catch database errors                  │
│     ❌ Database errors are generic ("constraint violated")          │
│     ❌ Partial mutations might need manual rollback                 │
│     ❌ Hard to give user-friendly error messages                    │
│                                                                     │
│  INTERVIEW TIP: "We use validate-then-act: all business rules are  │
│  checked before any database mutation. This ensures clear error      │
│  messages, no partial state, and straightforward testing."           │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 6. How to Verify Your Work

```bash
# Verify imports
docker-compose exec backend python -c "
from app.modules.habits.service import HabitService
print('✅ service.py imports OK')
print(f'Methods: {[m for m in dir(HabitService) if not m.startswith(\"_\")]}')
"

# Integration test: create + list + archive
docker-compose exec backend python -c "
import asyncio
from app.modules.habits.service import HabitService
from app.modules.habits.schemas import HabitCreate

# This just verifies the class can be instantiated and methods exist
service = HabitService.__new__(HabitService)
print(f'create_habit: {callable(service.create_habit)}')
print(f'get_habits: {callable(service.get_habits)}')
print(f'update_habit: {callable(service.update_habit)}')
print(f'delete_habit: {callable(service.delete_habit)}')
print(f'reorder_habits: {callable(service.reorder_habits)}')
print('✅ All service methods exist')
"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: HabitRepository` | repository.py not created | Complete Part 05b first |
| `AttributeError: 'HabitType' has no attribute 'value'` | Using Enum class instead of instance | Ensure `data.habit_type` is `HabitType.NUMERIC`, not `HabitType` |
| `HabitLimitExceededError` unexpectedly | Over 20 active habits | Archive some habits first |
| `DuplicateHabitNameError` on update | Name check not excluding self | Verify `exclude_habit_id` is passed |

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Validate-then-act** | Check all rules before mutation | `create_habit` |
| 2 | **Enum `.value`** | Convert Enum to plain string for DB storage | `data.habit_type.value` |
| 3 | **`model_dump(exclude_unset=True)`** | Only include fields the client explicitly sent | `update_habit` |
| 4 | **Schema-level immutability** | Exclude field from Update schema to prevent changes | `HabitUpdate` has no `habit_type` |
| 5 | **Class attribute as constant** | `HabitLimitExceededError.MAX_HABITS` — single source of truth | `create_habit` limit check |
| 6 | **Thin passthrough** | Service method that delegates to repo without extra logic | `get_habits` |
| 7 | **Ownership check pattern** | Fetch with user_id → if None → raise 404 | `get_habit`, `update_habit`, `delete_habit` |
| 8 | **Self-exclusion in duplicate check** | `exclude_habit_id` prevents habit from conflicting with itself | `update_habit` name check |
| 9 | **Soft delete delegation** | Service calls `repo.archive_habit()` not `repo.delete()` | `delete_habit` |
| 10 | **Batch commit** | Reorder flushes multiple UPDATEs, then commits once | `reorder_habits` |
| 11 | **Structured logging** | Log business events with contextual fields | Every mutation method |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: Walk through what happens when a user creates a habit.
**A:** "Three validation steps, then creation. First, we count the user's active habits — if they have 20, we reject with a 422 error. Second, we check if the user already has a habit with the same name — duplicates return 409. Third, we get the next sort_order value so the new habit goes at the end of the dashboard. Only after all checks pass do we call the repository to INSERT the row. The transaction commits at the end — if anything fails, nothing is persisted. We also log the event with structured fields for monitoring."

### Q2: How do you handle partial updates?
**A:** "Pydantic v2's `model_dump(exclude_unset=True)` returns only fields the client explicitly included in the request. If the client sends `{\"target_value\": 10}`, only `target_value` is in the dict — name, color, icon are untouched. We loop through the dict with `setattr()` to apply each field dynamically. For the name field specifically, we run a duplicate check with `exclude_habit_id` to avoid the habit conflicting with its own current name."

### Q3: Why is the delete method named `delete_habit` but doesn't actually delete?
**A:** "It's named from the API consumer's perspective — the client calls `DELETE /habits/{id}` and the habit disappears from their view. Internally, it's a soft delete: `is_archived=True`. We chose this naming because the HTTP verb is DELETE, and the user's intent is deletion. The implementation detail (archive vs hard delete) is invisible to the client. This is the principle of abstraction — the interface hides the implementation."

### Q4: How does the service differ from the repository?
**A:** "The repository translates business requests into SQL — it knows about SELECT, WHERE, ORDER BY. The service knows business rules — max 20 habits, no duplicates, immutable type. The service calls multiple repository methods in sequence (count → check name → get sort order → create), wraps them in a transaction, and raises domain-specific errors. You could swap the repository's database from PostgreSQL to MongoDB without changing a single line in the service."

### Q5: What happens if two users simultaneously try to create a habit with the same count at the limit?
**A:** "This is a race condition. Both check `count_active_habits` → both get 19 → both proceed to create → now the user has 21 habits. In practice, this is extremely unlikely (same user, same millisecond). If we needed strict enforcement, we'd use a PostgreSQL advisory lock or a serializable transaction. For our scale, the 20-limit is a soft limit for UX, not a hard security boundary — having 21 habits briefly won't cause issues."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 05b: Habits Repository](./phase4-part05b-habits-repositories.md) |
| ➡️ Next | [Phase 4 Part 05d: Habits Router](./phase4-part05d-habits-controller-docker.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Habits Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 05a | ✅ Done | Habits Models, Exceptions, Schemas & Migration |
| 05b | ✅ Done | Habits Repository |
| **05c** | ✅ **You are here** | Habits Service |
| 05d | ⬜ Next | Habits Router |
| 05e | ⬜ | Habits Connections & Flows |

---

**End of Phase 4 Part 05c: Habits Service**

*Business logic is done — 6 methods enforcing max limits, duplicate checks, ownership, soft delete, and reordering. Same validate-then-act pattern as Auth. Next: the router that exposes all this as HTTP endpoints.*
