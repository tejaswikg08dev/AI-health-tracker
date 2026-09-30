# 🔐 Phase 4 Part 04: Auth Module — Overview & Roadmap

> **"Authentication is the front door of your application. Get it wrong and the entire house is compromised. Get it right and every room inside is protected."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04 (Auth Module — Overview) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part03-shared-utilities-middleware.md](./phase4-part03-shared-utilities-middleware.md) |
| **Next** | [phase4-part04a-auth-entities-schemas.md](./phase4-part04a-auth-entities-schemas.md) |
| **Module Files** | 7 Python files + 1 Alembic migration + nginx config + main.py updates |
| **Endpoints** | 6 (signup, login, refresh, logout, get profile, update profile) |
| **Sub-Parts** | 6 documents (04a through 04f) |
| **Time to Type** | ~4 hours (across all 6 sub-parts) |
| **Difficulty** | Hard (JWT, bcrypt, token blacklisting, dependency injection) |

---

## 📖 Table of Contents

1. [What Is the Auth Module?](#what-is-auth)
2. [Why Authentication Matters](#why-auth)
3. [How Authentication Works — The Big Picture](#how-auth-works)
4. [Endpoints Overview](#endpoints)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap (What Each Doc Covers)](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Prerequisites — What You Need Before Starting](#prerequisites)
10. [Design Decisions Summary](#design-decisions)
11. [Verification Checklist (After All Sub-Parts)](#verification)
12. [Interview Q&A (Module Level)](#interview)
13. [Navigation](#navigation)

---

<a name="what-is-auth"></a>
## 1. What Is the Auth Module?

The **Auth module** handles everything related to user identity:
- **Who are you?** (Registration — creating an account)
- **Prove it.** (Login — email + password → JWT tokens)
- **Stay logged in.** (Token refresh — get new tokens without re-entering password)
- **Done for now.** (Logout — blacklist tokens so they can't be reused)
- **What's my info?** (Profile — view and update your details)

Every other module in the app depends on Auth. You can't create a habit without knowing WHO is creating it. You can't view logs without knowing WHOSE logs to show. Auth is the foundation that every feature sits on.

### Real-World Analogy

Think of Auth as the **security system of an office building**:

| Auth Concept | Office Building Equivalent |
|-------------|---------------------------|
| **Signup** | Getting your employee ID card made on your first day |
| **Login** | Swiping your ID card at the entrance to get a visitor badge (JWT token) |
| **Access Token** | The visitor badge — expires at 5 PM (30 minutes for our tokens) |
| **Refresh Token** | Your employee ID card — valid for a year, used to get new visitor badges |
| **Logout** | Returning your visitor badge to the front desk (blacklisting the token) |
| **Protected Endpoints** | Doors that only open with a valid visitor badge |
| **Token Blacklist** | A list of returned/cancelled badges that the security system checks |

---

<a name="why-auth"></a>
## 2. Why Authentication Matters

### Without Auth (Insecure):
```
GET /api/v1/habits
→ Returns ALL habits for ALL users  😱
→ Anyone can see anyone's data
→ No way to know WHO is making the request
```

### With Auth (Secure):
```
GET /api/v1/habits
Headers: Authorization: Bearer eyJhbGciOi...
→ JWT token contains user_id=abc-123
→ Query: SELECT * FROM habits WHERE user_id = 'abc-123'
→ Returns ONLY this user's habits  ✅
```

### What Happens Without Proper Auth

| Vulnerability | Impact | Our Protection |
|---------------|--------|----------------|
| No password hashing | Database breach = all passwords exposed | bcrypt with salt (one-way hash) |
| No rate limiting on login | Attacker tries millions of passwords | 5 login attempts per minute |
| Predictable user IDs | Attacker guesses IDs: `/users/1`, `/users/2`... | UUID primary keys (unguessable) |
| No token expiration | Stolen token works forever | Access token expires in 30 minutes |
| No token blacklisting | Logged-out token still works | Redis blacklist checked on every request |
| Same error for email/password | Attacker learns which emails exist | Generic "Invalid credentials" for both |

---

<a name="how-auth-works"></a>
## 3. How Authentication Works — The Big Picture

### Flow 1: User Signup

```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client   │         │  Router   │         │  Service  │         │ Database  │
│ (React)   │         │ (HTTP)    │         │ (Logic)   │         │ (Postgres)│
└─────┬─────┘         └─────┬─────┘         └─────┬─────┘         └─────┬─────┘
      │                     │                     │                     │
      │ POST /auth/signup   │                     │                     │
      │ {email, password,   │                     │                     │
      │  full_name}         │                     │                     │
      │────────────────────>│                     │                     │
      │                     │                     │                     │
      │                     │ Validate with       │                     │
      │                     │ Pydantic schema     │                     │
      │                     │                     │                     │
      │                     │ service.register()  │                     │
      │                     │────────────────────>│                     │
      │                     │                     │                     │
      │                     │                     │ Check email exists?  │
      │                     │                     │────────────────────>│
      │                     │                     │     No (good) ✅    │
      │                     │                     │<────────────────────│
      │                     │                     │                     │
      │                     │                     │ Hash password        │
      │                     │                     │ (bcrypt)            │
      │                     │                     │                     │
      │                     │                     │ INSERT user          │
      │                     │                     │────────────────────>│
      │                     │                     │     Created ✅      │
      │                     │                     │<────────────────────│
      │                     │                     │                     │
      │                     │ UserResponse        │                     │
      │                     │<────────────────────│                     │
      │                     │                     │                     │
      │ 201 Created         │                     │                     │
      │ {id, email,         │                     │                     │
      │  full_name, ...}    │                     │                     │
      │<────────────────────│                     │                     │
```

### Flow 2: User Login

```
┌──────────┐         ┌──────────┐         ┌──────────┐    ┌──────────┐
│  Client   │         │  Router   │         │  Service  │    │  Redis    │
└─────┬─────┘         └─────┬─────┘         └─────┬─────┘    └─────┬─────┘
      │                     │                     │                │
      │ POST /auth/login    │                     │                │
      │ {email, password}   │                     │                │
      │────────────────────>│                     │                │
      │                     │ service.login()     │                │
      │                     │────────────────────>│                │
      │                     │                     │                │
      │                     │                     │ Find user by email
      │                     │                     │ Verify password (bcrypt)
      │                     │                     │ Generate access_token (JWT, 30 min)
      │                     │                     │ Generate refresh_token (JWT, 7 days)
      │                     │                     │                │
      │                     │ TokenResponse       │                │
      │                     │<────────────────────│                │
      │                     │                     │                │
      │ 200 OK              │                     │                │
      │ {access_token,      │                     │                │
      │  refresh_token,     │                     │                │
      │  token_type}        │                     │                │
      │<────────────────────│                     │                │
```

### Flow 3: Accessing a Protected Endpoint

```
┌──────────┐         ┌──────────────┐    ┌──────────┐    ┌──────────┐
│  Client   │         │ get_current_  │    │  Redis    │    │ Service   │
│           │         │ user_id()     │    │ (blacklist)│    │          │
└─────┬─────┘         └──────┬───────┘    └─────┬─────┘    └─────┬─────┘
      │                      │                  │                │
      │ GET /auth/me         │                  │                │
      │ Authorization:       │                  │                │
      │   Bearer eyJ...      │                  │                │
      │─────────────────────>│                  │                │
      │                      │                  │                │
      │                      │ Extract token    │                │
      │                      │ Decode JWT       │                │
      │                      │ Verify signature │                │
      │                      │ Check expiry     │                │
      │                      │                  │                │
      │                      │ Is blacklisted?  │                │
      │                      │─────────────────>│                │
      │                      │      No ✅       │                │
      │                      │<─────────────────│                │
      │                      │                  │                │
      │                      │ user_id = abc-123│                │
      │                      │─────────────────────────────────>│
      │                      │                  │                │
      │                      │    UserResponse  │                │
      │                      │<─────────────────────────────────│
      │                      │                  │                │
      │ 200 OK               │                  │                │
      │ {id, email, ...}     │                  │                │
      │<─────────────────────│                  │                │
```

---

<a name="endpoints"></a>
## 4. Endpoints Overview

| # | Method | Endpoint | Auth Required | Request Body | Response | Status | Purpose |
|---|--------|----------|:-------------:|--------------|----------|--------|---------|
| 1 | `POST` | `/api/v1/auth/signup` | ❌ No | `{email, password, full_name}` | `UserResponse` | `201` | Register new account |
| 2 | `POST` | `/api/v1/auth/login` | ❌ No | `{email, password}` | `TokenResponse` | `200` | Get JWT tokens |
| 3 | `POST` | `/api/v1/auth/refresh` | ❌ No | `{refresh_token}` | `TokenResponse` | `200` | Refresh expired access token |
| 4 | `POST` | `/api/v1/auth/logout` | ✅ Yes | — | `SuccessResponse` | `200` | Blacklist current token |
| 5 | `GET` | `/api/v1/auth/me` | ✅ Yes | — | `UserResponse` | `200` | Get my profile |
| 6 | `PUT` | `/api/v1/auth/me` | ✅ Yes | `{full_name?, timezone?}` | `UserResponse` | `200` | Update my profile |

### Error Responses

| Scenario | Status | Error Code | Triggered By |
|----------|--------|------------|-------------|
| Email already registered | `409` | `EMAIL_ALREADY_EXISTS` | Signup with existing email |
| Wrong email or password | `401` | `INVALID_CREDENTIALS` | Login with bad credentials |
| Token expired | `401` | `TOKEN_EXPIRED` | Using expired access token |
| Token tampered/invalid | `401` | `TOKEN_INVALID` | Using fake or blacklisted token |
| Account deactivated | `401` | `ACCOUNT_DEACTIVATED` | Login with deactivated account |
| Invalid request body | `422` | `VALIDATION_ERROR` | Missing fields, bad email format |
| Too many login attempts | `429` | `RATE_LIMIT_EXCEEDED` | >5 login requests per minute |

---

<a name="file-list"></a>
## 5. File List & Build Order

The Auth module consists of **7 Python files** in `backend/app/modules/auth/`, plus supporting files.

### Module File Structure

```
backend/app/modules/auth/
├── __init__.py           ← Empty — marks as Python package
├── models.py             ← User database model (SQLAlchemy)
├── exceptions.py         ← Auth-specific exception classes
├── schemas.py            ← Request/response Pydantic schemas
├── security.py           ← JWT token + bcrypt password utilities
├── repository.py         ← Database queries (CRUD + custom)
├── service.py            ← Business logic (register, login, refresh, logout)
└── router.py             ← HTTP endpoint definitions (6 endpoints)
```

### Supporting Files (Modified/Created)

```
backend/
├── app/
│   └── main.py               ← Register auth router + middleware
├── alembic/
│   └── versions/
│       └── 001_create_users_table.py  ← Database migration
├── alembic.ini                ← Alembic configuration
└── alembic/
    └── env.py                 ← Alembic environment setup

nginx/
└── default.conf               ← Nginx reverse proxy config
```

### Build Order (Type Files in This Sequence)

| # | File | Doc | Why This Order |
|---|------|-----|---------------|
| 1 | `models.py` | Part 04a | Database table must exist before queries |
| 2 | `exceptions.py` | Part 04a | Service uses these exceptions |
| 3 | `schemas.py` | Part 04a | Router uses these for request/response |
| 4 | `security.py` | Part 04b | Service uses JWT + bcrypt functions |
| 5 | `repository.py` | Part 04c | Service calls repository for DB access |
| 6 | `service.py` | Part 04c | Router calls service for business logic |
| 7 | `router.py` | Part 04d | HTTP layer — calls service, uses schemas |
| 8 | `main.py` (update) | Part 04d | Wire auth router into the app |
| 9 | `nginx/default.conf` | Part 04d | Reverse proxy for API + frontend |
| 10 | `alembic.ini` | Part 04e | Migration tool configuration |
| 11 | `alembic/env.py` | Part 04e | Migration environment setup |
| 12 | `001_create_users_table.py` | Part 04e | Create the users table |

### Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP LAYER                              │
│  router.py — 6 endpoints, thin wrappers around service       │
│  schemas.py — request validation, response formatting        │
├─────────────────────────────────────────────────────────────┤
│                      BUSINESS LAYER                          │
│  service.py — register, login, refresh, logout logic         │
│  security.py — JWT creation/verification, bcrypt hashing     │
│  exceptions.py — domain-specific error types                 │
├─────────────────────────────────────────────────────────────┤
│                      DATA LAYER                              │
│  repository.py — SQL queries (get_by_email, create_user)     │
│  models.py — User table definition (SQLAlchemy ORM)          │
├─────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                          │
│  PostgreSQL (user data) + Redis (token blacklist)             │
│  Alembic migrations + Nginx reverse proxy                    │
└─────────────────────────────────────────────────────────────┘
```

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap (What Each Doc Covers)

### Part 04a: Auth Models, Exceptions & Schemas

```
📄 phase4-part04a-auth-entities-schemas.md
├── models.py         — User database model (8 columns, UUID PK, timestamps)
├── exceptions.py     — 5 auth-specific exceptions (InvalidCredentials, TokenExpired, etc.)
└── schemas.py        — 6 schemas (UserCreate, UserLogin, UserResponse, UserUpdate, TokenResponse, UserInDB)

KEY CONCEPTS: ORM, mapped_column, Pydantic vs SQLAlchemy, EmailStr validation
TIME: ~45 minutes
```

### Part 04b: Auth Security — JWT & Password Hashing

```
📄 phase4-part04b-auth-security-jwt.md
└── security.py       — hash_password, verify_password, create_token, decode_token

KEY CONCEPTS: bcrypt, salt, JWT structure (header.payload.signature), token types
TIME: ~45 minutes
```

### Part 04c: Auth Repository & Service

```
📄 phase4-part04c-auth-repository-service.md
├── repository.py     — UserRepository (inherits BaseRepository, adds get_by_email)
└── service.py        — AuthService (register, login, refresh_tokens, logout, get/update profile)

KEY CONCEPTS: Repository pattern inheritance, business logic vs data access, Redis blacklist
TIME: ~60 minutes
```

### Part 04d: Auth Router, Main App & Nginx

```
📄 phase4-part04d-auth-controller-main-nginx.md
├── router.py         — 6 endpoint definitions with dependency injection
├── main.py (update)  — Wire auth router, middleware, CORS, lifespan
└── nginx/default.conf — Reverse proxy configuration

KEY CONCEPTS: APIRouter, Depends(), get_current_user_id dependency, FastAPI lifespan
TIME: ~60 minutes
```

### Part 04e: Alembic Migrations

```
📄 phase4-part04e-auth-alembic-migrations.md
├── alembic.ini                    — Migration tool config
├── alembic/env.py                 — Migration environment (async support)
└── 001_create_users_table.py      — First migration: CREATE TABLE users

KEY CONCEPTS: What are migrations, why not just CREATE TABLE, upgrade/downgrade, version chain
TIME: ~30 minutes
```

### Part 04f: Auth Connections & Flows

```
📄 phase4-part04f-auth-connections-and-flows.md
├── Signup flow (step-by-step sequence diagram)
├── Login flow (with token generation)
├── Token refresh flow
├── Logout flow (Redis blacklisting)
├── Protected request flow (get_current_user_id dependency)
└── Cross-module dependency map (how Auth connects to Habits, Logs, AI)

KEY CONCEPTS: End-to-end request lifecycle, error paths, security edge cases
TIME: ~30 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

### How the Auth Module Fits in the System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (Port 80)                                 │
│  Routes: /api/* → Backend (Port 8000)                                        │
│          /*     → Frontend (Port 3000)                                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI APPLICATION                                │
│                                                                              │
│  main.py                                                                     │
│  ├── Lifespan: startup (connect DB, Redis, setup logging)                    │
│  ├── Middleware: CORS → Logging → RateLimiter → ErrorHandler                 │
│  └── Routers:                                                                │
│      ├── /api/v1/auth/*    ← AUTH MODULE (this module) 🔐                    │
│      ├── /api/v1/habits/*  ← Habits Module (needs auth)                      │
│      ├── /api/v1/logs/*    ← Logs Module (needs auth)                        │
│      ├── /api/v1/analytics/* ← Analytics Module (needs auth)                 │
│      └── /api/v1/ai/*     ← AI Module (needs auth)                          │
│                                                                              │
│  ┌───────────────────── AUTH MODULE ──────────────────────┐                  │
│  │                                                         │                  │
│  │  router.py ──→ service.py ──→ repository.py ──→ models.py                │
│  │      │              │              │                     │                  │
│  │      │              │              └── PostgreSQL         │                  │
│  │      │              │                                    │                  │
│  │      │              ├── security.py (JWT + bcrypt)        │                  │
│  │      │              └── Redis (token blacklist)           │                  │
│  │      │                                                   │                  │
│  │      └── schemas.py (validation) + exceptions.py         │                  │
│  └─────────────────────────────────────────────────────────┘                  │
│                                                                              │
│  OTHER MODULES use auth's get_current_user_id dependency:                    │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  @router.get("/habits")                                               │    │
│  │  async def list_habits(user_id: UUID = Depends(get_current_user_id)): │    │
│  │      # user_id extracted from JWT token                               │    │
│  │      habits = await service.get_habits(user_id)                       │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                              │
                    ▼                              ▼
           ┌───────────────┐              ┌───────────────┐
           │  PostgreSQL    │              │    Redis       │
           │  - users table │              │  - token       │
           │  - habits      │              │    blacklist   │
           │  - logs        │              │  - rate limits │
           │  - analytics   │              │  - cache       │
           └───────────────┘              └───────────────┘
```

### Auth Module Internal Flow

```
                    ┌──────────────┐
                    │   schemas.py  │ ← Validates request data
                    │  UserCreate   │    (email format, password length)
                    │  UserLogin    │
                    │  UserResponse │ ← Formats response (hides password)
                    └──────┬───────┘
                           │ used by
                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  router.py    │───>│  service.py   │───>│ repository.py │
│  6 endpoints  │    │  Business     │    │  SQL queries   │
│               │    │  Logic        │    │  (CRUD + find  │
│  HTTP in/out  │    │  (register,   │    │   by email)    │
│               │    │   login,      │    └──────┬─────────┘
│  Depends()    │    │   refresh,    │           │
│  injection    │    │   logout)     │           ▼
└───────────────┘    └──────┬───────┘    ┌──────────────┐
                           │             │   models.py   │
                           │             │   User table  │
                           │             │  (SQLAlchemy) │
                    uses   │             └──────────────┘
                           ▼
                    ┌──────────────┐    ┌──────────────┐
                    │ security.py   │    │ exceptions.py │
                    │  - bcrypt     │    │  - InvalidCred│
                    │  - JWT create │    │  - TokenExpired│
                    │  - JWT decode │    │  - UserExists  │
                    └──────────────┘    └──────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **ORM (Object-Relational Mapping)** | Python classes that represent database tables | `models.py` |
| 2 | **`mapped_column()`** | SQLAlchemy 2.0 way to define table columns | `models.py` |
| 3 | **UUID Primary Keys** | Globally unique, unguessable identifiers | `models.py` |
| 4 | **Pydantic Validation** | Auto-validate request data (email format, string length) | `schemas.py` |
| 5 | **`EmailStr`** | Pydantic type that validates email format | `schemas.py` |
| 6 | **bcrypt Password Hashing** | One-way hash — even DB admins can't see passwords | `security.py` |
| 7 | **Salt** | Random data added before hashing — prevents rainbow table attacks | `security.py` |
| 8 | **JWT (JSON Web Token)** | Stateless authentication token (header.payload.signature) | `security.py` |
| 9 | **Access Token vs Refresh Token** | Short-lived (30 min) vs long-lived (7 days) tokens | `security.py` |
| 10 | **Token Blacklisting** | Store logged-out tokens in Redis — prevent reuse | `service.py` |
| 11 | **Repository Pattern (Inheritance)** | `UserRepository(BaseRepository[User])` — extends CRUD | `repository.py` |
| 12 | **Service Layer** | Business logic separated from HTTP and database concerns | `service.py` |
| 13 | **`Depends()` (Dependency Injection)** | FastAPI automatically provides services, sessions, user_id | `router.py` |
| 14 | **`Annotated` Type Hints** | Modern Python way to combine type + metadata | `router.py` |
| 15 | **Alembic Migrations** | Version-controlled database schema changes | `001_create_users_table.py` |
| 16 | **Nginx Reverse Proxy** | Routes traffic: `/api/*` → backend, `/*` → frontend | `nginx/default.conf` |
| 17 | **CORS (Cross-Origin Resource Sharing)** | Allows frontend (port 3000) to call backend (port 8000) | `main.py` |
| 18 | **Lifespan Events** | Setup/teardown code that runs on app start/stop | `main.py` |

---

<a name="prerequisites"></a>
## 9. Prerequisites — What You Need Before Starting

### Must Be Completed

| # | Prerequisite | Document | What It Gives You |
|---|-------------|----------|-------------------|
| 1 | Docker environment | [Part 01](./phase4-part01-project-setup-docker.md) | PostgreSQL + Redis running |
| 2 | Backend foundation | [Part 02](./phase4-part02-backend-foundation.md) | config.py, database.py, redis_client.py, dependencies.py |
| 3 | Shared utilities | [Part 03](./phase4-part03-shared-utilities-middleware.md) | exceptions.py, base_schemas.py, base_repository.py, logging.py, middleware |

### Verify Prerequisites

```bash
# Ensure Docker services are running
docker-compose ps
# Should show: postgres, redis, backend — all "Up"

# Ensure database connection works
docker-compose exec backend python -c "
from app.database import get_async_session
print('✅ Database connection configured')
"

# Ensure Redis connection works
docker-compose exec backend python -c "
from app.redis_client import get_redis_client
print('✅ Redis connection configured')
"

# Ensure shared modules import
docker-compose exec backend python -c "
from app.shared.exceptions import UnauthorizedError, ConflictError
from app.shared.base_repository import BaseRepository
from app.shared.base_schemas import BaseSchema, PaginatedResponse
print('✅ All shared modules import correctly')
"
```

---

<a name="design-decisions"></a>
## 10. Design Decisions Summary

These decisions are explained in detail in the sub-part docs. This is a quick reference.

### Decision 1: JWT vs Session-Based Authentication

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Authentication Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: JWT (JSON Web Tokens) — stateless authentication           │
│                                                                     │
│  WHY:                                                               │
│  • Stateless — no session storage needed on the server              │
│  • Scalable — works with multiple server instances (no sticky        │
│    sessions needed behind load balancer)                            │
│  • Mobile-friendly — tokens stored in client, sent with every req   │
│  • Microservice-ready — any service can verify the token            │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Server-side sessions (stored in Redis/DB)                       │
│     ❌ Requires session storage, sticky sessions with LB           │
│  2. OAuth2 with external provider only (Google, GitHub)             │
│     ❌ No email/password option, dependency on third party         │
│  3. API keys (like Stripe)                                          │
│     ❌ Meant for service-to-service, not user authentication       │
│                                                                     │
│  TRADE-OFF: JWT can't be invalidated without a blacklist.           │
│  We use Redis blacklist to handle logout/token revocation.          │
│                                                                     │
│  INTERVIEW TIP: "We chose JWT for stateless auth that scales        │
│  horizontally. The trade-off is that JWTs can't be revoked          │
│  natively, so we maintain a Redis blacklist for logout."            │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: Access + Refresh Token Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Token Strategy                                    │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Dual token — short-lived access (30 min) + long-lived      │
│          refresh (7 days)                                           │
│                                                                     │
│  WHY:                                                               │
│  • Access token is short → if stolen, attacker has limited time     │
│  • Refresh token is long → user doesn't re-enter password daily     │
│  • On refresh, old tokens are blacklisted → limits damage window    │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Single long-lived token (7 days)                                │
│     ❌ If stolen, attacker has access for a week                   │
│  2. Single short-lived token (30 min, user re-logs every 30 min)    │
│     ❌ Terrible UX — users hate re-entering passwords              │
│  3. Sliding window (extend expiry on each use)                      │
│     ❌ Token never expires if used continuously — stolen = forever  │
│                                                                     │
│  INTERVIEW TIP: "Access tokens expire in 30 minutes to limit the   │
│  blast radius of token theft. Refresh tokens last 7 days for UX.    │
│  On refresh, we rotate both tokens and blacklist the old ones."     │
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 3: bcrypt vs Argon2 for Password Hashing

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Password Hashing Algorithm                        │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: bcrypt (via passlib library)                               │
│                                                                     │
│  WHY:                                                               │
│  • Industry standard for 20+ years — battle-tested                  │
│  • Built-in salt generation — prevents rainbow table attacks        │
│  • Configurable cost factor — can increase as hardware improves     │
│  • Widely supported — every language has a bcrypt library           │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Argon2 (winner of Password Hashing Competition 2015)            │
│     ⚠️ More secure (memory-hard) but less library support           │
│     (We'd use this for a new project in 2026 — bcrypt is fine)     │
│  2. SHA-256 / MD5                                                   │
│     ❌ NOT designed for passwords. Too fast = easy to brute-force  │
│  3. PBKDF2                                                          │
│     ⚠️ Fine but bcrypt is more commonly used in Python ecosystem   │
│                                                                     │
│  INTERVIEW TIP: "We use bcrypt because it's purpose-built for       │
│  passwords — it's intentionally slow (configurable rounds) to       │
│  resist brute-force attacks, and includes automatic salt             │
│  generation to prevent rainbow table attacks."                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verification"></a>
## 11. Verification Checklist (After All Sub-Parts)

Complete this checklist after finishing all 6 sub-parts (04a through 04f).

### API Tests with curl

```bash
# 1. Signup
curl -X POST http://localhost/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#","full_name":"Shreya"}'
# Expected: 201 Created with user data

# 2. Login
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}'
# Expected: 200 with access_token and refresh_token

# 3. Get Profile (replace TOKEN with actual access_token from login)
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 with user profile

# 4. Update Profile
curl -X PUT http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Shreya V","timezone":"Asia/Kolkata"}'
# Expected: 200 with updated profile

# 5. Refresh Token (replace REFRESH_TOKEN with actual refresh_token from login)
curl -X POST http://localhost/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '"REFRESH_TOKEN"'
# Expected: 200 with new access_token and refresh_token

# 6. Logout
curl -X POST http://localhost/api/v1/auth/logout \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 with success message

# 7. Verify logout worked (use the same token)
curl http://localhost/api/v1/auth/me \
  -H "Authorization: Bearer TOKEN"
# Expected: 401 (token is blacklisted)
```

### Checklist

- [ ] Signup creates user in database
- [ ] Login returns valid JWT tokens
- [ ] Access token expires after 30 minutes
- [ ] Refresh token generates new token pair
- [ ] Logout blacklists the token in Redis
- [ ] Blacklisted token is rejected
- [ ] Invalid email format returns 422
- [ ] Duplicate email returns 409
- [ ] Wrong password returns 401 (generic "Invalid credentials")
- [ ] Protected endpoints reject requests without token
- [ ] Rate limiter blocks after 5 login attempts per minute
- [ ] Alembic migration creates users table correctly
- [ ] Nginx proxies `/api/*` to backend correctly

---

<a name="interview"></a>
## 12. Interview Q&A (Module Level)

### Q1: Walk me through your authentication flow.
**A:** "The user signs up with email, password, and name. The password is hashed with bcrypt before storage — we never store plain text. On login, we verify the password against the hash and generate two JWT tokens: an access token (30 minutes) and a refresh token (7 days). The access token is sent with every API request in the Authorization header. When it expires, the frontend uses the refresh token to get a new pair. On logout, we blacklist the access token in Redis with a TTL matching its remaining lifetime. Every protected endpoint uses a `get_current_user_id` dependency that decodes the JWT, verifies the signature, checks the Redis blacklist, and extracts the user ID."

### Q2: Why JWT instead of session-based auth?
**A:** "JWT is stateless — the server doesn't need to store session data. This makes horizontal scaling straightforward: any server behind the load balancer can verify any token because the verification only needs the secret key, not a database lookup. Sessions require either sticky sessions (all requests from one user go to the same server) or a shared session store (Redis), adding complexity. The trade-off is that JWTs can't be instantly invalidated, which is why we maintain a Redis blacklist for logout."

### Q3: What security measures did you implement?
**A:** "Five main measures: (1) bcrypt password hashing with automatic salting — even database admins can't see passwords. (2) JWT with HS256 signature — tokens can't be tampered with. (3) Token blacklisting via Redis — logged-out tokens are immediately invalidated. (4) Rate limiting — 5 login attempts per minute to prevent brute-force. (5) Generic error messages — 'Invalid credentials' for both wrong email and wrong password, so attackers can't enumerate registered emails. Plus: UUIDs as primary keys (no sequential ID guessing), password minimum length validation, and CORS restrictions."

### Q4: How do you handle token expiration gracefully?
**A:** "The access token expires in 30 minutes. When the frontend receives a 401 with error code `TOKEN_EXPIRED`, it automatically sends the refresh token to `/auth/refresh`. If the refresh token is still valid (7-day lifetime), the backend issues a new token pair, the frontend stores them, and retries the failed request — seamless to the user. If the refresh token is also expired, the frontend redirects to the login page. This pattern is called 'silent refresh' and is used by most modern SPAs."

### Q5: How does the dependency injection work in FastAPI for auth?
**A:** "FastAPI uses `Depends()` to inject dependencies. We define `get_current_user_id` as a dependency function that extracts and validates the JWT from the Authorization header, checks the Redis blacklist, and returns the user UUID. Any endpoint that needs authentication just adds `user_id: UUID = Depends(get_current_user_id)` as a parameter. FastAPI automatically calls the dependency before the handler, and if it raises an exception (invalid token), the handler never runs. This same dependency is reused across ALL modules — Habits, Logs, Analytics, AI — without duplicating auth logic."

### Q6: What is the difference between authentication and authorization?
**A:** "Authentication verifies WHO you are (login, tokens). Authorization verifies WHAT you're allowed to do (permissions, roles). Our auth module handles authentication — confirming the user's identity via JWT. Authorization is simpler in our app: each user can only access their own data. The `get_current_user_id` dependency provides the user_id, and every query filters by that user_id. We don't have role-based access control (RBAC) because we don't have admin users, but the architecture supports adding it — you'd extend the User model with a `role` column and add a `require_role('admin')` dependency."

---

<a name="navigation"></a>
## 13. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 03: Shared Utilities & Middleware](./phase4-part03-shared-utilities-middleware.md) |
| ➡️ Next | [Phase 4 Part 04a: Auth Models, Exceptions & Schemas](./phase4-part04a-auth-entities-schemas.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Sub-Part Quick Links

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 04a | [Auth Models, Exceptions & Schemas](./phase4-part04a-auth-entities-schemas.md) | models.py + exceptions.py + schemas.py |
| 04b | [Auth Security — JWT & bcrypt](./phase4-part04b-auth-security-jwt.md) | security.py |
| 04c | [Auth Repository & Service](./phase4-part04c-auth-repository-service.md) | repository.py + service.py |
| 04d | [Auth Router, Main & Nginx](./phase4-part04d-auth-controller-main-nginx.md) | router.py + main.py + nginx |
| 04e | [Auth Alembic Migrations](./phase4-part04e-auth-alembic-migrations.md) | alembic.ini + env.py + migration |
| 04f | [Auth Connections & Flows](./phase4-part04f-auth-connections-and-flows.md) | Sequence diagrams for all flows |

---

**End of Phase 4 Part 04: Auth Module Overview**

*You now understand WHAT the Auth module does, WHY each piece exists, and HOW they connect. Next, start building: Part 04a covers the data layer — User model, auth exceptions, and request/response schemas.*
