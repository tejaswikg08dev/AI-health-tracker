# ============================================================================
# Health Tracker — Date & Timezone Utilities
# ============================================================================
# WHAT THIS FILE DOES:
#   Helper functions for date operations used across all modules.
#   Handles timezone conversion, date range generation, week/month boundaries.
#
# WHY DATES ARE TRICKY:
#   - User in India logs a habit at 11 PM IST (May 5th for them)
#   - Server stores it as 5:30 PM UTC (May 5th UTC)
#   - If we don't handle timezones, the log might show as May 6th for them
#
#   Rule: Store everything in UTC in the database.
#   Convert to user's timezone only when displaying.
# ============================================================================

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """
    Get current UTC datetime (timezone-aware).

    WHY timezone-aware:
        datetime.utcnow() returns a "naive" datetime (no timezone info).
        This causes bugs when comparing with timezone-aware datetimes.
        Always use timezone-aware datetimes in production code.
    """
    return datetime.now(timezone.utc)


def today_utc() -> date:
    """Get today's date in UTC."""
    return utc_now().date()


def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    """
    Convert a UTC datetime to the user's local timezone.

    Args:
        dt: A UTC datetime
        user_timezone: IANA timezone string (e.g., "Asia/Kolkata", "America/New_York")

    Returns:
        Datetime in user's timezone

    Example:
        utc_time = datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "Asia/Kolkata")
        # Result: 2026-09-27 00:00:00+05:30 (next day in India!)
    """
    tz = ZoneInfo(user_timezone)
    return dt.astimezone(tz)


def start_of_week(d: date | None = None) -> date:
    """
    Get the Monday of the current (or given) week.

    WHY Monday:
        ISO standard: Monday = start of week.
        Consistent across all locales in our app.

    Example:
        start_of_week(date(2026, 9, 26))  # Saturday
        # Returns: date(2026, 9, 21)       # Monday of that week
    """
    if d is None:
        d = today_utc()
    return d - timedelta(days=d.weekday())


def end_of_week(d: date | None = None) -> date:
    """Get the Sunday of the current (or given) week."""
    return start_of_week(d) + timedelta(days=6)


def start_of_month(d: date | None = None) -> date:
    """Get the first day of the current (or given) month."""
    if d is None:
        d = today_utc()
    return d.replace(day=1)


def end_of_month(d: date | None = None) -> date:
    """
    Get the last day of the current (or given) month.

    TRICK: Go to first of NEXT month, then subtract 1 day.
    This correctly handles months with 28, 29, 30, or 31 days.
    """
    if d is None:
        d = today_utc()
    # Go to first of next month
    if d.month == 12:
        next_month_first = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month_first = d.replace(month=d.month + 1, day=1)
    # Subtract 1 day to get last day of current month
    return next_month_first - timedelta(days=1)


def date_range(start: date, end: date) -> list[date]:
    """
    Generate a list of all dates between start and end (inclusive).

    Used for: filling gaps in chart data (days with no logs still show on chart).

    Example:
        date_range(date(2026, 9, 1), date(2026, 9, 5))
        # Returns: [Sep 1, Sep 2, Sep 3, Sep 4, Sep 5]
    """
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]


def days_ago(n: int) -> date:
    """Get the date N days ago. Shortcut for common queries."""
    return today_utc() - timedelta(days=n)
