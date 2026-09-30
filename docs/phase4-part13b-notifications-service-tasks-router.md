# 🔔 Phase 4 Part 13b: Notifications — Service, Tasks & Router

> **"The service manages settings and sends 4 types of emails using Jinja2 templates. The tasks define scheduled jobs for Lambda/Celery. The router exposes 3 endpoints. Full source code for all 3 files."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part13a-notifications-models-schemas-email-provider.md](./phase4-part13a-notifications-models-schemas-email-provider.md) |
| **Next** | [phase4-part13c-notifications-templates-migration.md](./phase4-part13c-notifications-templates-migration.md) |
| **Files in This Doc** | 3 files (service.py, tasks.py, router.py) |
| **Time to Type** | ~45 minutes |

---

## 1. File 1: `service.py` — Settings CRUD + Email Sending

### Type This Code: `backend/app/modules/notifications/service.py`

```python
# ============================================================================
# Notifications Module — Service Layer
# ============================================================================
# Manages notification settings and sends emails using templates.
# ============================================================================

from uuid import UUID

from jinja2 import Template
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.email_provider import get_email_provider
from app.modules.notifications.models import NotificationSettings
from app.modules.notifications.schemas import NotificationSettingsUpdate
from app.shared.logging import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = "app/modules/notifications/templates"


class NotificationService:
    """Notification settings management and email sending."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_provider = get_email_provider()

    async def get_settings(self, user_id: UUID) -> NotificationSettings:
        """Get or create notification settings for a user."""
        result = await self.session.execute(
            select(NotificationSettings).where(
                NotificationSettings.user_id == user_id
            )
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default settings on first access
            settings = NotificationSettings(user_id=user_id)
            self.session.add(settings)
            await self.session.commit()
            await self.session.refresh(settings)

        return settings

    async def update_settings(
        self, user_id: UUID, data: NotificationSettingsUpdate
    ) -> NotificationSettings:
        """Update notification preferences."""
        settings = await self.get_settings(user_id)
        update_data = data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(settings, key, value)

        await self.session.commit()
        await self.session.refresh(settings)

        logger.info("notification_settings_updated", user_id=str(user_id),
                    fields=list(update_data.keys()))
        return settings

    async def send_daily_reminder(
        self, user_email: str, user_name: str, date_str: str
    ) -> bool:
        """Send a daily habit reminder email."""
        html = self._render_template("daily_reminder.html", {
            "name": user_name, "date": date_str, "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"🏥 Time to log your habits — {date_str}",
            html_body=html,
        )

    async def send_weekly_report(
        self, user_email: str, user_name: str, week_start: str, week_end: str,
        total_habits: int, completion_pct: float, best_streak: str, ai_insights: str,
    ) -> bool:
        """Send the weekly health report email."""
        html = self._render_template("weekly_report.html", {
            "name": user_name, "week_start": week_start, "week_end": week_end,
            "total_habits": total_habits, "completion_pct": f"{completion_pct:.0f}",
            "best_streak": best_streak, "ai_insights": ai_insights,
            "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"📊 Your Weekly Health Report — {week_start} to {week_end}",
            html_body=html,
        )

    async def send_streak_milestone(
        self, user_email: str, user_name: str, habit_name: str, streak_days: int,
    ) -> bool:
        """Send a streak milestone celebration email."""
        html = self._render_template("streak_milestone.html", {
            "name": user_name, "habit_name": habit_name, "streak_days": streak_days,
            "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"🔥 {streak_days}-Day Streak on {habit_name}!",
            html_body=html,
        )

    async def send_export_ready(
        self, user_email: str, user_name: str, file_format: str,
        start_date: str, end_date: str, download_url: str,
    ) -> bool:
        """Send email when a data export is ready to download."""
        html = self._render_template("export_ready.html", {
            "name": user_name, "file_format": file_format,
            "start_date": start_date, "end_date": end_date,
            "download_url": download_url, "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject="📁 Your Health Tracker Export is Ready",
            html_body=html,
        )

    @staticmethod
    def _render_template(template_name: str, context: dict) -> str:
        """Render a Jinja2 HTML email template."""
        try:
            with open(f"{TEMPLATE_DIR}/{template_name}", "r", encoding="utf-8") as f:
                template = Template(f.read())
            return template.render(**context)
        except FileNotFoundError:
            logger.error("email_template_not_found", template=template_name)
            return f"<html><body><p>{context}</p></body></html>"
```

