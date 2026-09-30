# ============================================================================
# Analytics Module — Custom Exceptions
# ============================================================================

from app.shared.exceptions import ValidationError


class InsufficientDataError(ValidationError):
    """
    Not enough log data to generate meaningful analytics — HTTP 422.

    Raised when: user asks for weekly comparison but only has 2 days of data,
    or asks for correlation but only one habit has logs.

    The frontend should show a friendly "Log more data to see analytics" message.
    """

    def __init__(self, detail: str = "Not enough data for this analysis") -> None:
        super().__init__(
            message=detail,
            error_code="INSUFFICIENT_DATA",
        )


class InvalidDateRangeError(ValidationError):
    """Start date is after end date — HTTP 422."""

    def __init__(self) -> None:
        super().__init__(
            message="Start date must be before or equal to end date",
            error_code="INVALID_DATE_RANGE",
        )
