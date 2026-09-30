# Phase 4 — Part 03b: Base Schemas (shared/base_schemas.py)

> **"Schemas are the contract between your backend and frontend — they define exactly what data goes in and comes out."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 03b |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Shared Utilities |
| **File** | `backend/app/shared/base_schemas.py` |
| **Depends On** | Part 03a (exceptions.py — same shared package) |
| **Next** | [Part 03c — base_repository.py](./phase4-part03c-base-repository.md) |
| **Difficulty** | 🟡 Medium |
| **Time to Type** | ~15 minutes |
| **Lines of Code** | 125 lines |

---

## 📖 What is a Pydantic Schema? Read This First (Complete Beginner)

### If You've Never Heard of Pydantic

When someone sends data to your API, how do you know it's valid? What if they send `"age": "hello"` instead of `"age": 25`?

**Without Pydantic (manual checking):**
```python
def create_user(data):
    if "email" not in data:
        return {"error": "email required"}
    if "@" not in data["email"]:
        return {"error": "invalid email"}
    if "password" not in data:
        return {"error": "password required"}
    if len(data["password"]) < 8:
        return {"error": "password too short"}
    # ... 20 more checks
```

**With Pydantic (automatic):**
```python
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr                          # Pydantic checks email format automatically
    password: str = Field(min_length=8)      # Pydantic checks length automatically

# If data is invalid, Pydantic returns a clear error — you write ZERO validation code
```

Pydantic is a **data validation library**. You define the SHAPE of data as a Python class, and Pydantic:
1. Validates incoming data (rejects bad data with clear errors)
2. Converts types automatically (`"25"` string → `25` integer)
3. Generates JSON schema (for API documentation)

### Why "Base" Schemas?

Every module (auth, habits, logs) has its own schemas. But some patterns repeat:
- Every response needs `from_attributes=True` (to convert SQLAlchemy objects to JSON)
- Every list endpoint needs pagination (`page`, `page_size`, `total`)
- Every error looks the same (`error_code`, `message`, `detail`)

Base schemas define these patterns ONCE. Module schemas inherit from them.

**Real-world analogy:** Every form in an office has the same header (company name, date, employee ID). You print the header on the form template, not write it by hand on each form.

### What is `Generic[T]`? (The Hardest Concept Here)

`Generic[T]` means "this class works with ANY type." `T` is a placeholder:

```python
class Box(Generic[T]):
    item: T

Box[str]  → item is a string
Box[int]  → item is an integer
Box[Habit] → item is a Habit object
```

In our code:
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]    # A list of... WHAT? T could be anything!
    total: int

PaginatedResponse[HabitResponse]  → items: list[HabitResponse]
PaginatedResponse[LogResponse]    → items: list[LogResponse]
```

Write the pagination wrapper ONCE. Use it for ANY type. This is the Python equivalent of TypeScript's `PaginatedResponse<T>` or Java's `PaginatedResponse<T>`.

---

## 🏗️ Architecture: Where This File Fits

```
THIS FILE: shared/base_schemas.py
  │
  │ Defines 7 reusable schema classes
  │
  │ INHERITED BY:
  ├── modules/auth/schemas.py
  │     class UserResponse(BaseSchema)     ← inherits from_attributes=True
  │
  ├── modules/habits/schemas.py
  │     class HabitResponse(BaseSchema)    ← inherits from_attributes=True
  │
  ├── modules/logs/schemas.py
  │     class LogResponse(BaseSchema)      ← inherits from_attributes=True
  │
  │ USED DIRECTLY BY:
  ├── modules/habits/router.py
  │     return SuccessResponse(message="Habit deleted")
  │
  ├── middleware/error_handler.py
  │     returns ErrorResponse format
  │
  └── ANY list endpoint
        return PaginatedResponse[HabitResponse](items=[...], total=150, ...)
