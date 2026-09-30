"""
Lambda 2: Weekly AI Report Generator
Trigger: EventBridge cron (Sunday 9 AM UTC)
Flow: Gather week data → Call Groq LLM → Generate HTML → Save to S3 → Email
"""

import json
from datetime import date, timedelta

import httpx

import sys
sys.path.insert(0, "..")
from shared.config import GROQ_API_KEY
from shared.db_utils import execute_query, execute_update
from shared.email_utils import send_email
from shared.s3_utils import upload_file


def lambda_handler(event, context):
    today = date.today()
    week_start = today - timedelta(days=today.weekday() + 7)  # Last Monday
    week_end = week_start + timedelta(days=6)

    # Get users with weekly reports enabled
    users = execute_query("""
        SELECT u.id, u.email, u.full_name
        FROM users u
        JOIN notification_settings ns ON u.id = ns.user_id
        WHERE ns.weekly_report = true AND u.is_active = true
    """)

    reports_sent = 0

    for user in users:
        try:
            # Step 1: Gather data
            data_summary = _gather_data(user["id"], week_start, week_end)

            # Step 2: AI analysis (via Groq — free)
            analysis = _generate_ai_analysis(data_summary, user["full_name"])

            # Step 3: Build HTML report
            report_html = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
                <h1>🏥 Weekly Health Report</h1>
                <p>Hi {user['full_name']}! Here's your week ({week_start} to {week_end}).</p>
                <div style="background: #f0f9ff; padding: 16px; border-radius: 8px;">
                    {analysis}
                </div>
                <hr>
                <h3>Raw Data</h3>
                <pre style="font-size: 12px;">{data_summary}</pre>
            </div>
            """

            # Step 4: Save to S3
            s3_key = f"reports/{user['id']}/{today}.html"
            upload_file(s3_key, report_html.encode("utf-8"), "text/html")

            # Step 5: Send email
            send_email(user["email"], f"📊 Weekly Health Report — {week_start} to {week_end}", report_html)
            reports_sent += 1

        except Exception as e:
            print(f"Error for user {user['id']}: {e}")

    return {"statusCode": 200, "body": json.dumps({"reports_sent": reports_sent})}


def _gather_data(user_id, week_start, week_end) -> str:
    """Gather habit log data for the week."""
    logs = execute_query("""
        SELECT hl.log_date, h.name, h.habit_type,
               hl.value_numeric, hl.value_boolean, hl.value_scale
        FROM habit_logs hl
        JOIN habits h ON hl.habit_id = h.id
        WHERE hl.user_id = %(uid)s AND hl.log_date >= %(start)s AND hl.log_date <= %(end)s
        ORDER BY hl.log_date, h.name
    """, {"uid": str(user_id), "start": str(week_start), "end": str(week_end)})

    lines = [f"Week: {week_start} to {week_end}\n"]
    for log in logs:
        val = log.get("value_numeric") or log.get("value_scale") or ("Yes" if log.get("value_boolean") else "No")
        lines.append(f"  {log['log_date']} | {log['name']}: {val}")
    return "\n".join(lines)


def _generate_ai_analysis(data_summary: str, user_name: str) -> str:
    """Call Groq LLM for AI analysis (free tier)."""
    if not GROQ_API_KEY:
        return "<p><em>AI analysis unavailable — set GROQ_API_KEY.</em></p>"

    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a health coach. Analyze this weekly data and give 3 brief insights with recommendations. Use HTML formatting."},
                    {"role": "user", "content": f"User: {user_name}\n\n{data_summary}"},
                ],
                "temperature": 0.4,
                "max_tokens": 500,
            },
            timeout=30.0,
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"<p>AI analysis error: {e}</p>"
