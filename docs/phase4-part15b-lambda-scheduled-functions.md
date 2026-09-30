# ☁️ Phase 4 Part 15b: Lambda — Scheduled Functions (Lambdas 1, 2, 5)

> **"Three cron-triggered Lambdas: daily reminder emails at 8 AM, AI weekly reports every Sunday, monthly data cleanup. Each runs on schedule, queries the database, does its job, and logs the results."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part15a-lambda-shared-sam-template.md](./phase4-part15a-lambda-shared-sam-template.md) |
| **Next** | [phase4-part15c-lambda-event-driven-functions.md](./phase4-part15c-lambda-event-driven-functions.md) |
| **Files in This Doc** | 3 handler.py files (daily_reminder, weekly_report, data_cleanup) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (SQL in Lambda, Groq API call, VACUUM ANALYZE) |

---

## 1. Lambda 1: Daily Reminder (`01_daily_reminder/handler.py`)

### Type This Code:

```python
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
```

### Key Implementation Details

**The SQL: "Find users who haven't logged today"**
```sql
SELECT u.id, u.email, u.full_name
FROM users u
JOIN notification_settings ns ON u.id = ns.user_id
WHERE ns.daily_reminder = true           -- reminders enabled
  AND u.is_active = true                 -- active account
  AND u.id NOT IN (                      -- NOT already logged today
      SELECT DISTINCT user_id FROM habit_logs WHERE log_date = %(today)s
  )
```
- JOINs `users` with `notification_settings` — only gets users with reminders ON
- `NOT IN` subquery — excludes users who have ANY log for today
- Even if a user logged 1 of 6 habits, they're excluded (they've started, they'll finish)
- This is intentional: once you start logging, the reminder would be annoying

**`sys.path.insert(0, "..")`**
```python
import sys
sys.path.insert(0, "..")
from shared.db_utils import execute_query
```
- Lambda functions run from their own directory (`01_daily_reminder/`)
- `shared/` is one level up — `sys.path.insert(0, "..")` adds the parent to Python's import path
- In production deployment, SAM packages shared/ with each function's code

**Every user in a try/except**
```python
for user in users:
    try:
        send_email(...)
        sent_count += 1
    except Exception as e:
        errors.append(...)
```
- If one user's email fails, the others still get sent
- Never abort the entire batch because of one failure
- Results are logged: `"users_found": 30, "emails_sent": 28, "errors": 2`

---

## 2. Lambda 2: Weekly AI Report (`02_weekly_report/handler.py`)

### Type This Code:

```python
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
```

### Key: Lambda Uses Groq (Not Ollama)

**Why Groq in Lambda?**
- Lambda runs in AWS — can't access a local Ollama server
- Groq's free tier: 14,400 requests/day — more than enough for weekly reports
- Same API format as OpenAI (`/chat/completions`) — familiar from Part 08b
- httpx call instead of our Strategy pattern — Lambda is standalone, doesn't import the FastAPI app

**Graceful degradation:**
```python
if not GROQ_API_KEY:
    return "<p><em>AI analysis unavailable — set GROQ_API_KEY.</em></p>"
```
If the API key isn't configured, the report still generates — just without AI analysis. Raw data is still useful.

---

## 3. Lambda 5: Data Cleanup (`05_data_cleanup/handler.py`)

### Type This Code:

```python
"""
Lambda 5: Monthly Data Cleanup
Trigger: EventBridge cron (1st of every month)
Flow: Delete expired tokens, old chats, orphaned S3 files, VACUUM
"""

import json
from datetime import datetime

import sys
sys.path.insert(0, "..")
from shared.db_utils import execute_update, get_db_connection


def lambda_handler(event, context):
    results = {}

    # 1. Delete old AI chat messages (older than 90 days)
    results["old_chats"] = execute_update("""
        DELETE FROM ai_chat_messages
        WHERE created_at < NOW() - INTERVAL '90 days'
    """)

    # 2. Delete old AI insights (older than 180 days, except weekly reports)
    results["old_insights"] = execute_update("""
        DELETE FROM ai_insights
        WHERE created_at < NOW() - INTERVAL '180 days'
          AND insight_type != 'weekly_report'
    """)

    # 3. Delete failed document processing attempts (older than 30 days)
    results["failed_docs"] = execute_update("""
        DELETE FROM documents
        WHERE status = 'failed'
          AND created_at < NOW() - INTERVAL '30 days'
    """)

    # 4. VACUUM ANALYZE for PostgreSQL performance
    try:
        conn = get_db_connection()
        conn.autocommit = True  # VACUUM can't run inside a transaction
        with conn.cursor() as cur:
            cur.execute("VACUUM ANALYZE habit_logs")
            cur.execute("VACUUM ANALYZE ai_chat_messages")
        conn.autocommit = False
        results["vacuum"] = "completed"
    except Exception as e:
        results["vacuum"] = f"error: {e}"

    result = {
        "statusCode": 200,
        "body": json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "results": results,
        }),
    }
    print(json.dumps(result))
    return result
```

### Key: VACUUM ANALYZE

```python
conn.autocommit = True  # VACUUM can't run inside a transaction
cur.execute("VACUUM ANALYZE habit_logs")
```

**What is VACUUM?** PostgreSQL doesn't immediately delete rows when you `DELETE` — it marks them as "dead." `VACUUM` reclaims that space. Without it, the table grows forever.

**What is ANALYZE?** Updates PostgreSQL's query planner statistics — helps it choose the best indexes and query plans.

**Why `autocommit = True`?** VACUUM can't run inside a transaction block. psycopg2 opens a transaction by default, so we switch to autocommit mode temporarily.

**Data Retention Policy:**
| Data | Retention | Why |
|------|-----------|-----|
| Chat messages | 90 days | Conversation context is short-lived |
| On-demand insights | 180 days | Useful for review, but not forever |
| Weekly reports | ∞ (kept) | `insight_type != 'weekly_report'` — permanently preserved |
| Failed documents | 30 days | Processing errors are temporary |

---

## 4. What You Learned

| # | Concept | Where Used |
|---|---------|-----------|
| 1 | **SQL `NOT IN` subquery** | Daily reminder: find users who haven't logged |
| 2 | **Groq API in Lambda** | Weekly report: free LLM call via httpx |
| 3 | **Graceful degradation** | No API key → skip AI analysis, keep raw data |
| 4 | **VACUUM ANALYZE** | Cleanup: reclaim dead rows, update query planner |
| 5 | **`autocommit = True`** | VACUUM requires no active transaction |
| 6 | **Data retention policy** | Different TTLs for different data types |
| 7 | **Per-user try/except** | One failure doesn't block other users |
| 8 | **`sys.path.insert`** | Import shared/ from parent directory |

---

## 5. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 15a: Shared + SAM](./phase4-part15a-lambda-shared-sam-template.md) |
| ➡️ Next | [Part 15c: Event-Driven Functions](./phase4-part15c-lambda-event-driven-functions.md) |

---

**End of Phase 4 Part 15b: Scheduled Functions**
