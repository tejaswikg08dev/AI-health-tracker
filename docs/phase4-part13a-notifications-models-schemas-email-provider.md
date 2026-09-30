# 🔔 Phase 4 Part 13a: Notifications — Models, Schemas & Email Provider

> **"One model for per-user settings, 3 schemas for the API, and 3 email providers using the Strategy pattern. The ConsoleProvider prints to terminal, ResendProvider calls a free API, SESProvider talks to AWS. Same pattern you mastered in Part 08."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 13a (Notifications Data Layer + Email Provider) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Previous** | [phase4-part13-notifications-module-overview.md](./phase4-part13-notifications-module-overview.md) |
| **Next** | [phase4-part13b-notifications-service-tasks-router.md](./phase4-part13b-notifications-service-tasks-router.md) |
| **Files in This Doc** | 4 files (models.py, schemas.py, email_provider.py, 005_migration.py) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (unique per-user row, field_validator for HH:MM, Strategy pattern, boto3 async) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: models.py — NotificationSettings Model](#models)
3. [File 2: schemas.py — Settings Schemas](#schemas)
4. [File 3: email_provider.py — Strategy Pattern for Email](#email-provider)
5. [File 4: 005_create_notification_settings.py — Migration](#migration)
6. [How These Files Connect](#connections)
7. [What You Learned](#what-you-learned)
8. [Interview Q&A](#interview)
9. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

4 files that define the data layer and email infrastructure:

| # | File | What It Does |
|---|------|-------------|
| 1 | `models.py` | NotificationSettings table — 1 row per user with toggle switches |
| 2 | `schemas.py` | 3 Pydantic schemas: SettingsResponse, SettingsUpdate, TestEmailRequest |
| 3 | `email_provider.py` | Abstract base + 3 providers (Console, Resend, SES) + factory |
| 4 | `005_migration.py` | CREATE TABLE with unique user_id constraint |

---

<a name="models"></a>
## 2. File 1: `models.py` — NotificationSettings Model

### Type This Code: `backend/app/modules/notifications/models.py`

```python
# ============================================================================
# Notifications Module — Database Model
# ============================================================================
# Stores each user's notification preferences.
# One row per user — created when user signs up.
# ============================================================================

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationSettings(Base):
    """
    User notification preferences.

    Controls: daily reminders, weekly reports, streak milestone alerts.
    Each setting can be independently toggled on/off.

    reminder_time: What time to send the daily reminder (in user's timezone).
    Default 08:00 — most people check habits in the morning.
    """

    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,       # One settings row per user
        index=True,
    )

    # Toggle settings
    daily_reminder: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send daily 'time to log' reminder email",
    )
    weekly_report: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send weekly AI-generated health report",
    )
    streak_alerts: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true",
        comment="Send milestone alerts (7-day, 30-day streaks)",
    )

    # Reminder time (user's local time)
    reminder_time: Mapped[str] = mapped_column(
        String(5), default="08:00", server_default="08:00",
        comment="Daily reminder time in HH:MM format (user's timezone)",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None,
        onupdate=lambda: datetime.now(timezone.utc), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<NotificationSettings(user={self.user_id}, reminder={self.daily_reminder})>"
```

### Key Differences from Previous Models

**`unique=True` on `user_id` — One Row Per User**
```python
user_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="CASCADE"),
    unique=True,   # ← This is new
)
```
- Previous models (Habits, Logs): many rows per user. A user has many habits, many logs.
- NotificationSettings: exactly ONE row per user. `unique=True` enforces this at DB level
- If the app tries to create a second settings row → PostgreSQL raises `UniqueViolation`
- The service uses "get-or-create" pattern: `get_settings()` returns existing or creates default

**`String(5)` for Time — Why Not `Time` Type?**
```python
reminder_time: Mapped[str] = mapped_column(String(5), default="08:00")
```
- PostgreSQL has a `TIME` type, but it stores hours+minutes+seconds+microseconds
- We only need `HH:MM` — a simple `String(5)` is sufficient
- The schema validates the format: `field_validator` ensures it's valid `HH:MM` (00:00–23:59)
- Simpler than timezone-aware `Time` objects (which have DST complications)

**All Toggles Default to `True`**
```python
daily_reminder: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
```
- New users get ALL notifications enabled by default (opt-out, not opt-in)
- Opt-out is better for engagement: users who want silence will turn them off
- Opt-in would mean most users never enable them (they don't know they exist)

---

<a name="schemas"></a>
## 3. File 2: `schemas.py` — Settings Schemas

### Type This Code: `backend/app/modules/notifications/schemas.py`

```python
# ============================================================================
# Notifications Module — Schemas
# ============================================================================

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.base_schemas import BaseSchema


class NotificationSettingsResponse(BaseSchema):
    """Current notification preferences."""

    id: UUID
    daily_reminder: bool
    weekly_report: bool
    streak_alerts: bool
    reminder_time: str
    created_at: datetime


class NotificationSettingsUpdate(BaseModel):
    """Update notification preferences — all fields optional."""

    daily_reminder: bool | None = None
    weekly_report: bool | None = None
    streak_alerts: bool | None = None
    reminder_time: str | None = Field(
        default=None,
        description="Daily reminder time in HH:MM format",
        examples=["08:00", "20:30"],
    )

    @field_validator("reminder_time")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
        except ValueError:
            raise ValueError("Time must be valid HH:MM (00:00 to 23:59)")
        return v


class TestEmailRequest(BaseModel):
    """Request to send a test email."""

    email_type: str = Field(
        default="daily_reminder",
        description="Type of test email: daily_reminder, weekly_report, streak_milestone",
    )
```

### Key Schema Concepts

**`field_validator` for Time Format**
```python
@field_validator("reminder_time")
@classmethod
def validate_time_format(cls, v: str | None) -> str | None:
    if v is None:
        return v
    parts = v.split(":")
    if len(parts) != 2:
        raise ValueError("Time must be in HH:MM format")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError()
    return v
```
- Validates the time string: `"08:00"` ✅, `"20:30"` ✅, `"25:00"` ❌, `"abc"` ❌
- `split(":")` → `["08", "00"]`. Convert to ints. Check bounds.
- Returns `None` if not provided (field is optional in the update schema)
- Same `@field_validator` pattern from Habits (Part 05a — hex color validation)

---

<a name="email-provider"></a>
## 4. File 3: `email_provider.py` — Strategy Pattern for Email

### Type This Code: `backend/app/modules/notifications/email_provider.py`

```python
# ============================================================================
# Notifications — Email Provider (Abstract + Implementations)
# ============================================================================
# PROVIDERS:
#   ConsoleProvider → prints to terminal (dev — no real emails)
#   ResendProvider  → Resend.com API (free tier: 100 emails/day)
#   SESProvider     → AWS SES (production: 3K emails/month free from EC2)
# ============================================================================

from abc import ABC, abstractmethod

import httpx

from app.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseEmailProvider(ABC):
    """Abstract email provider — all implementations send emails the same way."""

    @abstractmethod
    async def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Send an email.
        Returns True if sent successfully, False on failure.
        Never raises — email failures shouldn't crash the app.
        """
        ...


class ConsoleProvider(BaseEmailProvider):
    """
    Development email provider — prints emails to the terminal.
    No API keys, no external services.
    """

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        logger.info(
            "email_sent_console",
            to=to_email,
            subject=subject,
            body_preview=html_body[:200],
        )
        print(f"\n{'='*60}")
        print(f"📧 EMAIL (console mode)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"{'─'*60}")
        print(html_body[:500])
        if len(html_body) > 500:
            print(f"... ({len(html_body)} chars total)")
        print(f"{'='*60}\n")
        return True


class ResendProvider(BaseEmailProvider):
    """
    Resend.com email provider — free tier: 100 emails/day.
    Simple REST API. Sign up at resend.com, get an API key.
    """

    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.SES_FROM_EMAIL

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "from": self.from_email,
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info("email_sent_resend", to=to_email, subject=subject)
                return True
        except Exception as e:
            logger.error("email_send_error_resend", to=to_email, error=str(e))
            return False


class SESProvider(BaseEmailProvider):
    """
    AWS SES email provider — production use.
    Free tier: 3,000 emails/month when sending from EC2.
    """

    def __init__(self):
        import boto3
        self.ses_client = boto3.client("ses", region_name=settings.AWS_REGION)
        self.from_email = settings.SES_FROM_EMAIL

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.ses_client.send_email(
                    Source=self.from_email,
                    Destination={"ToAddresses": [to_email]},
                    Message={
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                    },
                ),
            )
            logger.info("email_sent_ses", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("email_send_error_ses", to=to_email, error=str(e))
            return False


def get_email_provider() -> BaseEmailProvider:
    """Factory — returns the configured email provider."""
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        return ResendProvider()
    elif provider == "ses":
        return SESProvider()
    else:
        return ConsoleProvider()
```

### Line-by-Line: Key Concepts

**`send()` Returns `bool`, Never Raises**
```python
async def send(self, to_email, subject, html_body) -> bool:
```
Every provider wraps its logic in try/except and returns `True`/`False`. Email sending is NOT critical — if it fails, the app continues. A failed daily reminder is NOT worth crashing the scheduled task and blocking 49 other users' emails.

**ConsoleProvider — Dev Mode**
```python
print(f"📧 EMAIL (console mode)")
print(f"To: {to_email}")
print(f"Subject: {subject}")
print(html_body[:500])
```
Prints the email to your terminal. During development, you see EXACTLY what the user would receive — without configuring any email API. This is the zero-cost, zero-setup option.

**ResendProvider — Staging**
```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {self.api_key}"},
        json={"from": ..., "to": [to_email], "subject": ..., "html": ...},
    )
```
- Resend.com is a modern email API — free tier: 100 emails/day
- Simple REST POST with API key in header
- `httpx.AsyncClient` for async HTTP — same library as Ollama/Groq LLM clients

**SESProvider — Production (boto3 in Async)**
```python
import asyncio
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    lambda: self.ses_client.send_email(...)
)
```
- **The problem:** `boto3` (AWS SDK) is synchronous. Our app is async (`async def`). Calling sync code in async context blocks the event loop.
- **The solution:** `run_in_executor(None, sync_function)` — runs the sync function in a thread pool. The async event loop isn't blocked while waiting.
- `None` = default executor (ThreadPoolExecutor). Creates a new thread for the boto3 call
- This is a common pattern: any sync library (boto3, Pillow, PyPDF2) in an async app

**Factory Function**
```python
def get_email_provider() -> BaseEmailProvider:
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        return ResendProvider()
    elif provider == "ses":
        return SESProvider()
    else:
        return ConsoleProvider()
```
Same factory pattern as LLM (Part 08b). Reads config, returns the right implementation. Default: Console (safest fallback — never accidentally sends real emails in development).

---

<a name="migration"></a>
## 5. File 4: `005_create_notification_settings.py` — Migration

### Type This Code: `backend/alembic/versions/005_create_notification_settings.py`

```python
"""create notification_settings table

Revision ID: 005
Revises: 004
Create Date: 2026-09-26

Creates the notification_settings table — one row per user
with toggles for daily reminders, weekly reports, and streak alerts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("daily_reminder", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("weekly_report", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("streak_alerts", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("reminder_time", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_settings_user_id", "notification_settings", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("notification_settings")
```

**`unique=True` in Both Model AND Index**

The `unique=True` on `user_id` in the model creates a `UNIQUE` constraint. The `unique=True` in `create_index` creates a `UNIQUE INDEX`. Both enforce the same rule — one row per user. The index also speeds up lookups: `WHERE user_id = ?`.

---

<a name="connections"></a>
## 6. How These Files Connect

```
GET /notifications/settings
  │
  ├── Router calls service.get_settings(user_id)
  │     → SELECT FROM notification_settings WHERE user_id = ?
  │     → If None → CREATE with defaults (all enabled, 08:00)
  │     → Return NotificationSettings ORM object
  │
  ├── Router converts: NotificationSettingsResponse.model_validate(settings)
  │     → {"daily_reminder": true, "weekly_report": true, "streak_alerts": true,
  │        "reminder_time": "08:00", ...}
  │
  └── HTTP 200 with JSON response

PUT /notifications/settings {"reminder_time": "20:30", "daily_reminder": false}
  │
  ├── Pydantic validates: NotificationSettingsUpdate
  │     → field_validator: "20:30" → valid HH:MM ✅
  │
  ├── Service: update_settings()
  │     → model_dump(exclude_unset=True) → {"reminder_time": "20:30", "daily_reminder": false}
  │     → setattr(settings, key, value) for each field
  │     → commit()
  │
  └── HTTP 200 with updated settings

Daily Reminder Task (Lambda/Celery, 8 PM):
  │
  ├── Query: all users with daily_reminder=True in notification_settings
  ├── For each user: check if all habits logged today
  ├── If NOT all logged → service.send_daily_reminder(email, name, date)
  │     → _render_template("daily_reminder.html", {...})
  │     → email_provider.send(to, subject, html)
  │         → Console (prints) / Resend (API) / SES (AWS)
  └── Log results
```

---

<a name="what-you-learned"></a>
## 7. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`unique=True` on FK** | One settings row per user (not many like habits/logs) | models.py user_id |
| 2 | **`String(5)` for time** | Store "HH:MM" as simple string (no timezone complexity) | models.py reminder_time |
| 3 | **Opt-out defaults** | All notifications enabled by default (better engagement) | models.py Boolean defaults |
| 4 | **`field_validator` for HH:MM** | Custom time format validation with split + int + range check | schemas.py |
| 5 | **Strategy Pattern (3rd time)** | Abstract + Console/Resend/SES + factory | email_provider.py |
| 6 | **`send() → bool` (never raises)** | Email failure = False, not crash | All providers |
| 7 | **`httpx.AsyncClient`** | Async HTTP for Resend API | ResendProvider |
| 8 | **`run_in_executor()`** | Run sync boto3 in async context (thread pool) | SESProvider |
| 9 | **Lazy import (`import boto3`)** | Only import when SES provider is used | SESProvider.__init__ |
| 10 | **Unique index in migration** | `unique=True` in `create_index` matches model constraint | 005_migration |

---

<a name="interview"></a>
## 8. Interview Q&A

### Q1: How do you handle the synchronous boto3 SDK in an async FastAPI app?
**A:** "boto3 is synchronous — calling it directly in an async function would block the event loop. We use `asyncio.run_in_executor(None, sync_function)` which runs the boto3 call in a thread pool. The event loop continues handling other requests while the thread waits for AWS. This is the standard pattern for using any synchronous library in an async Python app."

### Q2: Why is email sending designed to never raise exceptions?
**A:** "Email is best-effort, not critical. If the daily reminder Lambda sends 50 emails and the 12th fails (timeout), we don't want the remaining 38 to be skipped. Each provider's `send()` catches all exceptions and returns `False`. The task logs the failure and continues. For critical emails (password reset), we'd add a retry queue, but habit reminders are not worth the complexity."

### Q3: Why store reminder_time as String(5) instead of PostgreSQL TIME?
**A:** "Simplicity. PostgreSQL `TIME` stores hours, minutes, seconds, and microseconds — overkill for 'remind me at 8 PM.' A `String(5)` stores `'08:00'` or `'20:30'` — exactly what we need. Pydantic's `field_validator` validates the format. And we avoid timezone complications that `TIME WITH TIME ZONE` introduces — the user's timezone is stored separately on the User model."

---

<a name="navigation"></a>
## 9. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 13: Notifications Overview](./phase4-part13-notifications-module-overview.md) |
| ➡️ Next | [Phase 4 Part 13b: Service, Tasks & Router](./phase4-part13b-notifications-service-tasks-router.md) |

### Notifications Sub-Parts Progress

| Sub-Part | Status |
|----------|--------|
| **13a** | ✅ **You are here** — Models, Schemas, Email Provider, Migration |
| 13b | ⬜ Next — Service, Tasks, Router |
| 13c | ⬜ Email Templates |
| 13d | ⬜ Connections & Flows |

---

**End of Phase 4 Part 13a: Notifications Models, Schemas & Email Provider**

*Per-user settings with opt-out defaults, time format validation, and the Strategy pattern applied for the third time (Console/Resend/SES). Next: the service that sends 4 types of emails, the background tasks, and the 3-endpoint router.*
