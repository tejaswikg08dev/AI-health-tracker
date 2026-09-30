# 🔄 Phase 4 Part 04f: Auth — Connections & Flows

> **"If you can trace a request from the browser through every layer to the database and back — and explain what happens at each step — you've mastered the architecture. This document is that trace."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04f (Auth Flows & Architecture) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04e-auth-alembic-migrations.md](./phase4-part04e-auth-alembic-migrations.md) |
| **Next** | [phase4-part05-habits-service-overview.md](./phase4-part05-habits-service-overview.md) |
| **Files in This Doc** | 0 (architecture diagrams only — no new code) |
| **Time to Read** | ~20 minutes |
| **Difficulty** | Medium (connecting all pieces you've already built) |

---

## 📖 Table of Contents

1. [Auth Module — Complete File Map](#file-map)
2. [Flow 1: User Signup (Step by Step)](#signup-flow)
3. [Flow 2: User Login (Step by Step)](#login-flow)
4. [Flow 3: Accessing a Protected Endpoint](#protected-flow)
5. [Flow 4: Token Refresh](#refresh-flow)
6. [Flow 5: Logout](#logout-flow)
7. [Flow 6: Error Paths](#error-flows)
8. [Cross-Module Dependency Map](#cross-module)
9. [Auth Module Summary](#summary)
10. [Navigation](#navigation)

---

<a name="file-map"></a>
## 1. Auth Module — Complete File Map

Every file you built in Parts 04a–04e, and how they connect:

```
backend/app/modules/auth/
├── models.py          ─── Part 04a ── User table (8 columns, SQLAlchemy ORM)
├── exceptions.py      ─── Part 04a ── 5 exception classes (InvalidCredentials, TokenExpired, etc.)
├── schemas.py         ─── Part 04a ── 5 schemas (UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse)
├── security.py        ─── Part 04b ── 4 functions (hash_password, verify_password, create_token, decode_token)
├── repository.py      ─── Part 04c ── UserRepository (inherits BaseRepository + 3 custom queries)
├── service.py         ─── Part 04c ── AuthService (register, login, refresh, logout, profile)
├── router.py          ─── Part 04d ── 6 endpoints + 2 dependency functions
└── __init__.py        ─── (empty)

backend/app/main.py              ─── Part 04d ── App factory, middleware, router registration
nginx/default.conf                ─── Part 04d ── Reverse proxy, rate limiting, SSE support
backend/alembic.ini               ─── Part 04e ── Migration tool config
backend/alembic/env.py            ─── Part 04e ── Model discovery + DB connection
backend/alembic/versions/001_...  ─── Part 04e ── CREATE TABLE users migration
```

### Dependency Graph (Who Imports What)

```
router.py ──imports──→ schemas.py (UserCreate, UserResponse, TokenResponse)
    │                  exceptions.py (TokenExpiredError, TokenInvalidError)
    │                  security.py (decode_token)
    │                  service.py (AuthService)
    │
    ▼
service.py ──imports──→ repository.py (UserRepository)
    │                   security.py (hash_password, verify_password, create_*_token)
    │                   exceptions.py (InvalidCredentials, UserAlreadyExists, AccountDeactivated)
    │                   schemas.py (TokenResponse, UserCreate, UserUpdate)
    │
    ▼
repository.py ──imports──→ models.py (User)
    │                      base_repository.py (BaseRepository — from shared/)
    │
    ▼
models.py ──imports──→ database.py (Base — from Part 02)
```

---

<a name="signup-flow"></a>
## 2. Flow 1: User Signup (Step by Step)

```
STEP  COMPONENT         ACTION                                    FILE
────  ───────────       ──────                                    ────
 1    Browser           POST /api/v1/auth/signup                   —
                        Body: {"email":"shreya@test.com",
                               "password":"Pass123!",
                               "full_name":"Shreya"}

 2    Nginx             Match: /api/ location block                default.conf
                        Rate check: api_limit (30 req/s) → OK
                        Forward to backend:8000

 3    CORS Middleware    Check Origin header → allowed              main.py

 4    Logging MW        Generate request_id: "a1b2c3d4"           logging_middleware.py
                        Start timer

 5    Rate Limiter MW   Check Redis counter → within limit         rate_limiter.py

 6    FastAPI Router    Match: POST /api/v1/auth/signup            router.py
                        Parse body → UserCreate schema
                        Pydantic validates:
                          ✅ email format valid
                          ✅ password >= 8 chars
                          ✅ full_name 1-100 chars

 7    Depends()         Create AuthService(session, redis)         router.py
                        (session from get_async_session,
                         redis from get_redis_client)

 8    Service           service.register(data):                    service.py
      .register()         a) repo.email_exists("shreya@test.com")
                            → SELECT * FROM users WHERE email = ?
                            → None (email not taken) ✅
                          b) hash_password("Pass123!")
                            → "$2b$12$..." (bcrypt hash)
                          c) repo.create(email=..., password_hash=...)
                            → INSERT INTO users (...) VALUES (...)
                            → User(id=uuid-001)
                          d) session.commit()
                          e) return User

 9    Router            UserResponse.model_validate(user)          router.py
                        Filters: ✅ id, email, full_name, timezone
                                 ❌ password_hash (hidden!)

10    Logging MW        Stop timer: 45ms                           logging_middleware.py
                        Log: {"event":"http_request", "method":"POST",
                              "path":"/api/v1/auth/signup",
                              "status":201, "duration_ms":45}

11    Nginx             Add headers, gzip compress                 default.conf

12    Browser           HTTP 201 Created                           —
                        {"id":"uuid-001","email":"shreya@test.com",
                         "full_name":"Shreya","timezone":"UTC",
                         "is_active":true,"created_at":"2026-09-26T..."}
```

---

<a name="login-flow"></a>
## 3. Flow 2: User Login (Step by Step)

```
STEP  COMPONENT         ACTION                                    FILE
────  ───────────       ──────                                    ────
 1    Browser           POST /api/v1/auth/login                    —
                        Body: {"email":"shreya@test.com",
                               "password":"Pass123!"}

 2    Nginx             Match: /api/v1/auth/login (specific)       default.conf
                        Rate check: login_limit (5 req/min) → OK
                        Forward to backend:8000

 3    Middleware         CORS → Logging → Rate Limit → OK          main.py

 4    FastAPI Router    Match: POST /api/v1/auth/login             router.py
                        Parse body → UserLogin schema

 5    Depends()         Create AuthService(session, redis)         router.py

 6    Service           service.login(email, password):            service.py
      .login()            a) repo.get_by_email("shreya@test.com")
                            → SELECT * FROM users WHERE email = ?
                            → User(id=uuid-001, password_hash="$2b$12$...")
                          b) verify_password("Pass123!", "$2b$12$...")
                            → bcrypt: extract salt, hash attempt, compare
                            → True ✅
                          c) user.is_active → True ✅
                          d) create_access_token(user.id)
                            → JWT: {"sub":"uuid-001","type":"access",
                                    "exp": now+30min}
                            → "eyJhbGciOi..." (signed with SECRET_KEY)
                          e) create_refresh_token(user.id)
                            → JWT: {"sub":"uuid-001","type":"refresh",
                                    "exp": now+7days}
                            → "eyJhbGciOi..." (different token)
                          f) return TokenResponse

 7    Browser           HTTP 200 OK                                —
                        {"access_token":"eyJ...access...",
                         "refresh_token":"eyJ...refresh...",
                         "token_type":"bearer"}

 8    Frontend          Stores tokens:                             React app
                        localStorage.setItem("access_token", ...)
                        Sets default header:
                        axios.defaults.headers.Authorization =
                          "Bearer eyJ...access..."
```

---

<a name="protected-flow"></a>
## 4. Flow 3: Accessing a Protected Endpoint

This flow applies to ALL protected endpoints across ALL modules (Habits, Logs, Analytics, AI).

```
STEP  COMPONENT              ACTION                              FILE
────  ───────────            ──────                              ────
 1    Browser                GET /api/v1/auth/me                  —
                             Headers: Authorization: Bearer eyJ...

 2    Nginx → Middleware     Rate check + logging + CORS → OK     —

 3    FastAPI Router         Match: GET /api/v1/auth/me           router.py
                             Sees: user_id = Depends(get_current_user_id)
                             → Must resolve dependency FIRST

 4    get_current_user_id()  Extract token from header:           router.py
                               "Bearer eyJhbGci..." → "eyJhbGci..."

                             decode_token(token, expected_type="access"):
                               a) jwt.decode(token, SECRET_KEY, HS256)
                                  → Verify signature ✅
                                  → Check expiry (25 min remaining) ✅
                               b) payload.type == "access" ✅
                               c) payload.sub exists ✅

                             Check blacklist:
                               redis.get("token_blacklist:eyJhbGci...")
                               → None (not blacklisted) ✅

                             Return: UUID("uuid-001")

 5    Depends()              Create AuthService(session, redis)    router.py

 6    Handler                service.get_current_user(uuid-001)    router.py
      get_my_profile()         → repo.get_active_by_id(uuid-001)
                               → SELECT * FROM users
                                 WHERE id = 'uuid-001'
                                 AND is_active = true
                               → User(id=uuid-001, email="shreya@test.com")

 7    Response               UserResponse.model_validate(user)     router.py
                             → HTTP 200 {"id":"uuid-001",
                                "email":"shreya@test.com",
                                "full_name":"Shreya", ...}
```

---

<a name="refresh-flow"></a>
## 5. Flow 4: Token Refresh

```
TRIGGER: Frontend gets 401 TOKEN_EXPIRED on an API call

STEP  COMPONENT         ACTION                                    FILE
────  ───────────       ──────                                    ────
 1    Frontend          Intercept 401 response                     React app
                        Check: error_code == "TOKEN_EXPIRED"?
                        → Yes: try refreshing

 2    Frontend          POST /api/v1/auth/refresh                  React app
                        Body: "eyJ...refresh_token..."

 3    Router            Parse refresh_token string                 router.py
                        Depends(get_auth_service)

 4    Service           service.refresh_tokens(refresh_token):     service.py
      .refresh_tokens()
                        a) decode_token(token, expected_type="refresh")
                           → Verify signature ✅
                           → Check expiry (5 days remaining) ✅
                           → type == "refresh" ✅
                           → user_id = UUID(payload["sub"])

                        b) redis.get("token_blacklist:eyJ...refresh...")
                           → None (not blacklisted) ✅

                        c) repo.get_active_by_id(user_id)
                           → User still active ✅

                        d) _blacklist_token(old_refresh_token)
                           → decode to get exp timestamp
                           → TTL = exp - now = 432,000 seconds (5 days)
                           → redis.setex("token_blacklist:eyJ...",
                                         432000, "blacklisted")

                        e) create_access_token(user.id) → new access JWT
                        f) create_refresh_token(user.id) → new refresh JWT

                        g) return TokenResponse(new tokens)

 5    Frontend          Store new tokens                           React app
                        Retry the original failed request
                        → User never notices the refresh happened

SECURITY: Old refresh token is now blacklisted.
If attacker tries to use the stolen old token → REJECTED.
```

---

<a name="logout-flow"></a>
## 6. Flow 5: Logout

```
STEP  COMPONENT         ACTION                                    FILE
────  ───────────       ──────                                    ────
 1    Browser           POST /api/v1/auth/logout                   —
                        Headers: Authorization: Bearer eyJ...access...

 2    get_current_user_id  Validate token first → uuid-001        router.py
                           (must be logged in to log out!)

 3    Service           service.logout(access_token):              service.py
      .logout()
                        _blacklist_token("eyJ...access..."):
                          a) decode_token → payload with exp
                          b) TTL = exp - now = 1200 sec (20 min remaining)
                          c) redis.setex(
                               "token_blacklist:eyJhbGciOiJIUzI1...",
                               1200,
                               "blacklisted"
                             )

 4    Response          {"message": "Successfully logged out"}     router.py

 5    Frontend          Clear stored tokens                        React app
                        Redirect to login page

AFTER LOGOUT:
  Any request with the blacklisted token:
    get_current_user_id()
      → redis.get("token_blacklist:eyJ...") → "blacklisted"
      → raise TokenInvalidError() → HTTP 401

  After 20 minutes:
    Redis auto-deletes the blacklist entry (TTL expired)
    The token itself is also expired → rejected by JWT expiry check
    No stale data in Redis!
```

---

<a name="error-flows"></a>
## 7. Flow 6: Error Paths

### Signup — Email Already Exists

```
POST /auth/signup {"email": "shreya@test.com", ...}
  → service.register()
    → repo.email_exists("shreya@test.com") → True
    → raise UserAlreadyExistsError()
      → error_handler catches BaseAppError
      → HTTP 409: {"error_code":"EMAIL_ALREADY_EXISTS",
                    "message":"A user with this email already exists"}
```

### Login — Wrong Password

```
POST /auth/login {"email": "shreya@test.com", "password": "wrong"}
  → service.login()
    → repo.get_by_email("shreya@test.com") → User ✅
    → verify_password("wrong", "$2b$12$...") → False ❌
    → raise InvalidCredentialsError()
      → HTTP 401: {"error_code":"INVALID_CREDENTIALS",
                    "message":"Invalid email or password"}
```

### Login — Email Not Found

```
POST /auth/login {"email": "nobody@test.com", "password": "anything"}
  → service.login()
    → repo.get_by_email("nobody@test.com") → None ❌
    → raise InvalidCredentialsError()    ← SAME error as wrong password!
      → HTTP 401: {"error_code":"INVALID_CREDENTIALS",
                    "message":"Invalid email or password"}
```

### Protected Endpoint — Expired Token

```
GET /auth/me  Headers: Authorization: Bearer eyJ...expired...
  → get_current_user_id()
    → decode_token(token, expected_type="access")
      → jwt.decode() → jwt.ExpiredSignatureError
      → raise TokenExpiredError()
        → HTTP 401: {"error_code":"TOKEN_EXPIRED",
                      "message":"Token has expired"}
  → Frontend catches TOKEN_EXPIRED → tries /auth/refresh
```

### Protected Endpoint — No Token

```
GET /auth/me  (no Authorization header)
  → FastAPI: missing required header "authorization"
    → HTTP 422: {"error_code":"VALIDATION_ERROR",
                  "message":"Request validation failed",
                  "detail":["header → authorization: Field required"]}
```

### Rate Limited

```
POST /auth/login (6th attempt in 1 minute)
  → Nginx: login_limit zone exceeded
    → HTTP 429: {"error_code":"RATE_LIMIT_EXCEEDED",
                  "message":"Too many requests. Please slow down."}
  → Never reaches FastAPI!
```

---

<a name="cross-module"></a>
## 8. Cross-Module Dependency Map

The Auth module is used by EVERY other module:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTH MODULE                                    │
│                                                                   │
│  Exports:                                                         │
│  1. get_current_user_id  ← dependency function for protected      │
│                             endpoints                             │
│  2. User model           ← foreign key reference for other tables │
│  3. UserResponse schema  ← response format when returning user    │
│                             data                                  │
└───────────┬───────────────┬──────────────┬───────────────────────┘
            │               │              │
            ▼               ▼              ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Habits Module  │  │  Logs Module   │  │  AI Module     │
│                │  │                │  │                │
│ @router.post() │  │ @router.post() │  │ @router.post() │
│ async def ..   │  │ async def ..   │  │ async def ..   │
│  user_id =     │  │  user_id =     │  │  user_id =     │
│  Depends(      │  │  Depends(      │  │  Depends(      │
│   get_current  │  │   get_current  │  │   get_current  │
│   _user_id)    │  │   _user_id)    │  │   _user_id)    │
│                │  │                │  │                │
│ habits table:  │  │ habit_logs:    │  │ ai_messages:   │
│  user_id FK→   │  │  user_id FK→   │  │  user_id FK→   │
│  users.id      │  │  users.id      │  │  users.id      │
└───────────────┘  └───────────────┘  └───────────────┘

Similarly: Analytics, Notifications, Export modules
           ALL depend on auth's get_current_user_id
```

### How Other Modules Use Auth

```python
# In habits/router.py:
from app.modules.auth.router import get_current_user_id

@router.post("/")
async def create_habit(
    data: HabitCreate,
    user_id: UUID = Depends(get_current_user_id),  # ← From auth module
    service: HabitService = Depends(get_habit_service),
):
    habit = await service.create_habit(user_id, data)
    return HabitResponse.model_validate(habit)
```

The auth dependency is the ONLY connection between modules. Each module is otherwise independent — clean modular architecture.

---

<a name="summary"></a>
## 9. Auth Module Summary

### What You Built (Parts 04a–04f)

| Part | Files | What It Does |
|------|-------|-------------|
| **04a** | models.py, exceptions.py, schemas.py | Data layer — table, errors, API shapes |
| **04b** | security.py | Crypto layer — bcrypt hashing, JWT tokens |
| **04c** | repository.py, service.py | Business layer — CRUD queries, auth rules |
| **04d** | router.py, main.py, nginx/default.conf | HTTP layer — endpoints, app wiring, proxy |
| **04e** | alembic.ini, env.py, 001_migration.py | Database layer — migration tool + first migration |
| **04f** | (this doc) | Architecture — flows, connections, error paths |

### By the Numbers

| Metric | Count |
|--------|-------|
| Python files | 7 (+ 3 infrastructure) |
| Endpoints | 6 |
| Exception classes | 5 |
| Pydantic schemas | 5 |
| Security functions | 5 |
| Repository methods | 3 custom + 5 inherited |
| Service methods | 6 + 1 private |
| Database columns | 8 |
| Design decisions (boxed) | 12 across all parts |
| Interview Q&A | 30+ across all parts |

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04e: Auth Alembic Migrations](./phase4-part04e-auth-alembic-migrations.md) |
| ➡️ Next | [Phase 4 Part 05: Habits Module Overview](./phase4-part05-habits-service-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module — All Sub-Parts Complete ✅

| Sub-Part | Status | Document |
|----------|--------|----------|
| 04a | ✅ Done | Auth Models, Exceptions & Schemas |
| 04b | ✅ Done | Auth Security — JWT & bcrypt |
| 04c | ✅ Done | Auth Repository & Service |
| 04d | ✅ Done | Auth Router, Main & Nginx |
| 04e | ✅ Done | Auth Alembic Migrations |
| **04f** | ✅ **Done** | Auth Connections & Flows |

---

**End of Phase 4 Part 04f: Auth Connections & Flows**

**🎉 The Auth module is COMPLETE.**

*You can now: sign up, log in, refresh tokens, log out, view and update your profile. Every request is authenticated, rate-limited, logged, and properly error-handled. Next: the Habits module — the first feature that users actually interact with.*
