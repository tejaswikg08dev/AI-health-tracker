# ☁️ Phase 4 Part 15c: Lambda — Event-Driven Functions (Lambdas 3, 4, 6)

> **"Three event-triggered Lambdas: CSV export (SQS → generate → S3 → email link), streak milestone (SQS → calculate → check → celebrate), document processor (S3 upload → extract → chunk → embed → pgvector). Each responds to an event, processes, and returns."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Previous** | [phase4-part15b-lambda-scheduled-functions.md](./phase4-part15b-lambda-scheduled-functions.md) |
| **Next** | [phase4-part15d-lambda-connections-and-flows.md](./phase4-part15d-lambda-connections-and-flows.md) |
| **Files in This Doc** | 3 handler.py files |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Hard (SQS message parsing, gaps-and-islands SQL, S3 event structure, pgvector INSERT) |

---

## 1. Lambda 3: CSV Export (`03_csv_export/handler.py`)

**Trigger:** SQS message (API sends message when user requests large export)

### Type This Code:

```python
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
                <a href="{download_url}" style="display: inline-block; background: #10B981;
                   color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none;">
                   Download CSV →</a>
                <p style="color: #999; font-size: 12px;">Link expires in 24 hours.</p>
            </div>
            """,
        )

        print(f"Export complete: {user_id}, {len(logs)} rows, {len(csv_bytes)} bytes")

    return {"statusCode": 200, "body": json.dumps({"status": "complete"})}
```

### SQS Message Format

The FastAPI API sends an SQS message like:
```json
{
    "user_id": "uuid-001",
    "start_date": "2026-01-01",
    "end_date": "2026-09-30",
    "user_email": "shreya@test.com",
    "user_name": "Shreya"
}
```

Lambda receives it in `event["Records"][0]["body"]` as a JSON string → `json.loads()` → dict.

**`for record in event["Records"]:`** — SQS can batch multiple messages (though we set `BatchSize: 1` in SAM). The loop handles any batch size.

---

## 2. Lambda 4: Streak Milestone (`04_streak_milestone/handler.py`)

**Trigger:** SQS message (sent when a user creates a new habit log)

### Type This Code:

```python
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
                       log_date - (ROW_NUMBER() OVER (ORDER BY log_date))::int
                         * INTERVAL '1 day' AS grp
                FROM habit_logs
                WHERE habit_id = %(hid)s AND user_id = %(uid)s
                  AND (value_numeric IS NOT NULL OR value_boolean = true
                       OR value_scale IS NOT NULL)
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
            "content": f"Congratulations! You've logged {habit_name} for "
                       f"{current_streak} consecutive days!",
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
```

### Key: Gaps-and-Islands SQL in Lambda

```sql
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
```

Same algorithm from Part 07b (Analytics repository), simplified for one habit. The Lambda version only calculates the CURRENT streak for ONE habit (not all habits like the analytics version).

### Key: Idempotency Check

```python
already_sent = execute_query("""
    SELECT 1 FROM ai_insights
    WHERE user_id = %(uid)s
      AND insight_type = 'streak_milestone'
      AND title LIKE %(pattern)s
    LIMIT 1
""", {"uid": user_id, "pattern": f"%{habit_name}%{current_streak}%"})

if already_sent:
    continue  # Already celebrated this milestone
```

SQS has **at-least-once delivery** — the same message might be delivered twice. Without idempotency, the user gets 2 "30-day streak!" emails. By checking the database first, we ensure exactly-once celebration.

---

## 3. Lambda 6: Document Processor (`06_document_processor/handler.py`)

**Trigger:** S3 event (file uploaded to `documents/` prefix)

### Type This Code:

