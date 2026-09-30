# 🛠️ Phase 4 Part 03: Shared Utilities & Middleware

> **"Before you build any feature, build the safety net that catches every error, logs every request, and blocks every attacker. This invisible layer is what separates a toy project from production software."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 03 |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.1 — Backend Infrastructure |
| **Previous** | [phase4-part02-backend-foundation.md](./phase4-part02-backend-foundation.md) |
| **Next** | [phase4-part04-auth-service-overview.md](./phase4-part04-auth-service-overview.md) |
| **Files in This Doc** | 8 files (4 shared utilities + 3 middleware + 1 logging config) |
| **Endpoints** | 0 (infrastructure only — no routes yet) |
| **Time to Type** | ~120 minutes |
| **Difficulty** | Medium-Hard (new concepts: generics, inheritance, middleware, structured logging, rate limiting) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [File 1: shared/exceptions.py — Custom Exception Hierarchy](#exceptions)
3. [File 2: shared/base_schemas.py — Reusable Pydantic Schemas](#base-schemas)
4. [File 3: shared/base_repository.py — Generic CRUD Repository](#base-repository)
5. [File 4: shared/date_utils.py — Date & Timezone Utilities](#date-utils)
6. [File 5: shared/logging.py — Structured Logging Setup](#logging)
7. [File 6: middleware/error_handler.py — Global Error Handler](#error-handler)
8. [File 7: middleware/logging_middleware.py — Request/Response Logging](#logging-middleware)
9. [File 8: middleware/rate_limiter.py — Redis Rate Limiter](#rate-limiter)
10. [How All 8 Files Connect — Architecture Diagram](#connections)
11. [Design Decisions](#design-decisions)
12. [How to Verify Your Work](#verify)
13. [What You Learned](#what-you-learned)
14. [Interview Q&A](#interview)
15. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

In the previous part (Part 02), we built the **plumbing** — database connections, Redis, configuration, and dependency injection. Now we build the **safety systems** — the code that catches errors, logs requests, blocks attackers, and provides reusable building blocks for every module.

### Real-World Analogy

Think of a hospital:
- **Exceptions** (File 1) = The alarm system. Different alarms for different emergencies (fire alarm, code blue, security alert). Each alarm triggers a specific response.
- **Base Schemas** (File 2) = Admission/discharge forms. Every department uses the same standard forms — saves time, prevents confusion.
- **Base Repository** (File 3) = The medical records system. Every department (cardiology, neurology) stores/retrieves patient records the same way — one system, many departments.
- **Date Utils** (File 4) = The timezone clock in a global hospital. Patient in India, doctor in USA — everyone needs the correct local time.
- **Logging** (File 5) = The CCTV + activity log. Records everything that happens — who entered, what they did, when. If something goes wrong, you rewind the tape.
- **Error Handler** (File 6) = The reception desk. When something goes wrong, the receptionist gives the visitor a clear, polite message — not raw technical jargon.
- **Logging Middleware** (File 7) = The front door security camera. Records every person entering and leaving, how long they stayed, and whether they left happy or angry.
- **Rate Limiter** (File 8) = The security guard. If someone keeps entering and leaving too fast (suspicious behavior), the guard blocks them.

### File Structure After This Part

```
backend/app/
├── shared/                      ← Reusable code for ALL modules
│   ├── __init__.py              ← (empty — marks as Python package)
│   ├── exceptions.py            ← File 1: Custom exception classes
│   ├── base_schemas.py          ← File 2: Reusable Pydantic schemas
│   ├── base_repository.py       ← File 3: Generic CRUD operations
│   ├── date_utils.py            ← File 4: Date/timezone helpers
│   └── logging.py               ← File 5: Structured logging setup
├── middleware/                   ← Request/response processing pipeline
│   ├── __init__.py              ← (empty)
│   ├── error_handler.py         ← File 6: Catch errors → JSON responses
│   ├── logging_middleware.py    ← File 7: Log every request with timing
│   └── rate_limiter.py          ← File 8: Block excessive requests
```

### Build Order (Type These Files in This Order)

| # | File | Why This Order |
|---|------|---------------|
| 1 | `shared/exceptions.py` | Error handler (File 6) catches these exceptions |
| 2 | `shared/base_schemas.py` | Every module's schemas inherit from these |
| 3 | `shared/base_repository.py` | Every module's repository inherits from this |
| 4 | `shared/date_utils.py` | Used by analytics, logs, and AI modules |
| 5 | `shared/logging.py` | Middleware files (6, 7, 8) all use the logger |
| 6 | `middleware/error_handler.py` | Catches exceptions from File 1 |
| 7 | `middleware/logging_middleware.py` | Uses logger from File 5 |
| 8 | `middleware/rate_limiter.py` | Uses logger + Redis from Part 02 |

---

<a name="exceptions"></a>
## 2. File 1: `shared/exceptions.py` — Custom Exception Hierarchy

### What Are Exceptions? Read This First

An **exception** is Python's way of saying "something went wrong." When an error happens, Python **raises** an exception. If no one **catches** it, the program crashes.

```python
# This raises an exception:
result = 10 / 0  # ZeroDivisionError!

# This catches it:
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Can't divide by zero!")
```

**Why custom exceptions?** Python has built-in exceptions (`ValueError`, `TypeError`, etc.), but they don't know about HTTP status codes. We need exceptions that say "this is a 404 Not Found" or "this is a 401 Unauthorized" so our error handler can return the correct HTTP response.

### What Is Inheritance? (Used Heavily Here)

**Inheritance** means one class gets all the features of another class, plus adds its own.

```
Think of it like a family:
  Parent: "I know how to walk and talk"
  Child:  "I know everything my parent knows, PLUS I can skateboard"
```

In our code:
```
BaseAppError (parent) → knows: message, status_code, error_code
├── NotFoundError (child) → inherits all above + sets status_code=404
├── ConflictError (child) → inherits all above + sets status_code=409
├── UnauthorizedError (child) → inherits all above + sets status_code=401
└── ForbiddenError (child) → inherits all above + sets status_code=403
```

### Type This Code: `backend/app/shared/exceptions.py`

```python
# ============================================================================
# Health Tracker — Base Exception Hierarchy
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines custom exception classes that all modules can use.
#   Each exception maps to an HTTP status code.
#
# WHY CUSTOM EXCEPTIONS:
#   Instead of returning {"error": "not found"} manually in every route,
#   you raise NotFoundError("User not found") and the error_handler middleware
#   automatically converts it to a proper HTTP 404 response.
#
#   Benefits:
#   1. Consistent error format across ALL endpoints
#   2. Service layer can raise errors without knowing about HTTP
#   3. Easy to test — assert that service raises NotFoundError
#
# EXCEPTION HIERARCHY:
#   BaseAppError (base)
#   ├── NotFoundError      → 404
#   ├── ConflictError      → 409 (duplicate data)
#   ├── ValidationError    → 422 (invalid input)
#   ├── UnauthorizedError  → 401 (not logged in)
#   └── ForbiddenError     → 403 (logged in but not allowed)
# ============================================================================


class BaseAppError(Exception):
    """
    Base exception for all application errors.

    All custom exceptions inherit from this.
    The error_handler middleware catches BaseAppError and its subclasses
    to return structured JSON error responses.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code to return
        error_code: Machine-readable error code (for frontend to handle specific errors)
    """

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundError(BaseAppError):
    """
    Resource not found — HTTP 404.

    Raised when: user, habit, log entry, document doesn't exist.

    Example:
        raise NotFoundError("Habit not found", error_code="HABIT_NOT_FOUND")
    """

    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message=message, status_code=404, error_code=error_code)


class ConflictError(BaseAppError):
    """
    Resource conflict — HTTP 409.

    Raised when: duplicate email on signup, duplicate log for same day+habit.

    Example:
        raise ConflictError("Email already registered", error_code="EMAIL_EXISTS")
    """

    def __init__(self, message: str = "Resource already exists", error_code: str = "CONFLICT"):
        super().__init__(message=message, status_code=409, error_code=error_code)


class ValidationError(BaseAppError):
    """
    Validation failed — HTTP 422.

    Raised when: invalid habit value, future date, value out of range.
    Note: Pydantic handles request schema validation automatically.
    This is for BUSINESS LOGIC validation.

    Example:
        raise ValidationError("Sleep hours must be between 0 and 24")
    """

    def __init__(
        self, message: str = "Validation failed", error_code: str = "VALIDATION_ERROR"
    ):
        super().__init__(message=message, status_code=422, error_code=error_code)


class UnauthorizedError(BaseAppError):
    """
    Authentication required — HTTP 401.

    Raised when: no token, expired token, invalid token.

    Example:
        raise UnauthorizedError("Token expired")
    """

    def __init__(
        self, message: str = "Authentication required", error_code: str = "UNAUTHORIZED"
    ):
        super().__init__(message=message, status_code=401, error_code=error_code)


class ForbiddenError(BaseAppError):
    """
    Access denied — HTTP 403.

    Raised when: user tries to access another user's data.
    Different from 401: user IS logged in, but NOT allowed.

    Example:
        raise ForbiddenError("You can only view your own habits")
    """

    def __init__(self, message: str = "Access denied", error_code: str = "FORBIDDEN"):
        super().__init__(message=message, status_code=403, error_code=error_code)
```

### Line-by-Line Explanation

**Lines 1-25: The comment block**
```python
# ============================================================================
# Health Tracker — Base Exception Hierarchy
# ============================================================================
```
Every file starts with a header explaining WHAT it does, WHY it exists, and HOW it fits. This is documentation for your future self (and your team).

**Line 27: `class BaseAppError(Exception):`**
```python
class BaseAppError(Exception):
```
- `class` — a keyword that creates a new type (a blueprint for objects)
- `BaseAppError` — the name of our class. "Base" because all other errors inherit from it
- `(Exception)` — this means BaseAppError **inherits from** Python's built-in `Exception` class. This makes it a "throwable" error that Python's `try/except` can catch
- `:` — starts the class body (everything indented below belongs to this class)

**Lines 38-45: The `__init__` method (constructor)**
```python
def __init__(
    self,
    message: str = "An error occurred",
    status_code: int = 500,
    error_code: str = "INTERNAL_ERROR",
):
```
- `def` — defines a function (when inside a class, it's called a "method")
- `__init__` — a special method called **constructor**. Python runs it automatically when you create an object: `error = BaseAppError("oops")`
- `self` — refers to the object being created. Every method in a class must have `self` as the first parameter. Python passes it automatically
- `message: str = "An error occurred"` — a parameter with a **type hint** (`str`) and a **default value**. If you don't pass a message, it uses "An error occurred"
- `status_code: int = 500` — HTTP status code. Default 500 (Internal Server Error)
- `error_code: str = "INTERNAL_ERROR"` — machine-readable code the frontend can check

**Lines 46-48: Storing values**
```python
self.message = message
self.status_code = status_code
self.error_code = error_code
```
- `self.message = message` — stores the `message` parameter as an **attribute** of the object. Now you can access it later: `error.message`
- This is like filling in a form: the blank form is the class, the filled form is the object

**Line 49: `super().__init__(self.message)`**
```python
super().__init__(self.message)
```
- `super()` — refers to the **parent class** (`Exception`)
- `.__init__(self.message)` — calls the parent's constructor, passing our message
- WHY: Python's `Exception` class expects a message. If we don't call `super().__init__()`, the base `Exception` features (like `str(error)` returning the message) won't work

**Lines 52-62: NotFoundError (child class)**
```python
class NotFoundError(BaseAppError):
    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message=message, status_code=404, error_code=error_code)
```
- `class NotFoundError(BaseAppError):` — inherits from `BaseAppError` (not `Exception` directly)
- The constructor takes `message` and `error_code`, but NOT `status_code` — because it's ALWAYS 404
- `super().__init__(...)` — calls `BaseAppError.__init__()` with `status_code=404` hardcoded
- Result: `raise NotFoundError("User not found")` creates an error with status=404, code="NOT_FOUND"

**The same pattern repeats for all other exceptions:**
| Exception | Status Code | When Used |
|-----------|-------------|-----------|
| `NotFoundError` | 404 | Resource doesn't exist (user, habit, log) |
| `ConflictError` | 409 | Duplicate data (email already registered) |
| `ValidationError` | 422 | Invalid input (sleep hours > 24) |
| `UnauthorizedError` | 401 | Not logged in or token expired |
| `ForbiddenError` | 403 | Logged in but not allowed (accessing other user's data) |

### How This File Gets Used (Preview)

```python
# In auth/service.py:
async def login(self, email: str, password: str) -> TokenPair:
    user = await self.repo.get_by_email(email)
    if not user:
        raise NotFoundError("User not found", error_code="USER_NOT_FOUND")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid password")

# The error_handler middleware (File 6) catches this and returns:
# HTTP 404: {"error_code": "USER_NOT_FOUND", "message": "User not found", "detail": null}
```

---

<a name="base-schemas"></a>
## 3. File 2: `shared/base_schemas.py` — Reusable Pydantic Schemas

### What Is a Schema? Read This First

A **schema** defines the **shape** of data — what fields it has, what types they are, and what's required vs optional.

**Real-world analogy:** A **form** at a bank.
- The blank form = the schema (defines what fields exist: Name, Account Number, Amount)
- The filled form = the data (actual values: "Shreya", "12345", "$500")
- The bank clerk = Pydantic (checks if you filled the form correctly before processing)

**Why separate schemas from database models?**
```
Database Model (SQLAlchemy):  stores password_hash, internal IDs, soft-delete flags
API Schema (Pydantic):        NEVER exposes password_hash, only returns safe fields

Security principle: Never trust the client. Never expose internals.
```

### What Are Generics? (Used in PaginatedResponse)

**Generics** let you write code that works with ANY type, decided later.

```python
# Without generics — you'd write separate classes:
class PaginatedHabits:
    items: list[Habit]
    total: int

class PaginatedLogs:
    items: list[Log]
    total: int

# With generics — one class works for ALL types:
class PaginatedResponse(Generic[T]):
    items: list[T]     # T could be Habit, Log, User, anything!
    total: int

# Usage:
PaginatedResponse[Habit]  # T becomes Habit
PaginatedResponse[Log]    # T becomes Log
```

**Real-world analogy:** A **shipping box**. The box doesn't care what's inside — it works for books, electronics, or food. The label on the box tells you what's inside. `Generic[T]` is the box, `T` is the label.

### Type This Code: `backend/app/shared/base_schemas.py`

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

### Line-by-Line Explanation

**Lines 18-22: Imports**
```python
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID
from pydantic import BaseModel, ConfigDict
```
- `datetime` — Python's date/time type. Used for `created_at`, `updated_at` fields
- `Generic` — from Python's `typing` module. Lets us create classes that work with any type (like `PaginatedResponse[Habit]` or `PaginatedResponse[Log]`)
- `TypeVar` — creates a "type placeholder" named `T`. Think of it as a variable, but for types instead of values
- `UUID` — Universally Unique Identifier. Our primary keys are UUIDs, not auto-increment integers
- `BaseModel` — Pydantic's base class. Any class inheriting from `BaseModel` gets automatic validation, serialization, and documentation
- `ConfigDict` — Pydantic v2 way to configure model behavior (replaces the old `class Config:`)

**Line 25: `T = TypeVar("T")`**
```python
T = TypeVar("T")
```
- Creates a type variable named `T`. This is a placeholder that gets replaced with a real type when used
- `TypeVar("T")` — the string `"T"` must match the variable name `T` (Python convention)
- Used in `PaginatedResponse(Generic[T])` — when you write `PaginatedResponse[HabitResponse]`, `T` becomes `HabitResponse`

**Lines 28-43: BaseSchema**
```python
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```
- `class BaseSchema(BaseModel):` — our base schema inherits from Pydantic's `BaseModel`
- `model_config = ConfigDict(from_attributes=True)` — this one line is CRUCIAL:
  - Without it: you can't create a schema from a SQLAlchemy model object
  - With it: `UserResponse.model_validate(user_db_object)` works automatically
  - It tells Pydantic: "When creating this schema, you can read attributes from a Python object, not just a dictionary"
  - **Spring Boot equivalent:** This is like using `@JsonProperty` or ModelMapper — automatic conversion from entity to DTO

**Lines 46-52: TimestampSchema**
```python
class TimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime | None = None
```
- Inherits from `BaseSchema` (gets `from_attributes=True`)
- `created_at: datetime` — required field, type `datetime`
- `updated_at: datetime | None = None` — optional field. The `| None` means it can be `None` (null). `= None` is the default value
- **Why a separate class?** Most of our response schemas need timestamps. Instead of adding `created_at` and `updated_at` to every schema, we inherit from `TimestampSchema`

**Lines 55-67: ErrorResponse**
```python
class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: str | None = None
```
- Note: inherits from `BaseModel`, NOT `BaseSchema`. Error responses don't come from SQLAlchemy objects — they're constructed manually
- `error_code: str` — machine-readable code like `"HABIT_NOT_FOUND"`. The frontend uses this to show specific UI (e.g., redirect to login page on `"UNAUTHORIZED"`)
- `detail: str | None = None` — extra info, like validation error details. Optional

**Lines 78-94: PaginationParams**
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
- `page: int = 1` — which page to return. Default: first page
- `page_size: int = 20` — how many items per page. Default: 20
- `@property` — a Python decorator that makes a method behave like an attribute. Instead of `params.offset()` (with parentheses), you write `params.offset` (no parentheses)
- `offset` calculation: page 1 → offset 0, page 2 → offset 20, page 3 → offset 40. This maps directly to SQL's `OFFSET` clause
- **Why not just pass offset/limit directly?** Frontend developers think in "pages" (page 1, page 2). Backend SQL thinks in "offset/limit". This class translates between the two

**Lines 97-116: PaginatedResponse (Generic)**
```python
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
```
- `BaseModel, Generic[T]` — inherits from BOTH BaseModel and Generic[T] (multiple inheritance)
- `items: list[T]` — the actual data. `T` is replaced with the real type: `list[HabitResponse]`, `list[LogResponse]`, etc.
- `total` — total items across ALL pages (e.g., 150)
- `total_pages` — calculated: `ceil(total / page_size)` = `ceil(150 / 20)` = 8 pages
- This ONE class replaces what would be 7+ separate paginated response classes

**Lines 119-121: IDResponse**
```python
class IDResponse(BaseModel):
    id: UUID
```
- Simple response with just an ID. Returned after creating a resource: `POST /habits` → `{"id": "abc-123"}`
- `UUID` type ensures the ID is a valid UUID format

---

<a name="base-repository"></a>
## 4. File 3: `shared/base_repository.py` — Generic CRUD Repository

### What Is the Repository Pattern? Read This First

The **Repository Pattern** creates a layer between your business logic and the database. Your service says "give me user #5" and the repository translates that to SQL.

```
WITHOUT Repository Pattern:
  Route Handler → writes SQL directly → Database
  Problem: SQL scattered everywhere, hard to test, hard to change DB

WITH Repository Pattern:
  Route Handler → Service → Repository → Database
  Benefit: SQL is in ONE place, service doesn't know about SQL
```

**Real-world analogy:** You go to a **library**. You don't search the shelves yourself. You tell the librarian (repository): "I need the book about Python." The librarian knows WHERE it is and HOW to get it. If the library reorganizes shelves, YOU don't need to learn the new system — the librarian handles it.

### What Are Generics in This Context?

```python
class BaseRepository(Generic[ModelType]):
```
This means: "I'm a repository that works with ANY model type."

- `BaseRepository[User]` → all methods work with User objects
- `BaseRepository[Habit]` → all methods work with Habit objects
- `BaseRepository[Log]` → all methods work with Log objects

Same code, different types. Write once, use everywhere.

### Type This Code: `backend/app/shared/base_repository.py`

```python
# ============================================================================
# Health Tracker — Generic Base Repository
# ============================================================================
# WHAT THIS FILE DOES:
#   Provides reusable CRUD (Create, Read, Update, Delete) database operations.
#   Every module's repository inherits from this — no more rewriting
#   the same SELECT, INSERT, UPDATE queries in every module.
#
# WHAT IS THE REPOSITORY PATTERN:
#   A layer between your service (business logic) and database (SQL queries).
#
#   Service says: "Give me user with id=5"
#   Repository does: SELECT * FROM users WHERE id = 5
#   Service never writes SQL directly.
#
# WHY:
#   1. Reusable — CRUD operations written once, used by all modules
#   2. Testable — mock the repository in unit tests, no real DB needed
#   3. Swappable — if you switch from PostgreSQL to MongoDB, only repos change
#   4. Clean — services contain business logic, repos contain data access
#
# THIS IS THE SAME PATTERN AS:
#   Spring Boot: JpaRepository<T, ID>
#   .NET: Repository<T>
#   Django: Manager (queryset)
# ============================================================================

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

# ModelType is a placeholder for any SQLAlchemy model
# When you do BaseRepository[User], ModelType becomes User
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic CRUD repository.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            # Add custom queries specific to users
            async def get_by_email(self, email: str) -> User | None:
                ...

    The base class gives you: create, get_by_id, get_all, update, delete
    You only write custom queries in the subclass.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """
        Initialize with the model class and a database session.

        Args:
            model: The SQLAlchemy model class (e.g., User, Habit)
            session: The async database session for this request
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record in the database.

        Example:
            user = await user_repo.create(email="a@b.com", full_name="Shreya")

        HOW IT WORKS:
            1. Creates a model instance with the given fields
            2. Adds it to the session (marks for insert)
            3. Flushes to DB (executes INSERT, assigns id)
            4. Refreshes the object (loads DB-generated fields like created_at)
            5. Returns the created object

        WHY flush + refresh (not commit):
            Commit happens at the route handler level.
            This allows multiple repo operations in a single transaction.
            If any operation fails, everything rolls back.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()       # Execute INSERT, get generated id
        await self.session.refresh(instance)  # Load DB defaults (created_at, etc.)
        return instance

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """
        Get a single record by its primary key (UUID).

        Returns None if not found — the service layer decides whether to raise 404.

        Example:
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User not found")
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        Get all records with pagination.

        Example:
            habits = await habit_repo.get_all(offset=0, limit=20)  # First 20

        WHY offset/limit (not page/page_size):
            SQL uses OFFSET and LIMIT directly.
            The PaginationParams schema converts page to offset.
        """
        result = await self.session.execute(
            select(self.model)
            .offset(offset)
            .limit(limit)
            .order_by(self.model.created_at.desc())  # Newest first
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """
        Count total records — used for pagination metadata.

        Example:
            total = await habit_repo.count()
            # Returns: 47
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def update(self, id: UUID, **kwargs) -> ModelType | None:
        """
        Update a record by ID with the given fields.

        Only updates fields that are provided — doesn't overwrite other fields.

        Example:
            updated_user = await user_repo.update(
                user_id,
                full_name="New Name",
                timezone="Asia/Kolkata"
            )

        Returns None if record doesn't exist.
        """
        instance = await self.get_by_id(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """
        Delete a record by ID.

        Returns True if deleted, False if not found.

        NOTE: For most resources (habits, logs), we use SOFT DELETE
        (set is_archived=True) instead of real delete. This preserves
        data for analytics. Hard delete is used for things like
        expired tokens or test data.
        """
        result = await self.session.execute(
            sa_delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0
```

### Line-by-Line Explanation

**Lines 27-30: Imports**
```python
from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
```
- `Generic, TypeVar` — for creating a generic class (works with any model)
- `UUID` — our primary keys are UUIDs
- `select` — builds `SELECT` queries: `select(User).where(User.id == id)` → `SELECT * FROM users WHERE id = ?`
- `func` — SQL functions: `func.count()` → `COUNT(*)`
- `delete as sa_delete` — renamed to `sa_delete` to avoid conflicting with our `delete` method name
- `AsyncSession` — async database session. All DB operations use `await` because they're non-blocking
- `Base` — our SQLAlchemy base class from `database.py` (Part 02). All models inherit from it

**Line 34: `ModelType = TypeVar("ModelType", bound=Base)`**
```python
ModelType = TypeVar("ModelType", bound=Base)
```
- Creates a type variable named `ModelType`
- `bound=Base` — restricts it: `ModelType` can ONLY be classes that inherit from `Base` (our SQLAlchemy models). You can't use `BaseRepository[str]` or `BaseRepository[int]`
- This is a **compile-time type safety** feature — your IDE will warn if you try to use the wrong type

**Line 37: `class BaseRepository(Generic[ModelType]):`**
```python
class BaseRepository(Generic[ModelType]):
```
- `Generic[ModelType]` — makes this a generic class. When a subclass writes `BaseRepository[User]`, `ModelType` becomes `User` throughout the class
- **Spring Boot equivalent:** `JpaRepository<User, UUID>` — same concept, different syntax

**Lines 54-57: Constructor**
```python
def __init__(self, model: type[ModelType], session: AsyncSession):
    self.model = model
    self.session = session
```
- `model: type[ModelType]` — the model CLASS itself (e.g., `User`, `Habit`), not an instance. `type[ModelType]` means "the class, not an object of the class"
- `session: AsyncSession` — the database connection for this request. Each request gets its own session (from `dependencies.py` in Part 02)
- We store both as instance attributes for use in all methods

**Lines 59-77: `create` method**
```python
async def create(self, **kwargs) -> ModelType:
    instance = self.model(**kwargs)
    self.session.add(instance)
    await self.session.flush()
    await self.session.refresh(instance)
    return instance
```
- `async def` — this is an **asynchronous** method. It uses `await` to pause while waiting for the database, letting other requests be handled meanwhile
- `**kwargs` — accepts ANY keyword arguments. `create(email="a@b.com", name="Shreya")` → `kwargs = {"email": "a@b.com", "name": "Shreya"}`
- `self.model(**kwargs)` — creates a model instance: `User(email="a@b.com", name="Shreya")`
- `self.session.add(instance)` — marks the object for insertion (doesn't execute SQL yet)
- `await self.session.flush()` — executes the INSERT SQL. The `await` pauses here until DB responds. After flush, the DB assigns the `id` and `created_at`
- `await self.session.refresh(instance)` — reloads the object from DB to get generated values
- **Why flush, not commit?** Flush executes SQL but doesn't finalize the transaction. Commit finalizes. We flush here so multiple operations can be in ONE transaction. If anything fails, everything rolls back

**Lines 79-92: `get_by_id` method**
```python
async def get_by_id(self, id: UUID) -> ModelType | None:
    result = await self.session.execute(
        select(self.model).where(self.model.id == id)
    )
    return result.scalar_one_or_none()
```
- `-> ModelType | None` — return type: either a model object OR `None` (if not found)
- `select(self.model)` — equivalent to `SELECT * FROM {table_name}`
- `.where(self.model.id == id)` — adds `WHERE id = ?`
- `result.scalar_one_or_none()` — returns the single result or `None` if no rows match. If multiple rows match (impossible for primary key), raises an error

**Lines 94-110: `get_all` method**
```python
async def get_all(self, offset: int = 0, limit: int = 100) -> list[ModelType]:
    result = await self.session.execute(
        select(self.model)
        .offset(offset)
        .limit(limit)
        .order_by(self.model.created_at.desc())
    )
    return list(result.scalars().all())
```
- `.offset(offset)` → `OFFSET 0` (skip 0 rows for page 1)
- `.limit(limit)` → `LIMIT 100` (return max 100 rows)
- `.order_by(self.model.created_at.desc())` → `ORDER BY created_at DESC` (newest first)
- `result.scalars().all()` — `scalars()` extracts the model objects from the result rows. `all()` converts to a list

**Lines 127-143: `update` method**
```python
async def update(self, id: UUID, **kwargs) -> ModelType | None:
    instance = await self.get_by_id(id)
    if not instance:
        return None
    for key, value in kwargs.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    await self.session.flush()
    await self.session.refresh(instance)
    return instance
```
- First, GET the existing record. If not found, return `None`
- `for key, value in kwargs.items():` — loop through each field to update
- `hasattr(instance, key)` — check if the model has this attribute (prevents setting non-existent fields)
- `setattr(instance, key, value)` — dynamically set the attribute: `instance.full_name = "New Name"`
- SQLAlchemy tracks changes automatically. `flush()` generates the `UPDATE` SQL

**Lines 145-159: `delete` method**
```python
async def delete(self, id: UUID) -> bool:
    result = await self.session.execute(
        sa_delete(self.model).where(self.model.id == id)
    )
    await self.session.flush()
    return result.rowcount > 0
```
- `sa_delete(self.model)` → `DELETE FROM {table_name}`
- `.where(self.model.id == id)` → `WHERE id = ?`
- `result.rowcount > 0` — returns `True` if a row was actually deleted, `False` if ID didn't exist
- **Note:** In practice, we rarely hard-delete. Most modules use soft-delete (set `is_archived=True`). Hard delete is for tokens, test data, etc.

---

<a name="date-utils"></a>
## 5. File 4: `shared/date_utils.py` — Date & Timezone Utilities

### Why Dates Are Tricky — Read This First

Imagine Shreya in India logs "drank 8 glasses of water" at 11:30 PM IST on September 26th. The server stores this as 6:00 PM UTC (September 26th). No problem... yet.

But what if she logs at **12:30 AM IST on September 27th**? That's **7:00 PM UTC on September 26th**. If the analytics query groups by UTC date, it counts this log on September 26th — but Shreya thinks it's September 27th!

**Rule:** Store everything in UTC. Convert to user's timezone only when displaying.

### What Is UTC?

**UTC** (Coordinated Universal Time) is the world's reference time. Every timezone is defined as an offset from UTC:
- **IST** (India) = UTC + 5:30
- **EST** (New York) = UTC - 5:00
- **PST** (California) = UTC - 8:00

By storing all times in UTC, we have ONE source of truth. Converting to local time is just math.

### Type This Code: `backend/app/shared/date_utils.py`

```python
# ============================================================================
# Health Tracker — Date & Timezone Utilities
# ============================================================================
# WHAT THIS FILE DOES:
#   Helper functions for date operations used across all modules.
#   Handles timezone conversion, date range generation, week/month boundaries.
#
# WHY DATES ARE TRICKY:
#   - User in India logs a habit at 11 PM IST (May 5th for them)
#   - Server stores it as 5:30 PM UTC (May 5th UTC)
#   - If we don't handle timezones, the log might show as May 6th for them
#
#   Rule: Store everything in UTC in the database.
#   Convert to user's timezone only when displaying.
# ============================================================================

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """
    Get current UTC datetime (timezone-aware).

    WHY timezone-aware:
        datetime.utcnow() returns a "naive" datetime (no timezone info).
        This causes bugs when comparing with timezone-aware datetimes.
        Always use timezone-aware datetimes in production code.
    """
    return datetime.now(timezone.utc)


def today_utc() -> date:
    """Get today's date in UTC."""
    return utc_now().date()


def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    """
    Convert a UTC datetime to the user's local timezone.

    Args:
        dt: A UTC datetime
        user_timezone: IANA timezone string (e.g., "Asia/Kolkata", "America/New_York")

    Returns:
        Datetime in user's timezone

    Example:
        utc_time = datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "Asia/Kolkata")
        # Result: 2026-09-27 00:00:00+05:30 (next day in India!)
    """
    tz = ZoneInfo(user_timezone)
    return dt.astimezone(tz)


def start_of_week(d: date | None = None) -> date:
    """
    Get the Monday of the current (or given) week.

    WHY Monday:
        ISO standard: Monday = start of week.
        Consistent across all locales in our app.

    Example:
        start_of_week(date(2026, 9, 26))  # Saturday
        # Returns: date(2026, 9, 21)       # Monday of that week
    """
    if d is None:
        d = today_utc()
    return d - timedelta(days=d.weekday())


def end_of_week(d: date | None = None) -> date:
    """Get the Sunday of the current (or given) week."""
    return start_of_week(d) + timedelta(days=6)


def start_of_month(d: date | None = None) -> date:
    """Get the first day of the current (or given) month."""
    if d is None:
        d = today_utc()
    return d.replace(day=1)


def end_of_month(d: date | None = None) -> date:
    """
    Get the last day of the current (or given) month.

    TRICK: Go to first of NEXT month, then subtract 1 day.
    This correctly handles months with 28, 29, 30, or 31 days.
    """
    if d is None:
        d = today_utc()
    # Go to first of next month
    if d.month == 12:
        next_month_first = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month_first = d.replace(month=d.month + 1, day=1)
    # Subtract 1 day to get last day of current month
    return next_month_first - timedelta(days=1)


def date_range(start: date, end: date) -> list[date]:
    """
    Generate a list of all dates between start and end (inclusive).

    Used for: filling gaps in chart data (days with no logs still show on chart).

    Example:
        date_range(date(2026, 9, 1), date(2026, 9, 5))
        # Returns: [Sep 1, Sep 2, Sep 3, Sep 4, Sep 5]
    """
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


def days_ago(n: int) -> date:
    """Get the date N days ago. Shortcut for common queries."""
    return today_utc() - timedelta(days=n)
```

### Line-by-Line Explanation

**Lines 17-18: Imports**
```python
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
```
- `date` — represents a calendar date (year, month, day) without time
- `datetime` — represents a date AND time (year, month, day, hour, minute, second)
- `timedelta` — represents a duration: `timedelta(days=7)` = 7 days. You can add/subtract it from dates
- `timezone` — timezone information. `timezone.utc` is the UTC timezone object
- `ZoneInfo` — Python 3.9+ module for timezone names. `ZoneInfo("Asia/Kolkata")` creates the IST timezone. Uses the IANA timezone database (the industry standard)

**Lines 21-29: `utc_now()`**
```python
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```
- `def` — defines a function (not inside a class, so it's a standalone function)
- `-> datetime` — return type hint. This function returns a `datetime` object
- `datetime.now(timezone.utc)` — gets current time WITH timezone info (UTC)
- **Why not `datetime.utcnow()`?** That returns a "naive" datetime (no timezone attached). If you compare a naive datetime with a timezone-aware datetime, Python raises an error. This is a famous Python gotcha

**Lines 32-33: `today_utc()`**
```python
def today_utc() -> date:
    return utc_now().date()
```
- Calls `utc_now()` to get the current UTC datetime
- `.date()` strips the time, returning just the date portion
- Used for queries like "get all logs for today"

**Lines 36-52: `to_user_timezone()`**
```python
def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    tz = ZoneInfo(user_timezone)
    return dt.astimezone(tz)
```
- `dt: datetime` — the UTC datetime to convert
- `user_timezone: str` — IANA timezone string stored in the user's profile (e.g., `"Asia/Kolkata"`)
- `ZoneInfo(user_timezone)` — creates the timezone object
- `.astimezone(tz)` — converts the datetime to the target timezone. Python handles the math automatically (adds 5:30 for IST, subtracts 5 for EST)

**Lines 55-67: `start_of_week()`**
```python
def start_of_week(d: date | None = None) -> date:
    if d is None:
        d = today_utc()
    return d - timedelta(days=d.weekday())
```
- `d: date | None = None` — optional parameter. If not passed, uses today's date
- `d.weekday()` — returns 0 for Monday, 1 for Tuesday, ..., 6 for Sunday
- `d - timedelta(days=d.weekday())` — subtracts the weekday number of days. Saturday (5) → subtract 5 days → Monday
- Used by analytics: "show this week's habits"

**Lines 82-93: `end_of_month()` — The Clever Trick**
```python
def end_of_month(d: date | None = None) -> date:
    if d is None:
        d = today_utc()
    if d.month == 12:
        next_month_first = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month_first = d.replace(month=d.month + 1, day=1)
    return next_month_first - timedelta(days=1)
```
- **The problem:** How do you know if a month has 28, 29, 30, or 31 days?
- **The trick:** Go to the FIRST day of the NEXT month, then subtract 1 day
- February: first of March minus 1 = Feb 28 (or 29 in leap year). Works perfectly!
- `d.replace(month=d.month + 1, day=1)` — creates a new date with same year, next month, day 1
- Special case: December (month 12) → next month is January of NEXT year

**Lines 96-103: `date_range()`**
```python
def date_range(start: date, end: date) -> list[date]:
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]
```
- `(end - start).days` — subtracting two dates gives a `timedelta`. `.days` extracts the number of days
- `+ 1` — make it inclusive (Sep 1 to Sep 5 = 5 days, not 4)
- `[start + timedelta(days=i) for i in range(days)]` — a **list comprehension** (Python shortcut for building lists). Equivalent to a for-loop that adds each date
- Used in analytics to fill gaps: if user logged nothing on Sep 3, the chart still shows Sep 3 with value 0

---

<a name="logging"></a>
## 6. File 5: `shared/logging.py` — Structured Logging Setup

### What Is Structured Logging? Read This First

**Regular logging** (what beginners do):
```
INFO: User 123 logged in from 192.168.1.1 at 2026-09-26 10:00:00
```
This is readable by humans. But try searching "find all logins from IP 192.168.1.1" in millions of log lines — you'd need regex, and it's fragile.

**Structured logging** (what companies do):
```json
{"event": "user_login", "user_id": "123", "ip": "192.168.1.1", "timestamp": "2026-09-26T10:00:00Z"}
```
This is JSON. You can search `user_id=123` in Elasticsearch, aggregate `event=user_login` in Kibana dashboards, and filter `ip=192.168.1.1` in CloudWatch Logs.

**Real-world analogy:** Structured logging is like filling a form vs writing a paragraph. A form has named fields (name, date, amount) — easy to sort and search. A paragraph has the same info but buried in text — impossible to query at scale.

### What Is structlog?

`structlog` is a Python library that makes structured logging easy. Instead of:
```python
logging.info(f"User {user_id} created habit {habit_name}")
```

You write:
```python
logger.info("habit_created", user_id=str(user_id), habit_name=habit_name)
```

structlog outputs JSON with all the fields as separate keys — perfect for log aggregation tools (ELK Stack, AWS CloudWatch, Datadog).

### Type This Code: `backend/app/shared/logging.py`

```python
# ============================================================================
# Health Tracker — Structured Logging Configuration
# ============================================================================
# WHAT THIS FILE DOES:
#   Configures structlog for structured JSON logging.
#
# WHY STRUCTURED LOGGING:
#   Regular logging:  "User 123 created habit 'Water' at 2026-09-26T10:00:00"
#   Structured logging: {"user_id": "123", "action": "create_habit",
#                         "habit_name": "Water", "timestamp": "2026-09-26T10:00:00"}
#
#   Structured logs are:
#   1. Searchable — find all logs where user_id=123 in Elasticsearch
#   2. Parseable — machines can read JSON, not regex on strings
#   3. Dashboardable — Kibana can aggregate by action type, count errors
#
# HOW COMPANIES DO IT:
#   Same. Structured JSON logs → shipped to ELK/Datadog/Splunk → dashboards.
#   This is NOT optional in production — it's how you debug issues at 3 AM.
# ============================================================================

import logging
import sys

import structlog

from app.config import get_settings


def setup_logging() -> None:
    """
    Configure structured logging for the application.

    Call this once at application startup (in main.py lifespan).
    After this, use structlog.get_logger() anywhere in the code.

    Usage:
        logger = structlog.get_logger()
        logger.info("habit_created", user_id=str(user.id), habit_name="Water")

    Output (JSON):
        {"event": "habit_created", "user_id": "abc-123", "habit_name": "Water",
         "timestamp": "2026-09-26T10:00:00Z", "level": "info"}
    """
    settings = get_settings()

    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Configure structlog processors
    # Processors are a pipeline — each one transforms the log event
    shared_processors: list[structlog.types.Processor] = [
        # Add log level (info, warning, error)
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso"),
        # If there's an exception, format the traceback
        structlog.processors.format_exc_info,
        # Add caller info (file, line number) — helpful for debugging
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # In development: pretty colored output for readability
    # In production: JSON output for machine parsing (ELK, CloudWatch)
    if settings.APP_ENV == "development":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            # Prepare event dict for standard logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard Python logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Route all logs through structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance.

    Args:
        name: Optional logger name (usually __name__ of the module)

    Usage:
        from app.shared.logging import get_logger
        logger = get_logger(__name__)
        logger.info("something_happened", key="value")
    """
    return structlog.get_logger(name)
```

### Line-by-Line Explanation

**Lines 22-26: Imports**
```python
import logging
import sys
import structlog
from app.config import get_settings
```
- `logging` — Python's built-in logging module. structlog builds ON TOP of it, not replacing it
- `sys` — system-specific functions. `sys.stdout` is the standard output stream (console/terminal)
- `structlog` — third-party library for structured logging. Installed via `pip install structlog`
- `get_settings` — our settings from `config.py` (Part 02). We need `LOG_LEVEL`, `APP_ENV`, and `DEBUG`

**Lines 29-44: `setup_logging()` function**
```python
def setup_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
```
- `-> None` — this function doesn't return anything (it configures logging as a side effect)
- `get_settings()` — loads settings from environment variables
- `getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)` — this is a clever trick:
  - `settings.LOG_LEVEL` might be `"debug"`, `"info"`, `"warning"`, etc.
  - `.upper()` converts to `"DEBUG"`, `"INFO"`, `"WARNING"`
  - `getattr(logging, "INFO")` returns `logging.INFO` (which is the integer `20`)
  - The third argument `logging.INFO` is the default if the string doesn't match anything
  - This converts a string from `.env` to a Python logging level constant

**Lines 47-60: Processor Pipeline**
```python
shared_processors: list[structlog.types.Processor] = [
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.format_exc_info,
    structlog.processors.CallsiteParameterAdder(
        parameters=[
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
        ]
    ),
]
```
- **Processors** are functions that transform a log event. They run in order, like an assembly line
- `add_log_level` — adds `"level": "info"` to the log dict
- `TimeStamper(fmt="iso")` — adds `"timestamp": "2026-09-26T10:00:00Z"` in ISO 8601 format
- `format_exc_info` — if an exception is being logged, formats the full traceback
- `CallsiteParameterAdder` — adds `"filename": "service.py"` and `"lineno": 42` — tells you WHERE the log was written

**Lines 63-66: Environment-Based Renderer**
```python
if settings.APP_ENV == "development":
    renderer = structlog.dev.ConsoleRenderer(colors=True)
else:
    renderer = structlog.processors.JSONRenderer()
```
- In **development**: pretty colored output in the terminal (easy to read while coding)
- In **production**: raw JSON output (machines read it, not humans). This JSON goes to ELK Stack, CloudWatch, Datadog
- **Why different?** Developers want readable logs. Log aggregation tools want parseable JSON. Same data, different format

**Lines 68-74: Configure structlog**
```python
structlog.configure(
    processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
```
- `processors=[*shared_processors, ...]` — the `*` unpacks the list. Same as writing each processor individually
- `wrap_for_formatter` — bridges structlog with Python's standard logging
- `LoggerFactory()` — tells structlog to use Python's logging underneath
- `BoundLogger` — the type of logger object returned by `get_logger()`
- `cache_logger_on_first_use=True` — performance optimization. Don't re-configure the logger on every call

**Lines 76-89: Standard Logging Integration**
```python
formatter = structlog.stdlib.ProcessorFormatter(
    processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(log_level)
```
- This connects structlog to Python's standard `logging` module
- `StreamHandler(sys.stdout)` — sends log output to stdout (console). In Docker, this is how logs get collected
- `root_logger.handlers.clear()` — removes any existing handlers (prevents duplicate logs)
- `root_logger.setLevel(log_level)` — only logs at this level or above are emitted

**Lines 91-94: Quieting Noisy Loggers**
```python
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(
    logging.INFO if settings.DEBUG else logging.WARNING
)
```
- Uvicorn (our ASGI server) and SQLAlchemy log A LOT by default
- We set them to WARNING so they only log when something's wrong
- Exception: in DEBUG mode, SQLAlchemy logs all SQL queries (helpful for development)

**Lines 97-107: `get_logger()` Helper**
```python
def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```
- Convenience function used throughout the codebase
- `name` is usually `__name__` (Python's magic variable for the current module name, e.g., `"app.auth.service"`)
- Every file that needs logging does: `logger = get_logger(__name__)`

---

<a name="error-handler"></a>
## 7. File 6: `middleware/error_handler.py` — Global Error Handler

### What Is an Error Handler? Read This First

Without an error handler, when something crashes in your code, the user sees:
```html
<h1>Internal Server Error</h1>
<pre>Traceback (most recent call last):
  File "service.py", line 42, in login
    user = await self.repo.get_by_email(email)
  ...</pre>
```
This is BAD because:
1. It's HTML, but your frontend expects JSON
2. It exposes internal file paths and code structure (security risk!)
3. Different errors return inconsistent formats

With our error handler, EVERY error returns:
```json
{"error_code": "NOT_FOUND", "message": "User not found", "detail": null}
```
Consistent, safe, parseable.

### How FastAPI Exception Handlers Work

FastAPI lets you register **exception handlers** — functions that run when a specific exception type is raised. Think of it like a phone switchboard:

```
Exception raised → FastAPI checks: "Who handles this type?"
├── BaseAppError      → app_error_handler()      → 4xx response
├── ValidationError   → validation_error_handler() → 422 response
├── HTTPException     → http_error_handler()      → various responses
└── Exception (catch-all) → unhandled_error_handler() → 500 response
```

### Type This Code: `backend/app/middleware/error_handler.py`

```python
# ============================================================================
# Health Tracker — Global Error Handler
# ============================================================================
# WHAT THIS FILE DOES:
#   Catches ALL exceptions and converts them to structured JSON responses.
#   Without this, unhandled exceptions return ugly HTML 500 errors.
#
# WHY:
#   Your frontend expects JSON responses — always. Even on errors.
#   This middleware guarantees every error returns:
#     {"error_code": "...", "message": "...", "detail": "..."}
#
# HOW IT WORKS:
#   1. FastAPI exception handlers are registered for specific exception types
#   2. When any code raises an exception, FastAPI finds the matching handler
#   3. The handler converts it to a JSONResponse with the correct status code
#
# REQUEST FLOW ON ERROR:
#   Route handler raises NotFoundError("Habit not found")
#   → FastAPI catches BaseAppError
#   → app_error_handler() converts to {"error_code": "NOT_FOUND", "message": "Habit not found"}
#   → Returns HTTP 404 with JSON body
# ============================================================================

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.exceptions import BaseAppError
from app.shared.logging import get_logger

logger = get_logger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI app.

    Called once during app startup (in main.py).
    """

    @app.exception_handler(BaseAppError)
    async def app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
        """
        Handle our custom application errors.

        These are EXPECTED errors — a user did something wrong or
        a resource wasn't found. Log at warning level, not error.

        Examples:
            NotFoundError → 404
            ConflictError → 409
            UnauthorizedError → 401
        """
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "detail": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors.

        These happen when the request body/query doesn't match the schema.
        Example: POST /habits with {"name": 123} when name should be a string.

        Pydantic gives detailed error info — we pass it through.
        """
        # Extract readable error messages from Pydantic errors
        errors = []
        for error in exc.errors():
            field = " → ".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")

        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "detail": errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle standard HTTP exceptions (404 for unknown routes, 405 method not allowed, etc.).

        These are raised by FastAPI/Starlette itself, not our code.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": "HTTP_ERROR",
                "message": exc.detail or "An HTTP error occurred",
                "detail": None,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Catch-all for unexpected errors.

        These are BUGS — something we didn't anticipate.
        Log at error level with full traceback for debugging.

        IMPORTANT: In production, NEVER expose the actual error message to the user.
        It might contain sensitive info (SQL queries, file paths, API keys).
        Return a generic message and log the real error server-side.
        """
        logger.error(
            "unhandled_error",
            error_type=type(exc).__name__,
            error_message=str(exc),
            path=request.url.path,
            method=request.method,
            exc_info=exc,  # structlog will format the full traceback
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "detail": None,
            },
        )
```

### Line-by-Line Explanation

**Lines 24-29: Imports**
```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.shared.exceptions import BaseAppError
from app.shared.logging import get_logger
```
- `FastAPI` — the app instance. We register exception handlers on it
- `Request` — the incoming HTTP request object. We use it to log the URL path
- `RequestValidationError` — raised by Pydantic when request body/query doesn't match the schema
- `JSONResponse` — a response that serializes a Python dict to JSON with the correct `Content-Type: application/json` header
- `StarletteHTTPException` — Starlette (FastAPI's foundation) raises this for standard HTTP errors (404 unknown route, 405 wrong method)
- `BaseAppError` — our custom base exception (File 1). We catch this and all its children
- `get_logger` — our structured logger (File 5)

**Lines 33-34: `register_error_handlers(app: FastAPI)`**
```python
def register_error_handlers(app: FastAPI) -> None:
```
- This function takes the FastAPI app and registers all handlers on it
- Called once in `main.py` during startup: `register_error_handlers(app)`
- `-> None` — returns nothing (registers handlers as a side effect)

**Lines 36-53: `@app.exception_handler(BaseAppError)`**
```python
@app.exception_handler(BaseAppError)
async def app_error_handler(request: Request, exc: BaseAppError) -> JSONResponse:
```
- `@app.exception_handler(BaseAppError)` — a **decorator** that tells FastAPI: "When a `BaseAppError` (or any subclass) is raised, call THIS function"
- The function receives the `request` and the exception (`exc`)
- Since `NotFoundError`, `ConflictError`, etc. all inherit from `BaseAppError`, this ONE handler catches them ALL
- `logger.warning(...)` — logged as WARNING, not ERROR. These are expected — user did something wrong, not our bug
- Returns a `JSONResponse` with the status code and error details from the exception

**Lines 55-77: `validation_error_handler`**
```python
errors = []
for error in exc.errors():
    field = " → ".join(str(loc) for loc in error["loc"])
    errors.append(f"{field}: {error['msg']}")
```
- Pydantic's `exc.errors()` returns a list of dicts: `[{"loc": ["body", "name"], "msg": "field required", "type": "missing"}]`
- `error["loc"]` is the field path: `["body", "name"]` means the `name` field in the request body
- `" → ".join(...)` creates `"body → name"` — human-readable field path
- `f"{field}: {error['msg']}"` creates `"body → name: field required"`
- The `detail` field contains ALL validation errors — frontend can highlight each invalid field

**Lines 79-92: `http_error_handler`**
```python
@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
```
- Catches HTTP errors raised by FastAPI/Starlette ITSELF (not our code)
- Example: user hits `GET /api/v1/nonexistent` → FastAPI raises `HTTPException(404)`
- We wrap it in our standard error format for consistency

**Lines 94-117: `unhandled_error_handler` (The Safety Net)**
```python
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
```
- `Exception` catches EVERYTHING — this is the catch-all
- These are BUGS (unexpected errors). We log them at `error` level with full traceback
- `exc_info=exc` — tells structlog to include the full stack trace in the log
- **CRITICAL SECURITY:** The response says "An unexpected error occurred" — NOT the actual error message. In production, the real error might contain SQL queries, file paths, or other sensitive info. Log it server-side, but never expose it to the client
- `type(exc).__name__` — gets the exception class name (e.g., "AttributeError", "KeyError") for the log

---

<a name="logging-middleware"></a>
## 8. File 7: `middleware/logging_middleware.py` — Request/Response Logging

### What Is Middleware? Read This First

**Middleware** is code that runs BEFORE and AFTER every request. Think of it as a checkpoint at the entrance and exit of a building.

```
Request → [Middleware BEFORE] → Route Handler → [Middleware AFTER] → Response

Example:
  1. Request arrives: POST /api/v1/habits
  2. BEFORE: Start timer, generate request_id
  3. Route handler creates the habit
  4. AFTER: Stop timer, log "POST /habits → 201 → 45ms"
  5. Response sent to client
```

**Real-world analogy:** Airport security.
- **Before** your flight (request): check passport, scan luggage, record entry time
- **Your flight** (handler): the actual work
- **After** your flight (response): record exit time, total time in airport

### What Is a Request ID?

Every request gets a **unique ID** (like `abc-12345`). When a user reports "the app is slow" or "I got an error," you search your logs for that request ID and see EXACTLY what happened — which endpoint, how long, what error.

Companies include the request ID in response headers (`X-Request-ID: abc-12345`). The frontend can display it in error dialogs: "Error occurred. Reference: abc-12345."

### Type This Code: `backend/app/middleware/logging_middleware.py`

```python
# ============================================================================
# Health Tracker — Request/Response Logging Middleware
# ============================================================================
# WHAT THIS FILE DOES:
#   Logs every HTTP request and response with timing, status, and context.
#   Every request gets a unique request_id for tracing.
#
# WHY:
#   When a user reports "the app is slow" or "I got an error",
#   you need to find THAT specific request in your logs.
#   Request IDs let you trace a single request across all log entries.
#
# WHAT GETS LOGGED:
#   Request:  method, path, client IP, user-agent, request_id
#   Response: status code, response time (ms)
#
# EXAMPLE LOG OUTPUT:
#   {"event": "http_request", "method": "POST", "path": "/api/v1/auth/login",
#    "status": 200, "duration_ms": 45.2, "request_id": "abc-123"}
# ============================================================================

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.shared.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request with timing info.

    HOW MIDDLEWARE WORKS:
      For every request, FastAPI calls dispatch().
      We run code BEFORE the handler (start timer),
      call the handler (call_next),
      then run code AFTER the handler (stop timer, log).

    MIDDLEWARE LIFECYCLE:
      1. Request arrives
      2. dispatch() starts timer, generates request_id
      3. call_next(request) — passes request to the next middleware or route handler
      4. Response comes back
      5. dispatch() logs the request with duration
      6. Returns response to client
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique ID for this request — used to trace in logs
        request_id = str(uuid.uuid4())[:8]  # Short 8-char ID (enough for tracing)

        # Attach request_id to request state — accessible in route handlers
        request.state.request_id = request_id

        # Start timing
        start_time = time.perf_counter()

        # Skip logging for health checks (too noisy)
        if request.url.path == "/health":
            return await call_next(request)

        try:
            # Pass request to the route handler
            response = await call_next(request)
        except Exception:
            # If an unhandled exception occurs, log it and re-raise
            # The error_handler will catch it and return proper JSON
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=500,
                duration_ms=round(duration_ms, 2),
            )
            raise

        # Calculate how long the request took
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request_id to response headers — frontend can include it in bug reports
        response.headers["X-Request-ID"] = request_id

        # Log the request
        # Choose log level based on status code:
        #   2xx/3xx → info (everything is fine)
        #   4xx     → warning (client error — bad input, unauthorized)
        #   5xx     → error (server error — our bug)
        log_level = "info"
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"

        getattr(logger, log_level)(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )

        return response
```

### Line-by-Line Explanation

**Lines 22-27: Imports**
```python
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from app.shared.logging import get_logger
```
- `time` — for `time.perf_counter()`, a high-precision timer for measuring request duration
- `uuid` — for generating unique request IDs (`uuid.uuid4()` creates a random UUID)
- `BaseHTTPMiddleware` — Starlette's base class for HTTP middleware. We override its `dispatch` method
- `RequestResponseEndpoint` — type hint for the `call_next` function (the next handler in the chain)
- `Request, Response` — Starlette's request/response types

**Line 32: `class LoggingMiddleware(BaseHTTPMiddleware):`**
```python
class LoggingMiddleware(BaseHTTPMiddleware):
```
- Inherits from `BaseHTTPMiddleware`. This gives us the middleware lifecycle
- We only need to implement `dispatch()` — Starlette handles the rest

**Lines 48-50: Request ID Generation**
```python
request_id = str(uuid.uuid4())[:8]
request.state.request_id = request_id
start_time = time.perf_counter()
```
- `uuid.uuid4()` — generates a random UUID like `550e8400-e29b-41d4-a716-446655440000`
- `[:8]` — takes first 8 characters: `550e8400`. Short enough to be practical, unique enough for our scale
- `request.state.request_id` — Starlette's `request.state` is a storage object. Anything stored here is accessible in route handlers. This lets us include the request_id in service-layer logs
- `time.perf_counter()` — high-resolution timer (nanosecond precision). Better than `time.time()` for measuring short durations

**Lines 53-54: Skip Health Checks**
```python
if request.url.path == "/health":
    return await call_next(request)
```
- Health check endpoints are called by Docker/Kubernetes every few seconds
- Logging them would create thousands of useless log lines per hour
- We skip logging but still PROCESS the request (call_next passes it through)

**Lines 56-66: Try/Except Block**
```python
try:
    response = await call_next(request)
except Exception:
    duration_ms = (time.perf_counter() - start_time) * 1000
    logger.error("http_request", request_id=request_id, ...)
    raise
```
- `await call_next(request)` — passes the request to the next middleware or route handler. This is where your actual endpoint code runs
- If the handler raises an exception, we STILL want to log the request (with status 500 and duration)
- `raise` — re-raises the exception after logging. The `error_handler` (File 6) will catch it and return proper JSON

**Lines 69-70: Response Timing**
```python
duration_ms = (time.perf_counter() - start_time) * 1000
response.headers["X-Request-ID"] = request_id
```
- `perf_counter() - start_time` gives duration in seconds. `* 1000` converts to milliseconds
- Adding `X-Request-ID` to response headers lets the frontend include it in bug reports

**Lines 73-87: Adaptive Log Level**
```python
log_level = "info"
if response.status_code >= 500:
    log_level = "error"
elif response.status_code >= 400:
    log_level = "warning"

getattr(logger, log_level)("http_request", ...)
```
- Status 200-399 → `info` (normal operation)
- Status 400-499 → `warning` (client error — bad input, unauthorized)
- Status 500+ → `error` (server bug)
- `getattr(logger, log_level)` — dynamically calls `logger.info()`, `logger.warning()`, or `logger.error()` based on the variable. This is cleaner than three separate `if/elif/else` blocks with duplicate log calls

---

<a name="rate-limiter"></a>
## 9. File 8: `middleware/rate_limiter.py` — Redis Rate Limiter

### What Is Rate Limiting? Read This First

**Rate limiting** restricts how many requests a client can make in a time window. Without it:
- An attacker tries 10,000 passwords per second → brute-force login
- A script calls your AI chat endpoint 1,000 times → costs you $50 in LLM API calls
- A buggy frontend sends 100 requests per second → server crashes (DDoS)

**Real-world analogy:** A bouncer at a club. "You can enter 5 times tonight. After that, wait until tomorrow." The bouncer counts entries. If you hit the limit, you're turned away.

### Sliding Window vs Fixed Window

```
FIXED WINDOW (simpler, what we implement):
  Time:    |--- minute 1 ---|--- minute 2 ---|
  Requests: ●●●●●            ●●●●●
  Counter resets at exact minute boundaries.

  Problem: 5 requests at 0:59, 5 more at 1:00 = 10 requests in 2 seconds!

SLIDING WINDOW (more accurate, complex):
  Looks at the last 60 seconds from NOW.
  "In the last 60 seconds, you've made X requests."
  No boundary gaming.

We implement fixed window (Redis INCR) — good enough for our scale.
True sliding window uses Redis sorted sets (more complex, more memory).
```

### How Redis Helps

Why not just use a Python dictionary to count requests? Because in production you have MULTIPLE server instances behind a load balancer:

```
Request 1 → Server A (counter: 1)
Request 2 → Server B (counter: 1)  ← Server B doesn't know about Server A's counter!
```

Redis is a SHARED counter — all servers read/write the same Redis key:
```
Request 1 → Server A → Redis (counter: 1)
Request 2 → Server B → Redis (counter: 2)  ✅ Correct!
```

### Type This Code: `backend/app/middleware/rate_limiter.py`

```python
# ============================================================================
# Health Tracker — Redis-Based Rate Limiter
# ============================================================================
# WHAT THIS FILE DOES:
#   Limits how many requests a client can make per time window.
#   Uses Redis sliding window algorithm — industry standard.
#
# WHY RATE LIMITING:
#   Without it, someone could:
#   - Brute-force login passwords (try millions of passwords)
#   - Spam AI chat (expensive LLM calls — costs you money)
#   - DDoS your API (flood with requests until server crashes)
#
# ALGORITHM: Sliding Window Counter
#   - Each client gets a Redis key: "rate_limit:{ip}:{window}"
#   - Each request increments the counter
#   - If counter > limit, request is rejected with HTTP 429
#   - Key expires after the window (auto-cleanup)
#
# EXAMPLE:
#   Limit: 60 requests per minute
#   Client sends request #61 within 1 minute → HTTP 429 Too Many Requests
#   After the minute resets, counter goes back to 0
#
# HOW COMPANIES DO IT:
#   Same algorithm. Some use Nginx rate limiting (we do that too),
#   but application-level rate limiting allows per-user limits
#   (logged-in users get higher limits than anonymous).
# ============================================================================

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.redis_client import get_redis_client
from app.shared.logging import get_logger

logger = get_logger(__name__)

# Rate limit configuration
# Different limits for different endpoint types
RATE_LIMITS = {
    "/api/v1/ai/": {"requests": 10, "window_seconds": 60},      # AI is expensive
    "/api/v1/auth/login": {"requests": 5, "window_seconds": 60}, # Prevent brute force
    "/api/v1/": {"requests": 60, "window_seconds": 60},          # General API
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Redis-based sliding window rate limiter.

    HOW SLIDING WINDOW WORKS:
      Fixed window: Counter resets at exact minute boundaries (00:00, 01:00, ...)
        Problem: Someone sends 60 requests at 0:59, and 60 more at 1:00
                 → 120 requests in 2 seconds. The limit is useless.

      Sliding window: Counter tracks the last 60 seconds from NOW.
        If you sent 60 requests in the last 60 seconds, you're blocked.
        No gaming the boundary.

    IMPLEMENTATION:
      We use Redis INCR + EXPIRE for simplicity.
      This is a "fixed window" implementation (close enough for our scale).
      For true sliding window, you'd use Redis sorted sets with timestamps.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and non-API routes
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Determine which rate limit applies to this path
        limit_config = self._get_limit_for_path(request.url.path)

        # Get client identifier (IP address)
        # In production behind a load balancer, use X-Forwarded-For header
        client_ip = request.client.host if request.client else "unknown"

        try:
            redis_client = get_redis_client()

            # Build Redis key: "rl:{ip}:{window_start}"
            # Window start = current time truncated to window_seconds boundary
            window_start = int(time.time()) // limit_config["window_seconds"]
            redis_key = f"rl:{client_ip}:{request.url.path}:{window_start}"

            # Increment counter and get current value
            current_count = await redis_client.incr(redis_key)

            # Set expiry on first request (when count becomes 1)
            if current_count == 1:
                await redis_client.expire(redis_key, limit_config["window_seconds"])

            # Check if over limit
            if current_count > limit_config["requests"]:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    path=request.url.path,
                    current_count=current_count,
                    limit=limit_config["requests"],
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "detail": None,
                    },
                    headers={
                        # Standard headers — tells client when to retry
                        "Retry-After": str(limit_config["window_seconds"]),
                        "X-RateLimit-Limit": str(limit_config["requests"]),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            # Request is within limits — proceed
            response = await call_next(request)

            # Add rate limit info to response headers (helpful for API consumers)
            remaining = max(0, limit_config["requests"] - current_count)
            response.headers["X-RateLimit-Limit"] = str(limit_config["requests"])
            response.headers["X-RateLimit-Remaining"] = str(remaining)

            return response

        except Exception:
            # If Redis is down, DON'T block requests — let them through
            # Rate limiting is a nice-to-have, not a hard requirement
            # This is called "fail open" — the opposite of "fail closed"
            logger.warning("rate_limiter_error", error="Redis unavailable, skipping rate limit")
            return await call_next(request)

    @staticmethod
    def _get_limit_for_path(path: str) -> dict:
        """
        Find the most specific rate limit for a given path.

        Checks path prefixes from most specific to least specific.
        Example: /api/v1/ai/chat matches "/api/v1/ai/" (10 req/min)
                 /api/v1/habits matches "/api/v1/" (60 req/min)
        """
        for prefix, config in sorted(RATE_LIMITS.items(), key=lambda x: -len(x[0])):
            if path.startswith(prefix):
                return config
        # Default: generous limit for unknown paths
        return {"requests": 100, "window_seconds": 60}
```

### Line-by-Line Explanation

**Lines 31-37: Imports**
```python
import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.redis_client import get_redis_client
from app.shared.logging import get_logger
```
- `time` — for `time.time()` which returns current Unix timestamp (seconds since Jan 1, 1970)
- `get_redis_client` — from Part 02's `redis_client.py`. Returns our async Redis connection
- The rest are the same as the logging middleware

**Lines 42-46: Rate Limit Configuration**
```python
RATE_LIMITS = {
    "/api/v1/ai/": {"requests": 10, "window_seconds": 60},      # AI is expensive
    "/api/v1/auth/login": {"requests": 5, "window_seconds": 60}, # Prevent brute force
    "/api/v1/": {"requests": 60, "window_seconds": 60},          # General API
}
```
- A dictionary mapping URL prefixes to their limits
- AI endpoints: 10 requests/minute (LLM calls cost money — OpenAI charges per token)
- Login endpoint: 5 requests/minute (prevents password brute-forcing)
- General API: 60 requests/minute (generous for normal use)
- **Order matters:** More specific paths are checked first (see `_get_limit_for_path`)

**Lines 70-73: Skip Non-API Routes**
```python
if not request.url.path.startswith("/api/"):
    return await call_next(request)
```
- Static files, health checks, and other non-API routes don't need rate limiting
- `startswith("/api/")` — only rate-limit API endpoints

**Lines 78-79: Client Identification**
```python
client_ip = request.client.host if request.client else "unknown"
```
- We identify clients by IP address
- `request.client.host` — the client's IP address
- `request.client` might be `None` in some test environments, so we default to `"unknown"`
- **In production:** Behind a load balancer (AWS ALB, Nginx), the real client IP is in the `X-Forwarded-For` header. Direct `request.client.host` would show the load balancer's IP

**Lines 82-86: Redis Key Construction**
```python
window_start = int(time.time()) // limit_config["window_seconds"]
redis_key = f"rl:{client_ip}:{request.url.path}:{window_start}"
```
- `time.time()` — Unix timestamp (e.g., `1727308800.123`)
- `int(...)` — truncates to integer: `1727308800`
- `// 60` — integer division by 60. This rounds DOWN to the nearest minute boundary
  - At 10:00:00 → `1727308800 // 60` = `28788480`
  - At 10:00:30 → `1727308830 // 60` = `28788480` (same!)
  - At 10:01:00 → `1727308860 // 60` = `28788481` (new window!)
- The Redis key includes IP, path, AND window — so counters are per-client, per-endpoint, per-window
- `"rl:"` prefix = "rate limit" — convention to namespace Redis keys

**Lines 89-91: Atomic Increment + Expiry**
```python
current_count = await redis_client.incr(redis_key)
if current_count == 1:
    await redis_client.expire(redis_key, limit_config["window_seconds"])
```
- `incr(redis_key)` — Redis INCR command. Atomically increments the counter by 1. If the key doesn't exist, creates it with value 1. Returns the new value
- **Atomic** means no race condition: even if 100 requests hit simultaneously, Redis guarantees correct counting
- `if current_count == 1` — first request in this window. Set the key to expire after `window_seconds`
- `expire(key, seconds)` — tells Redis to auto-delete this key after N seconds. This is self-cleanup — we never need to manually delete old counters

**Lines 94-112: Over Limit Response**
```python
if current_count > limit_config["requests"]:
    return JSONResponse(
        status_code=429,
        content={"error_code": "RATE_LIMIT_EXCEEDED", ...},
        headers={
            "Retry-After": str(limit_config["window_seconds"]),
            "X-RateLimit-Limit": str(limit_config["requests"]),
            "X-RateLimit-Remaining": "0",
        },
    )
```
- HTTP 429 = "Too Many Requests" (standard status code for rate limiting)
- `Retry-After` header — tells the client how many seconds to wait before retrying. Well-behaved clients (and good frontend code) respect this
- `X-RateLimit-Limit` — tells the client what the limit is (e.g., "60")
- `X-RateLimit-Remaining` — tells the client how many requests they have left (0 = blocked)
- These are **standard headers** used by GitHub, Twitter, Stripe, etc.

**Lines 114-119: Normal Response with Headers**
```python
response = await call_next(request)
remaining = max(0, limit_config["requests"] - current_count)
response.headers["X-RateLimit-Limit"] = str(limit_config["requests"])
response.headers["X-RateLimit-Remaining"] = str(remaining)
```
- If within limits, process the request normally
- Add rate limit headers to EVERY response (not just 429). This lets the frontend show "5 AI requests remaining" in the UI

**Lines 121-125: Fail Open**
```python
except Exception:
    logger.warning("rate_limiter_error", error="Redis unavailable, skipping rate limit")
    return await call_next(request)
```
- If Redis is down, we DON'T block requests. We let them through
- This is called **"fail open"** — when the safety system fails, allow access (availability > security for this feature)
- The opposite is **"fail closed"** — when the system fails, deny access (used for authentication — if the auth system is down, deny all requests)
- We log a warning so the ops team knows Redis is down

**Lines 127-137: Path Matching**
```python
@staticmethod
def _get_limit_for_path(path: str) -> dict:
    for prefix, config in sorted(RATE_LIMITS.items(), key=lambda x: -len(x[0])):
        if path.startswith(prefix):
            return config
    return {"requests": 100, "window_seconds": 60}
```
- `@staticmethod` — a decorator that means this method doesn't use `self` (doesn't need the instance)
- `sorted(..., key=lambda x: -len(x[0]))` — sorts by prefix length, LONGEST first. This ensures `/api/v1/ai/` (more specific) is checked before `/api/v1/` (less specific)
- `lambda x: -len(x[0])` — an anonymous function that returns the negative length of the key. Negative because `sorted()` sorts ascending, and we want descending (longest first)
- Default: 100 requests per minute for unknown paths

---

<a name="connections"></a>
## 10. How All 8 Files Connect — Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INCOMING HTTP REQUEST                               │
│                     POST /api/v1/habits  (body: {...})                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  MIDDLEWARE LAYER (runs in this order for EVERY request)                      │
│                                                                              │
│  ┌─────────────────────┐                                                     │
│  │  LoggingMiddleware   │ ← File 7: Generate request_id, start timer         │
│  │  (logging_middleware)│                                                     │
│  └──────────┬──────────┘                                                     │
│             │                                                                │
│             ▼                                                                │
│  ┌─────────────────────┐                                                     │
│  │  RateLimiterMiddleware│ ← File 8: Check Redis counter → allow or 429      │
│  │  (rate_limiter)      │   Uses: redis_client (Part 02), logger (File 5)    │
│  └──────────┬──────────┘                                                     │
│             │                                                                │
└─────────────┼────────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ROUTE HANDLER (e.g., POST /api/v1/habits)                                   │
│                                                                              │
│  Uses:                                                                       │
│  ├── PaginationParams (File 2) — for list endpoints                          │
│  ├── date_utils (File 4) — for date calculations                             │
│  ├── get_logger (File 5) — for logging in service/repo                       │
│  │                                                                           │
│  Calls: Service → Repository (inherits BaseRepository, File 3)               │
│                                                                              │
│  On error: raises NotFoundError / ConflictError / etc. (File 1)              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ERROR HANDLER (File 6) — catches exceptions from route handler              │
│                                                                              │
│  BaseAppError → 4xx JSON       (expected errors — user's fault)              │
│  ValidationError → 422 JSON    (bad request body)                            │
│  HTTPException → various JSON  (unknown route, wrong method)                 │
│  Exception → 500 JSON          (our bug — log full traceback)                │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  RESPONSE with headers:                                                      │
│  X-Request-ID: abc-12345     (from LoggingMiddleware)                        │
│  X-RateLimit-Remaining: 57   (from RateLimiterMiddleware)                    │
│  Content-Type: application/json                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dependency Map: Who Uses What

```
shared/exceptions.py ←──── middleware/error_handler.py (catches these)
                     ←──── auth/service.py, habits/service.py, etc. (raise these)

shared/base_schemas.py ←── auth/schemas.py, habits/schemas.py, etc. (inherit these)
                       ←── middleware/error_handler.py (ErrorResponse format)

shared/base_repository.py ←── auth/repository.py, habits/repository.py, etc. (inherit)

shared/date_utils.py ←──── analytics/repository.py (date ranges)
                     ←──── logs/service.py (today's date)
                     ←──── ai/agents (weekly report dates)

shared/logging.py ←──────── middleware/logging_middleware.py (request logging)
                  ←──────── middleware/rate_limiter.py (rate limit warnings)
                  ←──────── middleware/error_handler.py (error logging)
                  ←──────── EVERY service, repo, and handler in the app
```

---

<a name="design-decisions"></a>
## 11. Design Decisions

### Design Decision 1: Custom Exception Hierarchy vs FastAPI HTTPException

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Exception Strategy                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Custom exception hierarchy (BaseAppError + subclasses)     │
│                                                                     │
│  WHY:                                                               │
│  • Service layer stays HTTP-agnostic (no importing FastAPI)         │
│  • Consistent error format across ALL endpoints automatically       │
│  • Easy to test: assert service.login() raises UnauthorizedError    │
│  • Extensible: add RateLimitError, PaymentError later               │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. FastAPI HTTPException everywhere                                │
│     ❌ Couples service layer to HTTP (can't reuse in CLI/Celery)   │
│  2. Return error dicts from services                                │
│     ❌ No type safety, easy to forget fields, inconsistent formats │
│  3. Result monad (Ok/Err pattern)                                   │
│     ❌ Overkill for this project, unfamiliar to most Python devs   │
│                                                                     │
│  TRADE-OFFS:                                                        │
│  + Clean separation of concerns                                     │
│  + Framework-agnostic services                                      │
│  - One extra abstraction layer to learn                             │
│  - Must remember to catch in error handler                          │
│                                                                     │
│  AT SCALE:                                                          │
│  Same pattern. Add error codes for monitoring (alert on RATE_LIMIT  │
│  spikes). Add correlation_id for distributed tracing across         │
│  microservices.                                                     │
│                                                                     │
│  REAL-WORLD: Stripe, GitHub, Shopify all use custom error           │
│  hierarchies with machine-readable error codes.                     │
│                                                                     │
│  INTERVIEW TIP: "We used custom exceptions to keep the service      │
│  layer HTTP-agnostic. This made testing easier — we assert the      │
│  exception type, not HTTP status codes — and the same service can   │
│  be called from Celery tasks without knowing about HTTP."           │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Generic Base Repository vs Module-Specific CRUD

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Repository Pattern                                │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Generic BaseRepository with TypeVar + per-module subclass  │
│                                                                     │
│  WHY:                                                               │
│  • 5 CRUD methods written once, used by 6 modules                   │
│  • Type-safe: IDE autocomplete works with model-specific types      │
│  • Custom queries go in subclasses (single responsibility)          │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. No base — each repo writes its own CRUD                         │
│     ❌ 6 copies of identical get_by_id, create, update, delete     │
│  2. Mixin classes instead of inheritance                            │
│     ❌ More complex, harder to follow for beginners                │
│  3. SQLAlchemy 2.0 repository from sqlalchemy-utils                 │
│     ❌ Extra dependency, less control, harder to customize         │
│                                                                     │
│  TRADE-OFFS:                                                        │
│  + DRY (Don't Repeat Yourself) — CRUD in one place                 │
│  + Type safety via generics                                         │
│  - flush vs commit can confuse beginners                            │
│  - Generic type syntax looks intimidating at first                  │
│                                                                     │
│  AT SCALE:                                                          │
│  Add query filters to base: `get_all(filters={"status": "active"})` │
│  Add soft delete to base: `soft_delete(id)` sets `is_archived=True` │
│  Add audit logging: base repo logs every create/update/delete.      │
│                                                                     │
│  REAL-WORLD: Spring Boot's JpaRepository, Django's Manager —        │
│  every major framework uses this pattern.                           │
│                                                                     │
│  INTERVIEW TIP: "We used generics to create a type-safe base       │
│  repository. Each module inherits CRUD and adds custom queries.     │
│  This reduced boilerplate by about 70% and made unit testing        │
│  straightforward — we mock the base repo methods."                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 3: Structured JSON Logging vs Print Statements

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Logging Strategy                                  │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: structlog with JSON output + ELK-ready format              │
│                                                                     │
│  WHY:                                                               │
│  • Machine-parseable (ELK, CloudWatch, Datadog can index fields)    │
│  • Searchable by any field (user_id, request_id, error_code)        │
│  • Automatic context (timestamp, level, file, line number)          │
│  • Dev mode: pretty colors. Prod mode: JSON. Same code.             │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Python's logging with string formatting                         │
│     ❌ Not searchable by field, hard to aggregate in dashboards    │
│  2. Print statements                                                │
│     ❌ No levels, no file/line info, no rotation, amateur hour     │
│  3. loguru (popular alternative)                                    │
│     ❌ Less integration with stdlib, structlog is more enterprise  │
│                                                                     │
│  AT SCALE:                                                          │
│  Ship JSON logs to ELK Stack (Elasticsearch + Logstash + Kibana).   │
│  Create dashboards: error rate, slowest endpoints, 429 rate.        │
│  Set up alerts: if 500 errors > 10 per minute → PagerDuty alert.   │
│                                                                     │
│  INTERVIEW TIP: "We used structlog for structured JSON logging.     │
│  In development it renders pretty colored output, in production it  │
│  outputs JSON shipped to our ELK stack. This let us search logs     │
│  by user_id, request_id, or error_code across all services."        │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 4: Rate Limiter — Fail Open vs Fail Closed

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Rate Limiter Failure Mode                         │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Fail open (if Redis is down, allow all requests)           │
│                                                                     │
│  WHY:                                                               │
│  • Rate limiting is a protection, not a core feature                │
│  • Users shouldn't be blocked because Redis crashed                 │
│  • Availability > rate limiting. The app should keep working.       │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Fail closed (block all if Redis down)                           │
│     ❌ Redis outage = entire API down. Unacceptable.               │
│  2. In-memory fallback (Python dict counter)                        │
│     ❌ Doesn't work with multiple server instances (each has own   │
│        counter). Also, memory leak risk.                            │
│  3. No rate limiting                                                │
│     ❌ Wide open to abuse. Not production-ready.                   │
│                                                                     │
│  TRADE-OFFS:                                                        │
│  + API stays available during Redis outage                          │
│  - During Redis outage, no rate protection (short-lived risk)       │
│                                                                     │
│  NOTE: Authentication uses "fail closed" — if you can't verify the  │
│  token, DENY access. Security > availability for auth.              │
│                                                                     │
│  INTERVIEW TIP: "Rate limiting fails open because availability is   │
│  more important than throttling. Authentication fails closed because │
│  security is more important than availability. The failure mode      │
│  depends on what you're protecting."                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 12. How to Verify Your Work

After typing all 8 files, verify that the imports work and file structure is correct.

### Step 1: Check File Structure

```
backend/app/
├── shared/
│   ├── __init__.py              ← Create this (empty file)
│   ├── exceptions.py            ✅ File 1
│   ├── base_schemas.py          ✅ File 2
│   ├── base_repository.py       ✅ File 3
│   ├── date_utils.py            ✅ File 4
│   └── logging.py               ✅ File 5
├── middleware/
│   ├── __init__.py              ← Create this (empty file)
│   ├── error_handler.py         ✅ File 6
│   ├── logging_middleware.py    ✅ File 7
│   └── rate_limiter.py          ✅ File 8
```

### Step 2: Verify Imports (Run These Commands)

```bash
# From the backend/ directory:
docker-compose exec backend python -c "from app.shared.exceptions import NotFoundError; print('✅ exceptions.py OK')"
docker-compose exec backend python -c "from app.shared.base_schemas import PaginatedResponse; print('✅ base_schemas.py OK')"
docker-compose exec backend python -c "from app.shared.base_repository import BaseRepository; print('✅ base_repository.py OK')"
docker-compose exec backend python -c "from app.shared.date_utils import utc_now, start_of_week; print('✅ date_utils.py OK')"
docker-compose exec backend python -c "from app.shared.logging import get_logger; print('✅ logging.py OK')"
docker-compose exec backend python -c "from app.middleware.error_handler import register_error_handlers; print('✅ error_handler.py OK')"
docker-compose exec backend python -c "from app.middleware.logging_middleware import LoggingMiddleware; print('✅ logging_middleware.py OK')"
docker-compose exec backend python -c "from app.middleware.rate_limiter import RateLimiterMiddleware; print('✅ rate_limiter.py OK')"
```

### Step 3: Quick Smoke Test

```bash
# Test exception hierarchy
docker-compose exec backend python -c "
from app.shared.exceptions import NotFoundError, BaseAppError
e = NotFoundError('User not found')
assert e.status_code == 404
assert e.error_code == 'NOT_FOUND'
assert isinstance(e, BaseAppError)
print('✅ Exception hierarchy works!')
"

# Test date utilities
docker-compose exec backend python -c "
from app.shared.date_utils import utc_now, start_of_week, end_of_month
print(f'UTC now: {utc_now()}')
print(f'Start of week: {start_of_week()}')
print(f'End of month: {end_of_month()}')
print('✅ Date utils work!')
"

# Test pagination
docker-compose exec backend python -c "
from app.shared.base_schemas import PaginationParams
p = PaginationParams(page=3, page_size=20)
assert p.offset == 40  # (3-1) * 20
assert p.limit == 20
print('✅ Pagination math works!')
"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'app.shared'` | Missing `__init__.py` | Create empty `backend/app/shared/__init__.py` |
| `ModuleNotFoundError: No module named 'app.middleware'` | Missing `__init__.py` | Create empty `backend/app/middleware/__init__.py` |
| `ImportError: cannot import name 'Base' from 'app.database'` | database.py not created yet | Go back to Part 02, create `database.py` first |
| `ImportError: cannot import name 'get_settings' from 'app.config'` | config.py not created yet | Go back to Part 02, create `config.py` first |
| `ModuleNotFoundError: No module named 'structlog'` | Package not installed | Run `pip install structlog` or check `requirements.txt` |
| `ModuleNotFoundError: No module named 'pydantic'` | Package not installed | Run `pip install pydantic` or check `requirements.txt` |

---

<a name="what-you-learned"></a>
## 13. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Exception Hierarchy** | Parent class defines structure, children specialize (NotFoundError=404) | `shared/exceptions.py` |
| 2 | **Inheritance** | `class Child(Parent):` — child gets all parent's features + adds its own | All files in this doc |
| 3 | **`super().__init__()`** | Calls the parent class constructor — required when overriding `__init__` | `exceptions.py`, `base_repository.py` |
| 4 | **Pydantic Schemas** | Define the shape of API data — validation, serialization, documentation | `base_schemas.py` |
| 5 | **`from_attributes=True`** | Lets Pydantic create schemas from SQLAlchemy model objects | `base_schemas.py` |
| 6 | **Generics (`Generic[T]`)** | Write code that works with ANY type, decided at usage time | `base_schemas.py`, `base_repository.py` |
| 7 | **`TypeVar`** | Creates a type placeholder (`T`) for generics | Both files |
| 8 | **`@property`** | Makes a method look like an attribute (no parentheses to call) | `PaginationParams.offset` |
| 9 | **Repository Pattern** | Layer between service and database — services never write SQL | `base_repository.py` |
| 10 | **`async/await`** | Non-blocking I/O — while waiting for DB, handle other requests | `base_repository.py`, middleware files |
| 11 | **`**kwargs`** | Accept any keyword arguments as a dictionary | `base_repository.create()` |
| 12 | **`setattr(obj, key, value)`** | Set an attribute dynamically (like `obj.key = value` but with a variable) | `base_repository.update()` |
| 13 | **`flush()` vs `commit()`** | flush = execute SQL (reversible). commit = finalize transaction (permanent) | `base_repository.py` |
| 14 | **Timezone-Aware Datetimes** | Always attach timezone info — prevents comparison bugs | `date_utils.py` |
| 15 | **`ZoneInfo`** | Python 3.9+ IANA timezone support (`"Asia/Kolkata"` → UTC+5:30) | `date_utils.py` |
| 16 | **List Comprehension** | `[x for x in range(n)]` — concise way to build lists | `date_utils.date_range()` |
| 17 | **Structured Logging** | JSON logs with named fields — searchable by ELK/CloudWatch | `logging.py` |
| 18 | **Processor Pipeline** | Chain of functions that transform log events in order | `logging.py` |
| 19 | **Middleware** | Code that runs before AND after every request | `logging_middleware.py`, `rate_limiter.py` |
| 20 | **`call_next(request)`** | Passes request to the next handler in the middleware chain | Both middleware files |
| 21 | **Request ID** | Unique ID per request for tracing in logs | `logging_middleware.py` |
| 22 | **Rate Limiting** | Restrict requests per time window — prevents abuse | `rate_limiter.py` |
| 23 | **Redis INCR + EXPIRE** | Atomic counter with auto-cleanup — perfect for rate limiting | `rate_limiter.py` |
| 24 | **Fail Open vs Fail Closed** | Allow vs deny when the safety system itself fails | `rate_limiter.py` |
| 25 | **HTTP 429 Too Many Requests** | Standard response for rate-limited requests | `rate_limiter.py` |
| 26 | **`@staticmethod`** | Method that doesn't use `self` — belongs to the class, not an instance | `rate_limiter.py` |
| 27 | **Exception Handlers** | FastAPI functions that catch specific exception types → JSON response | `error_handler.py` |
| 28 | **`getattr(obj, name)`** | Get an attribute by name dynamically — useful for dynamic dispatch | `logging_middleware.py`, `logging.py` |

---

<a name="interview"></a>
## 14. Interview Q&A

### Q1: Why did you use custom exceptions instead of FastAPI's HTTPException?
**A:** "We created a custom exception hierarchy rooted at `BaseAppError` to keep the service layer HTTP-agnostic. Services raise domain-specific exceptions like `NotFoundError` or `ConflictError` without importing FastAPI. This means the same service code can be called from Celery background tasks, CLI scripts, or test suites without any HTTP dependency. The error handler middleware translates these exceptions to HTTP responses at the API boundary — clean separation of concerns."

### Q2: Explain the Repository Pattern and why you used generics.
**A:** "The Repository Pattern abstracts database access behind a clean interface. Our `BaseRepository[ModelType]` provides CRUD operations that work with any SQLAlchemy model — `create`, `get_by_id`, `get_all`, `update`, `delete`. Each module creates a subclass (e.g., `HabitRepository(BaseRepository[Habit])`) that inherits these operations and adds custom queries. Generics ensure type safety — the IDE knows that `HabitRepository.get_by_id()` returns a `Habit`, not a generic object. This reduced boilerplate by about 70% across our 6 modules."

### Q3: Why `flush()` instead of `commit()` in the base repository?
**A:** "Flush executes the SQL statement but keeps the transaction open. Commit finalizes the transaction. We flush in the repository so that the route handler (or the dependency injection middleware) controls when the transaction commits. This allows multiple repository operations in a single transaction — for example, creating a habit log AND updating the streak count. If either fails, both roll back. If we committed in the repository, each operation would be its own transaction and we couldn't guarantee atomicity."

### Q4: How does your rate limiter work? What happens if Redis goes down?
**A:** "We use Redis INCR with EXPIRE for a fixed-window rate limiter. Each request increments a Redis key scoped to the client IP, endpoint path, and time window. If the counter exceeds the limit, we return HTTP 429 with `Retry-After` and `X-RateLimit-Remaining` headers. Different endpoints have different limits — AI endpoints allow 10 requests per minute (LLM calls are expensive), login allows 5 (prevents brute-force), and general API allows 60. If Redis goes down, we fail open — requests are allowed through without rate limiting. We chose this because rate limiting is a protection feature, not a core requirement. The opposite choice, fail closed, is what we use for authentication — if you can't verify the token, deny the request."

### Q5: What is structured logging and why did you choose it over regular logging?
**A:** "Structured logging outputs log events as JSON with named fields instead of formatted strings. Instead of `'User 123 logged in'`, we log `{'event': 'user_login', 'user_id': '123'}`. This makes logs machine-parseable — we can search by `user_id`, filter by `event`, and aggregate by `status_code` in ELK Stack or CloudWatch. We use structlog, which provides a processor pipeline: each log event passes through processors that add timestamp, log level, caller info, and format the output. In development, it renders colored console output for readability. In production, it outputs JSON for log aggregation tools."

### Q6: Explain middleware execution order. Why does logging come before rate limiting?
**A:** "Middleware executes in registration order. We register LoggingMiddleware first, then RateLimiterMiddleware. This means logging wraps rate limiting — every request gets logged, even rate-limited ones. If we reversed the order, rate-limited requests (429 responses) wouldn't be logged, and we'd miss important security signals like brute-force attempts. The logging middleware also generates the request_id used by all subsequent log entries, so it must run first."

### Q7: What's the difference between HTTP 401 and 403?
**A:** "401 Unauthorized means 'I don't know who you are' — no token, expired token, invalid token. The user needs to log in. 403 Forbidden means 'I know who you are, but you're not allowed' — the user is authenticated but lacks permission. For example, user A trying to view user B's habits gets 403, not 401. This distinction matters for the frontend: 401 triggers a redirect to the login page, 403 shows an 'access denied' message."

### Q8: Why do you store all times in UTC?
**A:** "Storing in UTC gives us a single source of truth. A user in India at 11 PM IST and a user in New York at 1:30 PM EST are experiencing the same moment — UTC normalizes this. We convert to the user's timezone only when displaying data. This avoids edge cases like a habit logged at midnight IST being counted on the wrong day in UTC. The `to_user_timezone()` helper handles conversion using Python's `zoneinfo` module with IANA timezone strings stored in each user's profile."

### Q9: What is `from_attributes=True` in Pydantic and why is it needed?
**A:** "By default, Pydantic creates models from dictionaries. But our data comes from SQLAlchemy model objects, which use attributes (dot notation) not dictionary keys. Setting `from_attributes=True` in the model config tells Pydantic: 'You can read fields from Python object attributes, not just dictionary keys.' Without it, `UserResponse.model_validate(user_db_object)` would fail. With it, Pydantic automatically reads `user_db_object.email`, `user_db_object.full_name`, etc."

### Q10: How does `PaginatedResponse[T]` work with generics?
**A:** "PaginatedResponse inherits from both `BaseModel` and `Generic[T]`, where `T` is a type variable. When we write `PaginatedResponse[HabitResponse]`, Python substitutes `T` with `HabitResponse`, so `items: list[T]` becomes `items: list[HabitResponse]`. This one class handles pagination for all entity types — habits, logs, users — instead of writing separate `PaginatedHabitsResponse`, `PaginatedLogsResponse`, etc. FastAPI uses this type information to generate accurate OpenAPI documentation automatically."

---

<a name="navigation"></a>
## 15. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 02: Backend Foundation](./phase4-part02-backend-foundation.md) |
| ➡️ Next | [Phase 4 Part 04: Auth Module Overview](./phase4-part04-auth-service-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

---

**End of Phase 4 Part 03: Shared Utilities & Middleware**

*You now have the safety net — exceptions, schemas, repository, dates, logging, error handling, request logging, and rate limiting. Every module you build from here inherits these building blocks. Next up: the Auth module — the first real feature module.*
