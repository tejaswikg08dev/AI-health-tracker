# Phase 4 — Part 03c: Generic CRUD Repository (shared/base_repository.py)

| Field | Value |
|-------|-------|
| **Part** | 03c |
| **File** | `backend/app/shared/base_repository.py` |
| **Next** | [Part 03d — date_utils.py](./phase4-part03d-date-utils.md) |
| **Difficulty** | 🟠 Hard |
| **Time to Type** | ~15 minutes |
| **Lines** | ~85 lines |

---

## What is the Repository Pattern? Read This First

The Repository Pattern puts a **layer** between your business logic and the database. Services say "give me the user with this email." Repositories translate that to SQL.

```
WITHOUT Repository:
  # In route handler — SQL mixed with HTTP logic
  async def get_habits(db: DBSession):
      result = await db.execute(select(Habit).where(Habit.user_id == user_id))
      return result.scalars().all()

WITH Repository:
  # In service — clean business logic
  async def get_habits(user_id):
      return await self.habit_repo.get_user_habits(user_id)

  # In repository — SQL isolated
  async def get_user_habits(self, user_id):
      result = await self.session.execute(select(Habit).where(Habit.user_id == user_id))
      return list(result.scalars().all())
```

### What is `Generic[ModelType]`?

Instead of writing the same `create()`, `get_by_id()`, `delete()` for User, Habit, Log, Document... we write them ONCE with a type variable:

```python
ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    async def create(self, **kwargs) -> ModelType: ...
    async def get_by_id(self, id: UUID) -> ModelType | None: ...

# Usage:
class UserRepository(BaseRepository[User]):     # ModelType = User
class HabitRepository(BaseRepository[Habit]):    # ModelType = Habit
```

`UserRepository` gets `create()` that returns `User`. `HabitRepository` gets `create()` that returns `Habit`. Same code, different types. This is Python's equivalent of Java's `JpaRepository<T, ID>`.

---

## Source Code

> 📁 **File:** `backend/app/shared/base_repository.py`
> Type the full code from the source file

**6 methods provided for free:**
1. `create(**kwargs)` → INSERT + flush + refresh → returns new object
2. `get_by_id(id)` → SELECT WHERE id = → returns object or None
3. `get_all(offset, limit)` → SELECT with pagination → returns list
4. `count()` → SELECT COUNT(*) → returns int
5. `update(id, **kwargs)` → setattr + flush → returns updated object
6. `delete(id)` → DELETE WHERE id = → returns True/False

---

## 🎤 Interview Q&A

### Q: "What is the Repository pattern and why do you use it?"

> "The Repository pattern abstracts database access behind an interface. Services call `repo.get_by_email(email)` — they don't write SQL. This gives me: testability (mock the repository in unit tests), swappability (change PostgreSQL to MongoDB by rewriting repositories, not services), and DRY code (generic CRUD written once, inherited by all modules). My `BaseRepository[T]` uses Python Generics — `UserRepository(BaseRepository[User])` gets create, get_by_id, update, delete for free. Each module only adds custom queries."

### Q: "What are Python Generics?"

> "A way to write classes and functions that work with ANY type while preserving type safety. `TypeVar('T')` declares a placeholder type. `Generic[T]` means the class is parameterized. When I write `BaseRepository[User]`, `T` becomes `User` — so `create()` returns `User`, `get_by_id()` returns `User | None`. The IDE knows the exact type and gives autocomplete. It's Python's equivalent of Java's `<T>` or TypeScript's `<T>`."

---

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03b](./phase4-part03b-base-schemas.md) | | [Part 03d — date_utils.py](./phase4-part03d-date-utils.md) |