### Key Service Patterns

**Get-or-Create Pattern**
```python
async def get_settings(self, user_id):
    settings = result.scalar_one_or_none()
    if not settings:
        settings = NotificationSettings(user_id=user_id)  # Auto-create with defaults
        self.session.add(settings)
        await self.session.commit()
    return settings
```
First call for a user → creates the row with all defaults (reminders on, 08:00 AM). Every subsequent call → returns the existing row. The `unique=True` constraint prevents duplicates if two requests race.

**4 Email Methods — Same Pattern**
```python
async def send_daily_reminder(self, user_email, user_name, date_str) -> bool:
    html = self._render_template("daily_reminder.html", {context})
    return await self.email_provider.send(to_email, subject, html_body=html)
```
Every email method: (1) render the Jinja2 template with context, (2) call the provider's `send()`. The provider (Console/Resend/SES) handles the actual sending.

**`_render_template()` — Jinja2 File Loading**
```python
with open(f"{TEMPLATE_DIR}/{template_name}", "r") as f:
    template = Template(f.read())
return template.render(**context)
```
- Reads the HTML file from disk
- Creates a Jinja2 Template (same engine as prompt_templates.py in Part 08c)
- Renders with `**context` — unpacks the dict as keyword arguments
- Fallback: if template file is missing, returns a plain HTML fallback (not crash)

---

## 2. File 2: `tasks.py` — Background Task Definitions

### Type This Code: `backend/app/modules/notifications/tasks.py`

```python
# ============================================================================
# Notifications Module — Celery Tasks (Background Jobs)
# ============================================================================
# TASKS:
#   send_daily_reminders    → runs every day at 8 AM UTC
#   send_weekly_reports     → runs every Sunday at 9 AM UTC
#   check_streak_milestones → triggered when a new log is created
#
# NOTE: In production, Lambda functions (Part 15) replace Celery for these.
# ============================================================================

from app.shared.logging import get_logger

logger = get_logger(__name__)


async def send_daily_reminders() -> dict:
    """
    Send daily reminder emails to all users who have reminders enabled.

    Steps:
    1. Query all users with daily_reminder=True
    2. Filter: skip users who already logged today
    3. Send reminder email to each remaining user
    4. Log results
    """
    logger.info("task_started", task="send_daily_reminders")

    result = {
        "task": "send_daily_reminders",
        "status": "completed",
        "emails_sent": 0,
        "errors": 0,
    }

    logger.info("task_completed", **result)
    return result


async def send_weekly_reports() -> dict:
    """
    Generate and send weekly reports to all opted-in users.
    Triggers the weekly report agentic workflow for each user.
    """
    logger.info("task_started", task="send_weekly_reports")

    result = {
        "task": "send_weekly_reports",
        "status": "completed",
        "reports_generated": 0,
        "emails_sent": 0,
        "errors": 0,
    }

    logger.info("task_completed", **result)
    return result


async def check_streak_milestones(user_id: str, habit_id: str) -> dict:
    """
    Check if a user just hit a streak milestone.
    Milestones: 7, 14, 21, 30, 60, 90, 100, 180, 365 days.
    """
    MILESTONES = [7, 14, 21, 30, 60, 90, 100, 180, 365]

    logger.info("task_started", task="check_streak_milestones",
                user_id=user_id, habit_id=habit_id)

    result = {
        "task": "check_streak_milestones",
        "user_id": user_id,
        "habit_id": habit_id,
        "milestone_hit": None,
        "email_sent": False,
    }

    logger.info("task_completed", **result)
    return result
```

**These are task DEFINITIONS** — the structure that Lambda (Part 15) or Celery fills in with real logic. The pattern is clear: query users → check conditions → send emails → log results.

---

## 3. File 3: `router.py` — 3 Endpoints

