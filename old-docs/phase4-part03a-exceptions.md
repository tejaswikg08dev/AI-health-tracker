# Phase 4 — Part 03a: Exception Hierarchy (shared/exceptions.py)

> **"When something goes wrong, your app should EXPLAIN what happened — not crash with a cryptic error."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 03a |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Shared Utilities |
| **File** | `backend/app/shared/exceptions.py` |
| **Depends On** | Part 02a (requirements.txt — Python is installed) |
| **Next** | [Part 03b — base_schemas.py](./phase4-part03b-base-schemas.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~15 minutes |
| **Lines of Code** | 113 lines |

---

## 📖 What is an Exception? Read This First (Complete Beginner)

### If You've Never Seen an Exception Before

When your code hits a problem, Python **stops** and shows an error. This is called an **exception**.

```python
# This code has a problem:
number = int("hello")

# Python stops and shows:
# ValueError: invalid literal for int() with base 10: 'hello'
```

`ValueError` is a **built-in** Python exception. Python has many built-in ones:
- `ValueError` — wrong value ("hello" can't be a number)
- `TypeError` — wrong type (adding string + number)
- `FileNotFoundError` — file doesn't exist
- `KeyError` — dictionary key doesn't exist

### Why Create CUSTOM Exceptions?

Built-in exceptions don't know about our app. We need exceptions like:
- `HabitNotFoundError` — the habit with this ID doesn't exist
- `DuplicateLogError` — you already logged this habit today
- `TokenExpiredError` — your login session expired

Each should automatically become a proper HTTP error response:
```json
{
    "error_code": "HABIT_NOT_FOUND",
    "message": "Habit not found",
    "detail": null
}
```

### What is an Exception Hierarchy?

A hierarchy means exceptions are organized like a family tree. Children inherit from parents:

```
Exception (Python built-in — the grandparent of ALL exceptions)
  └── BaseAppError (OUR root — has message, status_code, error_code)
        ├── NotFoundError (status_code = 404)
        │     └── HabitNotFoundError (error_code = "HABIT_NOT_FOUND")
        ├── ConflictError (status_code = 409)
        │     └── DuplicateLogError (error_code = "DUPLICATE_LOG")
        └── UnauthorizedError (status_code = 401)
              └── TokenExpiredError (error_code = "TOKEN_EXPIRED")
```

**Why a hierarchy?** The error handler can catch `BaseAppError` — and it automatically catches ALL our custom errors. One handler, all errors.

### Real-World Analogy

A hospital has **alert codes**:
- **Code Blue** — cardiac arrest (critical, call the team)
- **Code Red** — fire (evacuate the area)
- **Code Yellow** — missing patient (search the building)

Each code has:
1. A **name** (Code Blue) — like our `error_code`
2. A **response protocol** (what to do) — like our `status_code`
3. A **description** (what happened) — like our `message`

The hospital doesn't write the protocol at each nurse's station. It's defined ONCE, and nurses just call the right code. Same with our exceptions — defined once, raised everywhere.

---

## 🏗️ Architecture: Where This File Fits

```
THIS FILE: shared/exceptions.py
  │
  │ Defines 6 exception classes (1 base + 5 specific)
  │
  │ USED BY (who inherits from these):
  ├── modules/auth/exceptions.py
  │     class InvalidCredentialsError(UnauthorizedError)
  │     class UserAlreadyExistsError(ConflictError)
  │     class TokenExpiredError(UnauthorizedError)
  │
  ├── modules/habits/exceptions.py
  │     class HabitNotFoundError(NotFoundError)
  │     class HabitLimitExceededError(ValidationError)
  │
  ├── modules/logs/exceptions.py
  │     class DuplicateLogError(ConflictError)
  │     class FutureDateError(ValidationError)
  │
  │ CAUGHT BY:
  └── middleware/error_handler.py
        catches BaseAppError → returns JSON with status_code
```

---

## 💻 Source Code — Type This EXACTLY

> 📁 **File:** `backend/app/shared/exceptions.py`
> 📏 **Lines:** 113
> ⏱️ **Time to type:** ~15 minutes
>
> **Before typing:** Make sure you have the folder structure:
> ```
> backend/
> └── app/
>     └── shared/
>         ├── __init__.py    ← create this empty file first!
>         └── exceptions.py  ← you will type THIS file
> ```
> Create `__init__.py` first (empty file — just tells Python this is a package):
> ```bash
> # Create the folder and init file:
> mkdir -p backend/app/shared
> touch backend/app/shared/__init__.py
> ```

Now type this file. I'll explain EVERY line below.

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

---

## 📝 Line-by-Line Explanation

### Lines 1-26: The Comment Block

```python
# ============================================================================
# Health Tracker — Base Exception Hierarchy
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines custom exception classes that all modules can use.
# ...
```

**What:** This is a multi-line comment. Everything after `#` on a line is ignored by Python.

**Why:** When another developer (or future you) opens this file, they immediately know:
1. WHAT the file does ("Defines custom exception classes")
2. WHY it exists ("Instead of returning errors manually everywhere...")
3. HOW the hierarchy looks (ASCII tree diagram)

**Teaching moment — Comments in Python:**
```python
# This is a single-line comment

"""
This is a multi-line string.
When placed at the top of a class or function,
it becomes a "docstring" — documentation that Python can read.
"""
```

### Lines 28-49: BaseAppError — The Root Class

```python
class BaseAppError(Exception):
```

**What this line does — WORD BY WORD:**
- `class` — keyword that tells Python "I'm defining a new type of thing"
- `BaseAppError` — the NAME of our new class (we chose this name)
- `(Exception)` — our class **inherits from** Python's built-in `Exception` class
- `:` — start of the class body (everything indented after this belongs to the class)

**What is `class`?**

A class is a **blueprint** for creating objects. Like a cookie cutter — the class is the cutter, each object is a cookie.

```python
class Dog:          # Blueprint: all dogs have a name and can bark
    def __init__(self, name):
        self.name = name

    def bark(self):
        return f"{self.name} says Woof!"

rex = Dog("Rex")    # Create an object from the blueprint
print(rex.bark())   # "Rex says Woof!"
```

**What is `(Exception)`?**

This is **inheritance**. Our class INHERITS everything from Python's `Exception` class. Like a child inheriting traits from a parent — `BaseAppError` is an `Exception` PLUS our extra stuff (message, status_code, error_code).

Without inheritance, Python wouldn't know how to handle `raise BaseAppError(...)`.

```python
class BaseAppError(Exception):    # ← Inherits from Exception
    """
    Base exception for all application errors.
    """

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
    ):
```

**What is `__init__`?**

`__init__` (called "dunder init" — double underscore init) is the **constructor**. It runs automatically when you create an object:

```python
# When you write:
error = BaseAppError("Something broke", 500, "INTERNAL_ERROR")

# Python automatically calls:
BaseAppError.__init__(error, "Something broke", 500, "INTERNAL_ERROR")
```

**What is `self`?**

`self` is the object being created. When you write `self.message = message`, you're storing the message INSIDE the object so you can access it later:

```python
error = BaseAppError("Something broke")
print(error.message)      # "Something broke" — stored by self.message = message
print(error.status_code)  # 500 — stored by self.status_code = status_code
print(error.error_code)   # "INTERNAL_ERROR" — stored by self.error_code = error_code
```

**What is `: str = "An error occurred"`?**

This is a **type hint** with a **default value**:
- `: str` — tells Python (and your IDE) this should be a string
- `= "An error occurred"` — if you don't provide a value, use this default

```python
# All three are valid:
BaseAppError("Custom message", 404, "NOT_FOUND")  # All three provided
BaseAppError("Custom message")                      # status_code=500, error_code="INTERNAL_ERROR" (defaults)
BaseAppError()                                       # All defaults: "An error occurred", 500, "INTERNAL_ERROR"
```

### The Constructor Body

```python
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)
```

- **`self.message = message`** — Store the message inside the object. Like writing someone's name on their locker — now it's THEIR message, accessible anytime with `error.message`.

- **`self.status_code = status_code`** — Store the HTTP status code. The error handler will read this to decide which HTTP status to return.

- **`self.error_code = error_code`** — Store the machine-readable code. The frontend reads this (not the message) to decide what to display.

- **`super().__init__(self.message)`** — Call the PARENT class (`Exception`) constructor with the message. This is REQUIRED — without it, Python's exception handling (`try/except`, `raise`) won't work properly.

**What is `super()`?**

`super()` means "my parent class." Since `BaseAppError` inherits from `Exception`:
```python
super().__init__(self.message)
# is the same as:
Exception.__init__(self, self.message)
```

This tells Python's Exception system: "Yes, I'm a real exception. Here's my error message."

### Lines 52-63: NotFoundError

```python
class NotFoundError(BaseAppError):
    """
    Resource not found — HTTP 404.
    """

    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message=message, status_code=404, error_code=error_code)
```

**What this does:**
- `class NotFoundError(BaseAppError)` — NotFoundError is a CHILD of BaseAppError
- The `__init__` HARDCODES `status_code=404` — you never need to specify it
- It calls `super().__init__(...)` which calls BaseAppError's constructor

**Why different from BaseAppError?**
- BaseAppError: you MUST specify everything (or use defaults)
- NotFoundError: `status_code=404` is automatic. You just say WHAT wasn't found.

```python
# Using NotFoundError (clean, specific):
raise NotFoundError("Habit not found", error_code="HABIT_NOT_FOUND")
# Automatically: status_code=404, message="Habit not found", error_code="HABIT_NOT_FOUND"

# Using BaseAppError (verbose, generic):
raise BaseAppError("Habit not found", status_code=404, error_code="HABIT_NOT_FOUND")
# Works but you have to remember 404 every time
```

### Lines 66-113: The Other 4 Error Classes

The pattern is IDENTICAL for `ConflictError`, `ValidationError`, `UnauthorizedError`, `ForbiddenError`:

```python
class ConflictError(BaseAppError):
    # status_code hardcoded to 409

class ValidationError(BaseAppError):
    # status_code hardcoded to 422

class UnauthorizedError(BaseAppError):
    # status_code hardcoded to 401

class ForbiddenError(BaseAppError):
    # status_code hardcoded to 403
```

**When to use which:**

| Exception | HTTP Code | When to Raise | Example |
|-----------|-----------|--------------|---------|
| `NotFoundError` | 404 | Thing doesn't exist | "Habit with this ID doesn't exist" |
| `ConflictError` | 409 | Duplicate / clash | "This email is already registered" |
| `ValidationError` | 422 | Business rule violated | "Can't log for a future date" |
| `UnauthorizedError` | 401 | Not logged in / bad token | "Token expired, please login again" |
| `ForbiddenError` | 403 | Logged in but not allowed | "You can't access another user's habits" |

**Key difference — 401 vs 403:**
- **401 Unauthorized:** "I don't know who you are. Please show ID." (no token, expired token)
- **403 Forbidden:** "I know who you are. You're not allowed here." (wrong user, wrong role)

---

## 🔌 How This Connects

```
 YOU RAISE:                 MIDDLEWARE CATCHES:              USER SEES:
 ──────────                 ──────────────────              ─────────
 raise NotFoundError(       error_handler catches           HTTP 404
   "Habit not found",       BaseAppError → reads            {
   error_code="..."         .status_code (404)                "error_code": "HABIT_NOT_FOUND",
 )                          .message ("Habit not found")      "message": "Habit not found",
                            .error_code ("HABIT_NOT_FOUND")   "detail": null
                            → JSONResponse(404, {...})      }
```

**Where is this raising and catching?**

1. **RAISING** (in service code):
```python
# backend/app/modules/habits/service.py (Part 05e — Week 2)
async def get_habit(self, user_id, habit_id):
    habit = await self.repo.get_user_habit(user_id, habit_id)
    if not habit:
        raise HabitNotFoundError()  # ← raises NotFoundError subclass
    return habit
```

2. **CATCHING** (in middleware):
```python
# backend/app/middleware/error_handler.py (Part 03f — we'll type this soon)
@app.exception_handler(BaseAppError)
async def app_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,     # 404
        content={
            "error_code": exc.error_code, # "HABIT_NOT_FOUND"
            "message": exc.message,       # "Habit not found"
            "detail": None,
        },
    )
```

3. **USER SEES** (in browser):
```json
HTTP/1.1 404 Not Found
Content-Type: application/json

{
    "error_code": "HABIT_NOT_FOUND",
    "message": "Habit not found",
    "detail": null
}
```

---

## ✅ What You Learned

| # | Concept | What It Means (One Sentence) |
|---|---------|------------------------------|
| 1 | `class` | A blueprint for creating objects (like a cookie cutter) |
| 2 | `(Exception)` | Inheritance — our class gets everything Exception has, plus our extras |
| 3 | `__init__` | Constructor — runs automatically when creating an object |
| 4 | `self` | The object being created — stores data inside it (`self.message = message`) |
| 5 | `super().__init__()` | Calls the parent class constructor (required for exceptions to work) |
| 6 | Type hints (`: str`) | Tells Python and IDE what type a parameter should be |
| 7 | Default values (`= "error"`) | Used when the caller doesn't provide a value |
| 8 | Exception hierarchy | Base class + children. Catching the parent catches ALL children |
| 9 | 401 vs 403 | 401 = "who are you?" (unauthenticated). 403 = "you can't do this" (unauthorized) |

---

## ❌ Common Errors & Fixes

| What You See | Why It Happens | How to Fix |
|-------------|---------------|------------|
| `NameError: name 'BaseAppError' is not defined` | You're importing from the wrong location | Use: `from app.shared.exceptions import BaseAppError` |
| `TypeError: BaseAppError() takes 0 positional arguments` | You forgot `self` in `__init__` | First parameter of `__init__` must be `self` |
| `AttributeError: 'NotFoundError' has no attribute 'status_code'` | Forgot `super().__init__(...)` call | Add `super().__init__(message=..., status_code=...)` in the child class |
| `ModuleNotFoundError: No module named 'app.shared'` | Missing `__init__.py` in the `shared/` folder | Create empty file: `touch backend/app/shared/__init__.py` |

---

## 🧪 Try It Yourself

After typing the file, test it in the Python REPL:

```bash
cd backend
source venv/bin/activate     # Mac/Linux
# venv\Scripts\activate      # Windows

python3
```

Then in the Python prompt:

```python
>>> from app.shared.exceptions import NotFoundError, ConflictError, UnauthorizedError

# Test 1: Create a NotFoundError
>>> error = NotFoundError("Habit not found", error_code="HABIT_NOT_FOUND")
>>> print(error.message)
Habit not found
>>> print(error.status_code)
404
>>> print(error.error_code)
HABIT_NOT_FOUND

# Test 2: Verify inheritance
>>> from app.shared.exceptions import BaseAppError
>>> isinstance(error, BaseAppError)
True
>>> isinstance(error, Exception)
True

# Test 3: Use defaults
>>> error2 = NotFoundError()
>>> print(error2.message)
Resource not found
>>> print(error2.status_code)
404

# Test 4: Raise and catch
>>> try:
...     raise NotFoundError("User not found")
... except BaseAppError as e:
...     print(f"Caught! {e.status_code}: {e.message}")
...
Caught! 404: User not found

>>> exit()
```

If ALL 4 tests work → this file is correct. Move to the next doc! ✅

---

## 🎤 Interview Q&A

### Q1: "What is an exception in Python?"

> "An exception is Python's way of handling errors. When something goes wrong, Python raises an exception — the normal code flow stops and Python looks for an `except` block that can handle it. Built-in exceptions handle generic problems: `ValueError`, `TypeError`, `FileNotFoundError`. For application-specific problems like 'habit not found' or 'token expired', I create custom exception classes that inherit from a base `Exception` class and carry additional information: the HTTP status code and a machine-readable error code."

### Q2: "How do you handle errors consistently across 38 API endpoints?"

> "A five-level exception hierarchy. `BaseAppError` is the root with `message`, `status_code`, and `error_code`. Five children map to HTTP codes: `NotFoundError` (404), `ConflictError` (409), `ValidationError` (422), `UnauthorizedError` (401), `ForbiddenError` (403). Each module creates even more specific errors — `HabitNotFoundError` extends `NotFoundError` with error_code `HABIT_NOT_FOUND`. A global error handler catches `BaseAppError` and returns consistent JSON: `{error_code, message, detail}`. The service layer raises exceptions; it doesn't know about HTTP. The middleware translates exceptions to HTTP responses."

### Q3: "What is inheritance in Python?"

> "A way for one class to get all the features of another class, plus add its own. In my project, `NotFoundError` inherits from `BaseAppError`, which inherits from Python's `Exception`. So `NotFoundError` IS a `BaseAppError` AND an `Exception`. I can catch `BaseAppError` in one handler and it automatically catches `NotFoundError`, `ConflictError`, and all other children. This is polymorphism — treating different types uniformly through their shared parent."

### Q4: "What's the difference between 401 and 403?"

> "401 Unauthorized means 'I don't know who you are — provide valid credentials.' The user's token is missing, expired, or invalid. 403 Forbidden means 'I know who you are, but you're not allowed to do this.' The user is logged in but trying to access another user's data. In my app, trying to access `/habits` without a token → 401. Trying to access another user's habit by ID → 403."

---

## 📚 Navigation

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03 Overview](./phase4-part03-shared-and-middleware-overview.md) | | [Part 03b — base_schemas.py](./phase4-part03b-base-schemas.md) |
