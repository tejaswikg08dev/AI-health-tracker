# 🗄️ Phase 4 Part 04c: Auth Repository & Service

> **"The repository knows HOW to talk to the database. The service knows WHAT to do with the data. Keep them separate, and you can test business logic without a database and swap databases without changing business logic."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04c (Auth Business Layer) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04b-auth-security-jwt.md](./phase4-part04b-auth-security-jwt.md) |
| **Next** | [phase4-part04d-auth-controller-main-nginx.md](./phase4-part04d-auth-controller-main-nginx.md) |
| **Files in This Doc** | 2 files (repository.py, service.py) |
| **Endpoints** | 0 (business logic only — router calls these) |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Medium-Hard (repository inheritance, business logic orchestration, Redis blacklist) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [File 1: repository.py — User Data Access Layer](#repository)
3. [File 2: service.py — Auth Business Logic](#service)
4. [How Repository and Service Connect](#connections)
5. [Design Decisions](#design-decisions)
6. [How to Verify Your Work](#verify)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

In Parts 04a and 04b, you built the **data definitions** (model, schemas, exceptions) and the **security utilities** (bcrypt, JWT). Now you build the **brain** of the auth module — the code that orchestrates everything:

- **Repository** — translates business requests into SQL queries ("find user by email")
- **Service** — implements business rules ("check if email exists, hash password, create user")

### Real-World Analogy

Think of a **bank**:
- **Repository** = the vault system. It knows HOW to store and retrieve money. "Put $500 in box #42." "Get contents of box #42." It doesn't know WHY you're accessing the vault.
- **Service** = the bank teller. Knows the RULES. "This customer wants to withdraw $500. Do they have enough? Is their account active? Is this transaction allowed?" The teller tells the vault what to do, but never touches the vault directly.

```
Customer → Bank Teller (service) → Vault System (repository) → Safe (database)
                │                         │
                │ Knows business rules     │ Knows SQL queries
                │ "Is this allowed?"       │ "SELECT, INSERT, UPDATE"
```

### Layer Architecture

```
┌────────────────────────────────────────────────────────┐
│  Router (Part 04d)                                      │
│  Handles HTTP: parse request → call service → respond   │
├────────────────────────────────────────────────────────┤
│  Service (this part)          ←→  Security (Part 04b)   │
│  Business logic: register,        bcrypt, JWT           │
│  login, refresh, logout           hash, verify, sign    │
├────────────────────────────────────────────────────────┤
│  Repository (this part)                                  │
│  SQL queries: get_by_email, email_exists, get_active     │
│  Inherits: BaseRepository[User] (CRUD from Part 03)     │
├────────────────────────────────────────────────────────┤
│  PostgreSQL + Redis                                      │
│  User data + Token blacklist                             │
└────────────────────────────────────────────────────────┘
```

### Build Order

| # | File | Why This Order |
|---|------|---------------|
| 1 | `repository.py` | Service depends on repository for database access |
| 2 | `service.py` | Depends on repository + security + schemas |

---

<a name="repository"></a>
## 2. File 1: `repository.py` — User Data Access Layer

### What Is a Repository in This Module?

The `UserRepository` **inherits** from `BaseRepository[User]` (Part 03). This gives it 5 free CRUD methods:

| Inherited Method | SQL Equivalent |
|-----------------|----------------|
| `create(**kwargs)` | `INSERT INTO users (...)` |
| `get_by_id(id)` | `SELECT * FROM users WHERE id = ?` |
| `get_all(offset, limit)` | `SELECT * FROM users LIMIT ? OFFSET ?` |
| `update(id, **kwargs)` | `UPDATE users SET ... WHERE id = ?` |
| `delete(id)` | `DELETE FROM users WHERE id = ?` |

The `UserRepository` adds **3 custom methods** that only the auth module needs:

| Custom Method | What It Does |
|--------------|-------------|
| `get_by_email(email)` | Find user by email (for login) |
| `get_active_by_id(id)` | Find user by ID + check `is_active=True` |
| `email_exists(email)` | Check if email is taken (for signup) |

### Type This Code: `backend/app/modules/auth/repository.py`

```python
# ============================================================================
# Auth Module — User Repository (Data Access Layer)
# ============================================================================
# WHAT THIS FILE DOES:
#   Handles all database queries related to users.
#   Extends BaseRepository with user-specific queries (get by email, etc.).
#
# WHY A REPOSITORY:
#   Service layer says: "Find the user with this email"
#   Repository translates that to: SELECT * FROM users WHERE email = :email
#
#   The service doesn't know (or care) about SQL.
#   If you switch databases, only the repository changes.
#
# LAYER RESPONSIBILITIES:
#   Router    → handles HTTP (request parsing, response formatting)
#   Service   → handles business logic (validation, rules)
#   Repository → handles data access (SQL queries)
#
#   Each layer has ONE job. This is called "Separation of Concerns."
# ============================================================================

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.shared.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    User-specific database operations.

    Inherits from BaseRepository[User]:
        create(**kwargs) → create a new user
        get_by_id(id) → get user by UUID
        get_all(offset, limit) → list users with pagination
        update(id, **kwargs) → update user fields
        delete(id) → hard delete user
    """

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """
        Find a user by email address.

        Used during:
        - Login (find user, then verify password)
        - Signup (check if email already exists)

        Returns None if no user found — service decides what to do:
        - Login: raise InvalidCredentialsError
        - Signup: proceed with creation

        WHY index on email column:
            Without an index, PostgreSQL scans ALL rows to find the email.
            With an index, it's like a book's index — jumps directly to the page.
            For 1 million users: without index ~100ms, with index ~1ms.
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: UUID) -> User | None:
        """
        Find an active user by ID.

        Different from get_by_id: this also checks is_active=True.
        Used by the auth dependency (get_current_user) to verify
        the token belongs to an active account.

        Deactivated users have valid tokens but can't access the API.
        """
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """
        Check if an email is already registered.

        Used during signup to return a friendly error message
        instead of crashing on the unique constraint violation.

        WHY not just catch the DB error:
            Database errors are vague ("unique constraint violated").
            Checking first gives us a specific error message
            ("A user with this email already exists").
        """
        user = await self.get_by_email(email)
        return user is not None
```

### Line-by-Line Explanation

**Lines 22-26: Imports**
```python
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.models import User
from app.shared.base_repository import BaseRepository
```
- `UUID` — for the `user_id` parameter type
- `select` — SQLAlchemy's query builder: `select(User).where(User.email == email)` → `SELECT * FROM users WHERE email = ?`
- `AsyncSession` — the async database session (from Part 02's `dependencies.py`)
- `User` — the SQLAlchemy model from Part 04a
- `BaseRepository` — the generic CRUD repository from Part 03

**Line 29: `class UserRepository(BaseRepository[User]):`**
```python
class UserRepository(BaseRepository[User]):
```
- `BaseRepository[User]` — inherits from the generic base repository, with `ModelType = User`
- This gives `UserRepository` all 5 CRUD methods FOR FREE: `create`, `get_by_id`, `get_all`, `update`, `delete`
- All these methods work with `User` objects specifically — type-safe
- **Spring Boot equivalent:** `public interface UserRepository extends JpaRepository<User, UUID>`

**Lines 41-43: Constructor**
```python
def __init__(self, session: AsyncSession):
    super().__init__(User, session)
```
- Takes only `session` — the database connection for this request
- `super().__init__(User, session)` — passes the `User` model class and session to `BaseRepository`
- The service creates the repository: `self.repo = UserRepository(session)`

**Lines 45-62: `get_by_email()`**
```python
async def get_by_email(self, email: str) -> User | None:
    result = await self.session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()
```
- `select(User)` → `SELECT * FROM users`
- `.where(User.email == email)` → `WHERE email = 'shreya@test.com'`
- `await` — pauses here while the database executes the query. Other requests are handled meanwhile
- `result.scalar_one_or_none()` — returns:
  - The `User` object if found
  - `None` if no rows match
  - Raises an error if multiple rows match (impossible for email since it has `unique=True`)
- **Why `Mapped` types work here:** `User.email == email` creates a SQLAlchemy comparison expression, not a Python boolean comparison. SQLAlchemy overrides the `==` operator for model columns

**Lines 64-78: `get_active_by_id()`**
```python
async def get_active_by_id(self, user_id: UUID) -> User | None:
    result = await self.session.execute(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
```
- Two conditions in `.where()` — SQLAlchemy AND's them: `WHERE id = ? AND is_active = true`
- `User.is_active.is_(True)` — NOT `User.is_active == True`. Why? In Python, `== True` is ambiguous (is it a comparison or assignment?). `.is_(True)` explicitly creates `IS TRUE` in SQL
- **Use case:** The `get_current_user_id` dependency (in router.py) extracts `user_id` from the JWT. But what if the account was deactivated AFTER the token was issued? This query catches that — deactivated users get `AccountDeactivatedError`

**Lines 80-92: `email_exists()`**
```python
async def email_exists(self, email: str) -> bool:
    user = await self.get_by_email(email)
    return user is not None
```
- Simple wrapper: returns `True` if a user with this email exists, `False` if not
- **Why not catch the database unique constraint error instead?** Two reasons:
  1. Database errors are vague: `"unique constraint \"users_email_key\" violated"`. Our error is clear: `"A user with this email already exists"`
  2. Proactive check vs reactive crash: better to check first and give a friendly error than to attempt the INSERT and handle the crash

---

<a name="service"></a>
## 3. File 2: `service.py` — Auth Business Logic

### What Is a Service Layer? Read This First

The **service layer** is where all business rules live. It orchestrates between:
- **Repository** — for database access
- **Security** — for password hashing and JWT tokens
- **Redis** — for token blacklisting
- **Exceptions** — for error handling

```
Service does NOT know about:
  ❌ HTTP status codes
  ❌ Request/response headers
  ❌ FastAPI or web frameworks
  ❌ How to format JSON

Service DOES know about:
  ✅ Can this user register? (email unique?)
  ✅ Is the password correct? (bcrypt verify)
  ✅ Should we issue tokens? (account active?)
  ✅ How to blacklist a token (Redis TTL)
```

This separation means:
1. **Testable** — unit tests call service methods directly, no HTTP needed
2. **Reusable** — Celery background tasks can call the same service methods
3. **Clean** — route handlers are thin wrappers (5-10 lines each)

### Type This Code: `backend/app/modules/auth/service.py`

```python
# ============================================================================
# Auth Module — Service Layer (Business Logic)
# ============================================================================
# WHAT THIS FILE DOES:
#   Contains all authentication BUSINESS LOGIC.
#   Orchestrates between repository (data), security (crypto), and schemas.
#
# WHY A SERVICE LAYER:
#   Router handles HTTP concerns (parse request, format response).
#   Service handles BUSINESS concerns (can this user register? is the password right?)
#
#   This separation means:
#   1. Business logic is testable WITHOUT running a web server
#   2. Same logic can be reused (e.g., Celery task needs to verify a user)
#   3. Route handlers stay thin and clean
#
# BUSINESS RULES IN THIS SERVICE:
#   - Users cannot register with an existing email
#   - Passwords are hashed before storage
#   - Login returns both access and refresh tokens
#   - Refresh tokens can only be used to get new access tokens
#   - Logged-out tokens are blacklisted in Redis
# ============================================================================

from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.auth.exceptions import (
    AccountDeactivatedError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenResponse, UserCreate, UserUpdate
from app.modules.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AuthService:
    """
    Authentication service — handles registration, login, token management.

    Each method represents a business operation.
    The service is instantiated per-request with the current DB session and Redis client.
    """

    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.repo = UserRepository(session)
        self.session = session
        self.redis = redis_client

    async def register(self, data: UserCreate) -> User:
        """
        Register a new user.

        Business rules:
        1. Email must not already be registered
        2. Password must be hashed before storage
        3. Account is active by default

        Flow:
            Validate email is unique → Hash password → Create user in DB → Return user

        Raises:
            UserAlreadyExistsError: if email is taken
        """
        # Check if email already exists
        if await self.repo.email_exists(data.email):
            raise UserAlreadyExistsError()

        # Hash the password — NEVER store plain text
        hashed = hash_password(data.password)

        # Create user in database
        user = await self.repo.create(
            email=data.email,
            password_hash=hashed,
            full_name=data.full_name,
            timezone=data.timezone,
        )

        # Commit the transaction
        await self.session.commit()

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return JWT tokens.

        Business rules:
        1. User must exist
        2. Password must match
        3. Account must be active
        4. Return both access and refresh tokens

        Flow:
            Find user by email → Verify password → Check active → Generate tokens

        Raises:
            InvalidCredentialsError: if email not found OR password wrong
            AccountDeactivatedError: if account is deactivated

        SECURITY NOTE:
            We use the SAME error for "email not found" and "wrong password".
            This prevents attackers from enumerating valid email addresses.
        """
        # Find user by email
        user = await self.repo.get_by_email(email)

        # User not found — raise generic "invalid credentials"
        if not user:
            raise InvalidCredentialsError()

        # Password doesn't match — same generic error (don't reveal which is wrong)
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # Account deactivated — different error (user knows they're blocked)
        if not user.is_active:
            raise AccountDeactivatedError()

        # Generate JWT tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        logger.info("user_logged_in", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Generate new access + refresh tokens using a valid refresh token.

        WHY REFRESH:
            Access tokens expire every 30 minutes.
            Instead of forcing the user to login again,
            the frontend silently calls /auth/refresh with the refresh token
            to get a new access token. User never notices.

        Flow:
            Decode refresh token → Verify not blacklisted → Verify user active
            → Generate new tokens → Blacklist old refresh token

        Raises:
            TokenExpiredError: if refresh token is expired
            TokenInvalidError: if token is tampered or wrong type
            AccountDeactivatedError: if account was deactivated since last login
        """
        # Decode and validate the refresh token
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = UUID(payload["sub"])

        # Check if the token has been blacklisted (user logged out)
        is_blacklisted = await self.redis.get(f"token_blacklist:{refresh_token[:32]}")
        if is_blacklisted:
            raise InvalidCredentialsError()

        # Verify user still exists and is active
        user = await self.repo.get_active_by_id(user_id)
        if not user:
            raise AccountDeactivatedError()

        # Blacklist the old refresh token (prevent reuse)
        # TTL = remaining lifetime of the old token
        await self._blacklist_token(refresh_token)

        # Generate new tokens
        new_access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)

        logger.info("tokens_refreshed", user_id=str(user.id))

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
        )

    async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
        """
        Logout — blacklist the current tokens.

        WHY BLACKLISTING:
            JWTs are stateless — the server doesn't track active sessions.
            When a user logs out, we can't "invalidate" the token because
            it's self-contained (carries its own expiry).

            Solution: maintain a BLACKLIST in Redis.
            On every request, check if the token is blacklisted.
            Blacklisted tokens = logged out.

        WHY Redis (not database):
            Token checks happen on EVERY request — must be fast (<1ms).
            Redis is perfect: in-memory, sub-millisecond reads.
            TTL auto-deletes entries when tokens expire (self-cleaning).
        """
        await self._blacklist_token(access_token)
        if refresh_token:
            await self._blacklist_token(refresh_token)

        logger.info("user_logged_out")

    async def get_current_user(self, user_id: UUID) -> User:
        """
        Get the currently authenticated user's profile.

        Called by the auth dependency after decoding the JWT token.

        Raises:
            AccountDeactivatedError: if account was deactivated
        """
        user = await self.repo.get_active_by_id(user_id)
        if not user:
            raise AccountDeactivatedError()
        return user

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
        """
        Update the current user's profile.

        Only updates fields that are provided (non-None).
        """
        # Build update dict with only provided fields
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            # Nothing to update — return current user
            user = await self.repo.get_by_id(user_id)
            return user

        user = await self.repo.update(user_id, **update_data)
        await self.session.commit()

        logger.info("profile_updated", user_id=str(user_id), fields=list(update_data.keys()))
        return user

    async def _blacklist_token(self, token: str) -> None:
        """
        Add a token to the Redis blacklist.

        Uses first 32 chars of token as key (unique enough, saves memory).
        TTL is set to the token's remaining lifetime — auto-deletes when expired.
        No point blacklisting a token that's already expired.
        """
        try:
            payload = decode_token(token, expected_type="access")
        except Exception:
            try:
                payload = decode_token(token, expected_type="refresh")
            except Exception:
                return  # Token is already invalid — nothing to blacklist

        # Calculate remaining TTL
        from datetime import datetime, timezone

        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        ttl_seconds = int((exp_datetime - now).total_seconds())

        if ttl_seconds > 0:
            # Store in Redis with auto-expiry
            await self.redis.setex(
                f"token_blacklist:{token[:32]}",
                ttl_seconds,
                "blacklisted",
            )
```

### Line-by-Line Explanation

**Lines 24-27: Imports — External Libraries**
```python
from uuid import UUID
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
```
- `redis.asyncio` — async Redis client. `import redis.asyncio as redis` lets us write `redis.Redis` instead of `redis.asyncio.Redis`
- We use async Redis because token blacklist checks happen on EVERY request — they must be non-blocking

**Lines 29-42: Imports — Our Modules**
```python
from app.modules.auth.exceptions import (
    AccountDeactivatedError, InvalidCredentialsError, UserAlreadyExistsError,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import TokenResponse, UserCreate, UserUpdate
from app.modules.auth.security import (
    create_access_token, create_refresh_token, decode_token,
    hash_password, verify_password,
)
from app.shared.logging import get_logger
```
- Notice how the service imports from EVERY other file in the module — it's the **orchestrator**
- The service is the only place where all pieces come together

**Lines 49-55: Constructor**
```python
class AuthService:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis):
        self.repo = UserRepository(session)
        self.session = session
        self.redis = redis_client
```
- `AuthService` is NOT a singleton — a new instance is created for EVERY request
- `self.repo = UserRepository(session)` — creates the repository with the current request's database session
- `self.session` — stored separately because we need `session.commit()` (repo only does `flush()`)
- `self.redis` — Redis client for token blacklisting
- **Who creates the service?** The router does, via dependency injection (Part 04d):
  ```python
  async def get_auth_service(session=Depends(get_async_session), redis=Depends(get_redis_client)):
      return AuthService(session, redis)
  ```

**Lines 57-82: `register()` Method**
```python
async def register(self, data: UserCreate) -> User:
    if await self.repo.email_exists(data.email):
        raise UserAlreadyExistsError()

    hashed = hash_password(data.password)

    user = await self.repo.create(
        email=data.email,
        password_hash=hashed,
        full_name=data.full_name,
        timezone=data.timezone,
    )

    await self.session.commit()
    logger.info("user_registered", user_id=str(user.id), email=user.email)
    return user
```
- `data: UserCreate` — the validated Pydantic schema from the request body
- **Step 1:** Check if email exists. If yes → raise `UserAlreadyExistsError` (409)
- **Step 2:** Hash the password. `data.password` is plain text → `hashed` is bcrypt hash
- **Step 3:** Create user via repository. Note: `password_hash=hashed`, NOT `password=data.password`. The plain text password NEVER touches the database
- **Step 4:** Commit the transaction. The repo's `create()` only did `flush()` (execute SQL without finalizing). `commit()` makes it permanent
- **Step 5:** Log the event. Structured log: `{"event": "user_registered", "user_id": "abc...", "email": "shreya@test.com"}`
- Returns the `User` object (the router wraps it in `UserResponse`)

**Lines 84-121: `login()` Method**
```python
async def login(self, email: str, password: str) -> TokenResponse:
    user = await self.repo.get_by_email(email)

    if not user:
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    if not user.is_active:
        raise AccountDeactivatedError()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
```
- **Three checks in sequence:**
  1. Does the user exist? If not → `InvalidCredentialsError` (NOT "user not found")
  2. Does the password match? If not → `InvalidCredentialsError` (SAME error — security)
  3. Is the account active? If not → `AccountDeactivatedError` (different — user should know)
- **Security:** Steps 1 and 2 use the SAME exception. An attacker trying emails can't tell if the email exists or the password is wrong
- Token generation happens ONLY after all 3 checks pass
- Returns `TokenResponse` directly (a Pydantic schema with `access_token`, `refresh_token`, `token_type`)

**Lines 123-159: `refresh_tokens()` Method**
```python
async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = UUID(payload["sub"])

    is_blacklisted = await self.redis.get(f"token_blacklist:{refresh_token[:32]}")
    if is_blacklisted:
        raise InvalidCredentialsError()

    user = await self.repo.get_active_by_id(user_id)
    if not user:
        raise AccountDeactivatedError()

    await self._blacklist_token(refresh_token)

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
```
- **Step 1:** Decode the refresh token. `expected_type="refresh"` prevents using an access token here
- **Step 2:** `UUID(payload["sub"])` — convert the string user_id back to a UUID object
- **Step 3:** Check Redis blacklist. `refresh_token[:32]` = first 32 chars as the key (unique enough, saves memory)
- **Step 4:** Verify user is still active (account might have been deactivated since login)
- **Step 5:** Blacklist the old refresh token — it can't be used again (**token rotation**)
- **Step 6:** Generate fresh token pair
- **Why blacklist the old refresh token?** Prevents **replay attacks**. If an attacker steals the refresh token and uses it, they get new tokens. But the legitimate user's refresh is now blacklisted — their next refresh fails, alerting them

**Lines 161-179: `logout()` Method**
```python
async def logout(self, access_token: str, refresh_token: str | None = None) -> None:
    await self._blacklist_token(access_token)
    if refresh_token:
        await self._blacklist_token(refresh_token)
    logger.info("user_logged_out")
```
- Blacklists the access token (and optionally the refresh token)
- After this, any request using the blacklisted token will be rejected
- `refresh_token: str | None = None` — optional. The router might not always have the refresh token

**Lines 195-220: `update_profile()` Method**
```python
async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        user = await self.repo.get_by_id(user_id)
        return user

    user = await self.repo.update(user_id, **update_data)
    await self.session.commit()
    return user
```
- `data.model_dump(exclude_unset=True)` — **key Pydantic v2 feature**. Converts the schema to a dict, but ONLY includes fields that were explicitly set by the client. If the client sends `{"full_name": "Shreya V"}`, the dict is `{"full_name": "Shreya V"}` — `timezone` is NOT included (it wasn't sent)
- If `update_data` is empty (client sent `{}`), just return the current user without hitting the database with an empty UPDATE
- `**update_data` — unpacks the dict: `repo.update(user_id, full_name="Shreya V")`

**Lines 222-247: `_blacklist_token()` Private Method**
```python
async def _blacklist_token(self, token: str) -> None:
    try:
        payload = decode_token(token, expected_type="access")
    except Exception:
        try:
            payload = decode_token(token, expected_type="refresh")
        except Exception:
            return

    exp_timestamp = payload.get("exp", 0)
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    ttl_seconds = int((exp_datetime - now).total_seconds())

    if ttl_seconds > 0:
        await self.redis.setex(
            f"token_blacklist:{token[:32]}",
            ttl_seconds,
            "blacklisted",
        )
```
- `_blacklist_token` — the `_` prefix means "private" (convention, not enforced). Only called within this class
- **Try access first, then refresh** — we don't know the token type, so we try both
- If both fail, the token is already invalid — no need to blacklist
- **TTL calculation:** We only blacklist for the remaining lifetime. If the token expires in 10 minutes, the Redis key expires in 10 minutes too. No point storing blacklist entries forever — expired tokens are already invalid
- `self.redis.setex(key, ttl, value)` — Redis `SETEX` command: set a key with an expiry. After `ttl_seconds`, Redis automatically deletes the key (self-cleaning!)
- `token[:32]` — first 32 characters as the key. Full JWTs are ~200 chars — using the first 32 saves ~80% memory in Redis while still being unique

---

<a name="connections"></a>
## 4. How Repository and Service Connect

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SIGNUP FLOW                                      │
│                                                                      │
│  Router: service.register(data)                                      │
│     │                                                                │
│     ▼                                                                │
│  Service.register():                                                 │
│     │                                                                │
│     ├─ repo.email_exists("shreya@test.com")                          │
│     │     └─ SQL: SELECT * FROM users WHERE email = 'shreya@test.com'│
│     │     └─ Returns: False (email is available)                     │
│     │                                                                │
│     ├─ hash_password("Pass123!")                                     │
│     │     └─ Returns: "$2b$12$..." (bcrypt hash)                     │
│     │                                                                │
│     ├─ repo.create(email=..., password_hash=..., ...)                │
│     │     └─ SQL: INSERT INTO users (...) VALUES (...)               │
│     │     └─ Returns: User(id=abc-123)                               │
│     │                                                                │
│     ├─ session.commit()  (finalize transaction)                      │
│     │                                                                │
│     └─ return User                                                   │
│                                                                      │
│  Router: UserResponse.model_validate(user) → JSON to client         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     LOGIN FLOW                                       │
│                                                                      │
│  Service.login("shreya@test.com", "Pass123!"):                       │
│     │                                                                │
│     ├─ repo.get_by_email("shreya@test.com")                          │
│     │     └─ Returns: User(id=abc, password_hash="$2b$12$...")       │
│     │                                                                │
│     ├─ verify_password("Pass123!", "$2b$12$...")                     │
│     │     └─ Returns: True ✅                                        │
│     │                                                                │
│     ├─ user.is_active → True ✅                                      │
│     │                                                                │
│     ├─ create_access_token(user.id) → "eyJ..." (30 min)             │
│     ├─ create_refresh_token(user.id) → "eyJ..." (7 days)            │
│     │                                                                │
│     └─ return TokenResponse(access_token=..., refresh_token=...)     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     LOGOUT FLOW                                      │
│                                                                      │
│  Service.logout("eyJaccess...", "eyJrefresh..."):                    │
│     │                                                                │
│     ├─ _blacklist_token("eyJaccess...")                               │
│     │     ├─ decode_token() → payload with exp=1727360800            │
│     │     ├─ TTL = exp - now = 1200 seconds (20 min remaining)       │
│     │     └─ redis.setex("token_blacklist:eyJhbGciOiJIUzI...",       │
│     │                    1200, "blacklisted")                        │
│     │                                                                │
│     └─ _blacklist_token("eyJrefresh...")                              │
│           └─ Same process, longer TTL (days remaining)               │
│                                                                      │
│  Next request with blacklisted token:                                │
│     get_current_user_id():                                           │
│       redis.get("token_blacklist:eyJhbGci...") → "blacklisted" ❌   │
│       → TokenInvalidError → 401                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="design-decisions"></a>
## 5. Design Decisions

### Design Decision 1: Service Per Request vs Singleton

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Service Lifecycle                                 │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: New service instance per request                           │
│                                                                     │
│  WHY:                                                               │
│  • Each request gets its own database session (transaction scope)   │
│  • No shared mutable state between requests (thread-safe)           │
│  • Service holds the session → clean transaction boundaries         │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Singleton service (one instance for all requests)               │
│     ❌ Can't hold per-request session (shared state = race         │
│        conditions). Would need to pass session as parameter to      │
│        every method — messy.                                        │
│  2. Class methods (no instance at all)                              │
│     ❌ Can't hold repository reference. Every method would need    │
│        session and redis as parameters.                             │
│                                                                     │
│  HOW IT WORKS:                                                      │
│  FastAPI's Depends() creates AuthService(session, redis) per        │
│  request. After the request, the session is closed automatically.   │
│                                                                     │
│  INTERVIEW TIP: "Services are instantiated per-request with the    │
│  current database session. This gives each request its own          │
│  transaction scope and avoids shared mutable state."                │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Token Blacklist in Redis vs Database

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Token Blacklist Storage                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Redis with TTL auto-expiry                                 │
│                                                                     │
│  WHY:                                                               │
│  • Checked on EVERY request — must be < 1ms (Redis: ~0.1ms)        │
│  • TTL auto-cleanup — no manual deletion of expired blacklist       │
│    entries. Redis deletes them automatically.                       │
│  • Simple key-value: key = token prefix, value = "blacklisted"     │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. PostgreSQL table (blacklisted_tokens)                           │
│     ❌ Database query on every request = 5-20ms overhead            │
│     ❌ Need manual cleanup job for expired entries                  │
│  2. In-memory set (Python set)                                      │
│     ❌ Lost on server restart. Doesn't work with multiple servers. │
│  3. No blacklist (just let tokens expire naturally)                 │
│     ❌ Logged-out tokens work until expiry — security hole         │
│                                                                     │
│  MEMORY ESTIMATE:                                                   │
│  Each blacklist entry: ~100 bytes (key + value + metadata)          │
│  1000 active users logging out: ~100KB. Redis handles millions.     │
│                                                                     │
│  INTERVIEW TIP: "We use Redis for the token blacklist because it's │
│  checked on every request. Redis delivers sub-millisecond reads,    │
│  and its built-in TTL auto-cleans expired entries."                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 6. How to Verify Your Work

```bash
# Verify repository imports
docker-compose exec backend python -c "
from app.modules.auth.repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession
print('✅ repository.py imports OK')
# Verify it has BaseRepository methods
print(f'Inherited methods: {[m for m in dir(UserRepository) if not m.startswith(\"_\")]}')
"

# Verify service imports
docker-compose exec backend python -c "
from app.modules.auth.service import AuthService
print('✅ service.py imports OK')
print(f'Service methods: {[m for m in dir(AuthService) if not m.startswith(\"_\")]}')
"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ImportError: cannot import name 'UserRepository'` | File not created or wrong path | Verify `backend/app/modules/auth/repository.py` exists |
| `ImportError: cannot import name 'BaseRepository'` | Part 03 not completed | Go back to Part 03, create `shared/base_repository.py` |
| `ModuleNotFoundError: No module named 'redis'` | redis not installed | `pip install redis` (already in requirements.txt) |
| `AttributeError: 'User' has no attribute 'is_active'` | models.py missing `is_active` column | Go back to Part 04a, check `models.py` |

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Repository Inheritance** | `UserRepository(BaseRepository[User])` — gets free CRUD | `repository.py` |
| 2 | **Custom Queries** | Module-specific methods on top of inherited CRUD | `get_by_email`, `get_active_by_id` |
| 3 | **`.is_(True)`** | SQLAlchemy way to write `IS TRUE` (not `== True`) | `get_active_by_id` |
| 4 | **`scalar_one_or_none()`** | Returns one result or None — perfect for lookups | Both repo methods |
| 5 | **Service Layer** | Business logic orchestrator — calls repo, security, Redis | `service.py` |
| 6 | **Per-Request Service** | New instance per request with own session and Redis client | Constructor pattern |
| 7 | **`session.commit()`** | Finalizes the transaction (makes changes permanent) | `register()`, `update_profile()` |
| 8 | **Token Blacklisting** | Store logged-out token prefixes in Redis with TTL | `_blacklist_token()` |
| 9 | **`redis.setex(key, ttl, value)`** | Redis command: set key + value with auto-expiry | Blacklist implementation |
| 10 | **`model_dump(exclude_unset=True)`** | Pydantic v2: convert to dict with only explicitly set fields | `update_profile()` |
| 11 | **Token Rotation** | On refresh, blacklist old tokens and issue new ones | `refresh_tokens()` |
| 12 | **Security Through Obscurity Prevention** | Same error for "no user" and "wrong password" | `login()` |
| 13 | **Structured Logging** | `logger.info("event", key=value)` — machine-parseable logs | All service methods |
| 14 | **Private Methods (`_prefix`)** | Convention: method meant for internal use only | `_blacklist_token()` |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: Why do you have both a repository and a service layer?
**A:** "Separation of concerns. The repository handles data access — SQL queries, database operations. The service handles business logic — validation rules, password hashing, token generation. This separation means business logic is testable without a database (mock the repository), and you can change the database without touching business logic. In our auth module, the service orchestrates between the repository (data), security module (crypto), and Redis (blacklist)."

### Q2: Why do you commit in the service, not the repository?
**A:** "The repository does `flush()` which executes the SQL but keeps the transaction open. The service does `commit()` which finalizes the transaction. This allows multiple repository operations in a single transaction. For example, if `register()` needed to create a user AND a welcome notification, both operations would be in one transaction — if either fails, both roll back. If the repository committed, each operation would be a separate transaction and we couldn't guarantee atomicity."

### Q3: How does token blacklisting work? Why Redis?
**A:** "When a user logs out, we store the first 32 characters of their token as a key in Redis with value 'blacklisted' and a TTL matching the token's remaining lifetime. On every authenticated request, we check Redis for this key — if it exists, the token is rejected. We use Redis because blacklist checks happen on every request and must be sub-millisecond. PostgreSQL would add 5-20ms per request. Redis's built-in TTL also auto-deletes expired entries — no cleanup job needed."

### Q4: What is token rotation and why do you do it on refresh?
**A:** "When a user refreshes their tokens, we blacklist the old refresh token and issue a completely new pair. This limits the window of a stolen refresh token — once the legitimate user refreshes, the stolen token is blacklisted. Without rotation, a stolen refresh token could be used indefinitely for 7 days."

### Q5: Explain `model_dump(exclude_unset=True)` and why you use it for updates.
**A:** "Pydantic v2's `model_dump()` converts a schema to a dictionary. The `exclude_unset=True` flag only includes fields that the client explicitly sent. If the client sends `{\"full_name\": \"Shreya V\"}`, the result is `{\"full_name\": \"Shreya V\"}` — `timezone` is excluded because it wasn't in the request. Without this, we'd overwrite `timezone` with `None` on every profile update. This enables true partial updates."

### Q6: Why use `InvalidCredentialsError` for both "user not found" and "wrong password"?
**A:** "Security best practice to prevent email enumeration. If we returned 'user not found' for a non-existent email and 'wrong password' for a wrong password, an attacker could systematically try emails to discover which ones are registered. With a generic 'invalid credentials' for both cases, the attacker can't distinguish between a non-existent email and a wrong password."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04b: Auth Security — JWT & bcrypt](./phase4-part04b-auth-security-jwt.md) |
| ➡️ Next | [Phase 4 Part 04d: Auth Router, Main & Nginx](./phase4-part04d-auth-controller-main-nginx.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 04a | ✅ Done | Auth Models, Exceptions & Schemas |
| 04b | ✅ Done | Auth Security — JWT & bcrypt |
| **04c** | ✅ **You are here** | Auth Repository & Service |
| 04d | ⬜ Next | Auth Router, Main & Nginx |
| 04e | ⬜ | Auth Alembic Migrations |
| 04f | ⬜ | Auth Connections & Flows |

---

**End of Phase 4 Part 04c: Auth Repository & Service**

*You've built the brain of the auth module. The repository talks to PostgreSQL, the service enforces business rules, and Redis handles token blacklisting. Next: the HTTP layer — router endpoints, main app wiring, and Nginx reverse proxy.*
