# 📥 Phase 4 Part 14a: Export — CSV Generator, PDF Generator & Storage

> **"csv_generator builds the file in memory — no disk, no temp files. storage.py talks to S3/MinIO via boto3. pdf_generator produces HTML reports (WeasyPrint-ready when you need real PDFs). Three files, three responsibilities."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 14a (Export Generators + Storage) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Previous** | [phase4-part14-export-module-overview.md](./phase4-part14-export-module-overview.md) |
| **Next** | [phase4-part14b-export-service-router.md](./phase4-part14b-export-service-router.md) |
| **Files in This Doc** | 3 files (csv_generator.py, pdf_generator.py, storage.py) |
| **Time to Type** | ~40 minutes |
| **Difficulty** | Medium (io.StringIO, csv.writer, boto3 S3, pre-signed URLs) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: csv_generator.py — In-Memory CSV](#csv)
3. [File 2: pdf_generator.py — HTML Report Template](#pdf)
4. [File 3: storage.py — S3/MinIO Abstraction](#storage)
5. [How These Files Connect](#connections)
6. [What You Learned](#what-you-learned)
7. [Interview Q&A](#interview)
8. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

| File | What It Does | Dependencies |
|------|-------------|-------------|
| `csv_generator.py` | Builds CSV from habit logs entirely in memory | HabitRepository + LogRepository |
| `pdf_generator.py` | Generates HTML report (PDF-ready placeholder) | None (pure string generation) |
| `storage.py` | Uploads/downloads files to S3-compatible storage | boto3 (AWS SDK) |

---

<a name="csv"></a>
## 2. File 1: `csv_generator.py` — In-Memory CSV

### Type This Code: `backend/app/modules/export/csv_generator.py`

```python
# ============================================================================
# Export — CSV Generator
# ============================================================================
# WHAT THIS FILE DOES:
#   Generates CSV files from habit log data.
#   Uses Python's csv module + io.StringIO for in-memory generation.
#
# WHY IN-MEMORY (not writing to disk):
#   1. Faster — no disk I/O
#   2. Serverless-friendly — Lambda has limited disk space
#   3. Streamable — can send to client before file is fully generated
#   4. No cleanup needed — memory is freed automatically
#
# CSV FORMAT:
#   Date,Habit Name,Type,Value,Unit,Notes
#   2026-09-26,Water Intake,numeric,8.0,glasses,
#   2026-09-26,Exercise,boolean,Yes,,Morning run
#   2026-09-26,Mood,scale,7,,Felt good today
# ============================================================================

import csv
import io
from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.repository import HabitRepository
from app.modules.logs.repository import LogRepository
from app.shared.logging import get_logger

logger = get_logger(__name__)


class CsvGenerator:
    """
    Generates CSV exports of habit log data.

    Usage:
        generator = CsvGenerator(session)
        csv_content = await generator.generate(user_id, start_date, end_date)
        # csv_content is a string — return as response, or upload to S3
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> str:
        """
        Generate a CSV string from habit log data.

        Returns the full CSV as a string (including header row).
        Uses io.StringIO to build the CSV in memory.
        """
        habit_repo = HabitRepository(self.session)
        log_repo = LogRepository(self.session)

        # Fetch data
        habits = await habit_repo.get_user_habits(user_id, include_archived=True)
        logs = await log_repo.get_logs_for_range(user_id, start_date, end_date)

        # Build lookup maps
        habit_map = {str(h.id): h for h in habits}

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "Date", "Habit Name", "Type", "Value", "Unit", "Notes",
        ])

        # Data rows
        for log in logs:
            habit = habit_map.get(str(log.habit_id))
            if not habit:
                continue

            # Determine value based on type
            if habit.habit_type == "numeric":
                value = log.value_numeric if log.value_numeric is not None else ""
            elif habit.habit_type == "boolean":
                value = "Yes" if log.value_boolean else "No" if log.value_boolean is not None else ""
            elif habit.habit_type == "scale":
                value = log.value_scale if log.value_scale is not None else ""
            else:
                value = ""

            writer.writerow([
                str(log.log_date),
                habit.name,
                habit.habit_type,
                value,
                habit.unit,
                log.notes or "",
            ])

        csv_content = output.getvalue()
        output.close()

        logger.info(
            "csv_generated",
            user_id=str(user_id),
            rows=len(logs),
            date_range=f"{start_date} to {end_date}",
        )

        return csv_content

    async def generate_bytes(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> bytes:
        """Generate CSV as bytes (for S3 upload or file download)."""
        csv_str = await self.generate(user_id, start_date, end_date)
        return csv_str.encode("utf-8")
```

### Line-by-Line Explanation

**`io.StringIO()` — In-Memory File**
```python
output = io.StringIO()
writer = csv.writer(output)
writer.writerow(["Date", "Habit Name", ...])
csv_content = output.getvalue()
output.close()
```
- `io.StringIO()` creates a file-like object IN MEMORY — not on disk
- `csv.writer(output)` writes CSV-formatted lines to this in-memory file
- `writer.writerow([...])` writes one CSV row (handles quoting, escaping commas in notes)
- `output.getvalue()` returns the complete CSV as a single string
- `output.close()` frees the memory buffer
- **No temp files, no disk I/O, no cleanup needed**

**`include_archived=True` — Include Deleted Habits**
```python
habits = await habit_repo.get_user_habits(user_id, include_archived=True)
```
- Exports include archived habits — historical data is valuable
- The user stopped tracking "Meditation" 2 months ago, but those 2 months of data should still be exportable

**Type-Specific Value Extraction**
```python
if habit.habit_type == "numeric":
    value = log.value_numeric if log.value_numeric is not None else ""
elif habit.habit_type == "boolean":
    value = "Yes" if log.value_boolean else "No" if log.value_boolean is not None else ""
elif habit.habit_type == "scale":
    value = log.value_scale if log.value_scale is not None else ""
```
- Same polymorphic value pattern as the Logs module (Part 06a)
- Boolean converts to "Yes"/"No" for human-readable CSV (not `True`/`False`)
- Empty string `""` for days without a log (not NULL — CSV doesn't have NULL)

**`generate_bytes()` — For S3 Upload**
```python
async def generate_bytes(self, user_id, start_date, end_date) -> bytes:
    csv_str = await self.generate(user_id, start_date, end_date)
    return csv_str.encode("utf-8")
```
- S3 needs bytes, not a string. `.encode("utf-8")` converts
- Wrapper method keeps the main `generate()` returning a string (for StreamingResponse)

---

<a name="pdf"></a>
## 3. File 2: `pdf_generator.py` — HTML Report Template

### Type This Code: `backend/app/modules/export/pdf_generator.py`

```python
# ============================================================================
# Export — PDF Generator (Placeholder)
# ============================================================================
# Generates HTML reports. When WeasyPrint is installed, can convert to PDF.
#
# PRODUCTION OPTIONS:
#   1. WeasyPrint (Python) — renders HTML/CSS to PDF, needs Cairo
#   2. wkhtmltopdf (CLI) — converts HTML to PDF via WebKit
#   3. Puppeteer (headless Chrome) — most accurate rendering
#   4. ReportLab (Python) — programmatic PDF, no HTML needed
#   5. Lambda with chrome-aws-lambda — serverless PDF generation
# ============================================================================

from app.shared.logging import get_logger

logger = get_logger(__name__)


class PdfGenerator:
    """
    PDF report generator.

    Currently returns HTML as a string (can be viewed in browser).
    When you install WeasyPrint, uncomment the generate_pdf method.
    """

    def generate_html_report(
        self,
        title: str,
        content: str,
        user_name: str,
    ) -> str:
        """
        Generate an HTML report that can be viewed in a browser
        or converted to PDF.
        """
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                       max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }}
                h1 {{ color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 8px; }}
                h2 {{ color: #1E40AF; margin-top: 24px; }}
                .meta {{ color: #666; font-size: 14px; }}
                .content {{ line-height: 1.6; }}
                .footer {{ margin-top: 40px; color: #999; font-size: 12px;
                          border-top: 1px solid #eee; padding-top: 16px; }}
            </style>
        </head>
        <body>
            <h1>🏥 {title}</h1>
            <p class="meta">Prepared for {user_name}</p>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                Generated by Health Tracker AI
            </div>
        </body>
        </html>
        """

    # Uncomment when WeasyPrint is installed:
    # def generate_pdf(self, title, content, user_name) -> bytes:
    #     from weasyprint import HTML
    #     html_str = self.generate_html_report(title, content, user_name)
    #     return HTML(string=html_str).write_pdf()
```

**Why a placeholder?** WeasyPrint requires Cairo (a C graphics library) — heavy to install in Docker. The HTML report is functional now: viewable in browser, usable as email content, and ready for PDF conversion when you add the dependency. The structure is in place — just uncomment `generate_pdf()` when ready.

**f-string with `{{ }}`** — Note the double braces in the CSS: `{{ color: #333; }}`. In an f-string, `{title}` is a variable. `{{` and `}}` produce literal `{` and `}` for CSS.

---

<a name="storage"></a>
## 4. File 3: `storage.py` — S3/MinIO Abstraction

### Type This Code: `backend/app/modules/export/storage.py`

```python
# ============================================================================
# Export — Object Storage (S3 / MinIO Abstraction)
# ============================================================================
# MinIO in development, AWS S3 in production — same API (boto3).
# ============================================================================

import boto3
from botocore.config import Config

from app.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageProvider:
    """
    S3-compatible object storage.

    Works with both AWS S3 and MinIO (local S3 clone).
    The only difference between MinIO and S3:
    - MinIO: endpoint_url = "http://localhost:9000"
    - S3:    endpoint_url = None (boto3 defaults to AWS)
    """

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT if settings.S3_ENDPOINT else None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.S3_BUCKET

    async def upload_file(
        self,
        key: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file to S3/MinIO.

        Args:
            key: S3 object key (path) e.g., "exports/user-id/2026-09-26.csv"
            content: File content as bytes
            content_type: MIME type (text/csv, application/pdf, etc.)

        Returns:
            The S3 key of the uploaded file
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
            logger.info("file_uploaded", key=key, size=len(content))
            return key
        except Exception as e:
            logger.error("file_upload_error", key=key, error=str(e))
            raise

    async def download_file(self, key: str) -> bytes:
        """Download a file from S3/MinIO."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read()
            logger.info("file_downloaded", key=key, size=len(content))
            return content
        except Exception as e:
            logger.error("file_download_error", key=key, error=str(e))
            raise

    async def get_presigned_url(self, key: str, expires_in: int = 86400) -> str:
        """
        Generate a temporary download URL.

        Valid for `expires_in` seconds (default: 24 hours).
        Anyone with the URL can download — no auth needed.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            logger.info("presigned_url_generated", key=key, expires_in=expires_in)
            return url
        except Exception as e:
            logger.error("presigned_url_error", key=key, error=str(e))
            raise

    async def delete_file(self, key: str) -> None:
        """Delete a file from S3/MinIO."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("file_deleted", key=key)
        except Exception as e:
            logger.error("file_delete_error", key=key, error=str(e))

    async def ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist (useful for MinIO setup)."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                logger.info("bucket_created", bucket=self.bucket)
            except Exception as e:
                logger.warning("bucket_create_error", error=str(e))
```

### Line-by-Line Explanation

**boto3 Client Configuration**
```python
self.s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT if settings.S3_ENDPOINT else None,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=settings.S3_REGION,
    config=Config(signature_version="s3v4"),
)
```
- `"s3"` — tells boto3 this is an S3 client (not DynamoDB, SQS, etc.)
- `endpoint_url` — THE key difference between MinIO and AWS:
  - MinIO: `"http://localhost:9000"` → boto3 talks to local MinIO
  - AWS: `None` → boto3 uses the default AWS S3 endpoints
- `aws_access_key_id` / `aws_secret_access_key` — credentials. MinIO defaults: `minioadmin`/`minioadmin`. AWS: from IAM
- `signature_version="s3v4"` — use Signature V4 (required for most S3 regions and MinIO)

**`put_object()` — Upload**
```python
self.s3_client.put_object(
    Bucket=self.bucket,
    Key=key,              # "exports/uuid-001/2026-09.csv"
    Body=content,         # CSV bytes
    ContentType="text/csv",
)
```
- `Key` = the S3 "path" — like a file system path but flat (S3 doesn't have real directories)
- `Body` = the file content as bytes
- `ContentType` = MIME type — ensures correct Content-Type header when downloading

**`generate_presigned_url()` — Temporary Download Link**
```python
url = self.s3_client.generate_presigned_url(
    "get_object",
    Params={"Bucket": self.bucket, "Key": key},
    ExpiresIn=86400,  # 24 hours in seconds
)
# → "https://bucket.s3.amazonaws.com/exports/...?X-Amz-Signature=abc123&X-Amz-Expires=86400"
```
- `"get_object"` — the URL will allow a GET (download), not PUT (upload)
- `ExpiresIn=86400` — 24 hours. After that, the URL returns 403 Forbidden
- The URL includes the cryptographic signature — anyone with the URL can download, no AWS auth needed
- **Security:** URL is unguessable (includes a signature hash). Share it via email or return in API response

**`ensure_bucket_exists()` — MinIO Setup**
```python
async def ensure_bucket_exists(self) -> None:
    try:
        self.s3_client.head_bucket(Bucket=self.bucket)  # Check if exists
    except Exception:
        self.s3_client.create_bucket(Bucket=self.bucket)  # Create if not
```
- MinIO starts empty — no buckets. This creates the bucket on first use
- AWS S3 buckets are usually created via CloudFormation or the console — this is mostly for MinIO
- `head_bucket` is cheaper than `list_buckets` — just checks if the bucket exists

**Why `async def` with Synchronous boto3?**

Notice: the methods are `async def` but `self.s3_client.put_object()` is synchronous. This works because:
1. For small files (<1MB), the blocking time is negligible (<100ms)
2. For production with large files, you'd use `run_in_executor()` (like SES in Part 13a)
3. For Lambda, there's no event loop to block — sync is fine

In a high-throughput production system, wrap boto3 calls in `asyncio.run_in_executor()`.

---

<a name="connections"></a>
## 5. How These Files Connect

```
ExportService.export_csv_sync():
  │
  ├── CsvGenerator(session).generate(user_id, start, end)
  │     → HabitRepository: get all habits (names, types, units)
  │     → LogRepository: get logs for date range
  │     → csv.writer → io.StringIO → CSV string
  │
  └── Return CSV string → router wraps in StreamingResponse

ExportService.export_csv_to_s3():
  │
  ├── CsvGenerator(session).generate_bytes(user_id, start, end)
  │     → Same as above, but .encode("utf-8") → bytes
  │
  ├── StorageProvider().upload_file(
  │     key="exports/uuid-001/2026-09-01_to_2026-09-30.csv",
  │     content=csv_bytes, content_type="text/csv"
  │   )
  │     → boto3 put_object → MinIO (dev) or S3 (prod)
  │
  └── StorageProvider().get_presigned_url(key)
        → boto3 generate_presigned_url → temporary URL (24h)
        → Return URL to client
```

---

<a name="what-you-learned"></a>
## 6. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`io.StringIO`** | In-memory file-like object (no disk writes) | csv_generator.py |
| 2 | **`csv.writer`** | Stdlib CSV: handles quoting, commas in notes | csv_generator.py |
| 3 | **`output.getvalue()`** | Get the complete string from StringIO | csv_generator.py |
| 4 | **`include_archived=True`** | Export includes historical (archived) habits | csv_generator.py |
| 5 | **f-string `{{ }}`** | Double braces for literal `{` in f-strings (CSS) | pdf_generator.py |
| 6 | **HTML → PDF pipeline** | Generate HTML, convert with WeasyPrint (placeholder) | pdf_generator.py |
| 7 | **boto3 `client("s3")`** | AWS SDK S3 client (works with MinIO too) | storage.py |
| 8 | **`endpoint_url`** | MinIO URL (dev) or None (AWS default) | storage.py |
| 9 | **`put_object()`** | Upload file bytes to S3 bucket | storage.py |
| 10 | **`generate_presigned_url()`** | Temporary download URL (24h, no auth) | storage.py |
| 11 | **`head_bucket()`** | Check if S3 bucket exists (cheaper than list) | storage.py |
| 12 | **`signature_version="s3v4"`** | Required signing format for modern S3/MinIO | boto3 Config |

---

<a name="interview"></a>
## 7. Interview Q&A

### Q1: How does in-memory CSV generation work?
**A:** "`io.StringIO` creates a file-like object in memory. `csv.writer` writes rows to it — handling quoting, escaping commas in notes, and proper line endings. `output.getvalue()` returns the complete CSV as a single string. No temp files, no disk I/O, no cleanup. For S3 upload, `.encode('utf-8')` converts the string to bytes. One year of data for 6 habits is ~2200 rows, ~220KB — trivial for memory."

### Q2: How does the same code work with MinIO (dev) and AWS S3 (prod)?
**A:** "One config difference: `endpoint_url`. For MinIO: `'http://localhost:9000'`. For AWS S3: `None` (boto3 defaults to AWS). Everything else — `put_object`, `get_object`, `generate_presigned_url` — uses the exact same boto3 API. MinIO implements the S3 protocol, so boto3 can't tell the difference. We run MinIO in Docker during development."

### Q3: What is a pre-signed URL and how is it secure?
**A:** "A pre-signed URL is an S3 download link with an embedded cryptographic signature and expiry. `generate_presigned_url('get_object', ...)` creates a URL like `https://bucket.s3.amazonaws.com/key?X-Amz-Signature=abc&X-Amz-Expires=86400`. Anyone with this URL can download the file — no AWS credentials needed. It expires after 24 hours (configurable). The signature is computed from the secret key, so it's unforgeable. After expiry, S3 returns 403 Forbidden."

---

<a name="navigation"></a>
## 8. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 14: Export Overview](./phase4-part14-export-module-overview.md) |
| ➡️ Next | [Phase 4 Part 14b: Export Service & Router](./phase4-part14b-export-service-router.md) |

### Export Sub-Parts Progress

| Sub-Part | Status |
|----------|--------|
| **14a** | ✅ **You are here** — CSV Generator, PDF Generator, Storage |
| 14b | ⬜ Next — Service, Router, Schemas |
| 14c | ⬜ Connections & Flows |

---

**End of Phase 4 Part 14a: CSV Generator, PDF Generator & Storage**

*CSV built in memory, HTML reports ready for PDF, S3/MinIO abstraction with pre-signed URLs. Next: the service that orchestrates generators + storage, and the router with StreamingResponse.*