```

---

## 💻 Source Code — Type This EXACTLY

> 📁 **File:** `backend/app/shared/base_schemas.py`
> 📏 **Lines:** 125
> ⏱️ **Time to type:** ~15 minutes
>
> **This file goes in the same `shared/` folder as exceptions.py:**
> ```
> backend/app/shared/
> ├── __init__.py       ← already created
> ├── exceptions.py     ← created in Part 03a
> └── base_schemas.py   ← YOU WILL TYPE THIS NOW
> ```

```python
# ============================================================================
# Health Tracker — Base Pydantic Schemas
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines reusable request/response schemas used across all modules.
#   These are the building blocks — every module's schemas build on these.
#
# WHAT IS A SCHEMA (in this context):
#   A Pydantic model that defines the SHAPE of data going in/out of the API.
#   - Request schema: validates what the client sends
#   - Response schema: controls what the API returns (hides internal fields)
#
# WHY SEPARATE SCHEMAS FROM MODELS:
#   SQLAlchemy Model = database table structure (has password_hash, internal IDs)
#   Pydantic Schema  = API contract (never exposes password_hash to the client)
#   This separation is a security best practice.
# ============================================================================

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# TypeVar for generic pagination — works with any response type
T = TypeVar("T")


class BaseSchema(BaseModel):
    """
    Base schema that all other schemas inherit from.

    model_config with from_attributes=True tells Pydantic:
    "You can create this schema from a SQLAlchemy model object"

    Without this:
        user = User(id=1, email="a@b.com")
        UserResponse(**user.__dict__)  # Works but ugly

    With this:
        UserResponse.model_validate(user)  # Clean, automatic
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """
    Adds created_at and updated_at to response schemas.
    Most database records have these timestamps.
    """

    created_at: datetime
    updated_at: datetime | None = None


class ErrorResponse(BaseModel):
    """
    Standard error response format.
    Every error from the API looks like this — consistent for frontend parsing.

    Example:
        {
            "error_code": "HABIT_NOT_FOUND",
            "message": "Habit with id 123 not found",
            "detail": null
        }
    """

    error_code: str
    message: str
    detail: str | None = None


class SuccessResponse(BaseModel):
    """
    Generic success response for operations that don't return data.

    Example:
        {"message": "Habit deleted successfully"}
    """

    message: str


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.

    Usage in route handler:
        @router.get("/habits")
        async def list_habits(pagination: PaginationParams = Depends()):
            # pagination.page = 1, pagination.page_size = 20

    WHY PAGINATION:
        Without it, GET /logs returns ALL logs — could be thousands of rows.
        With pagination: GET /logs?page=1&page_size=20 returns just 20 rows.
        The frontend shows a "Load More" button or page numbers.
    """

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """Calculate SQL OFFSET from page number."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Alias for page_size — used in SQL LIMIT clause."""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response wrapper.
    Wraps any list of items with pagination metadata.

    Example response:
        {
            "items": [...],
            "total": 150,
            "page": 1,
            "page_size": 20,
            "total_pages": 8
        }

    Generic[T] means this works with ANY item type:
        PaginatedResponse[HabitResponse]
        PaginatedResponse[LogResponse]
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class IDResponse(BaseModel):
    """Response containing just an ID — returned after creating a resource."""

    id: UUID
```

---

## 📝 Line-by-Line Explanation

### Lines 18-24: Imports

```python
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
```

**What each import does:**
- **`datetime`** — Python's date/time type. Used for `created_at: datetime` fields.
- **`Generic`** — Makes a class work with ANY type (the `T` in `PaginatedResponse[T]`).
- **`TypeVar`** — Creates a "type placeholder" named `T`. Like a blank in fill-the-blank.
- **`UUID`** — Universally Unique Identifier. A 128-bit random ID like `550e8400-e29b-41d4-a716-446655440000`. We use these as primary keys instead of numbers.
- **`BaseModel`** — Pydantic's base class. ANY class that inherits from `BaseModel` gets automatic validation, JSON conversion, and documentation.
- **`ConfigDict`** — A way to configure Pydantic behavior (like `from_attributes=True`).

### Line 27: TypeVar

```python
T = TypeVar("T")
```

**What this does:** Creates a **type variable** — a placeholder for "any type." When you write `PaginatedResponse[HabitResponse]`, Python replaces `T` with `HabitResponse`.

**Analogy:** `T` is like "X" in algebra. `f(x) = x + 1` works for any number. `PaginatedResponse[T]` works for any schema type.

### Lines 30-45: BaseSchema

```python
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**What this does:**
- `class BaseSchema(BaseModel)` — Our custom base class that all response schemas inherit from.
- `model_config = ConfigDict(from_attributes=True)` — This is the KEY line. It tells Pydantic: "You can create this schema from a SQLAlchemy model object automatically."

