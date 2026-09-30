"""
Lambda 4: Streak Milestone Checker
Trigger: SQS message (from FastAPI on new log creation)
Flow: Calculate streak → Check milestones (7,30,100 days) → Send congrats email
"""

import json
from datetime import date

import sys
sys.path.insert(0, "..")
from shared.db_utils import execute_query, execute_update
from shared.email_utils import send_email

MILESTONES = [7, 14, 21, 30, 60, 90, 100, 180, 365]


def lambda_handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        user_id = message["user_id"]
        habit_id = message["habit_id"]

        # Get user + habit info
        user_rows = execute_query(
            "SELECT email, full_name FROM users WHERE id = %(uid)s",
            {"uid": user_id},
        )
        habit_rows = execute_query(
            "SELECT name FROM habits WHERE id = %(hid)s",
            {"hid": habit_id},
        )

        if not user_rows or not habit_rows:
            continue

        user = user_rows[0]
        habit_name = habit_rows[0]["name"]

        # Calculate current streak using gaps-and-islands
        streak_rows = execute_query("""
            WITH numbered AS (
                SELECT log_date,
                       log_date - (ROW_NUMBER() OVER (ORDER BY log_date))::int * INTERVAL '1 day' AS grp
                FROM habit_logs
                WHERE habit_id = %(hid)s AND user_id = %(uid)s
                  AND (value_numeric IS NOT NULL OR value_boolean = true OR value_scale IS NOT NULL)
            )
            SELECT COUNT(*) as streak_length, MAX(log_date) as last_date
            FROM numbered
            GROUP BY grp
            HAVING MAX(log_date) >= CURRENT_DATE - INTERVAL '1 day'
            ORDER BY MAX(log_date) DESC
            LIMIT 1
        """, {"hid": habit_id, "uid": user_id})

        if not streak_rows:
            continue

        current_streak = streak_rows[0]["streak_length"]

        # Check if this is a milestone
        if current_streak not in MILESTONES:
            continue

        # Idempotency: check if we already sent this milestone
        already_sent = execute_query("""
            SELECT 1 FROM ai_insights
            WHERE user_id = %(uid)s
              AND insight_type = 'streak_milestone'
              AND title LIKE %(pattern)s
            LIMIT 1
        """, {"uid": user_id, "pattern": f"%{habit_name}%{current_streak}%"})

        if already_sent:
            continue

        # Record milestone
        execute_update("""
            INSERT INTO ai_insights (id, user_id, insight_type, title, content, tokens_used)
            VALUES (uuid_generate_v4(), %(uid)s, 'streak_milestone',
                    %(title)s, %(content)s, 0)
        """, {
            "uid": user_id,
            "title": f"🔥 {current_streak}-Day Streak: {habit_name}",
            "content": f"Congratulations! You've logged {habit_name} for {current_streak} consecutive days!",
        })

        # Send celebration email
        send_email(
            to_email=user["email"],
            subject=f"🔥 {current_streak}-Day Streak on {habit_name}!",
            html_body=f"""
            <div style="font-family: sans-serif; text-align: center; max-width: 500px; margin: 0 auto;">
                <div style="font-size: 64px;">🔥</div>
                <h2>{current_streak}-Day Streak!</h2>
                <p>Incredible work on <strong>{habit_name}</strong>, {user['full_name']}!</p>
                <p>You've logged this habit for <strong>{current_streak} consecutive days</strong>.</p>
            </div>
            """,
        )

        print(f"Milestone! {user['full_name']}: {habit_name} — {current_streak} days")

    return {"statusCode": 200}
