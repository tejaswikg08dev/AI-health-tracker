# 🌐 Phase 4 Part 04d: Auth Router, Main App & Nginx

> **"The router is the front door — it receives HTTP requests, validates them, calls the service, and formats the response. The main.py wires everything together. Nginx sits in front of it all, blocking abuse before it reaches your code."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04d (Auth HTTP Layer + App Wiring + Reverse Proxy) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04c-auth-repository-service.md](./phase4-part04c-auth-repository-service.md) |
| **Next** | [phase4-part04e-auth-alembic-migrations.md](./phase4-part04e-auth-alembic-migrations.md) |
| **Files in This Doc** | 3 files (router.py, main.py, nginx/default.conf) |
| **Endpoints** | 6 auth endpoints go live in this part |
| **Time to Type** | ~60 minutes |
| **Difficulty** | Hard (dependency injection, lifespan, middleware order, Nginx config) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [File 1: router.py — Auth API Endpoints](#router)
3. [File 2: main.py — FastAPI Application Entry Point](#main)
4. [File 3: nginx/default.conf — Reverse Proxy](#nginx)
5. [How All Three Files Connect](#connections)
6. [Design Decisions](#design-decisions)
7. [How to Verify Your Work](#verify)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

This is where everything comes together. The router defines HTTP endpoints, main.py wires the app, and Nginx sits in front.

### Real-World Analogy

Think of a **restaurant**:
- **router.py** = the waiter. Takes your order (HTTP request), passes it to the kitchen (service), brings back your food (HTTP response). The waiter doesn't cook — they translate between customer language and kitchen language.
- **main.py** = the restaurant manager. Opens the restaurant (startup), closes it (shutdown), hires the staff (registers middleware and routers), sets the rules (CORS, error handling).
- **nginx/default.conf** = the bouncer and hostess at the door. Checks IDs (rate limiting), directs people (reverse proxy), compresses bags (gzip), and handles overflow ("sorry, we're full" → 429).

### Request Flow Through All Three

```
Browser → Nginx (port 80)
           │
           ├─ /api/* → FastAPI backend (port 8000)
           │            │
           │            ├─ Middleware chain (CORS → Logging → Rate Limit)
           │            │
           │            ├─ Router match: POST /api/v1/auth/login
           │            │   │
           │            │   ├─ Depends(): create AuthService(session, redis)
           │            │   ├─ service.login(email, password)
           │            │   └─ return TokenResponse → JSON
           │            │
           │            └─ Error handler catches any exceptions → JSON
           │
           └─ /* → React frontend (static files or dev server)
```

---

<a name="router"></a>
## 2. File 1: `router.py` — Auth API Endpoints

### What Is a Router? Read This First

A **router** groups related endpoints under a prefix. Instead of defining all endpoints in `main.py` (which would be thousands of lines), each module has its own router.

```python
# In router.py:
router = APIRouter()  # Create a router

@router.post("/signup")   # Route: /signup (relative)
async def signup(...):     # Handler function
    ...

# In main.py:
app.include_router(router, prefix="/api/v1/auth")
# Now /signup becomes /api/v1/auth/signup (absolute)
```

### What Is `Depends()`? (Dependency Injection)

**Dependency Injection (DI)** means: "Don't create your own dependencies — let the framework provide them."

```python
# WITHOUT dependency injection:
@router.post("/signup")
async def signup(data: UserCreate):
    session = create_session()        # You manage the session
    redis = connect_to_redis()        # You manage Redis
    service = AuthService(session, redis)  # You create everything
    try:
        user = await service.register(data)
    finally:
        await session.close()         # You clean up

# WITH dependency injection (FastAPI's Depends):
@router.post("/signup")
async def signup(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),  # FastAPI creates + cleans up
):
    user = await service.register(data)
    # Session is auto-closed after the request. You never think about it.
```

`Depends()` tells FastAPI: "Before running this endpoint, call `get_auth_service()` and pass the result as the `service` parameter." FastAPI handles creation, injection, AND cleanup.

### Type This Code: `backend/app/modules/auth/router.py`

```python
# ============================================================================
# Auth Module — Router (API Endpoints)
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines all HTTP endpoints for authentication.
#   Each function handles one endpoint — thin wrappers around the service.
#
# ENDPOINTS:
#   POST /api/v1/auth/signup    → Register a new user
#   POST /api/v1/auth/login     → Login, get JWT tokens
#   POST /api/v1/auth/refresh   → Refresh expired access token
#   POST /api/v1/auth/logout    → Blacklist current tokens
#   GET  /api/v1/auth/me        → Get current user profile
#   PUT  /api/v1/auth/me        → Update current user profile
#
# ROUTER VS SERVICE:
#   Router knows about HTTP: request bodies, status codes, headers.
#   Service knows about business: can this user register? is the password right?
#
#   Router is a thin translation layer:
#     HTTP request → extract data → call service → format HTTP response
# ============================================================================

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

import redis.asyncio as redis

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_async_session
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError
from app.modules.auth.schemas import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.modules.auth.security import decode_token
from app.modules.auth.service import AuthService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()

settings = get_settings()


# ── Dependency: Get Auth Service ──
# This creates a new AuthService instance for each request,
# injecting the current DB session and Redis client.
async def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AuthService:
    return AuthService(session, redis_client)


# ── Dependency: Get Current User ID from JWT Token ──
# This is the core auth dependency — used by ALL protected endpoints.
async def get_current_user_id(
    authorization: Annotated[str, Header(description="Bearer <access_token>")],
    redis_client: redis.Redis = Depends(get_redis_client),
) -> UUID:
    """
    Extract and validate user ID from the JWT token in the Authorization header.

    HOW IT WORKS:
    1. Frontend sends: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
    2. We extract the token part (after "Bearer ")
    3. Decode and verify the JWT (signature, expiry, type)
    4. Check if token is blacklisted (user logged out)
    5. Return the user_id from the token payload

    This dependency is injected into any endpoint that needs authentication:
        @router.get("/me")
        async def get_profile(user_id: UUID = Depends(get_current_user_id)):
            ...

    Raises:
        TokenInvalidError: if no token, bad format, or tampered
        TokenExpiredError: if token has expired
    """
    # Extract token from "Bearer <token>" header value
    if not authorization.startswith("Bearer "):
        raise TokenInvalidError()

    token = authorization[7:]  # Skip "Bearer " (7 characters)

    # Decode and validate the JWT
    payload = decode_token(token, expected_type="access")

    # Check blacklist (logged-out tokens)
    is_blacklisted = await redis_client.get(f"token_blacklist:{token[:32]}")
    if is_blacklisted:
        raise TokenInvalidError()

    return UUID(payload["sub"])


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Register a new user account.

    - Validates email format and uniqueness
    - Hashes the password with bcrypt
    - Creates the user record in PostgreSQL
    - Returns the user profile (without password)

    After signup, the frontend should redirect to the login page.
    """
    user = await service.register(data)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(
    data: UserLogin,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Authenticate with email and password, receive JWT tokens.

    Returns:
    - access_token: Send with every API request (expires in 30 min)
    - refresh_token: Use to get new access_token (expires in 7 days)

    Frontend usage:
        const response = await api.post("/auth/login", { email, password });
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("refresh_token", response.refresh_token);
        // Then on every request:
        api.defaults.headers.Authorization = `Bearer ${access_token}`;
    """
    tokens = await service.login(data.email, data.password)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh expired access token",
)
async def refresh_tokens(
    refresh_token: str,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """
    Get new access + refresh tokens using a valid refresh token.

    Called automatically by the frontend when the access token expires.
    The old refresh token is blacklisted (can't be reused).

    Frontend usage:
        // When a request returns 401 (token expired):
        const newTokens = await api.post("/auth/refresh", {
            refresh_token: localStorage.getItem("refresh_token")
        });
        // Update stored tokens and retry the failed request
    """
    tokens = await service.refresh_tokens(refresh_token)
    return tokens


@router.post(
    "/logout",
    response_model=SuccessResponse,
    summary="Logout and blacklist tokens",
)
async def logout(
    user_id: UUID = Depends(get_current_user_id),
    authorization: str = Header(),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    """
    Logout — blacklist the current access token.

    After logout, the access token can no longer be used.
    The frontend should clear stored tokens and redirect to login.
    """
    token = authorization[7:]  # Extract token from "Bearer <token>"
    await service.logout(access_token=token)
    return SuccessResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Get the authenticated user's profile.

    Requires a valid access token in the Authorization header.
    Returns user info (never includes password).
    """
    user = await service.get_current_user(user_id)
    return UserResponse.model_validate(user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    data: UserUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """
    Update the authenticated user's profile.

    Only provided fields are updated (partial update).
    Email and password changes are not supported here
    (would need separate endpoints with additional verification).
    """
    user = await service.update_profile(user_id, data)
    return UserResponse.model_validate(user)
```

### Line-by-Line Explanation: Router

**Lines 23-25: Key Imports**
```python
from typing import Annotated
from fastapi import APIRouter, Depends, Header, status
```
- `Annotated` — Python 3.9+ feature that combines a type with metadata. Used for `Annotated[str, Header()]` — means "this is a string that comes from an HTTP header"
- `APIRouter` — creates a router for grouping endpoints. Registered on the app with a prefix
- `Depends` — FastAPI's dependency injection. `Depends(get_auth_service)` = "call this function and pass the result"
- `Header` — extracts a value from HTTP headers. `Header()` reads the `Authorization` header
- `status` — HTTP status code constants. `status.HTTP_201_CREATED` = `201`

**Lines 43-44: Router Instance**
```python
router = APIRouter()
settings = get_settings()
```
- `APIRouter()` — creates the router. Endpoints are attached to it with `@router.get()`, `@router.post()`, etc.
- This router is later registered in `main.py`: `app.include_router(router, prefix="/api/v1/auth")`

**Lines 48-52: `get_auth_service` Dependency**
```python
async def get_auth_service(
    session: AsyncSession = Depends(get_async_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> AuthService:
    return AuthService(session, redis_client)
```
- This is a **dependency factory** — creates `AuthService` with injected dependencies
- `Depends(get_async_session)` — FastAPI calls `get_async_session()` (from Part 02's `dependencies.py`), which yields a database session. After the request, the session is automatically closed
- `Depends(get_redis_client)` — provides the Redis client
- **Dependency chain:** Endpoint needs `AuthService` → `AuthService` needs `session` + `redis` → FastAPI resolves the whole chain automatically

**Lines 55-88: `get_current_user_id` Dependency (THE Core Auth Dependency)**
```python
async def get_current_user_id(
    authorization: Annotated[str, Header(description="Bearer <access_token>")],
    redis_client: redis.Redis = Depends(get_redis_client),
) -> UUID:
```
- `Annotated[str, Header(...)]` — extracts the `Authorization` HTTP header as a string
- This is the dependency that EVERY protected endpoint uses:
  ```python
  @router.get("/me")
  async def get_profile(user_id: UUID = Depends(get_current_user_id)):
  ```
- FastAPI automatically calls `get_current_user_id()` before the endpoint handler
- If it raises an exception (invalid token), the endpoint handler NEVER runs

```python
    if not authorization.startswith("Bearer "):
        raise TokenInvalidError()
    token = authorization[7:]
```
- The `Authorization` header looks like: `Bearer eyJhbGciOiJIUzI1NiIs...`
- `authorization[7:]` — skips the first 7 characters (`"Bearer "`) to get the raw token
- If the header doesn't start with `"Bearer "`, it's malformed → reject

```python
    payload = decode_token(token, expected_type="access")
    is_blacklisted = await redis_client.get(f"token_blacklist:{token[:32]}")
    if is_blacklisted:
        raise TokenInvalidError()
    return UUID(payload["sub"])
```
- `decode_token()` — verifies signature, checks expiry, validates type="access"
- Redis blacklist check — logged-out tokens are rejected
- `UUID(payload["sub"])` — converts the string user_id back to a UUID and returns it

**Lines 94-108: Signup Endpoint**
```python
@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def signup(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    user = await service.register(data)
    return UserResponse.model_validate(user)
```
- `@router.post("/signup")` — this handles `POST /api/v1/auth/signup` (prefix added in main.py)
- `response_model=UserResponse` — tells FastAPI (and Swagger docs): "this endpoint returns a UserResponse"
- `status_code=status.HTTP_201_CREATED` — returns 201 instead of default 200 (convention for resource creation)
- `summary=` — shows in Swagger docs
- `data: UserCreate` — FastAPI automatically parses the JSON body and validates it against `UserCreate` schema. If validation fails, Pydantic returns 422 BEFORE your code runs
- `service: AuthService = Depends(get_auth_service)` — injected auth service
- `UserResponse.model_validate(user)` — converts SQLAlchemy User object to Pydantic response (filtering out `password_hash`)
- **This is a THIN handler** — 2 lines of actual logic. All business logic is in the service

**Lines 146-155: Logout Endpoint (Multiple Dependencies)**
```python
async def logout(
    user_id: UUID = Depends(get_current_user_id),
    authorization: str = Header(),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse:
    token = authorization[7:]
    await service.logout(access_token=token)
    return SuccessResponse(message="Successfully logged out")
```
- **Three dependencies injected:** `user_id` (from JWT), `authorization` (raw header), `service`
- `user_id = Depends(get_current_user_id)` — validates the token FIRST. If invalid, logout never runs
- `authorization: str = Header()` — we also need the raw token string to blacklist it
- `token = authorization[7:]` — extract the token from "Bearer <token>"
- Returns a simple success message (no data to return)

---

<a name="main"></a>
## 3. File 2: `main.py` — FastAPI Application Entry Point

### What Is main.py?

This is the **first file that runs** when the server starts. It creates the FastAPI app, registers middleware, registers routers, and defines startup/shutdown behavior.

### Key Concepts in main.py

**App Factory Pattern** — instead of `app = FastAPI()` at the top level, we use `create_app()`:
```python
# Bad: global variable, hard to test
app = FastAPI()

# Good: factory function, testable
def create_app() -> FastAPI:
    app = FastAPI(...)
    # configure...
    return app

app = create_app()
```

**Lifespan** — code that runs on startup and shutdown:
```python
@asynccontextmanager
async def lifespan(app):
    # STARTUP: connect DB, setup logging
    yield
    # SHUTDOWN: close connections, cleanup
```

### Type This Code: `backend/app/main.py`

```python
# ============================================================================
# Health Tracker — FastAPI Application Entry Point
# ============================================================================
# WHAT THIS FILE DOES:
#   Creates and configures the FastAPI application.
#   This is the FIRST file that runs when the server starts.
#
# KEY CONCEPTS:
#   App Factory  — create_app() function builds the app (testable, configurable)
#   Lifespan     — startup/shutdown events (connect DB, close connections)
#   Middleware   — code that runs on EVERY request (logging, CORS, rate limiting)
#   Routers      — organize endpoints by module (auth, habits, logs, etc.)
#
# REQUEST FLOW:
#   Client → Nginx → FastAPI (middleware chain) → Router → Handler → Response
#   Each middleware can inspect/modify the request before it reaches the handler.
# ============================================================================

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.redis_client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan — runs code on startup and shutdown.

    WHAT IS LIFESPAN:
      Code before 'yield' runs when the server STARTS.
      Code after 'yield' runs when the server STOPS.

    WHY:
      - Startup: verify DB connection, create MinIO bucket, log config
      - Shutdown: close DB pool, close Redis connections, cleanup resources

    Without proper shutdown, you'd leak database connections.
    In production with 4 workers, that's 4 × 20 pool_size = 80 leaked connections.
    Eventually the database refuses new connections and the app crashes.
    """
    # ── Startup ──
    settings = get_settings()

    # Configure structured logging FIRST — so all other startup logs are formatted
    from app.shared.logging import setup_logging
    setup_logging()

    print(f"🚀 Starting {settings.APP_NAME} v{__version__}")
    print(f"   Environment: {settings.APP_ENV}")
    print(f"   Debug: {settings.DEBUG}")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Database: {settings.DATABASE_URL.split('@')[-1]}")  # Log host only, not password

    yield  # Application is running and handling requests

    # ── Shutdown ──
    print("🛑 Shutting down...")
    await close_redis()
    # SQLAlchemy engine cleanup happens automatically via garbage collection,
    # but we could call: await engine.dispose() if needed.
    print("✅ Shutdown complete.")


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI app.

    WHY A FACTORY FUNCTION (not a global variable):
      1. Testable — tests can create a fresh app with different settings
      2. Configurable — pass different settings for dev/staging/prod
      3. Clean — all setup logic in one place

    This pattern is used in Flask (create_app), Django (get_wsgi_application),
    Express.js (createApp), and Spring Boot (@SpringBootApplication).
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered Personal Health & Habit Tracker API",
        version=__version__,
        # Lifespan handles startup/shutdown events
        lifespan=lifespan,
        # API docs URL — visit http://localhost:8000/docs to see Swagger UI
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── Register Error Handlers ──
    from app.middleware.error_handler import register_error_handlers
    register_error_handlers(app)

    # ── Register Middleware ──
    _register_middleware(app, settings)

    # ── Register Routers ──
    _register_routers(app)

    # ── Health Check ──
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "version": __version__,
            "environment": settings.APP_ENV,
        }

    return app


def _register_middleware(app: FastAPI, settings: get_settings) -> None:
    """
    Register all middleware in the correct order.

    MIDDLEWARE ORDER MATTERS:
      Outermost (first added) runs first on request, last on response.
      Think of it like layers of an onion:

      Request  → CORS → Logging → Rate Limit → Error Handler → Route Handler
      Response ← CORS ← Logging ← Rate Limit ← Error Handler ← Route Handler

    WHY CORS FIRST:
      Browser sends a preflight OPTIONS request before actual API calls.
      CORS middleware must handle this BEFORE any other middleware runs.
      Without CORS, your React frontend can't talk to the API.
    """
    # CORS — Cross-Origin Resource Sharing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging middleware — logs every request with timing and request_id
    from app.middleware.logging_middleware import LoggingMiddleware
    app.add_middleware(LoggingMiddleware)

    # Rate limiter — prevents abuse, brute force, and expensive AI spam
    from app.middleware.rate_limiter import RateLimiterMiddleware
    app.add_middleware(RateLimiterMiddleware)


def _register_routers(app: FastAPI) -> None:
    """
    Register all module routers with their URL prefixes.

    URL DESIGN:
      /api/v1/auth/...        → Auth module
      /api/v1/habits/...      → Habits module
      /api/v1/logs/...        → Logs module
      /api/v1/analytics/...   → Analytics module
      /api/v1/ai/...          → AI module
      /api/v1/notifications/  → Notifications module
      /api/v1/export/...      → Export module

    WHY /api/v1/:
      - /api/ distinguishes API routes from frontend routes
      - /v1/ allows versioning — add /v2/ without breaking clients
    """
    from app.modules.auth.router import router as auth_router
    from app.modules.habits.router import router as habits_router
    from app.modules.logs.router import router as logs_router
    from app.modules.analytics.router import router as analytics_router
    from app.modules.ai.router import router as ai_router
    from app.modules.notifications.router import router as notifications_router
    from app.modules.export.router import router as export_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(habits_router, prefix="/api/v1/habits", tags=["Habits"])
    app.include_router(logs_router, prefix="/api/v1/logs", tags=["Logs"])
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI"])
    app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["Notifications"])
    app.include_router(export_router, prefix="/api/v1/export", tags=["Export"])


# ── Create the app instance ──
# This is what uvicorn/gunicorn imports: "app.main:app"
app = create_app()
```

### Line-by-Line Explanation: main.py

**Lines 18-20: Imports**
```python
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
```
- `asynccontextmanager` — decorator that creates an async context manager from a generator function. Used for the lifespan
- `AsyncGenerator[None, None]` — type hint for async generators that yield `None` and return `None`
- `CORSMiddleware` — Cross-Origin Resource Sharing. Without it, browsers block requests from `localhost:3000` (React) to `localhost:8000` (API)

**Lines 29-56: Lifespan**
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup code
    from app.shared.logging import setup_logging
    setup_logging()
    print(f"🚀 Starting {settings.APP_NAME}...")

    yield  # App is running

    # Shutdown code
    await close_redis()
    print("✅ Shutdown complete.")
```
- Everything BEFORE `yield` runs on **startup**
- `yield` — the app is now running and handling requests
- Everything AFTER `yield` runs on **shutdown** (Ctrl+C, Docker stop, etc.)
- **Why `from ... import` inside the function?** Lazy imports avoid circular dependencies. `setup_logging` depends on `config.py`, which might not be fully loaded at module import time
- `settings.DATABASE_URL.split('@')[-1]` — logs the database HOST but NOT the password. `postgresql://user:pass@localhost:5432/db` → `localhost:5432/db`

**Lines 58-90: `create_app()` Factory**
```python
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Personal Health & Habit Tracker API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)
```
- `title`, `description`, `version` — show in the auto-generated Swagger docs at `/docs`
- `lifespan=lifespan` — registers the startup/shutdown handler
- `docs_url="/docs" if not settings.is_production else None` — Swagger docs available in dev, DISABLED in production (security: don't expose API schema publicly)
- `redoc_url` — ReDoc is an alternative API docs viewer

**Lines 98-115: `_register_middleware()`**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- **CORS** (Cross-Origin Resource Sharing) — browsers block requests between different origins by default
- `allow_origins` — list of allowed origins: `["http://localhost:3000", "http://localhost:5173"]`
- `allow_credentials=True` — allows cookies and `Authorization` headers
- `allow_methods=["*"]` — allows GET, POST, PUT, DELETE, etc.
- `allow_headers=["*"]` — allows any header (including `Authorization`)
- **Why CORS first?** Browsers send a preflight `OPTIONS` request before the real request. CORS middleware must respond to this BEFORE logging/rate-limiting middleware runs

**Lines 117-140: `_register_routers()`**
```python
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
```
- `prefix="/api/v1/auth"` — all auth routes get this prefix. `@router.post("/signup")` becomes `POST /api/v1/auth/signup`
- `tags=["Authentication"]` — groups endpoints in Swagger docs under "Authentication" header
- **Why `/api/v1/`?** `/api/` separates API routes from frontend routes (Nginx sends `/api/*` to backend, `/*` to React). `/v1/` is API versioning — when you make breaking changes, add `/v2/` without breaking existing clients

**Last Line: `app = create_app()`**
```python
app = create_app()
```
- This is what uvicorn runs: `uvicorn app.main:app`
- The `app.main` part is the Python module path, `:app` is the variable name

---

<a name="nginx"></a>
## 4. File 3: `nginx/default.conf` — Reverse Proxy

### What Is a Reverse Proxy? Read This First

A **reverse proxy** sits between the client and your backend server. The client talks to Nginx, Nginx talks to FastAPI.

```
WITHOUT Nginx:
  Browser → FastAPI (:8000)
  Problem: No rate limiting, no compression, no static files, no SSL

WITH Nginx:
  Browser → Nginx (:80) → FastAPI (:8000)
  Nginx handles: rate limiting, gzip, static files, SSL, security headers
  FastAPI handles: only business logic (what it's good at)
```

**Real-world analogy:** A **receptionist** at a company. Visitors (requests) don't walk directly into offices (FastAPI). The receptionist checks IDs (rate limiting), directs them to the right floor (routing), and handles basic questions (static files) without bothering the staff.

### Why Not Just Use FastAPI Directly?

| Feature | FastAPI alone | Nginx + FastAPI |
|---------|--------------|-----------------|
| Rate limiting | Application-level only | Network-level + Application-level |
| Static files | Slow (Python is not designed for this) | Fast (Nginx serves files natively) |
| Gzip compression | Must add middleware | Built-in, zero Python overhead |
| SSL/TLS | Possible but complex | Battle-tested, automatic with Let's Encrypt |
| Security headers | Must add manually | Standard config block |
| Connection handling | One connection per worker | 10K+ concurrent connections |
| DDoS protection | Limited | Connection limits, request buffering |

### Type This Code: `health-tracker/nginx/default.conf`

```nginx
# ============================================================================
# Health Tracker — Nginx Reverse Proxy Configuration
# ============================================================================
# WHAT NGINX DOES IN THIS PROJECT:
#   1. Reverse Proxy: Routes /api/* requests to FastAPI backend
#   2. Static Files: Serves React frontend build (in production)
#   3. Rate Limiting: First line of defense against abuse
#   4. Security Headers: Prevents XSS, clickjacking, MIME sniffing
#   5. Gzip: Compresses responses for faster page loads
#   6. SSE Support: Allows streaming for AI chat responses
#
# HOW NGINX WORKS (Interview Gold):
#   Nginx uses an EVENT-DRIVEN, NON-BLOCKING architecture.
#   One master process + multiple worker processes.
#   Each worker handles THOUSANDS of connections using epoll (Linux) / kqueue (Mac).
#   It does NOT create a thread per connection (like Apache).
#   This is why Nginx handles 10K+ concurrent connections with minimal RAM.
#
# REQUEST FLOW:
#   Browser → Nginx (:80) → FastAPI (:8000)
#                          → Static files (React build)
#
# IN PRODUCTION (AWS):
#   Browser → CloudFront (CDN) → ALB → Nginx (sidecar in ECS) → FastAPI
# ============================================================================

# ── Upstream Backend ──
upstream backend {
    server backend:8000;
    keepalive 32;
}

# ── Rate Limiting Zones ──
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=ai_limit:10m rate=2r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;


# ── Server Block ──
server {
    listen 80;
    server_name localhost;

    # ── Security Headers ──
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ── Gzip Compression ──
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/json
        application/javascript
        application/xml
        image/svg+xml;

    # ── API Routes → Backend ──
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── AI Endpoints → Backend (Stricter Rate Limit + SSE Support) ──
    location /api/v1/ai/ {
        limit_req zone=ai_limit burst=5 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # ── SSE (Server-Sent Events) Support ──
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── Login Endpoint → Backend (Anti-Brute-Force Rate Limit) ──
    location /api/v1/auth/login {
        limit_req zone=login_limit burst=3 nodelay;

        proxy_pass http://backend;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }

    # ── Health Check ──
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # ── Frontend Static Files (Production) ──
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;

        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }
    }

    # ── Swagger/API Docs ──
    location /docs {
        proxy_pass http://backend/docs;
        proxy_set_header Host $host;
    }
    location /redoc {
        proxy_pass http://backend/redoc;
        proxy_set_header Host $host;
    }
    location /openapi.json {
        proxy_pass http://backend/openapi.json;
        proxy_set_header Host $host;
    }

    # ── Custom Error Pages ──
    error_page 429 @rate_limited;
    location @rate_limited {
        default_type application/json;
        return 429 '{"error_code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please slow down.", "detail": null}';
    }

    error_page 502 @bad_gateway;
    location @bad_gateway {
        default_type application/json;
        return 502 '{"error_code": "SERVICE_UNAVAILABLE", "message": "Backend service is starting up. Please try again in a moment.", "detail": null}';
    }

    error_page 504 @gateway_timeout;
    location @gateway_timeout {
        default_type application/json;
        return 504 '{"error_code": "GATEWAY_TIMEOUT", "message": "Request timed out. Please try again.", "detail": null}';
    }
}
```

### Key Nginx Concepts Explained

**Upstream Block**
```nginx
upstream backend {
    server backend:8000;
    keepalive 32;
}
```
- `upstream` — defines a group of backend servers. Nginx load-balances across them
- `server backend:8000` — Docker Compose resolves `backend` to the container's IP
- `keepalive 32` — keep 32 TCP connections open to the backend. Without this, Nginx opens a NEW TCP connection for every request (slow: TCP handshake takes ~1ms)

**Rate Limiting Zones**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```
- `$binary_remote_addr` — client's IP address in binary (saves memory vs string)
- `zone=api_limit:10m` — 10 MB shared memory zone named "api_limit" (stores ~160K IP addresses)
- `rate=30r/s` — 30 requests per second per IP for general API
- `rate=5r/m` — 5 requests per MINUTE for login (anti-brute-force)
- `rate=2r/s` — 2 requests per second for AI (LLM calls are expensive)

**Location Blocks — Nginx Matching Rules**
```nginx
location /api/v1/auth/login { ... }  # Most specific — checked first
location /api/v1/ai/ { ... }         # Specific prefix
location /api/ { ... }               # General prefix
location / { ... }                   # Catch-all
```
- Nginx matches the MOST SPECIFIC location first
- `/api/v1/auth/login` → uses `login_limit` (5/min)
- `/api/v1/ai/chat` → uses `ai_limit` (2/sec)
- `/api/v1/habits` → uses `api_limit` (30/sec)
- `/dashboard` → serves static React files

**Proxy Headers**
```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```
- Without these, FastAPI sees Nginx's IP as the client IP (all requests from "127.0.0.1")
- `X-Real-IP` — the actual client's IP address
- `X-Forwarded-For` — chain of proxies the request passed through
- `X-Forwarded-Proto` — `http` or `https` (needed for generating correct URLs)

**SSE Support for AI Chat**
```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 300s;
```
- AI chat uses **Server-Sent Events (SSE)** — the server streams response tokens one by one
- `proxy_buffering off` — send each token to the client immediately (don't wait for the full response)
- `proxy_cache off` — never cache streaming responses
- `proxy_read_timeout 300s` — AI responses can take up to 5 minutes (complex queries)

**SPA Routing**
```nginx
location / {
    root /usr/share/nginx/html;
    try_files $uri $uri/ /index.html;
}
```
- React is a Single-Page Application (SPA) — all routes are handled by JavaScript in the browser
- `try_files $uri $uri/ /index.html` — if the file exists (JS, CSS, images), serve it. Otherwise, serve `index.html` and let React Router handle the URL
- Example: user visits `/dashboard`. Nginx can't find a file called `dashboard`. Falls back to `index.html`. React Router sees `/dashboard` and renders the Dashboard component

**Custom JSON Error Pages**
```nginx
error_page 429 @rate_limited;
location @rate_limited {
    default_type application/json;
    return 429 '{"error_code": "RATE_LIMIT_EXCEEDED", ...}';
}
```
- By default, Nginx returns HTML error pages. Our frontend expects JSON
- We override error pages to return JSON matching our error format
- `@rate_limited` — a "named location" (internal redirect target, not a URL)

---

<a name="connections"></a>
## 5. How All Three Files Connect

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT (Browser / React)                                             │
│  POST http://localhost/api/v1/auth/login                              │
│  Body: {"email": "shreya@test.com", "password": "Pass123!"}          │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NGINX (default.conf) — port 80                                       │
│                                                                       │
│  1. Match: /api/v1/auth/login → login_limit zone (5 req/min)         │
│  2. Rate check: client has made 2 requests this minute → OK ✅       │
│  3. Add headers: X-Real-IP, X-Forwarded-For                          │
│  4. Proxy to: http://backend:8000/api/v1/auth/login                   │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FASTAPI (main.py) — port 8000                                        │
│                                                                       │
│  1. CORS Middleware: check origin → allowed ✅                        │
│  2. Logging Middleware: generate request_id, start timer              │
│  3. Rate Limiter Middleware: check Redis → 2/60 requests → OK ✅      │
│  4. Route match: POST /api/v1/auth/login → auth router                │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ROUTER (router.py) — login endpoint                                  │
│                                                                       │
│  1. Parse body → UserLogin schema (validates email format)            │
│  2. Depends(get_auth_service) → AuthService(session, redis)           │
│  3. service.login("shreya@test.com", "Pass123!")                      │
│  4. Returns: TokenResponse → JSON                                     │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  RESPONSE                                                             │
│  HTTP 200 OK                                                          │
│  Headers: X-Request-ID: abc-123, X-RateLimit-Remaining: 58            │
│  Body: {"access_token": "eyJ...", "refresh_token": "eyJ...",          │
│         "token_type": "bearer"}                                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

<a name="design-decisions"></a>
## 6. Design Decisions

### Design Decision 1: Thin Router Handlers

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Router Handler Thickness                          │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Thin handlers — 2-5 lines per endpoint                    │
│                                                                     │
│  WHY:                                                               │
│  • Business logic stays in the service (testable without HTTP)      │
│  • Route handlers are just translation layers:                      │
│    HTTP request → extract data → call service → format response     │
│  • Easy to read: each handler fits on one screen                    │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Fat handlers (business logic in the router)                     │
│     ❌ Untestable without running a web server                     │
│     ❌ Can't reuse logic from Celery tasks or CLI                  │
│  2. No router (define endpoints directly on the app)                │
│     ❌ All endpoints in one file — unmaintainable at scale         │
│                                                                     │
│  INTERVIEW TIP: "Our route handlers are 2-5 lines each. They       │
│  parse the request, call the service, and format the response.      │
│  All business logic lives in the service layer, making it           │
│  testable independently of HTTP."                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: Dual Rate Limiting (Nginx + Application)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Rate Limiting Strategy                            │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Two layers — Nginx (network) + application (business)      │
│                                                                     │
│  WHY BOTH:                                                          │
│  • Nginx rate limiting: fast, blocks before request reaches Python  │
│    → Protects against DDoS, reduces load on FastAPI                 │
│  • App rate limiting: user-aware, per-endpoint granularity          │
│    → Logged-in users get higher limits than anonymous               │
│    → Works across multiple Nginx instances (shared Redis)           │
│                                                                     │
│  LAYER COMPARISON:                                                  │
│  Nginx: IP-based, fast, stateless, per-server                      │
│  App:   User-based, flexible, Redis-backed, cluster-wide            │
│                                                                     │
│  AT SCALE: Add a WAF (Web Application Firewall) like AWS WAF       │
│  as a third layer in front of everything.                           │
│                                                                     │
│  INTERVIEW TIP: "We rate limit at two layers. Nginx handles         │
│  IP-based limiting at the network edge — fast and efficient.        │
│  Application-level limiting uses Redis for user-aware, cross-server │
│  rate limits. This defense-in-depth approach handles both DDoS      │
│  and application-level abuse."                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 3: CORS Configuration

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: CORS Strategy                                     │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Whitelist specific origins from environment variable        │
│                                                                     │
│  WHY:                                                               │
│  • Dev: allow localhost:3000, localhost:5173 (React dev servers)     │
│  • Prod: allow only the production domain                           │
│  • Never allow "*" with credentials (security vulnerability)        │
│                                                                     │
│  HOW: CORS_ORIGINS env var = "http://localhost:3000,..."            │
│  Parsed to list in config.py's cors_origins_list property.          │
│                                                                     │
│  INTERVIEW TIP: "CORS is configured via environment variables so    │
│  dev allows localhost origins and production restricts to the        │
│  actual domain. We never use '*' with credentials because browsers  │
│  reject that combination as a security measure."                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 7. How to Verify Your Work

```bash
# 1. Start all services
docker-compose up -d

# 2. Check Nginx is running
curl http://localhost/health
# Expected: {"status":"healthy","version":"0.1.0","environment":"development"}

# 3. Check Swagger docs
# Open in browser: http://localhost/docs
# You should see all 6 auth endpoints listed under "Authentication"

# 4. Test signup
curl -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#","full_name":"Shreya"}'
# Expected: 201 with user data (no password_hash!)

# 5. Test login
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}'
# Expected: 200 with access_token + refresh_token

# 6. Test protected endpoint (replace TOKEN)
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN_FROM_LOGIN"
# Expected: 200 with user profile

# 7. Test rate limiting on login (send 6 requests quickly)
for i in $(seq 1 6); do
  echo "Request $i:"
  curl -s -o /dev/null -w "%{http_code}" -X POST \
    http://localhost/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"wrong@test.com","password":"wrong"}'
  echo ""
done
# Expected: first 5 return 401, 6th returns 429 (rate limited)

# 8. Check Nginx rate limit headers
curl -v http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN" 2>&1 | grep -i "x-rate"
# Expected: X-RateLimit-Limit and X-RateLimit-Remaining headers
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `CORS error` in browser | Origin not in allowed list | Check `CORS_ORIGINS` in `.env` |
| `502 Bad Gateway` | Backend not running | `docker-compose logs backend` to check errors |
| `404 Not Found` for `/api/v1/auth/signup` | Router not registered | Check `_register_routers()` in `main.py` |
| Nginx returns HTML error | Custom error pages not configured | Check `error_page` directives in `default.conf` |
| `422 Unprocessable Entity` | Request body doesn't match schema | Check JSON field names match the schema |

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **APIRouter** | Groups related endpoints with a shared prefix | `router.py` |
| 2 | **`Depends()`** | FastAPI dependency injection — auto-creates and injects dependencies | `router.py` |
| 3 | **`Annotated[str, Header()]`** | Extract value from HTTP header with type annotation | `get_current_user_id` |
| 4 | **`response_model`** | Tells FastAPI (and Swagger) what the endpoint returns | All endpoints |
| 5 | **`status.HTTP_201_CREATED`** | Named HTTP status constant (clearer than `201`) | Signup endpoint |
| 6 | **Dependency Chain** | Endpoint → AuthService → session + redis (resolved recursively) | Router dependencies |
| 7 | **App Factory** | `create_app()` function (not global `app = FastAPI()`) for testability | `main.py` |
| 8 | **Lifespan** | Startup/shutdown code using `@asynccontextmanager` + `yield` | `main.py` |
| 9 | **CORS** | Allows cross-origin requests (React → FastAPI) | `main.py` middleware |
| 10 | **Middleware Order** | CORS first → Logging → Rate Limiter (order matters!) | `main.py` |
| 11 | **`include_router()`** | Registers a module's router with a URL prefix and tag | `main.py` |
| 12 | **API Versioning** | `/api/v1/` — add `/v2/` for breaking changes | URL prefix design |
| 13 | **Reverse Proxy** | Nginx sits in front, routes requests, adds security | `default.conf` |
| 14 | **`upstream`** | Nginx backend server group (supports load balancing) | `default.conf` |
| 15 | **`limit_req_zone`** | Nginx rate limiting with shared memory zones | `default.conf` |
| 16 | **`proxy_set_header`** | Pass real client info (IP, protocol) through the proxy | `default.conf` |
| 17 | **SSE Support** | `proxy_buffering off` for streaming AI responses | `default.conf` |
| 18 | **`try_files`** | SPA routing — serve `index.html` for unknown paths | `default.conf` |
| 19 | **Security Headers** | X-Frame-Options, X-Content-Type-Options, etc. | `default.conf` |
| 20 | **Custom Error Pages** | JSON errors instead of Nginx's default HTML | `default.conf` |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: What is dependency injection and how does FastAPI implement it?
**A:** "Dependency injection means components receive their dependencies from the framework instead of creating them. FastAPI uses `Depends()` — you declare a dependency as a function parameter, and FastAPI calls the provider function, resolves sub-dependencies recursively, and passes the result. For example, our endpoint receives `AuthService` via `Depends(get_auth_service)`, which itself depends on `get_async_session` and `get_redis_client`. FastAPI resolves the entire chain per-request and handles cleanup (closing sessions) automatically."

### Q2: Why use an app factory instead of a global app variable?
**A:** "The factory pattern `create_app()` makes the app configurable and testable. Tests can call `create_app()` with different settings (test database, disabled rate limiting). Integration tests create isolated app instances. Without a factory, the app is configured at import time with hardcoded settings, making it impossible to test different configurations. This pattern is standard: Flask's `create_app()`, Django's `get_wsgi_application()`, Spring Boot's `@SpringBootApplication`."

### Q3: Why is middleware order important?
**A:** "Middleware runs in registration order on requests and reverse order on responses — like layers of an onion. CORS must be first because browsers send a preflight OPTIONS request before the actual request. If logging middleware runs first, it would reject the OPTIONS request (no auth header) before CORS can respond. Rate limiting after logging ensures rate-limited requests are still logged — important for security monitoring."

### Q4: Why Nginx in front of FastAPI? Why not just FastAPI directly?
**A:** "Nginx excels at things Python is slow at: serving static files, handling 10K+ concurrent connections, gzip compression, and network-level rate limiting. Nginx uses an event-driven architecture — one worker thread handles thousands of connections via epoll. FastAPI would need one connection per Python async coroutine. Nginx also adds security headers, SSL termination, and DDoS protection before requests even reach Python. In production, this setup runs as a sidecar in ECS — Nginx and FastAPI in the same task."

### Q5: How does the `get_current_user_id` dependency work across all modules?
**A:** "It's a dependency function that extracts and validates the JWT from the Authorization header, checks the Redis blacklist, and returns the user UUID. Any protected endpoint in ANY module adds `user_id: UUID = Depends(get_current_user_id)` as a parameter. FastAPI calls this dependency before the handler — if the token is invalid, the handler never runs. The Habits, Logs, Analytics, and AI modules all import and reuse this same dependency. One auth check, used everywhere."

### Q6: Explain Nginx rate limiting — `limit_req_zone` and `burst`.
**A:** "`limit_req_zone` defines a shared memory zone that tracks request counts per IP. `rate=5r/m` means 5 requests per minute per IP. The `burst=3` parameter allows 3 requests to queue when the rate is exceeded — without burst, the 6th request is immediately rejected. `nodelay` means process burst requests immediately instead of spacing them out. We have three zones: `api_limit` (30 req/sec for general API), `ai_limit` (2 req/sec for expensive LLM calls), and `login_limit` (5 req/min to prevent brute-force)."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04c: Auth Repository & Service](./phase4-part04c-auth-repository-service.md) |
| ➡️ Next | [Phase 4 Part 04e: Auth Alembic Migrations](./phase4-part04e-auth-alembic-migrations.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 04a | ✅ Done | Auth Models, Exceptions & Schemas |
| 04b | ✅ Done | Auth Security — JWT & bcrypt |
| 04c | ✅ Done | Auth Repository & Service |
| **04d** | ✅ **You are here** | Auth Router, Main & Nginx |
| 04e | ⬜ Next | Auth Alembic Migrations |
| 04f | ⬜ | Auth Connections & Flows |

---

**End of Phase 4 Part 04d: Auth Router, Main App & Nginx**

*The auth module is now fully wired. Requests flow from browser → Nginx → FastAPI → router → service → database. The 6 auth endpoints are live. Next: Alembic migrations to create the users table in PostgreSQL.*