```python
"""
Lambda 6: RAG Document Processor
Trigger: S3 PutObject event (user uploads PDF via FastAPI)
Flow: Download from S3 → Extract text → Chunk → Embed → Store in pgvector
"""

import json
import uuid

import httpx

import sys
sys.path.insert(0, "..")
from shared.config import GROQ_API_KEY
from shared.db_utils import execute_update, get_db_connection
from shared.s3_utils import download_file

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]

        # Parse key: documents/{user_id}/{document_id}/{filename}
        parts = key.split("/")
        if len(parts) < 4:
            print(f"Unexpected key format: {key}")
            continue

        user_id = parts[1]
        document_id = parts[2]
        filename = parts[3]

        print(f"Processing: {filename} (user={user_id}, doc={document_id})")

        try:
            # Step 1: Download file from S3
            file_content = download_file(key)

            # Step 2: Extract text
            if filename.lower().endswith(".pdf"):
                text = _extract_pdf_text(file_content)
            else:
                text = file_content.decode("utf-8", errors="replace")

            if not text.strip():
                _update_doc_status(document_id, "failed", "No text content extracted")
                continue

            # Step 3: Chunk the text
            chunks = _chunk_text(text)

            # Step 4: Generate embeddings (placeholder — zero vectors)
            embeddings = _generate_embeddings([c["text"] for c in chunks])

            # Step 5: Store chunks with embeddings in pgvector
            conn = get_db_connection()
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings):
                    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                    cur.execute("""
                        INSERT INTO document_chunks
                        (id, document_id, user_id, chunk_text, chunk_index,
                         page_number, token_count, embedding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, NOW())
                    """, (
                        str(uuid.uuid4()), document_id, user_id,
                        chunk["text"], chunk["index"], chunk.get("page"),
                        len(chunk["text"]) // 4, embedding_str,
                    ))
                conn.commit()

            # Update document status
            _update_doc_status(document_id, "processed", None, len(chunks))
            print(f"✅ Processed {filename}: {len(chunks)} chunks")

        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            _update_doc_status(document_id, "failed", str(e)[:500])

    return {"statusCode": 200}


def _extract_pdf_text(content: bytes) -> str:
    import io
    from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())


def _chunk_text(text: str) -> list[dict]:
    chunks = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) >= 50:
            chunks.append({"text": chunk_text, "index": index, "page": None})
            index += 1
        start = end - CHUNK_OVERLAP
    return chunks


def _generate_embeddings(texts: list[str]) -> list[list[float]]:
    # Placeholder — returns zero vectors (768 dimensions)
    # In production: call Groq/OpenAI embedding API
    return [[0.0] * 768 for _ in texts]


def _update_doc_status(doc_id, status, error=None, chunk_count=0):
    if error:
        execute_update(
            "UPDATE documents SET status=%(s)s, error_message=%(e)s WHERE id=%(id)s",
            {"s": status, "e": error, "id": doc_id},
        )
    else:
        execute_update(
            "UPDATE documents SET status=%(s)s, chunk_count=%(c)s WHERE id=%(id)s",
            {"s": status, "c": chunk_count, "id": doc_id},
        )
```

### S3 Event Structure

Lambda receives:
```json
{
    "Records": [{
        "s3": {
            "bucket": {"name": "health-tracker"},
            "object": {"key": "documents/uuid-001/doc-001/Sleep Guide.pdf"}
        }
    }]
}
```

We parse the key to extract `user_id`, `document_id`, and `filename`.

### This Is the RAG Pipeline from Part 09 — In Lambda Form

Same steps as `AiService.upload_document()` (Part 12b), but:
- **Sync** (psycopg2 not asyncpg)
- **Standalone** (doesn't import FastAPI app code)
- **Triggered by S3** (not by API request)
- **Embedding placeholder** (zero vectors — replace with Groq embedding API in production)

The `::vector` cast in the INSERT tells PostgreSQL to store the array as a pgvector column.

---

## 4. What You Learned

| # | Concept | Where Used |
|---|---------|-----------|
| 1 | **SQS `event["Records"]`** | Parse SQS messages from batch | Lambdas 3, 4 |
| 2 | **`json.loads(record["body"])`** | SQS body is a JSON string | All SQS handlers |
| 3 | **Gaps-and-islands in Lambda** | Same streak SQL as Part 07b | Lambda 4 |
| 4 | **Idempotency via DB check** | Prevent duplicate milestone emails | Lambda 4 |
| 5 | **S3 event `record["s3"]`** | Parse bucket + key from S3 trigger | Lambda 6 |
| 6 | **`::vector` cast** | Store embedding as pgvector type | Lambda 6 |
| 7 | **`_update_doc_status()`** | Status machine: processing → processed/failed | Lambda 6 |
| 8 | **Simplified RAG pipeline** | Same steps as Part 09, sync version | Lambda 6 |

---

## 5. Navigation

| ⬅️ Previous | [Part 15b: Scheduled Functions](./phase4-part15b-lambda-scheduled-functions.md) |
| ➡️ Next | [Part 15d: Lambda Flows](./phase4-part15d-lambda-connections-and-flows.md) |

---

**End of Phase 4 Part 15c: Event-Driven Functions**