**Why this matters:**
```python
# WITHOUT from_attributes=True:
user = User(id="abc", email="a@b.com", full_name="Shreya")
# You'd need to manually extract each field:
response = UserResponse(id=user.id, email=user.email, full_name=user.full_name)

# WITH from_attributes=True:
response = UserResponse.model_validate(user)  # Automatic! Reads user.id, user.email, etc.
```

### Lines 48-53: TimestampSchema

```python
class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime | None = None
```

**What `datetime | None = None` means:**
- `datetime | None` — This field can be a datetime OR None (called "optional" or "nullable").
- `= None` — If not provided, defaults to None.
- **Why?** `created_at` always exists (set when record is created). `updated_at` is None until the record is updated.

**What is `|`?** (Python 3.10+)
```python
# Old way:
from typing import Optional
updated_at: Optional[datetime] = None

# New way (Python 3.10+):
updated_at: datetime | None = None

# Both mean the same thing: "datetime OR None"
```

### Lines 56-77: ErrorResponse and SuccessResponse

```python
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None

class SuccessResponse(BaseModel):
    message: str
```

**These are simple — just field declarations.** Every field with a type hint becomes a JSON key:
```python
ErrorResponse(error_code="HABIT_NOT_FOUND", message="Habit not found")
# Becomes JSON:
# {"error_code": "HABIT_NOT_FOUND", "message": "Habit not found", "detail": null}
```

### Lines 80-100: PaginationParams

```python
class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
```

**What is `@property`?**

`@property` makes a METHOD look like a FIELD. You call `params.offset` (no parentheses), but it runs code:

```python
params = PaginationParams(page=3, page_size=20)
print(params.offset)  # (3-1) * 20 = 40
print(params.limit)   # 20

# Used in SQL:
# SELECT * FROM habits OFFSET 40 LIMIT 20
# This skips the first 40 rows and returns rows 41-60 (page 3)
```

**What is `@`?** (Decorator)

The `@` symbol is a **decorator** — it wraps a function to add behavior. `@property` is a built-in decorator that turns a method into a read-only attribute.

```python
# WITHOUT @property:
print(params.offset())    # Need parentheses — it's a method call

# WITH @property:
print(params.offset)      # No parentheses — looks like a field, but runs code
```

### Lines 103-123: PaginatedResponse (the Generic one)

```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```

**What `Generic[T]` does here:**

`items: list[T]` means "a list of... SOMETHING. The caller decides what."

```python
# When used as PaginatedResponse[HabitResponse]:
#   T becomes HabitResponse
#   items: list[T] becomes items: list[HabitResponse]

# When used as PaginatedResponse[LogResponse]:
#   T becomes LogResponse
#   items: list[T] becomes items: list[LogResponse]
```

**Why is this useful?** Write the pagination wrapper ONCE. It works for habits, logs, users, documents — any type. Without `Generic[T]`, you'd need:
```python
class PaginatedHabits(BaseModel):
    items: list[HabitResponse]
    total: int
    ...

class PaginatedLogs(BaseModel):
    items: list[LogResponse]
    total: int
    ...
# Repeating the same 5 fields for EVERY list endpoint!
```

### Line 126: IDResponse

```python
class IDResponse(BaseModel):
    id: UUID
```

Simple — returned when creating a resource if you only need the new ID back.

---

## 🔌 How This Connects

```
base_schemas.py defines:
  │
  ├── BaseSchema ──── inherited by ALL response schemas in ALL modules
  │                   UserResponse(BaseSchema), HabitResponse(BaseSchema), etc.
  │
  ├── ErrorResponse ── used by middleware/error_handler.py
  │                    {"error_code": "...", "message": "...", "detail": null}
  │
  ├── SuccessResponse ── used by DELETE endpoints
  │                      {"message": "Habit deleted successfully"}
  │
  ├── PaginationParams ── used by list endpoints as query parameters
  │                       GET /habits?page=2&page_size=10
  │
  └── PaginatedResponse[T] ── used by list endpoints as response wrapper
                               {"items": [...], "total": 150, "page": 2, ...}
```

