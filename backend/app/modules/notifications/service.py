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

# Load email templates
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

        logger.info("notification_settings_updated", user_id=str(user_id), fields=list(update_data.keys()))
        return settings

    async def send_daily_reminder(
        self, user_email: str, user_name: str, date_str: str
    ) -> bool:
        """Send a daily habit reminder email."""
        html = self._render_template("daily_reminder.html", {
            "name": user_name,
            "date": date_str,
            "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"🏥 Time to log your habits — {date_str}",
            html_body=html,
        )

    async def send_weekly_report(
        self,
        user_email: str,
        user_name: str,
        week_start: str,
        week_end: str,
        total_habits: int,
        completion_pct: float,
        best_streak: str,
        ai_insights: str,
    ) -> bool:
        """Send the weekly health report email."""
        html = self._render_template("weekly_report.html", {
            "name": user_name,
            "week_start": week_start,
            "week_end": week_end,
            "total_habits": total_habits,
            "completion_pct": f"{completion_pct:.0f}",
            "best_streak": best_streak,
            "ai_insights": ai_insights,
            "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"📊 Your Weekly Health Report — {week_start} to {week_end}",
            html_body=html,
        )

    async def send_streak_milestone(
        self,
        user_email: str,
        user_name: str,
        habit_name: str,
        streak_days: int,
    ) -> bool:
        """Send a streak milestone celebration email."""
        html = self._render_template("streak_milestone.html", {
            "name": user_name,
            "habit_name": habit_name,
            "streak_days": streak_days,
            "app_url": "http://localhost:3000",
        })
        return await self.email_provider.send(
            to_email=user_email,
            subject=f"🔥 {streak_days}-Day Streak on {habit_name}!",
            html_body=html,
        )

    async def send_export_ready(
        self,
        user_email: str,
        user_name: str,
        file_format: str,
        start_date: str,
        end_date: str,
        download_url: str,
    ) -> bool:
        """Send email when a data export is ready to download."""
        html = self._render_template("export_ready.html", {
            "name": user_name,
            "file_format": file_format,
            "start_date": start_date,
            "end_date": end_date,
            "download_url": download_url,
            "app_url": "http://localhost:3000",
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
            # Fallback: plain text
            return f"<html><body><p>{context}</p></body></html>"
