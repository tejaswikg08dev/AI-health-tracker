# ============================================================================
# Habits Module — Custom Exceptions
# ============================================================================

from app.shared.exceptions import ConflictError, NotFoundError, ValidationError


class HabitNotFoundError(NotFoundError):
    """Habit does not exist or doesn't belong to this user — HTTP 404."""

    def __init__(self) -> None:
        super().__init__(
            message="Habit not found",
            error_code="HABIT_NOT_FOUND",
        )


class DuplicateHabitNameError(ConflictError):
    """User already has a habit with this name — HTTP 409."""

    def __init__(self, name: str) -> None:
        super().__init__(
            message=f"You already have a habit named '{name}'",
            error_code="DUPLICATE_HABIT_NAME",
        )


class HabitLimitExceededError(ValidationError):
    """User has reached the maximum number of active habits — HTTP 422."""

    MAX_HABITS = 20

    def __init__(self) -> None:
        super().__init__(
            message=f"Maximum {self.MAX_HABITS} active habits allowed. Archive some to add more.",
            error_code="HABIT_LIMIT_EXCEEDED",
        )


class InvalidHabitTypeError(ValidationError):
    """Habit type is not one of: numeric, boolean, scale — HTTP 422."""

    def __init__(self, habit_type: str) -> None:
        super().__init__(
            message=f"Invalid habit type '{habit_type}'. Must be: numeric, boolean, or scale.",
            error_code="INVALID_HABIT_TYPE",
        )
