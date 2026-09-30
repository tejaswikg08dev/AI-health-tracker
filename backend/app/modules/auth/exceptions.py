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
