# ============================================================================
# Health Tracker — Celery Application
# ============================================================================
# WHAT THIS FILE DOES:
#   Configures Celery — the background task queue.
#   Celery processes tasks asynchronously (outside the request/response cycle).
#
# WHY CELERY:
#   Some operations are too slow for an API response:
#   - Sending emails (2-5 seconds)
#   - Generating PDF reports (10-30 seconds)
#   - AI weekly analysis (30-60 seconds)
#
#   Instead of making the user wait, we:
#   1. Accept the request immediately: "Report generation started!"
#   2. Queue the work in Redis
#   3. Celery worker picks it up and processes in the background
#   4. User is notified when done (email, or poll status endpoint)
#
# ARCHITECTURE:
#   FastAPI → Redis (message broker) → Celery Worker → Task completed
#   Celery Beat (scheduler) → Redis → Celery Worker → Periodic tasks
# ============================================================================

from celery import Celery

from app.config import get_settings

settings = get_settings()

# Create Celery app with Redis as both broker and result backend
celery_app = Celery(
    "health_tracker",
    broker=settings.REDIS_URL,          # Where tasks are queued
    backend=settings.REDIS_URL,         # Where task results are stored
)

# Celery configuration
celery_app.conf.update(
    # Serialization: use JSON (readable, debuggable) not pickle (security risk)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution limits
    task_soft_time_limit=300,        # Warn after 5 minutes
    task_time_limit=600,             # Kill after 10 minutes

    # Retry policy
    task_acks_late=True,             # Acknowledge AFTER processing (not before)
    worker_prefetch_multiplier=1,    # Take one task at a time (fair scheduling)

    # Task result expiry (cleanup old results after 24 hours)
    result_expires=86400,
)

# Auto-discover tasks in all module 'tasks.py' files
# When we add tasks to notifications/tasks.py, Celery finds them automatically
celery_app.autodiscover_tasks([
    "app.modules.notifications",
], force=True)

# ── Celery Beat Schedule (Periodic Tasks) ──
# These run on a schedule, like cron jobs.
# Celery Beat is a separate process that submits tasks at the right time.
celery_app.conf.beat_schedule = {
    # Daily reminder: every day at 8:00 AM UTC
    # (In production, you'd use Lambda + EventBridge instead)
    # "send-daily-reminders": {
    #     "task": "app.modules.notifications.tasks.send_daily_reminders",
    #     "schedule": crontab(hour=8, minute=0),
    # },
    # Weekly report: every Sunday at 9:00 AM UTC
    # "generate-weekly-reports": {
    #     "task": "app.modules.notifications.tasks.generate_weekly_reports",
    #     "schedule": crontab(hour=9, minute=0, day_of_week=0),
    # },
}
