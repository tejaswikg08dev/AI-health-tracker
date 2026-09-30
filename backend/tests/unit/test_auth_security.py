# ============================================================================
# Unit Tests — Auth Security (JWT + Password Hashing)
# ============================================================================
# Tests the core security functions WITHOUT a database.
# These are pure functions — hash, verify, create token, decode token.
# ============================================================================

import pytest
from uuid import uuid4

from app.modules.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.modules.auth.exceptions import TokenExpiredError, TokenInvalidError


class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """Hashing a password returns a bcrypt hash string."""
        hashed = hash_password("mySecurePass123")
        assert hashed != "mySecurePass123"  # Not plain text
        assert hashed.startswith("$2b$")    # Bcrypt prefix
        assert len(hashed) > 50             # Bcrypt hashes are ~60 chars

    def test_verify_correct_password(self):
        """Correct password verifies against its hash."""
        hashed = hash_password("mySecurePass123")
        assert verify_password("mySecurePass123", hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password does NOT verify."""
        hashed = hash_password("mySecurePass123")
        assert verify_password("wrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password produces different hashes (random salt)."""
        hash1 = hash_password("samePassword")
        hash2 = hash_password("samePassword")
        assert hash1 != hash2  # Different salts → different hashes
        # But both verify correctly
        assert verify_password("samePassword", hash1) is True
        assert verify_password("samePassword", hash2) is True


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Access token is a non-empty string."""
        user_id = uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 50  # JWTs are long
        assert token.count(".") == 2  # JWTs have 3 parts separated by dots

    def test_decode_valid_access_token(self):
        """Decoding a valid access token returns the payload."""
        user_id = uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token, expected_type="access")

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_refresh_token(self):
        """Refresh token is created and decodable."""
        user_id = uuid4()
        token = create_refresh_token(user_id)
        payload = decode_token(token, expected_type="refresh")

        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_decode_wrong_type_raises_error(self):
        """Using a refresh token as access token raises TokenInvalidError."""
        user_id = uuid4()
        refresh_token = create_refresh_token(user_id)

        with pytest.raises(TokenInvalidError):
            decode_token(refresh_token, expected_type="access")

    def test_decode_garbage_token_raises_error(self):
        """Decoding a garbage string raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            decode_token("not.a.valid.jwt.token", expected_type="access")

    def test_decode_empty_token_raises_error(self):
        """Decoding an empty string raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            decode_token("", expected_type="access")

    def test_different_users_get_different_tokens(self):
        """Different user IDs produce different tokens."""
        token1 = create_access_token(uuid4())
        token2 = create_access_token(uuid4())
        assert token1 != token2
