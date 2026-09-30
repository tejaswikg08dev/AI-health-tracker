"""
Lambda 1: Daily Habit Reminder
Trigger: EventBridge cron (8 AM UTC daily)
Flow: Query users with reminders ON + not logged today → Send email via SES
"""

import json
from datetime import date

import sys
sys.path.insert(0, "..")
from shared.db_utils import execute_query
from shared.email_utils import send_email


def lambda_handler(event, context):
    today = str(date.today())

    # Find users who: have reminders enabled AND haven't logged today
    users = execute_query("""
        SELECT u.id, u.email, u.full_name
        FROM users u
        JOIN notification_settings ns ON u.id = ns.user_id
        WHERE ns.daily_reminder = true
          AND u.is_active = true
          AND u.id NOT IN (
              SELECT DISTINCT user_id FROM habit_logs WHERE log_date = %(today)s
          )
    """, {"today": today})

    sent_count = 0
    errors = []

    for user in users:
        try:
            html = f"""
            <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
                <h2>🏥 Hey {user['full_name']}!</h2>
                <p>Time to log your habits for <strong>{today}</strong>.</p>
                <p>Keep your streaks alive! 🔥</p>
            </div>
            """
            success = send_email(
                to_email=user["email"],
                subject=f"🏥 Time to log your habits — {today}",
                html_body=html,
            )
            if success:
                sent_count += 1
        except Exception as e:
            errors.append({"user_id": str(user["id"]), "error": str(e)})

    result = {
        "statusCode": 200,
        "body": json.dumps({
            "date": today,
            "users_found": len(users),
            "emails_sent": sent_count,
            "errors": len(errors),
        }),
    }
    print(json.dumps(result))
    return result
