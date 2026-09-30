# 🔐 Phase 4 Part 04a: Auth — Models, Exceptions & Schemas

> **"The data layer is the skeleton of your module. The model defines what's in the database, the exceptions define what can go wrong, and the schemas define what the outside world sees. Get these right and everything else follows."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04a (Auth Data Layer) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04-auth-service-overview.md](./phase4-part04-auth-service-overview.md) |
| **Next** | [phase4-part04b-auth-security-jwt.md](./phase4-part04b-auth-security-jwt.md) |
| **Files in This Doc** | 3 files (models.py, exceptions.py, schemas.py) |
| **Endpoints** | 0 (data definitions only — no routes yet) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (new concepts: ORM, mapped_column, EmailStr, schema separation) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [File 1: models.py — User Database Model](#models)
3. [File 2: exceptions.py — Auth-Specific Exceptions](#exceptions)
4. [File 3: schemas.py — Request/Response Schemas](#schemas)
5. [How These 3 Files Connect](#connections)
6. [Design Decisions](#design-decisions)
7. [How to Verify Your Work](#verify)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

Every module starts with the **data layer** — the three files that define:
1. **What's stored** (models.py — database table)
2. **What can go wrong** (exceptions.py — error types)
3. **What goes in and out** (schemas.py — API contracts)

### Real-World Analogy

Think of a **hospital patient registration system**:
- **models.py** = the patient record in the hospital database (name, DOB, blood type, insurance ID, internal notes)
- **exceptions.py** = possible problems (patient already registered, insurance not found, account deactivated)
- **schemas.py** = the forms the patient fills and receives:
  - **Registration form** (UserCreate) = what the patient provides (name, email, password)
  - **ID card** (UserResponse) = what the patient gets back (name, email, ID — NOT internal notes or insurance)
  - **Login form** (UserLogin) = what they show to get in (email + password)

### File Structure

```
backend/app/modules/auth/
├── __init__.py       ← Empty (marks as Python package)
├── models.py         ← File 1: User table definition (SQLAlchemy ORM)
├── exceptions.py     ← File 2: 5 auth-specific exception classes
└── schemas.py        ← File 3: 5 request/response Pydantic schemas
```

### Why This Order?

| # | File | Why First |
|---|------|----------|
| 1 | `models.py` | Defines the table — everything else depends on this structure |
| 2 | `exceptions.py` | Service (built later) raises these, error_handler catches them |
| 3 | `schemas.py` | Router (built later) uses these for request validation and response formatting |

---

<a name="models"></a>
## 2. File 1: `models.py` — User Database Model

### What Is an ORM Model? Read This First

An **ORM (Object-Relational Mapping)** model is a Python class that represents a database table. Each attribute of the class = a column in the table. Each instance of the class = a row in the table.

```
Python Class               ←→        Database Table
──────────────                        ──────────────
class User(Base):                     CREATE TABLE users (
    id = ...                              id UUID PRIMARY KEY,
    email = ...                           email VARCHAR(255),
    password_hash = ...                   password_hash VARCHAR(255),
    ...                                   ...
                                      );

user = User(email="a@b.com")          INSERT INTO users (email) VALUES ('a@b.com')
user.email                            SELECT email FROM users WHERE ...
user.email = "new@b.com"              UPDATE users SET email = 'new@b.com' WHERE ...
session.delete(user)                  DELETE FROM users WHERE ...
```

**Why not just write SQL?**
1. **Type safety** — Python catches typos; SQL doesn't (you won't know about a wrong column name until runtime)
2. **Migrations** — Alembic reads the model and auto-generates `ALTER TABLE` statements when you change a column
3. **Relationships** — `user.habits` gives you all habits without writing a JOIN
4. **Security** — ORM auto-escapes values, preventing SQL injection attacks
5. **Portability** — switch from PostgreSQL to MySQL by changing one connection string (in theory)

### What Is `mapped_column()`? (SQLAlchemy 2.0 Style)

SQLAlchemy 2.0 introduced a new way to define columns:

```python
# OLD WAY (SQLAlchemy 1.x) — still works but outdated
email = Column(String(255), unique=True, nullable=False)

# NEW WAY (SQLAlchemy 2.0) — type-safe, IDE-friendly
email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
```

The new way adds `Mapped[str]` — a **type annotation** that tells your IDE (VS Code) and type checker (mypy) that `user.email` is a `str`. The old way had no type info.

### Type This Code: `backend/app/modules/auth/models.py`

```python
# ============================================================================
# Auth Module — User Database Model
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the 'users' table in PostgreSQL using SQLAlchemy ORM.
#   Each class attribute = a column in the database table.
#
# WHY ORM (Object-Relational Mapping):
#   Instead of writing raw SQL:
#     "INSERT INTO users (email, password_hash) VALUES ('a@b.com', '$2b$...')"
#   You write Python:
#     user = User(email="a@b.com", password_hash="$2b$...")
#     session.add(user)
#
#   Benefits:
#   1. Type safety — Python catches typos, SQL doesn't
#   2. Migrations — Alembic auto-generates ALTER TABLE from model changes
#   3. Relationships — user.habits gives you all habits, no manual JOIN
#   4. Security — ORM auto-escapes values, preventing SQL injection
#
# TABLE SCHEMA:
#   users
#   ├── id           UUID (primary key, auto-generated)
#   ├── email        VARCHAR(255) (unique, indexed — login identifier)
#   ├── password_hash VARCHAR(255) (bcrypt hash, NEVER plain text)
#   ├── full_name    VARCHAR(100)
#   ├── timezone     VARCHAR(50) (IANA timezone, e.g., "Asia/Kolkata")
#   ├── is_active    BOOLEAN (soft delete — deactivate instead of delete)
#   ├── created_at   TIMESTAMP (auto-set on creation)
#   └── updated_at   TIMESTAMP (auto-set on every update)
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    """
    User database model.

    IMPORTANT DESIGN DECISIONS:

    1. UUID primary key (not auto-increment integer):
       - UUIDs are globally unique — safe to expose in URLs and APIs
       - Auto-increment IDs leak information (competitor can guess user count)
       - UUIDs allow future database sharding (split data across servers)

    2. password_hash (not password):
       - We NEVER store plain text passwords
       - bcrypt hash is one-way — even if database is stolen, passwords are safe
       - The column name reminds developers: this is a hash, not a password

    3. is_active (soft delete):
       - Deleting a user account doesn't remove their row
       - We set is_active=False — preserves data for analytics and legal compliance
       - User can potentially reactivate their account

    4. timezone:
       - Stored per user, not globally
       - Used to show dates/times in the user's local time
       - Used for daily reminder scheduling (8 AM in THEIR timezone)
    """

    __tablename__ = "users"

    # ── Primary Key ──
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,    # Auto-generate UUID on creation
        comment="Unique user identifier",
    )

    # ── Login Credentials ──
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,           # No duplicate emails
        index=True,            # Index for fast lookup on login
        nullable=False,
        comment="User email — used as login identifier",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Bcrypt password hash — NEVER store plain text",
    )

    # ── Profile ──
    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's display name",
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        server_default="UTC",
        nullable=False,
        comment="IANA timezone (e.g., Asia/Kolkata, America/New_York)",
    )

    # ── Account Status ──
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        comment="False = account deactivated (soft delete)",
    )

    # ── Timestamps ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Account creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
        comment="Last profile update timestamp (UTC)",
    )

    def __repr__(self) -> str:
        """String representation for debugging — NEVER include password_hash."""
        return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"
```

### Line-by-Line Explanation

**Lines 32-34: Imports**
```python
import uuid
from datetime import datetime, timezone
```
- `uuid` — Python's built-in module for generating UUIDs (Universally Unique Identifiers). `uuid.uuid4()` creates a random 128-bit UUID like `550e8400-e29b-41d4-a716-446655440000`
- `datetime` — represents date + time
- `timezone` — provides `timezone.utc` for creating timezone-aware datetimes

**Lines 36-38: SQLAlchemy Imports**
```python
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
```
- `Boolean, DateTime, String` — SQLAlchemy column types that map to SQL types:
  - `Boolean` → PostgreSQL `BOOLEAN`
  - `DateTime(timezone=True)` → PostgreSQL `TIMESTAMP WITH TIME ZONE`
  - `String(255)` → PostgreSQL `VARCHAR(255)`
- `UUID` — from PostgreSQL dialect (not all databases support UUID natively; PostgreSQL does)
- `as_uuid=True` tells SQLAlchemy to return Python `uuid.UUID` objects, not raw strings
- `Mapped[str]` — type annotation that tells Python/IDE: "this attribute is a string"
- `mapped_column()` — SQLAlchemy 2.0 function to define a column with full type safety

**Line 40: `from app.database import Base`**
```python
from app.database import Base
```
- `Base` is the declarative base class from Part 02's `database.py`
- ALL models must inherit from `Base`. This registers the model with SQLAlchemy so it knows about the table
- Alembic scans `Base.metadata` to auto-generate migrations

**Line 43: `class User(Base):`**
```python
class User(Base):
```
- `class User` — creates a new class named `User`
- `(Base)` — inherits from SQLAlchemy's declarative base. This makes `User` a database model
- Without `(Base)`, it would be a regular Python class with no database awareness

**Line 65: `__tablename__ = "users"`**
```python
__tablename__ = "users"
```
- Tells SQLAlchemy which table this model maps to in PostgreSQL
- Convention: model name is singular (`User`), table name is plural (`users`)
- If you don't set this, SQLAlchemy uses the class name lowercased (`user`)

**Lines 68-73: Primary Key — UUID**
```python
id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4,
    comment="Unique user identifier",
)
```
- `id: Mapped[uuid.UUID]` — type annotation: `id` is a `uuid.UUID` type
- `UUID(as_uuid=True)` — PostgreSQL UUID column type. `as_uuid=True` means Python gets `uuid.UUID` objects, not strings
- `primary_key=True` — this is THE unique identifier for each row. PostgreSQL auto-creates a unique index on it
- `default=uuid.uuid4` — when creating a new user, Python automatically calls `uuid.uuid4()` to generate an ID. Note: it's `uuid.uuid4` (no parentheses!) — passing the function itself, not calling it
- `comment=` — adds a comment in PostgreSQL: `COMMENT ON COLUMN users.id IS 'Unique user identifier'`

**Why UUID, not auto-increment integer?**
| Feature | Auto-increment (`1, 2, 3...`) | UUID |
|---------|------------------------------|------|
| Guessable | ✅ Yes — try `/users/1`, `/users/2`... | ❌ No — random 128-bit |
| Info leak | ✅ User count: last ID = 1000 users | ❌ No info leaked |
| Distributed | ❌ Two servers might assign same ID | ✅ UUIDs are globally unique |
| URL safety | ⚠️ Exposing reveals DB internals | ✅ Safe to expose anywhere |
| Performance | ✅ Slightly faster (smaller size, sequential) | ⚠️ Random order, larger |

**Lines 76-84: Email Column**
```python
email: Mapped[str] = mapped_column(
    String(255),
    unique=True,
    index=True,
    nullable=False,
    comment="User email — used as login identifier",
)
```
- `String(255)` — VARCHAR(255). 255 is the maximum email length per RFC spec
- `unique=True` — database enforces: no two users can have the same email. If you try, PostgreSQL raises a `UniqueViolation` error (which our code catches and converts to `UserAlreadyExistsError`)
- `index=True` — creates a database index on this column. Without it, login would scan ALL rows to find an email. With it, lookup is O(log n) instead of O(n). For 100K users, that's the difference between 1ms and 100ms
- `nullable=False` — cannot be NULL. Every user MUST have an email

**Lines 85-89: Password Hash**
```python
password_hash: Mapped[str] = mapped_column(
    String(255),
    nullable=False,
    comment="Bcrypt password hash — NEVER store plain text",
)
```
- Named `password_hash`, NOT `password` — the column name itself is documentation. It reminds every developer who reads it: "This is a hash. Don't treat it as a password."
- bcrypt hashes are 60 characters, but we use String(255) for future-proofing (different algorithms produce different lengths)
- No `unique=True` — multiple users CAN have the same password hash (bcrypt's salt makes this astronomically unlikely, but not impossible)

**Lines 92-97: Full Name**
```python
full_name: Mapped[str] = mapped_column(
    String(100),
    nullable=False,
    comment="User's display name",
)
```
- `String(100)` — max 100 characters for the display name
- `nullable=False` — every user must have a name (even if it's just an initial)

**Lines 98-104: Timezone**
```python
timezone: Mapped[str] = mapped_column(
    String(50),
    default="UTC",
    server_default="UTC",
    nullable=False,
    comment="IANA timezone (e.g., Asia/Kolkata, America/New_York)",
)
```
- `default="UTC"` — Python-side default. When you create `User()` without specifying timezone, Python sets it to `"UTC"`
- `server_default="UTC"` — database-side default. If you INSERT without this column (e.g., from a SQL script), PostgreSQL sets it to `"UTC"`
- **Why both?** `default` works when using Python ORM. `server_default` works when inserting directly via SQL or migrations. Belt and suspenders
- IANA timezone strings like `"Asia/Kolkata"` are the global standard (same as `ZoneInfo` in `date_utils.py`)

**Lines 107-113: Account Status (Soft Delete)**
```python
is_active: Mapped[bool] = mapped_column(
    Boolean,
    default=True,
    server_default="true",
    nullable=False,
    comment="False = account deactivated (soft delete)",
)
```
- `Boolean` → PostgreSQL `BOOLEAN` type (true/false)
- `default=True` — new accounts are active
- `server_default="true"` — note: string `"true"`, not Python `True`. PostgreSQL expects a string in `DEFAULT` clause
- **Soft delete:** Instead of `DELETE FROM users WHERE id = ...`, we do `UPDATE users SET is_active = false WHERE id = ...`. This preserves data for analytics, audit logs, and potential reactivation

**Lines 116-121: Created At**
```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(timezone.utc),
    nullable=False,
    comment="Account creation timestamp (UTC)",
)
```
- `DateTime(timezone=True)` → PostgreSQL `TIMESTAMP WITH TIME ZONE`. Stores timezone info along with the timestamp
- `default=lambda: datetime.now(timezone.utc)` — `lambda:` creates a tiny anonymous function. Each time a user is created, this function runs and returns the current UTC time
- **Why `lambda:` not just `datetime.now(timezone.utc)`?** Without lambda, `datetime.now()` runs ONCE when the module loads, and EVERY user gets the same creation time (the time the server started). With lambda, it runs fresh for each new user

**Lines 122-128: Updated At**
```python
updated_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    default=None,
    onupdate=lambda: datetime.now(timezone.utc),
    nullable=True,
    comment="Last profile update timestamp (UTC)",
)
```
- `Mapped[datetime | None]` — this column can be `None` (NULL). New users have `updated_at = NULL` until they update their profile
- `default=None` — starts as NULL (user hasn't been updated yet)
- `onupdate=lambda: datetime.now(timezone.utc)` — **magic feature**: SQLAlchemy automatically sets this to the current time whenever ANY column on this row changes. You don't have to manually set it
- `nullable=True` — allows NULL (for users who've never been updated)

**Lines 130-132: `__repr__` Method**
```python
def __repr__(self) -> str:
    return f"<User(id={self.id}, email={self.email}, active={self.is_active})>"
```
- `__repr__` is a special method Python calls when you `print(user)` or see it in a debugger
- We include `id`, `email`, and `is_active` — useful for debugging
- We NEVER include `password_hash` — even in debug output, passwords should stay hidden

---

<a name="exceptions"></a>
## 3. File 2: `exceptions.py` — Auth-Specific Exceptions

### Why Module-Specific Exceptions?

In Part 03, we created **generic** exceptions (`NotFoundError`, `UnauthorizedError`). Now we create **auth-specific** ones that inherit from those generics.

```
Generic (shared/exceptions.py):
  raise UnauthorizedError("Something went wrong")
  → error_code: "UNAUTHORIZED" (generic — frontend can't tell what happened)

Specific (auth/exceptions.py):
  raise InvalidCredentialsError()
  → error_code: "INVALID_CREDENTIALS" (specific — frontend shows "Wrong email or password")
  
  raise TokenExpiredError()
  → error_code: "TOKEN_EXPIRED" (specific — frontend tries to refresh the token)
```

The frontend checks `error_code` to decide what to do:
```javascript
// Frontend code:
if (error.error_code === "TOKEN_EXPIRED") {
    // Try refreshing the token automatically
    await refreshTokens();
} else if (error.error_code === "INVALID_CREDENTIALS") {
    // Show "Wrong email or password" to the user
    showError("Wrong email or password");
} else if (error.error_code === "ACCOUNT_DEACTIVATED") {
    // Show "Contact support" message
    showError("Your account has been deactivated. Contact support.");
}
```

### Type This Code: `backend/app/modules/auth/exceptions.py`

```python
# ============================================================================
# Auth Module — Custom Exceptions
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines auth-specific exceptions. Each maps to a specific HTTP error.
#   The service layer raises these; the error_handler converts them to JSON.
#
# WHY MODULE-SPECIFIC EXCEPTIONS:
#   Generic: raise UnauthorizedError("Something went wrong")
#   Specific: raise InvalidCredentialsError()
#
#   Specific exceptions carry the right error_code ("INVALID_CREDENTIALS")
#   so the frontend can show the right message (e.g., "Wrong email or password")
#   without parsing the message string.
# ============================================================================

from app.shared.exceptions import ConflictError, UnauthorizedError


class InvalidCredentialsError(UnauthorizedError):
    """
    Wrong email or password — HTTP 401.

    WHY one error for both "email not found" AND "wrong password":
      Security best practice. If we say "email not found",
      an attacker knows which emails are registered.
      With a generic "invalid credentials", they can't tell
      if the email exists or the password is wrong.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )


class UserAlreadyExistsError(ConflictError):
    """
    Email already registered — HTTP 409.

    Raised during signup when the email is already in use.
    """

    def __init__(self) -> None:
        super().__init__(
            message="A user with this email already exists",
            error_code="EMAIL_ALREADY_EXISTS",
        )


class TokenExpiredError(UnauthorizedError):
    """
    JWT token has expired — HTTP 401.

    The frontend should catch this and try to refresh the token.
    If refresh also fails, redirect to login page.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Token has expired",
            error_code="TOKEN_EXPIRED",
        )


class TokenInvalidError(UnauthorizedError):
    """
    JWT token is malformed or tampered with — HTTP 401.

    This means someone sent a fake token or the token was corrupted.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Invalid token",
            error_code="TOKEN_INVALID",
        )


class AccountDeactivatedError(UnauthorizedError):
    """
    User account has been deactivated — HTTP 401.

    is_active=False in the database. User needs to contact support.
    """

    def __init__(self) -> None:
        super().__init__(
            message="Account has been deactivated",
            error_code="ACCOUNT_DEACTIVATED",
        )
```

### Line-by-Line Explanation

**Line 17: Import**
```python
from app.shared.exceptions import ConflictError, UnauthorizedError
```
- We import the **generic** exceptions from the shared module (Part 03)
- `ConflictError` (409) — base for `UserAlreadyExistsError`
- `UnauthorizedError` (401) — base for all token/credential errors

**Lines 20-30: `InvalidCredentialsError`**
```python
class InvalidCredentialsError(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )
```
- `(UnauthorizedError)` — inherits from `UnauthorizedError` which inherits from `BaseAppError`. The full chain: `InvalidCredentialsError → UnauthorizedError → BaseAppError → Exception`
- `def __init__(self) -> None:` — the constructor takes NO arguments. The message and error_code are hardcoded. This ensures consistency — every time this error is raised, it says the same thing
- `super().__init__(...)` — calls `UnauthorizedError.__init__()` which sets `status_code=401`
- **Security note:** The message says "Invalid email or password" — NOT "Email not found" or "Wrong password." If we said "Email not found," an attacker could:
  1. Try `test@gmail.com` → "Email not found" → this email is NOT registered
  2. Try `shreya@gmail.com` → "Wrong password" → this email IS registered! Now brute-force the password
  
  With "Invalid email or password," the attacker learns nothing.

**Lines 32-41: `UserAlreadyExistsError`**
```python
class UserAlreadyExistsError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            message="A user with this email already exists",
            error_code="EMAIL_ALREADY_EXISTS",
        )
```
- Inherits from `ConflictError` (409). HTTP 409 means "conflict with existing resource"
- Raised in `service.py` during signup when the email is already in the database
- `error_code="EMAIL_ALREADY_EXISTS"` — the frontend uses this to show "This email is already registered. Try logging in instead."

**Lines 43-52: `TokenExpiredError`**
```python
class TokenExpiredError(UnauthorizedError):
```
- Raised in `security.py` when decoding a JWT that has passed its expiry time
- The frontend checks for `TOKEN_EXPIRED` and automatically tries to refresh:
  ```
  API call → 401 TOKEN_EXPIRED → call /auth/refresh → get new tokens → retry API call
  ```
- This happens transparently — the user doesn't notice the expired token

**Lines 54-63: `TokenInvalidError`**
```python
class TokenInvalidError(UnauthorizedError):
```
- Raised when the JWT is malformed (not valid base64), tampered with (signature doesn't match), or blacklisted (user logged out)
- Unlike `TOKEN_EXPIRED`, there's no recovery — redirect to login page

**Lines 65-75: `AccountDeactivatedError`**
```python
class AccountDeactivatedError(UnauthorizedError):
```
- Raised when a user tries to log in but `is_active=False`
- This is a soft-delete check — the account exists but has been deactivated
- The frontend shows "Your account has been deactivated. Contact support."

### Exception Hierarchy Diagram

```
Exception (Python built-in)
└── BaseAppError (shared/exceptions.py) — status_code, error_code, message
    ├── UnauthorizedError (401)
    │   ├── InvalidCredentialsError  → "Invalid email or password"
    │   ├── TokenExpiredError        → "Token has expired"
    │   ├── TokenInvalidError        → "Invalid token"
    │   └── AccountDeactivatedError  → "Account has been deactivated"
    └── ConflictError (409)
        └── UserAlreadyExistsError   → "A user with this email already exists"
```

---

<a name="schemas"></a>
## 3. File 3: `schemas.py` — Request/Response Schemas

### Why Separate Schemas from Models? Read This First

This is a **critical security concept**.

```
SQLAlchemy Model (models.py):          Pydantic Schema (schemas.py):
┌────────────────────────┐             ┌─────────────────────────┐
│ User                    │             │ UserResponse             │
│ ├── id                  │             │ ├── id                   │
│ ├── email               │             │ ├── email                │
│ ├── password_hash  ⚠️   │             │ ├── full_name            │
│ ├── full_name           │             │ ├── timezone             │
│ ├── timezone            │             │ ├── is_active            │
│ ├── is_active           │             │ └── created_at           │
│ ├── created_at          │             │                          │
│ └── updated_at          │             │ ❌ NO password_hash      │
└────────────────────────┘             │ ❌ NO updated_at         │
                                       └─────────────────────────┘
```

If you return the SQLAlchemy model directly in the API response, `password_hash` is included. A Pydantic response schema acts as a **filter** — only the listed fields are returned.

### Schema Naming Convention

| Schema Name | Purpose | Used In |
|------------|---------|---------|
| `UserCreate` | Signup request body | `POST /auth/signup` |
| `UserLogin` | Login request body | `POST /auth/login` |
| `UserUpdate` | Profile update body | `PUT /auth/me` |
| `UserResponse` | API response (safe) | All endpoints that return user data |
| `TokenResponse` | Login/refresh response | `POST /auth/login`, `POST /auth/refresh` |

### What Is `Field()` and `EmailStr`?

**`Field()`** adds validation rules and metadata to a schema field:
```python
# Without Field — no validation, no description:
email: str

# With Field — validated, documented, shows in OpenAPI docs:
email: EmailStr = Field(
    ...,                        # Required (... = no default)
    description="Valid email",  # Shows in Swagger docs
    examples=["a@b.com"],      # Example value in docs
)
```

**`EmailStr`** is a Pydantic type that automatically validates email format:
```python
email: EmailStr

# Valid:   "shreya@example.com" ✅
# Valid:   "user.name+tag@domain.co.uk" ✅
# Invalid: "not-an-email" ❌ → Pydantic raises ValidationError
# Invalid: "@no-local-part.com" ❌ → Pydantic raises ValidationError
```

You need to install the `email-validator` package for `EmailStr` to work (it's in our `requirements.txt`).

### Type This Code: `backend/app/modules/auth/schemas.py`

```python
# ============================================================================
# Auth Module — Pydantic Schemas (Request/Response Models)
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines the EXACT shape of data going in and out of auth endpoints.
#   Pydantic validates EVERY incoming request against these schemas.
#
# WHY SEPARATE SCHEMAS:
#   - UserCreate: what the client sends (includes password)
#   - UserResponse: what the API returns (NEVER includes password_hash)
#   - UserInDB: internal use only (includes password_hash for verification)
#
#   This separation prevents accidentally exposing sensitive data.
#   If you return the SQLAlchemy User model directly, password_hash leaks.
#
# SCHEMA NAMING CONVENTION:
#   {Entity}Create   → POST request body
#   {Entity}Update   → PUT/PATCH request body
#   {Entity}Response → API response (what client sees)
#   {Entity}InDB     → Internal only (includes DB-only fields)
# ============================================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.shared.base_schemas import BaseSchema


class UserCreate(BaseModel):
    """
    Schema for user registration (POST /auth/signup).

    Validates:
    - email: must be a valid email format (Pydantic's EmailStr handles this)
    - password: minimum 8 characters (security best practice)
    - full_name: 1-100 characters
    - timezone: optional, defaults to UTC

    Example request body:
    {
        "email": "shreya@example.com",
        "password": "mySecurePass123",
        "full_name": "Shreya",
        "timezone": "Asia/Kolkata"
    }
    """

    email: EmailStr = Field(
        ...,                               # ... means required (no default)
        description="Valid email address — used for login",
        examples=["shreya@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,                      # Security: minimum 8 characters
        max_length=128,                    # Prevent DoS with huge passwords
        description="Password (min 8 characters)",
        examples=["mySecurePass123"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name",
        examples=["Shreya"],
    )
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="IANA timezone identifier",
        examples=["Asia/Kolkata", "America/New_York", "UTC"],
    )


class UserLogin(BaseModel):
    """
    Schema for login (POST /auth/login).

    Only email and password — nothing else needed.

    Example request body:
    {
        "email": "shreya@example.com",
        "password": "mySecurePass123"
    }
    """

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """
    Schema for profile update (PUT /auth/me).

    All fields optional — only update what's provided.
    Password update could be a separate endpoint for extra security.

    Example request body:
    {
        "full_name": "Shreya V",
        "timezone": "America/New_York"
    }
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)


class UserResponse(BaseSchema):
    """
    Schema for user data in API responses.

    CRITICAL: Does NOT include password_hash.
    This is what the client sees when they call GET /auth/me.

    Example response:
    {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "shreya@example.com",
        "full_name": "Shreya",
        "timezone": "Asia/Kolkata",
        "is_active": true,
        "created_at": "2026-09-26T10:00:00Z"
    }
    """

    id: UUID
    email: str
    full_name: str
    timezone: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """
    Schema for authentication tokens (returned on login and refresh).

    TWO TOKENS:
    - access_token: short-lived (30 min), sent with every API request
    - refresh_token: long-lived (7 days), used ONLY to get a new access_token

    WHY TWO TOKENS:
      If access_token is stolen, attacker has only 30 minutes.
      Refresh token is sent less often (only to /auth/refresh),
      so it's less likely to be intercepted.

    token_type is always "bearer" — tells the frontend to send it as:
      Authorization: Bearer <access_token>

    Example response:
    {
        "access_token": "eyJhbGciOiJIUzI1NiIs...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
        "token_type": "bearer"
    }
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

### Line-by-Line Explanation

**Lines 22-25: Imports**
```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.shared.base_schemas import BaseSchema
```
- `datetime`, `UUID` — Python types used in schema fields
- `BaseModel` — Pydantic's base class. All schemas inherit from this for validation
- `EmailStr` — special Pydantic type that validates email format. Requires `email-validator` package
- `Field(...)` — adds validation constraints (min_length, max_length) and OpenAPI documentation (description, examples)
- `BaseSchema` — our custom base from Part 03 with `from_attributes=True`. Used for response schemas that are created from SQLAlchemy models

**Lines 28-65: `UserCreate` Schema**
```python
class UserCreate(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Valid email address — used for login",
        examples=["shreya@example.com"],
    )
```
- `class UserCreate(BaseModel):` — inherits from `BaseModel`, NOT `BaseSchema`. Why? This schema validates incoming JSON, not converting from a SQLAlchemy model. It doesn't need `from_attributes=True`
- `EmailStr` — automatically validates email format. If the client sends `"not-an-email"`, Pydantic rejects it BEFORE your code runs
- `Field(...)` — the `...` (Ellipsis) means **required**. No default value. If the client doesn't send `email`, Pydantic returns 422
- `description=` — shows in the auto-generated Swagger/OpenAPI docs at `/docs`
- `examples=` — shows example values in Swagger's "Try it out" feature

```python
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )
```
- `min_length=8` — password must be at least 8 characters (NIST recommendation)
- `max_length=128` — prevents DoS attack: without this, someone could send a 10MB password, and bcrypt hashing would take minutes (bcrypt is intentionally slow, and longer input = slower)
- Note: this is `password` (plain text from the client). It becomes `password_hash` in the database after bcrypt hashing

```python
    timezone: str = Field(
        default="UTC",
        max_length=50,
        description="IANA timezone identifier",
    )
```
- `default="UTC"` — optional field. If not provided, defaults to `"UTC"`
- This is the ONLY field with a default — email, password, and full_name are all required

**Lines 67-78: `UserLogin` Schema**
```python
class UserLogin(BaseModel):
    email: EmailStr
    password: str
```
- The simplest schema — just email and password
- No `Field()` constraints because the service layer handles verification (check if email exists, verify password hash)
- `EmailStr` still validates the format — prevents sending nonsense to the database query

**Lines 80-93: `UserUpdate` Schema**
```python
class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
```
- `str | None` — the field can be a string OR `None` (null). This means "optional"
- `default=None` — if not provided, the field is `None`
- The service layer only updates fields that are NOT `None`:
  ```python
  if data.full_name is not None:
      user.full_name = data.full_name
  ```
- Email and password are NOT updatable through this endpoint. Changing email requires verification, and changing password requires the old password. Those would be separate endpoints in a real app

**Lines 95-117: `UserResponse` Schema**
```python
class UserResponse(BaseSchema):
    id: UUID
    email: str
    full_name: str
    timezone: str
    is_active: bool
    created_at: datetime
```
- Inherits from `BaseSchema` (NOT `BaseModel`). Why? Because this schema is created from a SQLAlchemy `User` object: `UserResponse.model_validate(user)`. This requires `from_attributes=True`, which `BaseSchema` provides
- **CRITICAL: No `password_hash` field.** This is THE security feature. Even though the `User` model has `password_hash`, it's not listed here, so Pydantic NEVER includes it in the response
- No `updated_at` either — it's an internal field not useful for the frontend
- `id: UUID` — the user's UUID. The frontend uses this for API calls
- `created_at: datetime` — Pydantic serializes this to ISO 8601 format: `"2026-09-26T10:00:00Z"`

**Lines 119-144: `TokenResponse` Schema**
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```
- `access_token` — the JWT that the frontend sends with every request: `Authorization: Bearer <access_token>`
- `refresh_token` — the JWT used to get new tokens when the access token expires
- `token_type: str = "bearer"` — always `"bearer"`. This is part of the OAuth2 spec — tells the client HOW to send the token (in the `Authorization: Bearer` header). We hardcode it because we only support Bearer tokens
- Inherits from `BaseModel`, not `BaseSchema` — token responses are constructed manually, not from SQLAlchemy objects

---

<a name="connections"></a>
## 5. How These 3 Files Connect

```
┌─────────────────────────────────────────────────────────────────┐
│                        INCOMING REQUEST                          │
│  POST /api/v1/auth/signup                                        │
│  Body: {"email":"shreya@test.com","password":"Pass123!",         │
│         "full_name":"Shreya","timezone":"Asia/Kolkata"}          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  schemas.py → UserCreate                                          │
│  Validates:                                                       │
│  ✅ email is valid format (EmailStr)                              │
│  ✅ password is 8-128 characters (Field min/max)                  │
│  ✅ full_name is 1-100 characters                                 │
│  ✅ timezone defaults to "UTC" if not provided                    │
│  ❌ If invalid → 422 VALIDATION_ERROR (never reaches service)    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ valid data
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  service.py (Part 04c)                                            │
│  1. Check if email exists → raises UserAlreadyExistsError (409)  │
│  2. Hash password with bcrypt                                     │
│  3. Create User via repository                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  models.py → User                                                 │
│  INSERT INTO users (id, email, password_hash, full_name, ...)     │
│  id: auto-generated UUID                                          │
│  password_hash: bcrypt hash of "Pass123!"                         │
│  created_at: current UTC timestamp                                │
│  is_active: True                                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ User object
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  schemas.py → UserResponse.model_validate(user)                   │
│  Filters output:                                                  │
│  ✅ id, email, full_name, timezone, is_active, created_at         │
│  ❌ password_hash (NOT in schema → NOT in response)              │
│  ❌ updated_at (NOT in schema → NOT in response)                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  OUTGOING RESPONSE                                                │
│  HTTP 201 Created                                                 │
│  {"id": "550e8400...", "email": "shreya@test.com",               │
│   "full_name": "Shreya", "timezone": "Asia/Kolkata",             │
│   "is_active": true, "created_at": "2026-09-26T10:00:00Z"}      │
│                                                                   │
│  ✅ No password_hash exposed                                     │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow Summary

| Stage | File | What Happens |
|-------|------|-------------|
| **Request In** | `schemas.py` (UserCreate) | Validates email format, password length, required fields |
| **Business Logic** | `exceptions.py` | Raises specific errors if email exists, credentials wrong, etc. |
| **Database Write** | `models.py` (User) | Stores user with UUID, hashed password, timestamps |
| **Response Out** | `schemas.py` (UserResponse) | Filters sensitive fields, formats for JSON |

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision 1: UUID Primary Key vs Auto-Increment

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Primary Key Strategy                              │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: UUID v4 (random) as primary key                            │
│                                                                     │
│  WHY:                                                               │
│  • Globally unique — safe to expose in URLs and API responses       │
│  • No info leak — competitor can't guess user count                 │
│  • Distributed-ready — multiple servers can generate IDs            │
│    without coordination (no central ID counter)                     │
│  • Merge-safe — importing data between databases never conflicts    │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Auto-increment integer (1, 2, 3, ...)                           │
│     ❌ Leaks info: "/users/5001" tells competitor there are 5001    │
│        users. Sequential IDs are guessable.                         │
│  2. UUID v7 (timestamp-sortable)                                    │
│     ⚠️ Better for indexing (sorted by creation time) but less      │
│        library support in Python. Good future option.              │
│  3. ULID (Universally Unique Lexicographically Sortable ID)         │
│     ⚠️ Similar to UUID v7 — requires third-party library           │
│                                                                     │
│  TRADE-OFFS:                                                        │
│  + Secure, distributed, unguessable                                 │
│  - 16 bytes vs 4 bytes for integer (slightly larger)                │
│  - Random order = fragmented B-tree index (minor at our scale)      │
│                                                                     │
│  AT SCALE: Use UUID v7 for time-sorted inserts (reduces index       │
│  fragmentation). Or ULID. At massive scale, use Snowflake IDs.      │
│                                                                     │
│  INTERVIEW TIP: "We chose UUID v4 for security and distribution.    │
│  Auto-increment IDs leak information and don't work well in         │
│  distributed systems. At larger scale, UUID v7 or Snowflake IDs     │
│  offer better indexing because they're time-sorted."                │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Soft Delete (is_active) vs Hard Delete

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Account Deletion Strategy                         │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Soft delete — set is_active=False, keep data               │
│                                                                     │
│  WHY:                                                               │
│  • Preserves data for analytics ("how many users signed up?")       │
│  • Legal compliance (audit trails, GDPR data retention periods)     │
│  • Account recovery — user can reactivate                           │
│  • Referential integrity — foreign keys to users don't break        │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Hard delete (DELETE FROM users WHERE id = ...)                   │
│     ❌ Data lost forever. Habits, logs, analytics break.           │
│     ❌ Foreign keys to user_id cause cascade deletes or errors     │
│  2. Anonymize (replace name/email with "deleted_user_123")          │
│     ⚠️ Good for GDPR but more complex. Could be added later.      │
│                                                                     │
│  TRADE-OFFS:                                                        │
│  + Data preserved, reversible, analytics intact                     │
│  - Need to filter is_active=True in all queries                     │
│  - Storage grows (deactivated users still take space)               │
│                                                                     │
│  AT SCALE: Add data retention policy: anonymize after 2 years.      │
│  Implement GDPR "right to be forgotten" as anonymization, not       │
│  hard delete.                                                       │
│                                                                     │
│  INTERVIEW TIP: "We use soft delete to preserve referential         │
│  integrity and enable analytics. A user's habits and logs reference  │
│  their user_id — hard delete would cascade or orphan that data."    │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 3: Schema Separation (Create/Response/Update)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Schema Strategy                                   │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Separate schemas for each operation (UserCreate,           │
│          UserResponse, UserUpdate, UserLogin, TokenResponse)        │
│                                                                     │
│  WHY:                                                               │
│  • Security — UserResponse NEVER includes password_hash             │
│  • Validation — UserCreate requires password, UserUpdate doesn't    │
│  • API clarity — each endpoint has an explicit contract             │
│  • OpenAPI docs — auto-generated schemas are accurate               │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. One schema for everything (User for both request and response)  │
│     ❌ password_hash leaks in response. All fields become optional │
│        (is this a create or update?). Validation is impossible.    │
│  2. Use the SQLAlchemy model directly as the response               │
│     ❌ Exposes database internals. No validation on input.         │
│                                                                     │
│  REAL-WORLD: Stripe, GitHub, and every well-designed API uses       │
│  separate request/response schemas. It's industry standard.         │
│                                                                     │
│  INTERVIEW TIP: "Separate schemas enforce a clear API contract.     │
│  The response schema acts as a security filter — only whitelisted   │
│  fields are returned. This prevents accidental exposure of          │
│  sensitive data like password hashes."                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 7. How to Verify Your Work

```bash
# Verify file structure
ls -la backend/app/modules/auth/
# Should show: __init__.py, models.py, exceptions.py, schemas.py

# Verify imports
docker-compose exec backend python -c "
from app.modules.auth.models import User
print(f'Table name: {User.__tablename__}')
print(f'Columns: {[c.name for c in User.__table__.columns]}')
print('✅ models.py OK')
"
# Expected: Table name: users, Columns: ['id', 'email', 'password_hash', ...]

docker-compose exec backend python -c "
from app.modules.auth.exceptions import (
    InvalidCredentialsError, UserAlreadyExistsError,
    TokenExpiredError, TokenInvalidError, AccountDeactivatedError
)
e = InvalidCredentialsError()
assert e.status_code == 401
assert e.error_code == 'INVALID_CREDENTIALS'
print('✅ exceptions.py OK')
"

docker-compose exec backend python -c "
from app.modules.auth.schemas import UserCreate, UserResponse, TokenResponse
# Test validation
try:
    UserCreate(email='not-an-email', password='short', full_name='')
except Exception as e:
    print(f'Validation caught: {e.error_count()} errors')
# Test valid
user = UserCreate(email='a@b.com', password='12345678', full_name='Shreya')
print(f'Valid user: {user.email}')
print('✅ schemas.py OK')
"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: cannot import name 'Base' from 'app.database'` | `database.py` not created yet | Go back to Part 02, create it |
| `ImportError: cannot import name 'BaseSchema'` | `shared/base_schemas.py` missing | Go back to Part 03 |
| `ModuleNotFoundError: No module named 'email_validator'` | Package not installed | `pip install email-validator` |
| `ImportError: cannot import name 'mapped_column'` | Wrong SQLAlchemy version | Ensure SQLAlchemy >= 2.0 in requirements.txt |
| `ModuleNotFoundError: No module named 'app.modules.auth'` | Missing `__init__.py` | Create empty `backend/app/modules/__init__.py` AND `backend/app/modules/auth/__init__.py` |

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **ORM (Object-Relational Mapping)** | Python class = database table. Object = row. Attribute = column. | `models.py` |
| 2 | **`mapped_column()`** | SQLAlchemy 2.0 type-safe column definition | `models.py` |
| 3 | **`Mapped[type]`** | Type annotation that tells IDE/mypy the column's Python type | `models.py` |
| 4 | **`__tablename__`** | Tells SQLAlchemy which table this model maps to | `models.py` |
| 5 | **UUID Primary Key** | Random 128-bit ID — secure, unguessable, distributed-safe | `models.py` |
| 6 | **`unique=True`** | Database constraint: no duplicate values in this column | `models.py` (email) |
| 7 | **`index=True`** | Database index for fast lookups (O(log n) vs O(n)) | `models.py` (email) |
| 8 | **`default` vs `server_default`** | Python-side vs database-side defaults. Use both for safety | `models.py` |
| 9 | **`onupdate`** | SQLAlchemy auto-sets this column when ANY column changes | `models.py` (updated_at) |
| 10 | **`lambda:`** | Anonymous function — runs fresh each time (vs evaluated once) | `models.py` (created_at) |
| 11 | **Soft Delete** | Set `is_active=False` instead of `DELETE`. Preserves data. | `models.py` |
| 12 | **`__repr__`** | Special method for debug string representation of an object | `models.py` |
| 13 | **Exception Inheritance** | Module exceptions inherit from shared ones (specialization) | `exceptions.py` |
| 14 | **No-argument constructors** | Hardcode message + error_code for consistency | `exceptions.py` |
| 15 | **Security through obscurity prevention** | "Invalid credentials" for BOTH wrong email and password | `exceptions.py` |
| 16 | **Schema Separation** | Different schemas for Create, Update, Response — security filter | `schemas.py` |
| 17 | **`EmailStr`** | Pydantic type that auto-validates email format | `schemas.py` |
| 18 | **`Field(...)`** | `...` = required. `Field(min_length=8)` = validation constraint | `schemas.py` |
| 19 | **`str \| None`** | Union type — field can be a string OR None (optional) | `schemas.py` (UserUpdate) |
| 20 | **`BaseModel` vs `BaseSchema`** | BaseModel = raw schema. BaseSchema = from_attributes for ORM | `schemas.py` |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: Why did you use UUID instead of auto-increment integer for primary keys?
**A:** "Three reasons: security, distribution, and information hiding. Auto-increment IDs are sequential and guessable — an attacker can enumerate users by trying `/users/1`, `/users/2`, etc. They also leak your user count: if the latest ID is 5000, you have about 5000 users. UUIDs are random 128-bit values — unguessable, safe to expose in URLs, and globally unique. This also enables future database sharding since any node can generate a UUID without a central counter."

### Q2: What is `mapped_column` and why use SQLAlchemy 2.0 style?
**A:** "SQLAlchemy 2.0 introduced `mapped_column()` with `Mapped[type]` annotations. The old style, `Column(String(255))`, had no type information — your IDE didn't know if `user.email` was a string, integer, or datetime. The new style, `email: Mapped[str] = mapped_column(String(255))`, tells Python's type system that `email` is a `str`. This enables IDE autocomplete, catches type errors at development time, and works with mypy for static type checking."

### Q3: Why separate Pydantic schemas from SQLAlchemy models?
**A:** "The SQLAlchemy model includes ALL database columns, including `password_hash`. If we returned the model directly in API responses, the password hash would be exposed to every client — a critical security vulnerability. Pydantic response schemas act as a whitelist: only fields explicitly listed in `UserResponse` are serialized. This is the same principle as DTOs in Java/Spring Boot. It also allows different validation rules for different operations — `UserCreate` requires a password, but `UserUpdate` doesn't."

### Q4: Explain the `default=lambda: datetime.now(timezone.utc)` pattern.
**A:** "Without `lambda`, Python evaluates `datetime.now(timezone.utc)` once — when the module loads — and every User gets the same creation timestamp (the time the server started). With `lambda:`, it creates a tiny function that Python calls each time a new User is created, so each user gets the correct creation time. This is a common Python gotcha: mutable defaults and function calls in class definitions are evaluated at class creation time, not at instance creation time."

### Q5: What is soft delete and why did you choose it?
**A:** "Soft delete means setting `is_active=False` instead of running `DELETE FROM users`. The data stays in the database. We chose this for three reasons: (1) Referential integrity — the user has habits, logs, and analytics that reference their `user_id`. Hard delete would either cascade-delete everything or leave orphaned records. (2) Analytics — we need historical user counts and activity patterns. (3) Recovery — a user can reactivate. The trade-off is that queries need to filter by `is_active=True`, and storage grows. At scale, we'd add a data retention policy to anonymize old deactivated accounts."

### Q6: Why does `UserUpdate` have all optional fields?
**A:** "The `PUT /auth/me` endpoint supports partial updates — the client sends only the fields they want to change. If `full_name` and `timezone` were required, the frontend would have to send ALL fields even if only updating one. With optional fields (`str | None = None`), the service checks which fields are not None and only updates those. This is a better UX: the frontend can send `{\"timezone\": \"Asia/Kolkata\"}` without knowing the current `full_name`."

### Q7: What does `from_attributes=True` in BaseSchema do?
**A:** "Pydantic v2 schemas normally expect input as a dictionary. SQLAlchemy query results are Python objects with attributes (dot notation: `user.email`), not dictionaries. Setting `from_attributes=True` tells Pydantic: 'You can read fields from object attributes, not just dictionary keys.' Without it, `UserResponse.model_validate(user)` would fail because Pydantic wouldn't know how to access `user.email`. With it, Pydantic automatically reads each field from the object's attributes. This is equivalent to what `@JsonProperty` or ModelMapper does in Spring Boot."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04: Auth Module Overview](./phase4-part04-auth-service-overview.md) |
| ➡️ Next | [Phase 4 Part 04b: Auth Security — JWT & bcrypt](./phase4-part04b-auth-security-jwt.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| **04a** | ✅ **You are here** | Auth Models, Exceptions & Schemas |
| 04b | ⬜ Next | Auth Security — JWT & bcrypt |
| 04c | ⬜ | Auth Repository & Service |
| 04d | ⬜ | Auth Router, Main & Nginx |
| 04e | ⬜ | Auth Alembic Migrations |
| 04f | ⬜ | Auth Connections & Flows |

---

**End of Phase 4 Part 04a: Auth Models, Exceptions & Schemas**

*You've built the data layer — the skeleton of the Auth module. You know what's stored (User model), what can go wrong (5 exceptions), and what goes in/out (5 schemas). Next up: the security utilities that make everything safe — bcrypt password hashing and JWT token creation.*
