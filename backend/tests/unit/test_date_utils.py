# ============================================================================
# Unit Tests — Date Utilities
# ============================================================================

from datetime import date, datetime, timezone

from app.shared.date_utils import (
    utc_now,
    today_utc,
    to_user_timezone,
    start_of_week,
    end_of_week,
    start_of_month,
    end_of_month,
    date_range,
    days_ago,
)


class TestUtcNow:
    def test_returns_timezone_aware(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_returns_datetime(self):
        assert isinstance(utc_now(), datetime)


class TestTodayUtc:
    def test_returns_date(self):
        assert isinstance(today_utc(), date)


class TestToUserTimezone:
    def test_convert_utc_to_india(self):
        utc_time = datetime(2026, 9, 26, 18, 30, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "Asia/Kolkata")
        # IST is UTC+5:30 → 18:30 UTC = 00:00 IST (next day)
        assert local.hour == 0
        assert local.day == 27

    def test_convert_utc_to_new_york(self):
        utc_time = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)
        local = to_user_timezone(utc_time, "America/New_York")
        # EDT is UTC-4 → 12:00 UTC = 08:00 EDT
        assert local.hour == 8


class TestStartOfWeek:
    def test_monday_is_start(self):
        # September 26, 2026 is a Saturday
        result = start_of_week(date(2026, 9, 26))
        assert result == date(2026, 9, 21)  # Monday
        assert result.weekday() == 0  # 0 = Monday

    def test_monday_returns_itself(self):
        monday = date(2026, 9, 21)
        assert start_of_week(monday) == monday


class TestEndOfWeek:
    def test_sunday_is_end(self):
        result = end_of_week(date(2026, 9, 26))
        assert result == date(2026, 9, 27)  # Sunday
        assert result.weekday() == 6  # 6 = Sunday


class TestStartOfMonth:
    def test_returns_first_day(self):
        assert start_of_month(date(2026, 9, 26)) == date(2026, 9, 1)

    def test_first_day_returns_itself(self):
        assert start_of_month(date(2026, 9, 1)) == date(2026, 9, 1)


class TestEndOfMonth:
    def test_september_has_30_days(self):
        assert end_of_month(date(2026, 9, 15)) == date(2026, 9, 30)

    def test_february_non_leap(self):
        assert end_of_month(date(2025, 2, 10)) == date(2025, 2, 28)

    def test_december(self):
        assert end_of_month(date(2026, 12, 5)) == date(2026, 12, 31)


class TestDateRange:
    def test_generates_inclusive_range(self):
        result = date_range(date(2026, 9, 1), date(2026, 9, 5))
        assert len(result) == 5
        assert result[0] == date(2026, 9, 1)
        assert result[-1] == date(2026, 9, 5)

    def test_single_day_range(self):
        result = date_range(date(2026, 9, 1), date(2026, 9, 1))
        assert len(result) == 1


class TestDaysAgo:
    def test_zero_days_ago_is_today(self):
        assert days_ago(0) == today_utc()

    def test_seven_days_ago(self):
        result = days_ago(7)
        assert (today_utc() - result).days == 7
