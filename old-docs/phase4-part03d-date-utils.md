# Phase 4 — Part 03d: Date & Timezone Utilities (shared/date_utils.py)

> **"Timezones are where bugs hide. Store UTC, convert on display, test edge cases."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Phase** | 4 — Implementation |
| **Part** | 03d |
| **Sprint** | Sprint 1 — Foundation + Auth |
| **Release** | Release 1.2 — Shared Utilities |
| **File** | `backend/app/shared/date_utils.py` |
| **Depends On** | None (pure utility functions, no imports from our app) |
| **Next** | [Part 03e — logging.py](./phase4-part03e-logging.md) |
| **Difficulty** | 🟢 Easy |
| **Time to Type** | ~12 minutes |
| **Lines of Code** | 100 lines |

---

## 📖 Why Are Dates Tricky? Read This First

### The Timezone Problem

```
Shreya in India logs "Water" at 11:30 PM on May 5th (IST = UTC+5:30)
Server receives it at: May 5th, 6:00 PM UTC

If we store the user's local time:
  Database: log_date = "2026-05-05"  ← correct (May 5th in India)

If we store UTC time without thinking:
  Database: log_date = "2026-05-05"  ← correct (May 5th in UTC too, barely)

BUT if Shreya logs at 11:31 PM IST → that's May 6th 00:01 AM UTC
  Database: log_date = "2026-05-06"  ← WRONG! It was May 5th for Shreya!
```

### The Rule: Store UTC, Display Local

```
STORAGE:   Always store dates/times in UTC in the database
DISPLAY:   Convert to user's timezone (from their profile) when showing in the frontend
LOGGING:   Use the DATE portion from the user's perspective, not the server's
```

### What is UTC?

UTC = Coordinated Universal Time. It's the "reference clock" — everyone agrees on what time it is in UTC. Timezones are offsets from UTC:

```
UTC      = 00:00
IST      = UTC + 5:30  (India)
EST/EDT  = UTC - 5:00  (New York)
PST/PDT  = UTC - 8:00  (San Francisco)
```

### What is `date` vs `datetime`?

```python
from datetime import date, datetime

date(2026, 9, 26)                    # Just the date: September 26, 2026 (no time)
datetime(2026, 9, 26, 14, 30, 0)     # Date AND time: September 26, 2026 at 2:30 PM
```

In our app: `log_date` is a `date` (just the day). `created_at` is a `datetime` (day + time).

---

## 💻 Source Code — Type This EXACTLY

> 📁 **File:** `backend/app/shared/date_utils.py`
> 📏 **Lines:** 100
> ⏱️ **Time to type:** ~12 minutes

```python
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
```

---

## 📝 Line-by-Line Explanation

### Lines 17-18: Imports

```python
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
```

**What each import does:**
- **`date`** — A date without time: `date(2026, 9, 26)` = September 26, 2026
- **`datetime`** — A date WITH time: `datetime(2026, 9, 26, 14, 30)` = Sep 26 at 2:30 PM
- **`timedelta`** — A DURATION: `timedelta(days=7)` = 7 days. Used for date math: `today - timedelta(days=7)` = a week ago
- **`timezone`** — Timezone info. `timezone.utc` = the UTC timezone
- **`ZoneInfo`** — Converts timezone NAMES to objects. `ZoneInfo("Asia/Kolkata")` = the India timezone

**What is `zoneinfo`?**

Added in Python 3.9. Before this, you needed the third-party `pytz` library. `zoneinfo` uses the OS's timezone database (IANA Time Zone Database), so it's always up-to-date.

### Lines 21-31: `utc_now()`

```python
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

**What `-> datetime` means:** This is a **return type hint**. It tells Python (and your IDE): "This function returns a `datetime` object." It's documentation, not enforcement — Python won't crash if you return something else, but your IDE will warn you.

**Why `datetime.now(timezone.utc)` and NOT `datetime.utcnow()`?**

```python
# BAD — "naive" datetime (no timezone attached):
datetime.utcnow()
# Returns: datetime(2026, 9, 26, 14, 30, 0)
# Problem: Python doesn't KNOW this is UTC. If you compare with a timezone-aware
# datetime, Python raises: "TypeError: can't compare offset-naive and offset-aware"

# GOOD — "aware" datetime (timezone attached):
datetime.now(timezone.utc)
# Returns: datetime(2026, 9, 26, 14, 30, 0, tzinfo=UTC)
# Python KNOWS this is UTC. Comparisons work correctly.
```

### Lines 34-36: `today_utc()`

```python
def today_utc() -> date:
    return utc_now().date()
```

**What `.date()` does:** Strips the time part. `datetime(2026, 9, 26, 14, 30).date()` → `date(2026, 9, 26)`.

**Why a separate function?** We call `today_utc()` in ~20 places (log validation, analytics, seed data). Without this function, every place would write `datetime.now(timezone.utc).date()` — verbose and error-prone.

### Lines 39-53: `to_user_timezone()`

```python
def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
    tz = ZoneInfo(user_timezone)
    return dt.astimezone(tz)
```

**What `ZoneInfo("Asia/Kolkata")` does:** Creates a timezone object for India Standard Time (UTC+5:30).

**What `.astimezone(tz)` does:** Converts the datetime to the target timezone:
```python
utc_time = datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc)  # 6:30 PM UTC
india_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))       # 12:00 AM IST (next day!)
```

### Lines 56-68: `start_of_week()`

```python
def start_of_week(d: date | None = None) -> date:
    if d is None:
        d = today_utc()
    return d - timedelta(days=d.weekday())