---

## 🧪 Try It Yourself

```bash
cd backend
source venv/bin/activate
python3
```

```python
>>> from app.shared.base_schemas import BaseSchema, PaginationParams, PaginatedResponse, ErrorResponse, SuccessResponse

# Test 1: ErrorResponse
>>> error = ErrorResponse(error_code="NOT_FOUND", message="Habit not found")
>>> print(error.model_dump_json(indent=2))
{
  "error_code": "NOT_FOUND",
  "message": "Habit not found",
  "detail": null
}

# Test 2: PaginationParams
>>> params = PaginationParams(page=3, page_size=20)
>>> print(f"offset={params.offset}, limit={params.limit}")
offset=40, limit=20

# Test 3: PaginatedResponse with strings (T = str)
>>> resp = PaginatedResponse[str](items=["a", "b", "c"], total=100, page=1, page_size=3, total_pages=34)
>>> print(resp.model_dump_json(indent=2))
{
  "items": ["a", "b", "c"],
  "total": 100,
  "page": 1,
  "page_size": 3,
  "total_pages": 34
}

# Test 4: SuccessResponse
>>> s = SuccessResponse(message="Habit deleted")
>>> print(s.model_dump_json())
{"message":"Habit deleted"}

>>> exit()
```

If all 4 tests work → this file is correct. ✅

---

## ✅ What You Learned

| # | Concept | What It Means |
|---|---------|---------------|
| 1 | Pydantic BaseModel | A class that auto-validates, auto-converts types, auto-generates JSON |
| 2 | `ConfigDict(from_attributes=True)` | Convert SQLAlchemy objects to Pydantic schemas automatically |
| 3 | `datetime \| None = None` | "This field can be datetime or None. Defaults to None." |
| 4 | `@property` | Makes a method look like a field (no parentheses to call) |
| 5 | `TypeVar("T")` | A type placeholder — "any type, decided by the caller" |
| 6 | `Generic[T]` | Makes a class work with any type (like `<T>` in Java/TypeScript) |
| 7 | `list[T]` | A list of whatever T is (list of habits, list of logs, etc.) |
| 8 | Schema vs Model | Schema = API contract (what users see). Model = DB table (internal). |

---

## 🎤 Interview Q&A

### Q1: "What is Pydantic and why do you use it?"

> "Pydantic is a data validation library for Python. I define the shape of API data as Python classes with type hints, and Pydantic automatically: validates incoming requests (rejects bad data with clear errors), converts types (string '25' becomes integer 25), generates JSON schema (used by Swagger docs), and serializes to JSON (model_dump_json). I use it for ALL request and response schemas across 38 API endpoints. The key benefit: zero manual validation code. If I define `email: EmailStr`, Pydantic checks email format automatically."

### Q2: "What is Generic[T] in Python?"

> "A way to write classes that work with any type while maintaining type safety. I define `T = TypeVar('T')` as a placeholder, then `PaginatedResponse(BaseModel, Generic[T])` with `items: list[T]`. When I use `PaginatedResponse[HabitResponse]`, T becomes `HabitResponse`, so items becomes `list[HabitResponse]`. The IDE knows the exact type and gives autocomplete. It's Python's equivalent of Java's `<T>` or TypeScript's `<T>` — generic programming."

### Q3: "Why separate Pydantic schemas from SQLAlchemy models?"

> "Security and clean API design. The SQLAlchemy `User` model has `password_hash` — I never want that in an API response. The Pydantic `UserResponse` schema has `email`, `full_name`, `timezone` — only what the frontend should see. Schemas control what goes IN (request validation) and what goes OUT (response filtering). Models control what's STORED (database columns). Same data, different views for different purposes."

### Q4: "What does @property do?"

> "@property is a Python decorator that makes a method behave like a read-only attribute. In my `PaginationParams` class, `offset` is a @property that computes `(page - 1) * page_size`. The caller writes `params.offset` — no parentheses — but Python runs the calculation. I use it for computed values that depend on other fields: offset depends on page and page_size, so it's computed on access rather than stored."

---

## 📚 Navigation

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03a — exceptions.py](./phase4-part03a-exceptions.md) | | [Part 03c — base_repository.py](./phase4-part03c-base-repository.md) |
