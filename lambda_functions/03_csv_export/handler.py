"""
Lambda 3: Async CSV Export
Trigger: SQS message (from FastAPI POST /export/csv)
Flow: Query logs → Generate CSV → Upload to S3 → Email download link
"""

import csv
import io
import json

import sys
sys.path.insert(0, "..")
from shared.db_utils import execute_query
from shared.email_utils import send_email
from shared.s3_utils import upload_file, generate_presigned_url


def lambda_handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        user_id = message["user_id"]
        start_date = message["start_date"]
        end_date = message["end_date"]
        user_email = message["user_email"]
        user_name = message.get("user_name", "User")

        # Query log data
        logs = execute_query("""
            SELECT hl.log_date, h.name AS habit_name, h.habit_type, h.unit,
                   hl.value_numeric, hl.value_boolean, hl.value_scale, hl.notes
            FROM habit_logs hl
            JOIN habits h ON hl.habit_id = h.id
            WHERE hl.user_id = %(uid)s
              AND hl.log_date >= %(start)s AND hl.log_date <= %(end)s
            ORDER BY hl.log_date, h.name
        """, {"uid": user_id, "start": start_date, "end": end_date})

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Habit", "Type", "Value", "Unit", "Notes"])

        for log in logs:
            if log["habit_type"] == "numeric":
                value = log["value_numeric"]
            elif log["habit_type"] == "boolean":
                value = "Yes" if log["value_boolean"] else "No"
            else:
                value = log["value_scale"]

            writer.writerow([
                str(log["log_date"]), log["habit_name"], log["habit_type"],
                value, log["unit"] or "", log["notes"] or "",
            ])

        csv_bytes = output.getvalue().encode("utf-8")
        output.close()

        # Upload to S3
        s3_key = f"exports/{user_id}/{start_date}_to_{end_date}.csv"
        upload_file(s3_key, csv_bytes, "text/csv")

        # Generate presigned download URL (24 hours)
        download_url = generate_presigned_url(s3_key, expires_in=86400)

        # Send email with download link
        send_email(
            to_email=user_email,
            subject="📁 Your Health Tracker Export is Ready",
            html_body=f"""
            <div style="font-family: sans-serif; max-width: 500px; margin: 0 auto;">
                <h2>Your export is ready, {user_name}! 📁</h2>
                <p>Period: {start_date} to {end_date}</p>
                <p>Rows: {len(logs)}</p>
                <a href="{download_url}" style="display: inline-block; background: #10B981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none;">Download CSV →</a>
                <p style="color: #999; font-size: 12px; margin-top: 16px;">Link expires in 24 hours.</p>
            </div>
            """,
        )

        print(f"Export complete: {user_id}, {len(logs)} rows, {len(csv_bytes)} bytes")

    return {"statusCode": 200, "body": json.dumps({"status": "complete"})}