```

**What `d.weekday()` returns:**
```
Monday    = 0
Tuesday   = 1
Wednesday = 2
Thursday  = 3
Friday    = 4
Saturday  = 5
Sunday    = 6
```

**How the math works:**
```
If today is Saturday (weekday=5):
  d - timedelta(days=5) = Monday (5 days earlier)

If today is Monday (weekday=0):
  d - timedelta(days=0) = Monday (same day!)

If today is Wednesday (weekday=2):
  d - timedelta(days=2) = Monday (2 days earlier)
```

### Lines 80-94: `end_of_month()`

```python
def end_of_month(d: date | None = None) -> date:
    if d is None:
        d = today_utc()
    if d.month == 12:
        next_month_first = d.replace(year=d.year + 1, month=1, day=1)
    else:
        next_month_first = d.replace(month=d.month + 1, day=1)
    return next_month_first - timedelta(days=1)
```

**The trick:** Finding the last day of a month is hard (28? 29? 30? 31?). Instead:
1. Go to the FIRST day of the NEXT month
2. Subtract 1 day

```
Last day of September:
  First of October = Oct 1
  Oct 1 - 1 day = Sep 30 ✅

Last day of February 2024 (leap year):
  First of March = Mar 1
  Mar 1 - 1 day = Feb 29 ✅
```

**Why the `if d.month == 12` check?** December is month 12. There's no month 13. So "next month after December" is January of the NEXT YEAR.

### Lines 97-104: `date_range()` and `days_ago()`

```python
def date_range(start: date, end: date) -> list[date]:
    days = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(days)]
```

**What is `[... for i in range(n)]`?**

This is a **list comprehension** — Python's shorthand for building a list:

```python
# Long form:
result = []
for i in range(5):
    result.append(start + timedelta(days=i))

# Short form (list comprehension — same result):
result = [start + timedelta(days=i) for i in range(5)]
```

**Why `+1`?** To make it INCLUSIVE. `Sep 1 to Sep 5` = 4 days difference, but we want 5 dates (1, 2, 3, 4, 5). So `+1`.

---

## 🧪 Try It Yourself

```python
>>> from app.shared.date_utils import utc_now, today_utc, start_of_week, end_of_month, date_range, days_ago
>>> from datetime import date

# Test 1: UTC now is timezone-aware
>>> now = utc_now()
>>> print(now.tzinfo)
UTC

# Test 2: Start of week (Monday)
>>> start_of_week(date(2026, 9, 26))  # Saturday Sep 26
date(2026, 9, 21)  # Monday Sep 21

# Test 3: End of month
>>> end_of_month(date(2026, 9, 15))
date(2026, 9, 30)  # September has 30 days

# Test 4: Date range
>>> date_range(date(2026, 9, 1), date(2026, 9, 3))
[date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)]

# Test 5: Days ago
>>> days_ago(7)  # Should be 7 days before today
```

---

## ✅ What You Learned

| # | Concept | What It Means |
|---|---------|---------------|
| 1 | UTC | The universal reference timezone — store dates in this |
| 2 | Naive vs aware datetime | Naive has no timezone info (BAD). Aware has tzinfo (GOOD). |
| 3 | `-> date` return type hint | Documents what a function returns (not enforced, but IDE warns) |
| 4 | `date \| None = None` | Optional parameter — if not given, defaults to None |
| 5 | `.weekday()` | Monday=0, Sunday=6. Used for start-of-week math |
| 6 | `timedelta` | A duration. `date - timedelta(days=7)` = 7 days ago |
| 7 | List comprehension | `[x for x in range(5)]` — shorthand for building lists |
| 8 | `.replace(day=1)` | Create a new date with only the day changed |
| 9 | `ZoneInfo` | Python 3.9+ timezone support (replaces pytz) |

---

## 🎤 Interview Q&A

### Q1: "How do you handle timezones in your application?"

> "Store everything in UTC, convert on display. Every database timestamp column uses `DateTime(timezone=True)`. Each user has a `timezone` field in their profile (IANA format like 'Asia/Kolkata'). My `date_utils.py` module has `utc_now()` for timezone-aware UTC timestamps and `to_user_timezone()` for conversion. The key rule: the backend NEVER uses local time. All comparisons, all storage, all calculations are in UTC. The frontend converts to the user's timezone for display."

### Q2: "How do you find the last day of any month?"

> "I don't hardcode 28/29/30/31 — that's error-prone with leap years. Instead: go to the first day of the NEXT month, subtract one day. `replace(month=d.month+1, day=1) - timedelta(days=1)`. This handles February correctly in both leap and non-leap years. Special case: December — 'next month' is January of the next year."

### Q3: "What is a list comprehension?"

> "Python's shorthand for building a list from a loop: `[expression for item in iterable]`. Instead of 4 lines (create list, loop, append, return), it's 1 line. I use it in `date_range()`: `[start + timedelta(days=i) for i in range(days)]` generates all dates between two dates. It's more Pythonic and typically faster than the explicit loop because Python optimizes it internally."

---

## 📚 Navigation

| ← Previous | [📚 Index](./INDEX.md) | Next → |
|:-----------|:---------------------:|-------:|
| [Part 03c — base_repository.py](./phase4-part03c-base-repository.md) | | [Part 03e — logging.py](./phase4-part03e-logging.md) |
