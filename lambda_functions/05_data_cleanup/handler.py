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

    # 1. Delete expired token blacklist entries (if stored in DB)
    # In our app, token blacklist is in Redis (auto-expires), so this is for any
    # DB-based cleanup patterns.

    # 2. Delete old AI chat messages (older than 90 days)
    results["old_chats"] = execute_update("""
        DELETE FROM ai_chat_messages
        WHERE created_at < NOW() - INTERVAL '90 days'
    """)

    # 3. Delete old AI insights (older than 180 days, except weekly reports)
    results["old_insights"] = execute_update("""
        DELETE FROM ai_insights
        WHERE created_at < NOW() - INTERVAL '180 days'
          AND insight_type != 'weekly_report'
    """)

    # 4. Delete failed document processing attempts (older than 30 days)
    results["failed_docs"] = execute_update("""
        DELETE FROM documents
        WHERE status = 'failed'
          AND created_at < NOW() - INTERVAL '30 days'
    """)

    # 5. VACUUM ANALYZE for PostgreSQL performance
    # VACUUM reclaims storage from deleted rows
    # ANALYZE updates query planner statistics
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
