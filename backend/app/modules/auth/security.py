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
