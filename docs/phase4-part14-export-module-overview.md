# 📥 Phase 4 Part 14: Export Module — Overview & Roadmap

> **"Users own their data. CSV for spreadsheets, HTML reports for doctors. Two export modes: sync (instant download for small data) and async (S3 upload + download URL for large exports). MinIO locally, S3 in production — same boto3 API."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 14 (Export Module — Overview) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Release** | Release 4.2 — Data Export & Portability |
| **Previous** | [phase4-part13d-notifications-connections-and-flows.md](./phase4-part13d-notifications-connections-and-flows.md) |
| **Next** | [phase4-part14a-export-csv-pdf-storage.md](./phase4-part14a-export-csv-pdf-storage.md) |
| **Module Files** | 6 Python files |
| **Endpoints** | 2 (CSV direct download, CSV to S3 with URL) |
| **Sub-Parts** | 3 documents (14a generators+storage, 14b service+router, 14c flows) |
| **Difficulty** | Medium (io.StringIO, boto3 S3, pre-signed URLs, StreamingResponse) |

---

## 📖 Table of Contents

1. [What Is the Export Module?](#what-is-export)
2. [Two Export Modes — Sync vs Async](#two-modes)
3. [S3 Storage — MinIO Locally, AWS in Production](#storage)
4. [Endpoints Overview](#endpoints)
5. [File List & Build Order](#file-list)
6. [Sub-Part Roadmap](#roadmap)
7. [Architecture Diagram](#architecture)
8. [Key Concepts You'll Learn](#concepts)
9. [Design Decisions](#design-decisions)
10. [Interview Q&A](#interview)
11. [Navigation](#navigation)

---

<a name="what-is-export"></a>
## 1. What Is the Export Module?

The Export module lets users download their habit data as files — CSV for spreadsheets, HTML reports for viewing/printing. This is a **data portability** feature: users own their data and should be able to take it with them.

### Real-World Analogy

Think of a **bank statement export**:
- You log into your bank → click "Export Transactions" → download a CSV
- You can open it in Excel, give it to your accountant, or import it into another tool
- The bank doesn't hold your data hostage — you can always export it

Our export does the same: habits + logs → CSV file → download.

### What Gets Exported

```csv
Date,Habit Name,Type,Value,Unit,Notes
2026-09-20,Water Intake,numeric,7.0,glasses,
2026-09-20,Sleep Hours,numeric,7.5,hours,
2026-09-20,Exercise,boolean,Yes,,Morning run
2026-09-20,Mood,scale,8,,Felt great
2026-09-21,Water Intake,numeric,8.0,glasses,Hit target!
2026-09-21,Sleep Hours,numeric,6.0,hours,Late night
...
```

Each row = one log entry. All habits, all dates in the requested range.

---

<a name="two-modes"></a>
## 2. Two Export Modes — Sync vs Async

### Mode 1: Sync (Direct Download)

```
POST /export/csv {start_date, end_date}
  → Generate CSV in memory (io.StringIO)
  → Return as StreamingResponse with Content-Disposition: attachment
  → Browser saves file immediately

BEST FOR: Small exports (< 30 days, < 1000 rows)
TIME: < 1 second
STORAGE: None (generated and sent directly)
```

### Mode 2: Async (S3 + Download URL)

```
POST /export/csv/s3 {start_date, end_date}
  → Generate CSV in memory
  → Upload to S3/MinIO
  → Generate pre-signed download URL (expires in 24 hours)
  → Return URL to client

BEST FOR: Large exports, Lambda processing, email links
TIME: 2-5 seconds (including S3 upload)
STORAGE: S3 (with 24-hour expiring URL)
```

### Why Two Modes?

| Scenario | Mode | Why |
|----------|------|-----|
| User clicks "Export" in browser | Sync | Instant download, no storage needed |
| Lambda generates large export | Async | Lambda has limited response size, S3 handles big files |
| Email "Your export is ready" | Async | Need a URL to put in the email |
| Mobile app download | Async | Pre-signed URL works with any HTTP client |

---

<a name="storage"></a>
## 3. S3 Storage — MinIO Locally, AWS in Production

```
DEVELOPMENT:
  MinIO (S3-compatible, runs in Docker)
  endpoint: http://localhost:9000
  Same boto3 API as AWS S3

PRODUCTION:
  AWS S3
  endpoint: None (boto3 defaults to AWS)
  Same code — just different environment variables

CONFIGURATION:
  S3_ENDPOINT=http://localhost:9000  ← MinIO (dev)
  S3_ENDPOINT=                        ← AWS S3 (prod, leave empty)
  S3_ACCESS_KEY=minioadmin           ← MinIO default
  S3_SECRET_KEY=minioadmin
  S3_BUCKET=health-tracker-exports
  S3_REGION=us-east-1
```

### Pre-Signed URLs

```python
url = s3_client.generate_presigned_url(
    "get_object",
    Params={"Bucket": bucket, "Key": "exports/user-id/2026-09.csv"},
    ExpiresIn=86400,  # 24 hours
)
# → "https://bucket.s3.amazonaws.com/exports/...?X-Amz-Signature=...&X-Amz-Expires=86400"
```

- Anyone with the URL can download the file — no auth needed
- URL expires after 24 hours — security: can't reuse old links
- The file stays in S3 until explicitly deleted

---

<a name="endpoints"></a>
## 4. Endpoints Overview

| # | Method | Endpoint | Request Body | Response | What It Does |
|---|--------|----------|-------------|----------|-------------|
| 1 | `POST` | `/export/csv` | `ExportRequest` | `StreamingResponse` (file download) | Generate CSV, direct download |
| 2 | `POST` | `/export/csv/s3` | `ExportRequest` | `ExportResponse` (download URL) | Generate CSV, upload to S3, return URL |

### Request Schema

```json
{
    "start_date": "2026-09-01",
    "end_date": "2026-09-30",
    "format": "csv"
}
```

### Response (Sync — endpoint 1)

Browser downloads a file named `health-tracker-2026-09-01-to-2026-09-30.csv`

### Response (Async — endpoint 2)

```json
{
    "message": "Export ready! Download link valid for 24 hours.",
    "download_url": "https://bucket.s3.amazonaws.com/exports/...?X-Amz-Signature=...",
    "status": "ready"
}
```

---

<a name="file-list"></a>
## 5. File List & Build Order

```
backend/app/modules/export/
├── __init__.py
├── csv_generator.py    ← In-memory CSV generation (io.StringIO + csv.writer)
├── pdf_generator.py    ← HTML report generation (placeholder for WeasyPrint)
├── storage.py          ← S3/MinIO abstraction (boto3)
├── schemas.py          ← ExportRequest + ExportResponse + ReportMetadata
├── service.py          ← Orchestrates: generate → (optional S3 upload) → return
└── router.py           ← 2 endpoints (sync download, async S3)
```

### Build Order

| # | File | Why This Order |
|---|------|---------------|
| 1 | `csv_generator.py` | Core generation logic — no dependencies |
| 2 | `pdf_generator.py` | HTML report template — no dependencies |
| 3 | `storage.py` | S3 operations — standalone boto3 wrapper |
| 4 | `schemas.py` | Request/response shapes — router uses these |
| 5 | `service.py` | Orchestrates generator + storage |
| 6 | `router.py` | HTTP layer — calls service |

---

<a name="roadmap"></a>
## 6. Sub-Part Roadmap

### Part 14a: CSV Generator, PDF Generator & Storage

```
📄 phase4-part14a-export-csv-pdf-storage.md
├── csv_generator.py  — io.StringIO + csv.writer, generate() + generate_bytes()
├── pdf_generator.py  — HTML report template (WeasyPrint placeholder)
└── storage.py        — S3/MinIO: upload, download, presigned URL, delete, ensure_bucket

KEY CONCEPTS: io.StringIO (in-memory file), csv.writer, boto3 S3, pre-signed URLs, MinIO
TIME: ~30 minutes
```

### Part 14b: Service, Router & Schemas

```
📄 phase4-part14b-export-service-router.md
├── schemas.py   — ExportRequest (date range), ExportResponse (URL + status)
├── service.py   — export_csv_sync (direct) + export_csv_to_s3 (async)
└── router.py    — POST /csv (StreamingResponse), POST /csv/s3 (JSON URL)

KEY CONCEPTS: StreamingResponse, Content-Disposition header, S3 key naming
TIME: ~30 minutes
```

### Part 14c: Connections & Flows

```
📄 phase4-part14c-export-connections-and-flows.md
├── Sync export flow (generate → download)
├── Async export flow (generate → S3 upload → presigned URL)
├── Lambda export flow (triggered async → S3 → email notification)
└── Module summary

TIME: ~15 minutes
```

---

<a name="architecture"></a>
## 7. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXPORT MODULE                                  │
│                                                                   │
│  ┌─── router.py (2 endpoints) ──────────────────────────────┐   │
│  │  POST /export/csv     → sync: StreamingResponse (file)    │   │
│  │  POST /export/csv/s3  → async: JSON with download URL     │   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                             │                                     │
│                             ▼                                     │
│  ┌─── service.py ───────────────────────────────────────────┐   │
│  │  export_csv_sync()  → csv_generator.generate() → return   │   │
│  │  export_csv_to_s3() → csv_generator.generate_bytes()      │   │
│  │                     → storage.upload_file()                │   │
│  │                     → storage.get_presigned_url()          │   │
│  └──────────┬────────────────────┬───────────────────────────┘   │
│             │                    │                                │
│             ▼                    ▼                                │
│  ┌──────────────────┐  ┌────────────────────────────────────┐   │
│  │  csv_generator    │  │  storage (boto3)                    │   │
│  │  io.StringIO      │  │  Dev: MinIO (localhost:9000)        │   │
│  │  csv.writer       │  │  Prod: AWS S3                       │   │
│  │  In-memory only   │  │  Pre-signed URLs (24h expiry)       │   │
│  └──────────────────┘  └────────────────────────────────────┘   │
│                                                                   │
│  Data sources:                                                    │
│  ├── HabitRepository (names, types, units)                        │
│  └── LogRepository (values by date range)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

<a name="concepts"></a>
## 8. Key Concepts You'll Learn

| # | Concept | What It Is | Where |
|---|---------|-----------|-------|
| 1 | **`io.StringIO`** | In-memory file object — build CSV without writing to disk | csv_generator.py |
| 2 | **`csv.writer`** | Python stdlib CSV writer — handles quoting, escaping | csv_generator.py |
| 3 | **`StreamingResponse`** | FastAPI response that sends file as download | router.py |
| 4 | **`Content-Disposition`** | HTTP header that tells browser to save (not display) the response | router.py |
| 5 | **boto3 S3 client** | AWS SDK for Python — upload, download, delete, presign | storage.py |
| 6 | **MinIO** | S3-compatible local server (Docker) — same API as AWS | storage.py |
| 7 | **Pre-signed URLs** | Temporary download links (24h expiry, no auth needed) | storage.py |
| 8 | **`endpoint_url`** | boto3 config: MinIO URL for dev, None for AWS | storage.py |
| 9 | **Sync vs Async export** | Direct download vs S3 upload + URL | service.py |
| 10 | **`generate_bytes()`** | CSV string → UTF-8 bytes (for S3 upload) | csv_generator.py |

---

<a name="design-decisions"></a>
## 9. Design Decisions

### Decision 1: In-Memory CSV (Not File on Disk)

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: CSV Generation Strategy                           │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: In-memory generation using io.StringIO                     │
│                                                                     │
│  WHY:                                                               │
│  • Faster — no disk I/O, no temp file creation                     │
│  • Lambda-friendly — Lambda has limited disk space (/tmp: 512MB)    │
│  • No cleanup — memory is freed when the response completes        │
│  • Streamable — can start sending before generation completes       │
│                                                                     │
│  ALTERNATIVES CONSIDERED:                                           │
│  1. Write to /tmp file, then serve                                  │
│     ❌ Disk I/O overhead, cleanup needed, Lambda /tmp limits        │
│  2. Database → CSV library (e.g., pandas to_csv)                    │
│     ❌ Heavy dependency (pandas is 50MB+), overkill for CSV         │
│                                                                     │
│  MEMORY BUDGET:                                                     │
│  1 year of data (6 habits × 365 days) = ~2200 rows                 │
│  ~100 bytes per CSV row × 2200 = ~220KB — trivial for memory       │
│                                                                     │
│  INTERVIEW TIP: "We generate CSV in memory using io.StringIO and   │
│  csv.writer. No temp files, no disk I/O, Lambda-compatible. For     │
│  one year of habit data (~2200 rows, ~220KB), in-memory is trivial."│
└─────────────────────────────────────────────────────────────────────┘
```

### Decision 2: MinIO for Local S3

```
┌─────────────────────────────────────────────────────────────────────┐
│  DESIGN DECISION: Local Storage for Development                     │
│─────────────────────────────────────────────────────────────────────│
│  CHOSEN: MinIO (S3-compatible Docker container)                     │
│                                                                     │
│  WHY:                                                               │
│  • Same API as AWS S3 — identical boto3 calls                       │
│  • Runs in Docker (docker-compose service)                          │
│  • No AWS account needed for development                            │
│  • Test presigned URLs, multipart uploads, etc. locally             │
│  • Only difference: endpoint_url in config                          │
│                                                                     │
│  HOW IT WORKS:                                                      │
│  Dev:  S3_ENDPOINT=http://localhost:9000 → boto3 talks to MinIO     │
│  Prod: S3_ENDPOINT= (empty) → boto3 defaults to AWS S3             │
│  Same code. Zero changes.                                           │
│                                                                     │
│  INTERVIEW TIP: "MinIO is an S3-compatible server we run locally    │
│  in Docker. Same boto3 API as AWS S3 — the only config difference   │
│  is the endpoint URL. Our code works identically in both."          │
└─────────────────────────────────────────────────────────────────────┘
```

---

<a name="interview"></a>
## 10. Interview Q&A

### Q1: How does the CSV export work?
**A:** "Two modes. Sync: generate CSV in memory using `io.StringIO` and `csv.writer`, return directly as a `StreamingResponse` with `Content-Disposition: attachment` — the browser downloads it instantly. Async: same generation, but upload the bytes to S3 (MinIO locally, AWS in production), then return a pre-signed URL valid for 24 hours. Sync is for small exports (user clicks 'Download'). Async is for large exports or Lambda processing."

### Q2: What is a pre-signed URL and why use it?
**A:** "A pre-signed URL is a temporary link to an S3 object that includes an embedded signature. Anyone with the URL can download the file — no AWS credentials needed. It expires after a configured time (24 hours for us). We use it so the user can download their export without our API being in the download path — S3 handles the file transfer directly, offloading bandwidth from our server."

### Q3: How does MinIO help during development?
**A:** "MinIO is an S3-compatible server in a Docker container. It implements the same S3 API — `put_object`, `get_object`, `generate_presigned_url` — all with identical boto3 calls. The only difference is the `endpoint_url` config: `http://localhost:9000` for MinIO, empty for AWS. We test S3 operations locally without an AWS account. When we deploy, the same code works with real S3."

### Q4: Why in-memory CSV instead of writing to disk?
**A:** "Three reasons: speed (no disk I/O), Lambda compatibility (Lambda has only 512MB /tmp), and no cleanup needed (memory freed after response). One year of data for 6 habits is ~2200 CSV rows, ~220KB — trivial for memory. If we needed to export millions of rows, we'd stream directly to S3 in chunks instead of building the full CSV in memory."

---

<a name="navigation"></a>
## 11. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Phase 4 Part 13d: Notifications Flows](./phase4-part13d-notifications-connections-and-flows.md) |
| ➡️ Next | [Phase 4 Part 14a: CSV, PDF & Storage](./phase4-part14a-export-csv-pdf-storage.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Export Sub-Parts

| Sub-Part | Document | What's Inside |
|----------|----------|--------------|
| 14a | [CSV, PDF & Storage](./phase4-part14a-export-csv-pdf-storage.md) | csv_generator + pdf_generator + storage (full source) |
| 14b | [Service & Router](./phase4-part14b-export-service-router.md) | service + router + schemas (full source) |
| 14c | [Connections & Flows](./phase4-part14c-export-connections-and-flows.md) | Sync/async flows, Lambda integration |

---

**End of Phase 4 Part 14: Export Module Overview**

*Data portability in two modes: instant download for small data, S3 upload with pre-signed URLs for large exports. MinIO locally, AWS S3 in production — same boto3 code. Next: the generators and storage provider source code.*