### Type This Code: `backend/app/modules/notifications/router.py`

```python
# ============================================================================
# Notifications Module — Router
# ============================================================================
# ENDPOINTS:
#   GET  /api/v1/notifications/settings     → Get preferences
#   PUT  /api/v1/notifications/settings     → Update preferences
#   POST /api/v1/notifications/test-email   → Send a test email
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.auth.router import get_current_user_id
from app.modules.auth.service import AuthService
from app.modules.notifications.schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    TestEmailRequest,
)
from app.modules.notifications.service import NotificationService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()


async def get_notification_service(
    session: AsyncSession = Depends(get_async_session),
) -> NotificationService:
    return NotificationService(session)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Get notification preferences",
)
async def get_settings(
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationSettingsResponse:
    """Get the current user's notification preferences."""
    settings = await service.get_settings(user_id)
    return NotificationSettingsResponse.model_validate(settings)


@router.put(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Update notification preferences",
)
async def update_settings(
    data: NotificationSettingsUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationSettingsResponse:
    """Update notification preferences. Only provided fields are changed."""
    settings = await service.update_settings(user_id, data)
    return NotificationSettingsResponse.model_validate(settings)


@router.post(
    "/test-email",
    response_model=SuccessResponse,
    summary="Send a test email",
)
async def send_test_email(
    data: TestEmailRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
) -> SuccessResponse:
    """Send a test email to verify email settings are working."""
    from app.shared.date_utils import today_utc

    auth_service = AuthService(session, redis_client)
    user = await auth_service.get_current_user(user_id)
    service = NotificationService(session)

    sent = await service.send_daily_reminder(
        user_email=user.email,
        user_name=user.full_name,
        date_str=str(today_utc()),
    )

    if sent:
        return SuccessResponse(message="Test email sent successfully! Check your inbox.")
    return SuccessResponse(message="Failed to send test email. Check email provider settings.")
```

### Key Router Pattern: Test Email

The `POST /test-email` endpoint lets users verify their email configuration works. It:
1. Gets the user's email from the Auth module (cross-module dependency)
2. Sends a real daily reminder email using the configured provider
3. Returns success/failure message

In development (ConsoleProvider), this prints the email to the terminal — user can see exactly what it looks like.

---

## 4. How to Verify Your Work

```bash
docker-compose exec backend python -c "
from app.modules.notifications.service import NotificationService
from app.modules.notifications.email_provider import get_email_provider
provider = get_email_provider()
print(f'Email provider: {type(provider).__name__}')
print('✅ All notification files import OK')
"

# Test settings endpoint
curl http://localhost/api/v1/notifications/settings \
  -H "Authorization: Bearer TOKEN"
# Expected: 200 with default settings (all enabled, 08:00)

# Update reminder time
curl -X PUT http://localhost/api/v1/notifications/settings \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reminder_time":"20:30","daily_reminder":false}'
# Expected: 200 with updated settings

# Send test email
curl -X POST http://localhost/api/v1/notifications/test-email \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_type":"daily_reminder"}'
# Expected: 200 + email printed to backend terminal (console mode)
```

---

## 5. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **Get-or-create pattern** | Query → if None → create with defaults | service.get_settings() |
| 2 | **`model_dump(exclude_unset=True)`** | Only update fields the client sent | service.update_settings() |
| 3 | **`_render_template()`** | Load Jinja2 HTML file + render with context | All send_* methods |
| 4 | **Template fallback** | Return plain HTML if template file missing | _render_template except |
| 5 | **Task structure** | query users → check condition → send email → log | tasks.py |
| 6 | **Cross-module auth** | AuthService to get user email for test-email | router.py test endpoint |
| 7 | **`MILESTONES` list** | [7, 14, 21, 30, 60, 90, 100, 180, 365] | tasks.py |

---

## 6. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 13a: Models, Schemas, Email Provider](./phase4-part13a-notifications-models-schemas-email-provider.md) |
| ➡️ Next | [Part 13c: Email Templates & Migration](./phase4-part13c-notifications-templates-migration.md) |

---

**End of Phase 4 Part 13b: Service, Tasks & Router**
