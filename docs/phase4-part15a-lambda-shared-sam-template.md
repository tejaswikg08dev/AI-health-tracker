# ☁️ Phase 4 Part 15a: Lambda — Shared Utilities & SAM Template

> **"4 shared utility files power all 6 Lambdas: config reads env vars, db_utils manages a reusable sync connection, email_utils sends via SES, s3_utils handles file operations. The SAM template defines everything as infrastructure-as-code — one `sam deploy` creates 6 functions, 2 SQS queues, and 1 S3 bucket."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 15a (Lambda Shared Utilities + SAM Template) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Previous** | [phase4-part15-lambda-overview.md](./phase4-part15-lambda-overview.md) |
| **Next** | [phase4-part15b-lambda-scheduled-functions.md](./phase4-part15b-lambda-scheduled-functions.md) |
| **Files in This Doc** | 5 files (config.py, db_utils.py, email_utils.py, s3_utils.py, template.yaml) |
| **Time to Type** | ~45 minutes |
| **Difficulty** | Medium (psycopg2 connection reuse, SAM YAML syntax, CloudFormation parameters) |

---

## 📖 Table of Contents

1. [What We're Building](#overview)
2. [File 1: config.py — Environment Variables](#config)
3. [File 2: db_utils.py — Sync PostgreSQL with Connection Reuse](#db)
4. [File 3: email_utils.py — AWS SES Email](#email)
5. [File 4: s3_utils.py — S3 File Operations](#s3)
6. [File 5: template.yaml — SAM Infrastructure-as-Code](#sam)
7. [How to Deploy](#deploy)
8. [What You Learned](#what-you-learned)
9. [Interview Q&A](#interview)
10. [Navigation](#navigation)

---

<a name="overview"></a>
## 1. What We're Building

| File | What It Does | Used By |
|------|-------------|---------|
| `config.py` | Read Lambda environment variables | All 6 functions |
| `db_utils.py` | Sync PostgreSQL queries with connection reuse | 5 of 6 functions |
| `email_utils.py` | Send email via AWS SES | 4 of 6 functions |
| `s3_utils.py` | Upload/download files, pre-signed URLs | 3 of 6 functions |
| `template.yaml` | SAM: define all Lambdas + SQS + S3 as code | Deployment |

---

<a name="config"></a>
## 2. File 1: `config.py` — Environment Variables

### Type This Code: `health-tracker/lambda_functions/shared/config.py`

```python
# Lambda environment configuration — reads from Lambda env vars
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://healthuser:healthpass@localhost:5432/healthtracker")
S3_BUCKET = os.environ.get("S3_BUCKET", "health-tracker")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
SES_FROM_EMAIL = os.environ.get("SES_FROM_EMAIL", "noreply@healthtracker.app")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
```

**Why `os.environ.get()` with defaults?**
- In Lambda: environment variables are set in the SAM template → injected by CloudFormation
- Locally (testing): defaults let you run functions without setting every env var
- `GROQ_API_KEY` defaults to `""` — weekly report gracefully degrades if missing

**Why not Pydantic Settings (like the FastAPI app)?**
- Lambda runs independently from FastAPI — doesn't have access to `app.config`
- Lambda's Python path is different — `from app.config import get_settings` won't work
- Simple `os.environ` is sufficient — Lambda functions have ~5 config values, not 30+

---

<a name="db"></a>
## 3. File 2: `db_utils.py` — Sync PostgreSQL with Connection Reuse

### Type This Code: `health-tracker/lambda_functions/shared/db_utils.py`

```python
# Database connection utility for Lambda functions
# Lambda uses SYNC connections (not async like FastAPI)

import psycopg2
from psycopg2.extras import RealDictCursor
from shared.config import DATABASE_URL

# Connection pool — reused across Lambda invocations (warm starts)
_connection = None


def get_db_connection():
    """
    Get a database connection (reused for Lambda warm starts).

    WHY connection reuse:
        Lambda keeps the container alive between invocations (warm start).
        Creating a new DB connection every invocation wastes 50-100ms.
        Reusing the connection: ~1ms.
    """
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return _connection


def execute_query(query: str, params: dict = None) -> list[dict]:
    """Execute a SELECT query and return rows as dicts."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        return cur.fetchall()


def execute_update(query: str, params: dict = None) -> int:
    """Execute an INSERT/UPDATE/DELETE and return affected rows."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        conn.commit()
        return cur.rowcount
```

### Line-by-Line: The Most Important Lambda Pattern

**Global `_connection` — Warm Start Reuse**
```python
_connection = None

def get_db_connection():
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return _connection
```

This is THE critical Lambda optimization:

```
COLD START (first invocation):
  _connection = None → create new connection (50-100ms)
  → _connection now holds a live connection

WARM START (next invocation, within ~15 min):
  _connection is NOT None AND NOT closed → reuse it (1ms)
  → No new connection needed

CONTAINER REUSE:
  Lambda keeps the container alive for ~15 min after last invocation.
  Global variables persist across invocations.
  _connection survives → reused for free.
```

**Without this pattern:** Every invocation creates a new DB connection (50-100ms overhead × thousands of invocations = wasted seconds + DB connection exhaustion).

**`RealDictCursor` — Rows as Dicts**
```python
psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
```
- Default psycopg2: rows are tuples `(value1, value2, ...)` — access by index
- `RealDictCursor`: rows are dicts `{"column_name": value, ...}` — access by name
- `result[0]["email"]` instead of `result[0][1]` — more readable and maintainable

**`execute_query()` vs `execute_update()`**
```python
def execute_query(query, params) -> list[dict]:     # SELECT — returns rows
    cur.execute(query, params)
    return cur.fetchall()

def execute_update(query, params) -> int:            # INSERT/UPDATE/DELETE — returns count
    cur.execute(query, params)
    conn.commit()                                     # ← Commits! (query doesn't need commit)
    return cur.rowcount
```

**Why `commit()` in update but not in query?**
- SELECT doesn't change data — no transaction to commit
- INSERT/UPDATE/DELETE change data — must commit or changes are rolled back
- In Lambda, autocommit isn't on by default (psycopg2 opens a transaction)

---

<a name="email"></a>
## 4. File 3: `email_utils.py` — AWS SES Email

### Type This Code: `health-tracker/lambda_functions/shared/email_utils.py`

```python
# Email utility for Lambda — sends via AWS SES

import boto3
from shared.config import SES_FROM_EMAIL, S3_REGION

ses_client = boto3.client("ses", region_name=S3_REGION)


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via AWS SES. Returns True on success."""
    try:
        ses_client.send_email(
            Source=SES_FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False
```

**Module-level `ses_client`** — same warm-start reuse pattern as `_connection`. The boto3 client is created once at import time and reused across invocations.

**`print()` not `logger`** — Lambda captures `print()` output to CloudWatch Logs automatically. We don't need structlog here — Lambda's built-in logging is sufficient.

**Returns `bool`, never raises** — same fail-safe pattern as the FastAPI email provider (Part 13a). Email failure doesn't crash the Lambda.

---

<a name="s3"></a>
## 5. File 4: `s3_utils.py` — S3 File Operations

### Type This Code: `health-tracker/lambda_functions/shared/s3_utils.py`

```python
# S3 utility for Lambda — upload, download, presigned URLs

import boto3
from shared.config import S3_BUCKET, S3_REGION

s3_client = boto3.client("s3", region_name=S3_REGION)


def upload_file(key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
    s3_client.put_object(Bucket=S3_BUCKET, Key=key, Body=content, ContentType=content_type)
    return key


def download_file(key: str) -> bytes:
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    return response["Body"].read()


def generate_presigned_url(key: str, expires_in: int = 86400) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )


def delete_file(key: str) -> None:
    s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
```

**Same operations as the FastAPI `StorageProvider` (Part 14a)** — upload, download, presigned URL, delete. The difference: Lambda's version is simpler (no async, no class, no MinIO endpoint). In Lambda, S3 is always AWS S3 (never MinIO).

**Module-level `s3_client`** — reused across warm starts, just like the DB connection and SES client.

---

<a name="sam"></a>
## 6. File 5: `template.yaml` — SAM Infrastructure-as-Code

### Type This Code: `health-tracker/lambda_functions/template.yaml`

```yaml
# ============================================================================
# AWS SAM Template — All Lambda Functions
# ============================================================================
# Deploy with: sam build && sam deploy --guided
# Test locally: sam local invoke DailyReminderFunction --event events/daily.json
# ============================================================================

AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: Health Tracker Lambda Functions

Globals:
  Function:
    Runtime: python3.11
    Timeout: 120
    MemorySize: 256
    Environment:
      Variables:
        DATABASE_URL: !Ref DatabaseUrl
        S3_BUCKET: !Ref S3BucketName
        SES_FROM_EMAIL: !Ref SesFromEmail
        GROQ_API_KEY: !Ref GroqApiKey

Parameters:
  DatabaseUrl:
    Type: String
    Description: PostgreSQL connection string
  S3BucketName:
    Type: String
    Default: health-tracker
  SesFromEmail:
    Type: String
    Default: noreply@healthtracker.app
  GroqApiKey:
    Type: String
    Default: ""
    NoEcho: true

Resources:
  # ── Lambda 1: Daily Reminder ──
  DailyReminderFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 01_daily_reminder/
      Description: Send daily habit reminder emails
      Events:
        Schedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 8 * * ? *)
            Description: Every day at 8 AM UTC

  # ── Lambda 2: Weekly Report ──
  WeeklyReportFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 02_weekly_report/
      Timeout: 900
      MemorySize: 512
      Description: Generate and send weekly AI health reports
      Events:
        Schedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 9 ? * SUN *)
            Description: Every Sunday at 9 AM UTC

  # ── Lambda 3: CSV Export ──
  CsvExportFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 03_csv_export/
      Description: Generate CSV export and email download link
      Events:
        SQSEvent:
          Type: SQS
          Properties:
            Queue: !GetAtt ExportQueue.Arn
            BatchSize: 1

  # ── Lambda 4: Streak Milestone ──
  StreakMilestoneFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 04_streak_milestone/
      MemorySize: 128
      Description: Check and celebrate streak milestones
      Events:
        SQSEvent:
          Type: SQS
          Properties:
            Queue: !GetAtt StreakQueue.Arn
            BatchSize: 1

  # ── Lambda 5: Data Cleanup ──
  DataCleanupFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 05_data_cleanup/
      Description: Monthly cleanup of expired data
      Events:
        Schedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 0 1 * ? *)
            Description: First day of every month

  # ── Lambda 6: Document Processor ──
  DocumentProcessorFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      CodeUri: 06_document_processor/
      MemorySize: 512
      Timeout: 300
      Description: Process uploaded PDFs for RAG
      Events:
        S3Upload:
          Type: S3
          Properties:
            Bucket: !Ref DocumentsBucket
            Events: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: documents/

  # ── SQS Queues ──
  ExportQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: health-tracker-export
      VisibilityTimeout: 300

  StreakQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: health-tracker-streak
      VisibilityTimeout: 60

  # ── S3 Bucket ──
  DocumentsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref S3BucketName

Outputs:
  ExportQueueUrl:
    Value: !Ref ExportQueue
  StreakQueueUrl:
    Value: !Ref StreakQueue
```

### SAM Template Line-by-Line

**`Globals` — Shared Settings for All Functions**
```yaml
Globals:
  Function:
    Runtime: python3.11
    Timeout: 120           # 2 minutes default
    MemorySize: 256        # 256 MB default
    Environment:
      Variables:
        DATABASE_URL: !Ref DatabaseUrl
```
- Every function inherits these settings (can override individually)
- `!Ref DatabaseUrl` — references the `Parameters` section → value provided at deploy time
- Env vars are injected into Lambda at runtime → `os.environ.get("DATABASE_URL")` in config.py

**`Parameters` — Deploy-Time Configuration**
```yaml
Parameters:
  GroqApiKey:
    Type: String
    Default: ""
    NoEcho: true          # ← Don't show in logs (secret)
```
- `NoEcho: true` — CloudFormation masks this parameter in console/logs (for secrets)
- `Default: ""` — optional parameters don't block deployment

**Function Definition Pattern**
```yaml
DailyReminderFunction:
  Type: AWS::Serverless::Function
  Properties:
    Handler: handler.lambda_handler   # File: handler.py, Function: lambda_handler
    CodeUri: 01_daily_reminder/       # Directory containing the handler
    Events:
      Schedule:
        Type: Schedule
        Properties:
          Schedule: cron(0 8 * * ? *)
```
- `Handler: handler.lambda_handler` — Lambda looks for `lambda_handler` function in `handler.py`
- `CodeUri: 01_daily_reminder/` — directory SAM packages into the deployment
- `Events` — what triggers this Lambda. Schedule, SQS, or S3

**Weekly Report Overrides**
```yaml
WeeklyReportFunction:
  Properties:
    Timeout: 900           # 15 minutes (overrides 120s global)
    MemorySize: 512        # 512 MB (AI processing needs more RAM)
```
- AI report generation takes 10-30 seconds per user × 50 users = up to 15 minutes
- More memory = more CPU (Lambda allocates CPU proportional to memory)

**SQS Queue Definition**
```yaml
ExportQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: health-tracker-export
    VisibilityTimeout: 300   # 5 minutes — message hidden while Lambda processes
```
- `VisibilityTimeout` — after Lambda picks up a message, it's hidden for 300 seconds
- If Lambda finishes → message deleted. If Lambda crashes → message reappears after 300s → retried

**S3 Event Filter**
```yaml
Events:
  S3Upload:
    Type: S3
    Properties:
      Bucket: !Ref DocumentsBucket
      Events: s3:ObjectCreated:*
      Filter:
        S3Key:
          Rules:
            - Name: prefix
              Value: documents/
```
- Only triggers on uploads in the `documents/` prefix (not exports, not other files)
- `s3:ObjectCreated:*` — triggers on any upload method (PUT, POST, multipart)

---

<a name="deploy"></a>
## 7. How to Deploy

```bash
cd lambda_functions/

# Build (packages each function with its dependencies)
sam build

# Deploy (first time: --guided asks for parameter values)
sam deploy --guided
# Subsequent deploys:
sam deploy

# Test locally
sam local invoke DailyReminderFunction --event events/daily.json

# View logs
sam logs -n DailyReminderFunction --tail
```

`sam build` → packages each function's directory + shared/ into a ZIP.
`sam deploy` → creates/updates a CloudFormation stack → provisions all resources.
`sam local invoke` → runs the function locally in a Docker container (simulates Lambda).

---

<a name="what-you-learned"></a>
## 8. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`os.environ.get()`** | Read Lambda env vars with defaults | config.py |
| 2 | **Global `_connection`** | Reuse DB connection across warm starts | db_utils.py |
| 3 | **`psycopg2` (sync)** | Synchronous PostgreSQL — Lambda doesn't need async | db_utils.py |
| 4 | **`RealDictCursor`** | Return rows as dicts (not tuples) | db_utils.py |
| 5 | **`commit()` in update** | Writes need explicit commit in psycopg2 | db_utils.py |
| 6 | **Module-level boto3** | `ses_client` and `s3_client` created once, reused | email/s3_utils.py |
| 7 | **SAM Globals** | Shared defaults for all functions | template.yaml |
| 8 | **`!Ref`** | CloudFormation reference to a parameter | template.yaml |
| 9 | **`NoEcho: true`** | Hide secret parameter values in logs | template.yaml |
| 10 | **`VisibilityTimeout`** | SQS: message hidden while processing | template.yaml |
| 11 | **S3 event filter** | Only trigger on specific prefix uploads | template.yaml |
| 12 | **`sam build && sam deploy`** | Build + deploy all Lambdas in one command | CLI |

---

<a name="interview"></a>
## 9. Interview Q&A

### Q1: How do you optimize database connections in Lambda?
**A:** "Global variable reuse. The `_connection` variable is created on the first invocation and persists across warm starts — Lambda keeps the container alive for ~15 minutes. First call: ~50ms to connect. Subsequent calls: ~1ms. We also use psycopg2 (synchronous) because Lambda processes one request at a time — async provides no benefit. The `RealDictCursor` option returns rows as dicts for readable code."

### Q2: What is a SAM template and what does it define?
**A:** "SAM (Serverless Application Model) is AWS's framework for Lambda infrastructure-as-code. Our `template.yaml` defines: 6 Lambda functions with their handlers, triggers (EventBridge cron, SQS, S3 events), memory, and timeout settings. It also defines 2 SQS queues and 1 S3 bucket. A `Globals` section sets shared defaults (Python 3.11, environment variables). `sam deploy` creates a CloudFormation stack that provisions everything. One YAML file = the entire serverless infrastructure."

### Q3: How does SQS VisibilityTimeout prevent duplicate processing?
**A:** "When Lambda picks up an SQS message, it becomes invisible for `VisibilityTimeout` seconds (300s for exports, 60s for streaks). If Lambda succeeds, the message is deleted. If Lambda crashes or times out, the message becomes visible again after the timeout — SQS delivers it to another invocation for retry. This provides at-least-once delivery. For idempotency, the streak Lambda checks if the milestone was already recorded in the database before sending a duplicate email."

---

<a name="navigation"></a>
## 10. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 15: Lambda Overview](./phase4-part15-lambda-overview.md) |
| ➡️ Next | [Phase 4 Part 15b: Scheduled Functions](./phase4-part15b-lambda-scheduled-functions.md) |

### Lambda Sub-Parts Progress

| Sub-Part | Status |
|----------|--------|
| **15a** | ✅ **You are here** — Shared Utilities + SAM Template |
| 15b | ⬜ Next — Scheduled Functions (Lambdas 1, 2, 5) |
| 15c | ⬜ Event-Driven Functions (Lambdas 3, 4, 6) |
| 15d | ⬜ Connections & Flows |

---

**End of Phase 4 Part 15a: Shared Utilities & SAM Template**

*4 shared files (config, DB, email, S3) power all 6 Lambdas. The SAM template defines everything as code — 6 functions, 2 queues, 1 bucket. `sam deploy` creates the entire serverless infrastructure. Next: the 3 scheduled function handlers.*
