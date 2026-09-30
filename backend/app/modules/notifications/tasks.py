# ============================================================================
# Notifications Module — Celery Tasks (Background Jobs)
# ============================================================================
# WHAT THIS FILE DOES:
#   Defines background tasks that run on a schedule (via Celery Beat)
#   or triggered by events (via Celery worker).
#
# TASKS:
#   send_daily_reminders  → runs every day at 8 AM UTC
#   send_weekly_reports   → runs every Sunday at 9 AM UTC
#   check_streak_milestones → triggered when a new log is created
#
# WHY BACKGROUND TASKS:
#   Sending 100 emails takes 10-30 seconds.
#   You can't block an API response for that long.
#   Celery processes these asynchronously — the user doesn't wait.
#
# NOTE: These tasks use synchronous DB access (not async)
#   because Celery workers run in a separate process from FastAPI.
#   In production, you might use Lambda instead of Celery for these tasks.
# ============================================================================

from app.shared.logging import get_logger

logger = get_logger(__name__)

# These tasks would be registered with Celery in a production setup.
# For now, they're placeholder functions that show the structure.
# In production, decorate with @celery_app.task


async def send_daily_reminders() -> dict:
    """
    Send daily reminder emails to all users who have reminders enabled.

    Runs via Celery Beat schedule (every day at 8 AM UTC).
    In production, this would be an AWS Lambda triggered by EventBridge.

    Steps:
    1. Query all users with daily_reminder=True
    2. Filter: skip users who already logged today
    3. Send reminder email to each remaining user
    4. Log results
    """
    logger.info("task_started", task="send_daily_reminders")

    # In production, this would:
    # 1. Connect to the database
    # 2. Query users needing reminders
    # 3. Send emails in batches
    # 4. Return count of emails sent

    # Placeholder — structure shows the pattern
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

    Runs via Celery Beat schedule (every Sunday at 9 AM UTC).
    In production, this triggers the weekly report agentic workflow
    for each user and sends the result via email.
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

    Triggered when a new habit log is created (event-driven).
    Milestones: 7, 14, 21, 30, 60, 90, 100, 180, 365 days.

    In production, this would be triggered via SQS → Lambda.
    """
    MILESTONES = [7, 14, 21, 30, 60, 90, 100, 180, 365]

    logger.info(
        "task_started",
        task="check_streak_milestones",
        user_id=user_id,
        habit_id=habit_id,
    )

    # In production:
    # 1. Calculate current streak for this habit
    # 2. Check if it's a milestone number
    # 3. Check if we already sent this milestone (idempotency)
    # 4. If new milestone, send celebration email

    result = {
        "task": "check_streak_milestones",
        "user_id": user_id,
        "habit_id": habit_id,
        "milestone_hit": None,
        "email_sent": False,
    }

    logger.info("task_completed", **result)
    return result
