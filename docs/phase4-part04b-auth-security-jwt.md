# 🔑 Phase 4 Part 04b: Auth Security — JWT & Password Hashing

> **"If someone asks you 'How does JWT work?' in an interview and you can explain header, payload, signature, secret key, and token expiry — you've already passed. This file is where that knowledge lives."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 04b (Auth Security Layer) |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Authentication & Authorization |
| **Previous** | [phase4-part04a-auth-entities-schemas.md](./phase4-part04a-auth-entities-schemas.md) |
| **Next** | [phase4-part04c-auth-repository-service.md](./phase4-part04c-auth-repository-service.md) |
| **Files in This Doc** | 1 file (security.py) — but 4 critical functions |
| **Endpoints** | 0 (utility functions used by the service layer) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Hard (cryptography concepts, JWT internals, security best practices) |

---

## 📖 Table of Contents

1. [What We're Building in This Part](#overview)
2. [Concept Deep Dive: Password Hashing](#password-hashing)
3. [Concept Deep Dive: JWT (JSON Web Token)](#jwt-concept)
4. [File: security.py — Full Source Code](#security-code)
5. [Line-by-Line Explanation](#line-by-line)
6. [How JWT Tokens Look Inside](#jwt-anatomy)
7. [Design Decisions](#design-decisions)
8. [How to Verify Your Work](#verify)
9. [What You Learned](#what-you-learned)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building in This Part

This file contains **4 functions** that are the security backbone of the entire application:

| # | Function | What It Does | When Called |
|---|----------|-------------|------------|
| 1 | `hash_password()` | Converts plain text → bcrypt hash | Signup |
| 2 | `verify_password()` | Checks if plain text matches stored hash | Login |
| 3 | `create_access_token()` | Generates a short-lived JWT (30 min) | Login, Token refresh |
| 4 | `create_refresh_token()` | Generates a long-lived JWT (7 days) | Login, Token refresh |
| 5 | `decode_token()` | Verifies and extracts data from a JWT | Every protected request |

These functions are **pure utilities** — they don't touch the database or know about HTTP. They take input, do cryptographic operations, and return output. The service layer calls them.

### File Structure

```
backend/app/modules/auth/
├── models.py       ← Part 04a ✅
├── exceptions.py   ← Part 04a ✅
├── schemas.py      ← Part 04a ✅
├── security.py     ← THIS PART (you are here) 🔑
├── repository.py   ← Part 04c (next)
├── service.py      ← Part 04c (next)
└── router.py       ← Part 04d
```

---

<a name="password-hashing"></a>
## 2. Concept Deep Dive: Password Hashing

### Why Not Store Plain Text Passwords?

If your database gets breached (it happens — even to [LinkedIn, Adobe, Yahoo](https://haveibeenpwned.com/)):

```
PLAIN TEXT (catastrophic):
  email: shreya@test.com, password: MySecret123
  → Attacker has the actual password
  → Shreya probably uses this password on 5 other sites
  → All her accounts are compromised

HASHED (safe):
  email: shreya@test.com, password_hash: $2b$12$LJ3m4ys4Rz6...
  → Attacker has a hash — can't reverse it to get the password
  → Even if they try 1 billion guesses, bcrypt is so slow it takes years
```

### How Hashing Works

```
            ┌───────────────┐
"MySecret"  │   Hash        │  "$2b$12$LJ3m4ys4Rz6..."
  ────────> │   Function    │  ────────>
            │   (bcrypt)    │
            └───────────────┘

  ONE-WAY: You can go forward (password → hash)
           You CANNOT go backward (hash → password)
           This is NOT encryption (encryption is two-way)
```

### What Is a Salt?

A **salt** is random data added to the password BEFORE hashing.

```
WITHOUT salt:
  "MySecret" → hash → "abc123"
  "MySecret" → hash → "abc123"    ← Same password = same hash!
  → Attacker builds a "rainbow table": precomputed hash → password mappings
  → Look up "abc123" in the table → "MySecret" found instantly

WITH salt (what bcrypt does):
  "MySecret" + salt "x7Kp" → hash → "def456"
  "MySecret" + salt "mN2q" → hash → "ghi789"    ← Same password, DIFFERENT hash!
  → Rainbow table is useless — every hash is unique
  → Attacker must brute-force EACH hash individually
```

bcrypt generates a unique random salt for EVERY password. The salt is stored as part of the hash:

```
$2b$12$LJ3m4ys4Rz6YEoQKN7e3/.vG8kW2hQhKFS0hF7Rcx7sJUz1D7Xm6C
 │   │  │                      │
 │   │  │                      └── Hash output (31 chars)
 │   │  └── Salt (22 chars, unique per password)
 │   └── Cost factor: 2^12 = 4,096 iterations
 └── Algorithm: bcrypt
```

### Why bcrypt Is Intentionally Slow

Most hash functions (MD5, SHA-256) are designed to be **fast** — millions of hashes per second. That's great for file verification, but terrible for passwords:

```
SHA-256: 10 billion hashes/second on a GPU
  → 8-character password cracked in ~2 hours

bcrypt (cost=12): ~4,000 hashes/second on same GPU
  → 8-character password takes ~700 YEARS to crack
```

bcrypt is **intentionally slow** — the `cost factor` (12 by default) controls how many iterations the algorithm runs. Higher cost = slower = more secure. As hardware gets faster, increase the cost.

---

<a name="jwt-concept"></a>
## 3. Concept Deep Dive: JWT (JSON Web Token)

### What Is JWT?

A **JWT** is a compact, self-contained token that proves a user's identity. It's a string that looks like this:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhYmMtMTIzIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTcyNzM2MDgwMH0.K4p_2SvHqL8X_mZ1dR9yQ3N7wF5tJ8vGcYnK0bL1sM0
```

It has **three parts** separated by dots (`.`):

```
HEADER.PAYLOAD.SIGNATURE

┌─────────────────────────────────────────────────────────────────┐
│  PART 1: HEADER (metadata)                                       │
│  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9                          │
│  Base64 decode → {"alg": "HS256", "typ": "JWT"}                 │
│                                                                   │
│  alg: Algorithm used for the signature (HS256 = HMAC + SHA-256)  │
│  typ: Token type (always "JWT")                                   │
├─────────────────────────────────────────────────────────────────┤
│  PART 2: PAYLOAD (data — NOT encrypted, just base64 encoded!)    │
│  eyJzdWIiOiJhYmMtMTIzIi...                                      │
│  Base64 decode → {"sub": "abc-123", "type": "access",            │
│                   "exp": 1727360800, "iat": 1727359000}          │
│                                                                   │
│  sub: Subject (user_id — who this token belongs to)               │
│  type: "access" or "refresh"                                      │
│  exp: Expiry timestamp (token invalid after this time)            │
│  iat: Issued-at timestamp (when token was created)                │
├─────────────────────────────────────────────────────────────────┤
│  PART 3: SIGNATURE (tamper protection)                            │
│  K4p_2SvHqL8X_mZ1dR9yQ3N7wF5tJ8vGcYnK0bL1sM0                  │
│                                                                   │
│  Created by: HMAC-SHA256(header + "." + payload, SECRET_KEY)     │
│                                                                   │
│  Only our server knows SECRET_KEY → only we can create valid      │
│  signatures. If someone changes the payload, the signature        │
│  won't match → token rejected.                                    │
└─────────────────────────────────────────────────────────────────┘
```

### CRITICAL: JWT Is NOT Encrypted

Anyone can **read** the payload (it's just base64). Don't put secrets in it!

```python
import base64
token = "eyJhbGciOiJIUzI1NiIs..."
payload_b64 = token.split(".")[1]
payload = base64.b64decode(payload_b64 + "==")
# {"sub": "abc-123", "type": "access", "exp": 1727360800}
# Anyone can see the user_id!
```

JWT doesn't hide data — it **proves the data hasn't been tampered with**. The signature guarantees: "This token was created by our server, and nobody has modified it."

### Access Token vs Refresh Token

```
┌───────────────────────────────────────────────────────────────┐
│                    ACCESS TOKEN                                │
│  Lifetime: 30 minutes                                          │
│  Sent: with EVERY API request (Authorization: Bearer ...)      │
│  Purpose: prove "I am user abc-123"                            │
│  If stolen: attacker has 30 minutes of access                  │
│  Storage: memory/localStorage (frontend)                       │
├───────────────────────────────────────────────────────────────┤
│                    REFRESH TOKEN                               │
│  Lifetime: 7 days                                              │
│  Sent: ONLY to /auth/refresh endpoint                          │
│  Purpose: get a new access token without re-entering password  │
│  If stolen: attacker can generate new access tokens for 7 days │
│  Storage: httpOnly cookie or secure storage (frontend)          │
│  Extra protection: blacklisted on logout, rotated on refresh   │
└───────────────────────────────────────────────────────────────┘

FLOW:
  Login → get access_token (30 min) + refresh_token (7 days)
  ... 30 minutes later ...
  API call → 401 TOKEN_EXPIRED
  Frontend → POST /auth/refresh with refresh_token
  Server → new access_token + new refresh_token (old blacklisted)
  ... continues for 7 days without re-login ...
```

---

<a name="security-code"></a>
## 4. File: `security.py` — Full Source Code

### Type This Code: `backend/app/modules/auth/security.py`

```python
# ============================================================================
# Auth Module — Security Utilities (JWT + Password Hashing)
# ============================================================================
# WHAT THIS FILE DOES:
#   1. Password hashing — convert plain text password to bcrypt hash
#   2. Password verification — check if plain text matches the hash
#   3. JWT token creation — generate access and refresh tokens
#   4. JWT token decoding — verify and extract data from tokens
#
# HOW PASSWORD HASHING WORKS:
#   Password: "mySecurePass123"
#   Hash: "$2b$12$LJ3m4ys4Rz6YEoQKN7e3/.vG8kW2hQhKFS0hF7Rcx7sJUz1D7Xm6C"
#
#   The hash is ONE-WAY — you cannot reverse it to get the password.
#   To verify, you hash the attempt and compare hashes.
#   Even the database admin cannot see user passwords.
#
# HOW JWT WORKS:
#   JWT = Header.Payload.Signature (three parts, base64-encoded, dot-separated)
#   - Header: algorithm used (HS256)
#   - Payload: user data (user_id, expiry time)
#   - Signature: HMAC(header + payload, SECRET_KEY)
#
#   Anyone can READ the payload (it's just base64, not encrypted).
#   But only our server can CREATE a valid signature (needs SECRET_KEY).
#   If someone tampers with the payload, the signature won't match → rejected.
#
# INTERVIEW GOLD:
#   "How does JWT work?" is asked in 70%+ of backend interviews.
#   Understanding this file = understanding the answer.
# ============================================================================

from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError

settings = get_settings()

# ── Password Hashing Context ──
# bcrypt is the industry standard for password hashing.
# It's intentionally SLOW (takes ~100ms per hash) — this makes
# brute-force attacks impractical (billions of years to crack).
#
# "deprecated='auto'" means: if we switch algorithms in the future,
# old hashes still verify correctly, and new passwords use the new algorithm.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Called during: user registration (signup).

    Example:
        hash_password("mySecurePass123")
        → "$2b$12$LJ3m4ys4Rz6YEoQKN7e3/.vG8kW2hQhKFS0hF7Rcx7sJUz1D7Xm6C"

    The hash includes:
        $2b$   → bcrypt algorithm identifier
        12$    → cost factor (2^12 = 4096 iterations — higher = slower = more secure)
        LJ3... → 22-char salt (random, auto-generated, unique per hash)
        vG8... → 31-char hash output
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain text password matches the stored hash.

    Called during: login.

    HOW IT WORKS:
        1. Extract the salt from the stored hash
        2. Hash the plain_password with that same salt
        3. Compare the result with the stored hash
        4. Return True if they match, False if not

    We NEVER compare plain text passwords.
    We NEVER decrypt the hash (it's not encryption, it's hashing — one-way).
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID) -> str:
    """
    Create a short-lived JWT access token.

    This token is sent with EVERY API request in the Authorization header.
    Short-lived (30 min default) — if stolen, damage is limited.

    Payload contents:
        sub: user ID (subject — standard JWT claim name)
        type: "access" (distinguishes from refresh token)
        exp: expiry timestamp (after this, token is rejected)
        iat: issued-at timestamp (when the token was created)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),       # Subject — who this token belongs to
        "type": "access",          # Token type — prevents using refresh as access
        "exp": expire,             # Expiry — after this, token is invalid
        "iat": now,                # Issued at — when token was created
    }

    # Sign the payload with our SECRET_KEY
    # Only our server can create valid tokens (needs the key)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """
    Create a long-lived JWT refresh token.

    This token is used ONLY to get a new access token when the old one expires.
    Long-lived (7 days default) — so users don't have to login every 30 minutes.

    SECURITY:
    - Stored in httpOnly cookie or secure frontend storage
    - Sent ONLY to /auth/refresh endpoint (not with every request)
    - Can be blacklisted on logout (stored in Redis)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "type": "refresh",         # MUST be "refresh" — not valid as access token
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict:
    """
    Decode and validate a JWT token.

    Steps:
        1. Decode the token (verify signature with SECRET_KEY)
        2. Check expiry (jwt library does this automatically)
        3. Verify token type matches expected_type
        4. Return the payload (contains user_id, type, expiry)

    Raises:
        TokenExpiredError: if the token's exp claim is in the past
        TokenInvalidError: if the token is malformed, tampered, or wrong type

    Args:
        token: The JWT string from the Authorization header
        expected_type: "access" or "refresh" — prevents token type confusion
    """
    try:
        # jwt.decode verifies:
        # 1. Signature is valid (not tampered)
        # 2. Token is not expired (exp claim)
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Verify token type — prevent using a refresh token as an access token
        token_type = payload.get("type")
        if token_type != expected_type:
            raise TokenInvalidError()

        # Verify subject (user_id) exists
        if not payload.get("sub"):
            raise TokenInvalidError()

        return payload

    except jwt.ExpiredSignatureError:
        # Token was valid but has expired
        raise TokenExpiredError()
    except JWTError:
        # Token is malformed, tampered with, or has invalid signature
        raise TokenInvalidError()
```

---

<a name="line-by-line"></a>
## 5. Line-by-Line Explanation

### Imports

```python
from datetime import datetime, timedelta, timezone
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError
```

- `datetime, timedelta, timezone` — for calculating token expiry times. `timedelta(minutes=30)` creates a 30-minute duration
- `UUID` — user IDs are UUIDs. We convert to string for the JWT payload (`str(user_id)`)
- `jose` — the `python-jose` library. Handles JWT encoding/decoding. `jwt.encode()` creates tokens, `jwt.decode()` verifies them
- `JWTError` — base exception for all JWT-related errors (malformed, tampered, wrong algorithm)
- `CryptContext` — from `passlib`. A smart wrapper around password hashing algorithms. Handles bcrypt, salt generation, algorithm migration
- `get_settings` — loads our configuration (SECRET_KEY, expiry times, algorithm)
- `TokenExpiredError, TokenInvalidError` — our custom exceptions from Part 04a

### Password Hashing Context

```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

- `CryptContext` — a passlib feature that manages hashing algorithms
- `schemes=["bcrypt"]` — use bcrypt as the current hashing algorithm
- `deprecated="auto"` — **migration support**. If you later add `schemes=["argon2", "bcrypt"]`, new passwords use argon2, but old bcrypt hashes still verify correctly. This is how you upgrade hashing algorithms without forcing all users to change passwords
- This is a **module-level variable** (created once when the file loads), not inside a function. Creating a `CryptContext` is expensive — we reuse it

### `hash_password()` — Lines 52-67

```python
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```

- Takes plain text password, returns bcrypt hash
- `pwd_context.hash()` does ALL the work:
  1. Generates a random 16-byte salt
  2. Combines password + salt
  3. Runs bcrypt with 2^12 iterations (configurable via cost factor)
  4. Returns the hash string including algorithm identifier, cost, salt, and hash
- **One line. One call. That's it.** But behind it: cryptographically secure random number generation, 4,096 iterations of the Blowfish cipher, and a carefully designed output format

### `verify_password()` — Lines 70-83

```python
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

- `plain_password` — what the user typed in the login form
- `hashed_password` — what's stored in the database
- `pwd_context.verify()`:
  1. Extracts the salt from `hashed_password` (it's embedded in the hash string)
  2. Hashes `plain_password` with that same salt
  3. Compares the result with `hashed_password`
  4. Returns `True` if they match
- **Why not `plain_password == stored_password`?** We don't HAVE the stored password. We have a hash. You can't reverse a hash. So we hash the attempt with the same salt and compare hashes

### `create_access_token()` — Lines 86-109

```python
def create_access_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

- `datetime.now(timezone.utc)` — current time in UTC (timezone-aware). Tokens use UTC to avoid timezone confusion
- `timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)` — creates a duration. Default: 30 minutes. `now + timedelta(minutes=30)` = 30 minutes from now
- **Payload fields (JWT "claims"):**
  - `"sub"` — "subject" (standard JWT claim name, defined in RFC 7519). Contains the user_id as a string. When decoding, we convert back: `UUID(payload["sub"])`
  - `"type"` — custom claim: "access" or "refresh". Prevents token type confusion (using a refresh token as an access token)
  - `"exp"` — "expiration time" (standard claim). The `jose` library automatically rejects tokens past this time
  - `"iat"` — "issued at" (standard claim). When the token was created. Useful for debugging and audit
- `jwt.encode(payload, SECRET_KEY, algorithm="HS256")`:
  1. JSON-encodes the header: `{"alg": "HS256", "typ": "JWT"}`
  2. JSON-encodes the payload
  3. Base64url-encodes both
  4. Creates signature: `HMAC-SHA256(base64(header) + "." + base64(payload), SECRET_KEY)`
  5. Returns: `base64(header) + "." + base64(payload) + "." + base64(signature)`
- `settings.JWT_ALGORITHM` — "HS256" (HMAC with SHA-256). Symmetric algorithm: same key for signing and verifying

### `create_refresh_token()` — Lines 112-131

```python
def create_refresh_token(user_id: UUID) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # ... same structure, but type="refresh" and longer expiry
```

- Almost identical to `create_access_token`, but:
  - `type` is `"refresh"` (not `"access"`)
  - Expiry is `REFRESH_TOKEN_EXPIRE_DAYS` (7 days default, not 30 minutes)
- The `type` claim is CRITICAL. Without it, someone could use a refresh token in the `Authorization` header and bypass the short expiry of access tokens

### `decode_token()` — Lines 134-175

```python
def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        token_type = payload.get("type")
        if token_type != expected_type:
            raise TokenInvalidError()

        if not payload.get("sub"):
            raise TokenInvalidError()

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise TokenInvalidError()
```

- `jwt.decode()` does THREE things:
  1. **Verify signature** — recomputes `HMAC-SHA256(header.payload, SECRET_KEY)` and compares with the token's signature. If they don't match, the token was tampered with
  2. **Check expiry** — if `exp` is in the past, raises `ExpiredSignatureError`
  3. **Decode payload** — returns the payload as a Python dict
- `expected_type` check — prevents **token type confusion attack**:
  - Without this: attacker gets a refresh token (long-lived) and uses it as an access token
  - With this: `decode_token(refresh_token, expected_type="access")` → types don't match → rejected
- `payload.get("sub")` — verify the user_id exists. A token without a subject is malformed
- **Exception handling:**
  - `jwt.ExpiredSignatureError` → `TokenExpiredError` (401, code: `TOKEN_EXPIRED`). Frontend can try refreshing
  - `JWTError` (any other error) → `TokenInvalidError` (401, code: `TOKEN_INVALID`). Frontend redirects to login

---

<a name="jwt-anatomy"></a>
## 6. How JWT Tokens Look Inside

### Decoding a Real Token

You can paste any JWT token at [jwt.io](https://jwt.io) to see its contents. Here's what our tokens look like:

```
ACCESS TOKEN (30 minutes):
┌─────────────────────────────────────────────────┐
│ HEADER (base64 decoded):                         │
│ {                                                │
│   "alg": "HS256",                                │
│   "typ": "JWT"                                   │
│ }                                                │
├─────────────────────────────────────────────────┤
│ PAYLOAD (base64 decoded):                        │
│ {                                                │
│   "sub": "550e8400-e29b-41d4-a716-446655440000", │ ← user_id
│   "type": "access",                              │ ← token type
│   "exp": 1727360800,                             │ ← expires Sep 26, 2026 11:00 UTC
│   "iat": 1727359000                              │ ← issued Sep 26, 2026 10:30 UTC
│ }                                                │
├─────────────────────────────────────────────────┤
│ SIGNATURE:                                       │
│ HMAC-SHA256(                                     │
│   base64(header) + "." + base64(payload),        │
│   "your-secret-key-from-env"                     │
│ )                                                │
└─────────────────────────────────────────────────┘

REFRESH TOKEN (7 days):
┌─────────────────────────────────────────────────┐
│ PAYLOAD:                                         │
│ {                                                │
│   "sub": "550e8400-e29b-41d4-a716-446655440000", │
│   "type": "refresh",                             │ ← different type!
│   "exp": 1727964600,                             │ ← expires Oct 3, 2026
│   "iat": 1727359000                              │
│ }                                                │
└─────────────────────────────────────────────────┘
```

### Token Size

A typical JWT is about 200-300 characters. It's sent in the HTTP header with every request:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC...
```

This is small enough to not affect performance, but large enough to carry useful claims.

---

<a name="design-decisions"></a>
## 7. Design Decisions

### Design Decision 1: HS256 vs RS256 Algorithm

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: JWT Signing Algorithm                             │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: HS256 (HMAC + SHA-256) — symmetric algorithm               │
│                                                                     │
│  WHY:                                                               │
│  • Simple — one key for both signing and verifying                  │
│  • Fast — HMAC is computationally lightweight                       │
│  • Sufficient — monolith architecture, one service verifies tokens  │
│  • Familiar — most JWT tutorials and libraries default to HS256     │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. RS256 (RSA + SHA-256) — asymmetric (private key signs, public   │
│     key verifies)                                                   │
│     ⚠️ Better for microservices (auth service signs, other services│
│        verify with public key — secret never shared)               │
│     ❌ Overkill for monolith. Slower. More complex key management. │
│  2. ES256 (ECDSA + SHA-256) — asymmetric, smaller keys than RSA     │
│     ⚠️ Best of both worlds but less library support                │
│                                                                     │
│  AT SCALE (microservices):                                          │
│  Switch to RS256. Auth service holds private key (signs tokens).    │
│  Other services hold public key (verify tokens). Private key is     │
│  never shared across network boundaries.                            │
│                                                                     │
│  INTERVIEW TIP: "We used HS256 because our monolith has a single   │
│  point of token verification. In a microservice architecture, we'd  │
│  switch to RS256 so the auth service signs with a private key and   │
│  other services verify with the public key — no secret sharing."    │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 2: python-jose vs PyJWT

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: JWT Library                                       │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: python-jose (jose library)                                 │
│                                                                     │
│  WHY:                                                               │
│  • FastAPI's documentation recommends it                            │
│  • Supports JWS, JWE, and JWK (more than just JWT)                 │
│  • Clean API: jwt.encode() / jwt.decode()                           │
│  • Automatic expiry checking                                        │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. PyJWT (the most popular Python JWT library)                     │
│     ⚠️ Also great. API is nearly identical. Either works.          │
│  2. authlib (full OAuth2/OIDC library)                              │
│     ❌ Overkill — we only need JWT, not full OAuth2                │
│                                                                     │
│  NOTE: python-jose is installed as `pip install "python-jose[cryptography]"`│
│  The [cryptography] extra uses the C-based cryptography backend     │
│  instead of the pure-Python one (10x faster).                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Decision 3: Token Type Claim for Safety

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Token Type in Payload                             │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: Include "type": "access" | "refresh" in JWT payload        │
│                                                                     │
│  WHY:                                                               │
│  • Prevents token type confusion attack                             │
│  • Refresh tokens (7-day lifespan) can't be used as access tokens   │
│  • Without this, an attacker with a refresh token has 7 days of     │
│    full API access instead of 30 minutes                            │
│                                                                     │
│  HOW IT'S ENFORCED:                                                 │
│  decode_token(token, expected_type="access") checks the "type"      │
│  claim. If it's "refresh", the token is rejected. And vice versa.   │
│                                                                     │
│  INTERVIEW TIP: "We include a type claim in the JWT payload and     │
│  verify it during decoding. This prevents token type confusion —    │
│  a refresh token can't be used as an access token, even though      │
│  both are valid JWTs signed with the same key."                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="verify"></a>
## 8. How to Verify Your Work

```bash
# Test password hashing
docker-compose exec backend python -c "
from app.modules.auth.security import hash_password, verify_password

# Hash a password
hashed = hash_password('mySecurePass123')
print(f'Hash: {hashed}')
print(f'Hash starts with \$2b\$12: {hashed.startswith(\"\\\$2b\\\$12\")}'  )

# Verify correct password
assert verify_password('mySecurePass123', hashed) == True
print('✅ Correct password verified')

# Verify wrong password
assert verify_password('wrongPassword', hashed) == False
print('✅ Wrong password rejected')

# Same password, different hash each time (salt!)
hashed2 = hash_password('mySecurePass123')
assert hashed != hashed2  # Different salts!
print(f'Hash 1: {hashed[:30]}...')
print(f'Hash 2: {hashed2[:30]}...')
print('✅ Different hashes for same password (salt works!)')
"

# Test JWT creation and decoding
docker-compose exec backend python -c "
from uuid import uuid4
from app.modules.auth.security import create_access_token, create_refresh_token, decode_token

user_id = uuid4()
print(f'User ID: {user_id}')

# Create tokens
access = create_access_token(user_id)
refresh = create_refresh_token(user_id)
print(f'Access token: {access[:50]}...')
print(f'Refresh token: {refresh[:50]}...')

# Decode access token
payload = decode_token(access, expected_type='access')
assert payload['sub'] == str(user_id)
assert payload['type'] == 'access'
print(f'✅ Access token decoded: sub={payload[\"sub\"][:8]}..., type={payload[\"type\"]}')

# Decode refresh token
payload = decode_token(refresh, expected_type='refresh')
assert payload['type'] == 'refresh'
print(f'✅ Refresh token decoded: type={payload[\"type\"]}')

# Verify type confusion prevention
try:
    decode_token(refresh, expected_type='access')
    print('❌ Should have rejected refresh token as access!')
except Exception as e:
    print(f'✅ Refresh token rejected as access: {e}')

print('\\n🎉 All security tests passed!')
"
```

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'jose'` | python-jose not installed | `pip install "python-jose[cryptography]"` |
| `ModuleNotFoundError: No module named 'passlib'` | passlib not installed | `pip install "passlib[bcrypt]"` |
| `ModuleNotFoundError: No module named 'bcrypt'` | bcrypt backend missing | `pip install bcrypt` |
| `JWTError: Signature verification failed` | Wrong SECRET_KEY | Check `.env` has the same `SECRET_KEY` |
| `TokenExpiredError` immediately after creation | System clock wrong | Check server time: `date -u` |

---

<a name="what-you-learned"></a>
## 9. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Password Hashing** | One-way transformation: password → hash. Cannot be reversed. | `hash_password()` |
| 2 | **bcrypt** | Password hashing algorithm — intentionally slow to resist brute-force | `pwd_context` |
| 3 | **Salt** | Random data added before hashing — prevents rainbow table attacks | Automatic in bcrypt |
| 4 | **Cost Factor** | bcrypt's `12` = 2^12 = 4,096 iterations. Higher = slower = more secure | `$2b$12$...` |
| 5 | **CryptContext** | passlib wrapper that manages hashing algorithms and migration | `pwd_context` |
| 6 | **`deprecated="auto"`** | Old algorithm hashes still verify; new passwords use current algorithm | Migration feature |
| 7 | **JWT (JSON Web Token)** | Self-contained token: Header.Payload.Signature | All token functions |
| 8 | **JWT Header** | Metadata: algorithm, token type. Base64-encoded. | `{"alg": "HS256"}` |
| 9 | **JWT Payload** | Data: user_id, expiry, type. Base64-encoded. NOT encrypted! | `{"sub": "abc-123"}` |
| 10 | **JWT Signature** | HMAC(header + payload, SECRET_KEY). Tamper protection. | Created by `jwt.encode()` |
| 11 | **HS256** | HMAC + SHA-256. Symmetric: same key signs and verifies. | `settings.JWT_ALGORITHM` |
| 12 | **Standard Claims** | `sub` (subject), `exp` (expiry), `iat` (issued-at) — from RFC 7519 | Token payloads |
| 13 | **Custom Claims** | `type` — our own claim to distinguish access from refresh tokens | Token payloads |
| 14 | **Access Token** | Short-lived (30 min). Sent with every request. | `create_access_token()` |
| 15 | **Refresh Token** | Long-lived (7 days). Used only to get new access tokens. | `create_refresh_token()` |
| 16 | **Token Type Confusion** | Attack: using refresh token as access token. Prevented by `type` check. | `decode_token()` |
| 17 | **`timedelta`** | Duration: `timedelta(minutes=30)` = 30 minutes | Token expiry calculation |
| 18 | **`jwt.encode()`** | Creates a signed JWT from a payload dict | `create_access_token()` |
| 19 | **`jwt.decode()`** | Verifies signature + expiry, returns payload dict | `decode_token()` |
| 20 | **`ExpiredSignatureError`** | JWT library exception: token past its `exp` time | Caught in `decode_token()` |

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: How does JWT authentication work? Walk me through it.
**A:** "JWT has three parts: header, payload, and signature. The header specifies the algorithm (HS256 in our case). The payload contains claims — user_id (sub), token type, expiry (exp), and issued-at (iat). The signature is created by HMAC-SHA256(base64(header) + '.' + base64(payload), SECRET_KEY). When a client sends a token, we decode it using the same SECRET_KEY. If the signature matches, the token wasn't tampered with. If the exp claim is in the past, the token is expired. The payload is NOT encrypted — anyone can read it with base64 decode — but no one can forge a valid signature without the SECRET_KEY."

### Q2: Why is bcrypt better than SHA-256 for password hashing?
**A:** "SHA-256 is designed to be fast — a GPU can compute 10 billion hashes per second. For passwords, fast is bad: an attacker can try billions of guesses per second. bcrypt is designed to be slow — about 4,000 hashes per second. It uses a configurable cost factor (we use 12, meaning 2^12 = 4,096 iterations). As hardware improves, we increase the cost. bcrypt also auto-generates a unique salt per password, preventing rainbow table attacks. SHA-256 doesn't include salting by default."

### Q3: What is a salt and why is it important?
**A:** "A salt is random data concatenated with the password before hashing. Without salt, the same password always produces the same hash — an attacker can precompute a 'rainbow table' mapping common passwords to their hashes and look up any hash instantly. With a unique salt per password, even if two users have the same password, their hashes are different. The attacker must brute-force each hash individually. bcrypt generates a 16-byte random salt automatically and embeds it in the hash output."

### Q4: Why two tokens (access + refresh) instead of one?
**A:** "Security vs UX trade-off. A single long-lived token (say 7 days) means if it's stolen, the attacker has 7 days of access. A single short-lived token (30 minutes) means the user re-enters their password every 30 minutes — terrible UX. The dual-token pattern solves both: the access token is short-lived (30 min) to limit damage from theft, and the refresh token is long-lived (7 days) to avoid re-authentication. The refresh token is sent only to one endpoint (/auth/refresh), reducing its exposure. On refresh, we rotate both tokens and blacklist the old ones."

### Q5: How do you prevent a refresh token from being used as an access token?
**A:** "We include a 'type' claim in the JWT payload — 'access' or 'refresh'. When decoding a token, we pass the expected type: `decode_token(token, expected_type='access')`. If the token's type doesn't match, we reject it with TokenInvalidError. Without this, an attacker who obtains a refresh token could use it as an access token in the Authorization header, bypassing the 30-minute expiry and getting 7 days of access."

### Q6: What happens if someone steals the SECRET_KEY?
**A:** "If the SECRET_KEY is compromised, the attacker can create valid JWT tokens for any user — game over for authentication. This is why we store it in environment variables (never in code), use a strong random value (at least 256 bits), and in production, use AWS Secrets Manager or similar. To recover from a key compromise: rotate the SECRET_KEY (all existing tokens become invalid, all users must re-login) and investigate the breach. For additional security, you could use RS256 with separate signing/verification keys."

### Q7: What is the difference between hashing and encryption?
**A:** "Hashing is one-way: password → hash. You cannot get the password back from the hash. Encryption is two-way: plaintext → ciphertext → plaintext. You can decrypt with the key. We use hashing for passwords because we never NEED the original password — we only need to verify a match. If we used encryption, anyone with the encryption key could decrypt all passwords. With hashing, even if the database is stolen and the server's source code is leaked, the passwords are still safe."

### Q8: How does `passlib`'s `CryptContext` with `deprecated="auto"` help with algorithm migration?
**A:** "If we decide to switch from bcrypt to argon2, we'd update `schemes=["argon2", "bcrypt"]`. With `deprecated=\"auto\"`, passlib treats bcrypt as 'deprecated': existing bcrypt hashes still verify correctly (users can still log in), but new password hashes (signups, password changes) use argon2. Over time, as users log in and update passwords, the database gradually migrates from bcrypt to argon2 — no forced password reset, no downtime, no migration script."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 04a: Auth Models, Exceptions & Schemas](./phase4-part04a-auth-entities-schemas.md) |
| ➡️ Next | [Phase 4 Part 04c: Auth Repository & Service](./phase4-part04c-auth-repository-service.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Auth Module Sub-Parts Progress

| Sub-Part | Status | Document |
|----------|--------|----------|
| 04a | ✅ Done | Auth Models, Exceptions & Schemas |
| **04b** | ✅ **You are here** | Auth Security — JWT & bcrypt |
| 04c | ⬜ Next | Auth Repository & Service |
| 04d | ⬜ | Auth Router, Main & Nginx |
| 04e | ⬜ | Auth Alembic Migrations |
| 04f | ⬜ | Auth Connections & Flows |

---

**End of Phase 4 Part 04b: Auth Security — JWT & Password Hashing**

*You've built the cryptographic foundation — bcrypt for passwords, JWT for tokens. These 4 functions protect every user in the system. Next: the repository (database queries) and service (business logic) that wire everything together.*
