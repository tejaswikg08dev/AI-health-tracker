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
