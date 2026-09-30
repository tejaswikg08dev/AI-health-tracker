# 🔄 Phase 4 Part 14c: Export — Connections & Flows

> **"Two flows: sync (generate → download in 1 second) and async (generate → S3 → pre-signed URL → optional email notification). Plus the Lambda flow for batch exports."**

---

## 📋 Document Metadata

| **Previous** | [phase4-part14b-export-service-router.md](./phase4-part14b-export-service-router.md) |
| **Next** | [phase4-part15-lambda-overview.md](./phase4-part15-lambda-overview.md) |

---

## 1. Export Module — Complete File Map

```
backend/app/modules/export/
├── csv_generator.py  ─── Part 14a ── io.StringIO + csv.writer (in-memory)
├── pdf_generator.py  ─── Part 14a ── HTML report template (WeasyPrint placeholder)
├── storage.py        ─── Part 14a ── boto3 S3/MinIO (upload, download, presigned URL)
├── schemas.py        ─── Part 14b ── ExportRequest + ExportResponse
├── service.py        ─── Part 14b ── export_csv_sync + export_csv_to_s3
├── router.py         ─── Part 14b ── 2 endpoints (sync download, async S3)
└── __init__.py
```

---

## 2. Flow 1: Sync Export (Direct Download)

```
USER: Clicks "Export CSV" button on the Settings page

STEP  COMPONENT             ACTION                                TIME
────  ─────────             ──────                                ────
 1    Frontend              POST /api/v1/export/csv
                            Body: {"start_date":"2026-09-01","end_date":"2026-09-30"}
                            Headers: Authorization: Bearer <token>

 2    Router                Pydantic validates → ExportRequest
      export_csv()          Depends: get_current_user_id → user_id
                            Depends: get_export_service → ExportService(session)

 3    Service               export_csv_sync(user_id, Sep-1, Sep-30)
      .export_csv_sync()

 4    CsvGenerator          .generate(user_id, Sep-1, Sep-30)                    ~0.1s
      .generate()             ├── HabitRepository: get_user_habits(include_archived=True)
                              │   → 6 habits (Water, Sleep, Exercise, Mood, Meditation, Steps)
                              ├── LogRepository: get_logs_for_range(user_id, Sep-1, Sep-30)
                              │   → 180 log entries (6 habits × 30 days)
                              ├── io.StringIO() → in-memory file
                              ├── csv.writer → write header row
                              ├── For each log: determine value by type → writerow
                              └── output.getvalue() → CSV string (~18KB)

 5    Router                StreamingResponse(                                   ~0.01s
                              iter([csv_content]),
                              media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=..."},
                            )

 6    Browser               Receives HTTP response with CSV content
                            Content-Disposition: attachment → "Save As" dialog
                            → health-tracker-2026-09-01-to-2026-09-30.csv saved

TOTAL: ~0.2 seconds (DB query + CSV generation + HTTP response)
```

---

## 3. Flow 2: Async Export (S3 + Pre-Signed URL)

```
USER: Clicks "Export to Cloud" or Lambda triggers batch export

STEP  COMPONENT             ACTION                                TIME
────  ─────────             ──────                                ────
 1    Client/Lambda         POST /api/v1/export/csv/s3
                            Body: {"start_date":"2026-01-01","end_date":"2026-09-30"}

 2    Service               export_csv_to_s3(user_id, Jan-1, Sep-30)
      .export_csv_to_s3()

 3    CsvGenerator          .generate_bytes(user_id, Jan-1, Sep-30)              ~0.3s
      .generate_bytes()       → 6 habits × 270 days = ~1620 rows
                              → CSV string → .encode("utf-8") → bytes (~160KB)

 4    StorageProvider        .upload_file(                                       ~0.5s
      .upload_file()            key="exports/uuid-001/2026-01-01_to_2026-09-30.csv",
                                content=csv_bytes,
                                content_type="text/csv",
                              )
                              → boto3 put_object → MinIO (dev) or S3 (prod)

 5    StorageProvider        .get_presigned_url(key, expires_in=86400)           ~0.01s
      .get_presigned_url()     → boto3 generate_presigned_url
                              → "http://localhost:9000/health-tracker-exports/exports/
                                  uuid-001/2026-01-01_to_2026-09-30.csv?
                                  X-Amz-Signature=abc123&X-Amz-Expires=86400"

 6    Router                ExportResponse(                                      ~0.01s
                              message="Export ready! Download link valid for 24 hours.",
                              download_url="http://localhost:9000/...",
                              status="ready",
                            )

 7    Client                Shows download link to user
                            OR: Notification service emails the link to user

TOTAL: ~1 second (DB + CSV generation + S3 upload + URL generation)
```

---

## 4. Flow 3: Lambda Batch Export

```
TRIGGER: Lambda csv_export function (invoked async by API or scheduled)

 1    Lambda handler        Receives event: {user_id, start_date, end_date}

 2    CsvGenerator          generate_bytes() → CSV bytes (sync DB, no async needed)

 3    S3 Upload             boto3 put_object → S3 (direct, not through MinIO)

 4    Pre-signed URL        generate_presigned_url → 24-hour download link

 5    Notification           NotificationService.send_export_ready(
                              user_email, user_name, "CSV",
                              start_date, end_date, download_url
                            )
                            → Email: "📁 Your export is ready! [Download CSV →]"

 6    Return                {"status": "complete", "download_url": "https://..."}

WHY LAMBDA: Large exports (1 year = 2200 rows) take >1 second.
Lambda can run for up to 15 minutes — no API timeout risk.
The user gets an email with the download link when done.
```

---

## 5. Cross-Module Connections

```
┌─── TRIGGERS ────────────────────────────────────┐
│  Frontend "Export" button → POST /export/csv      │
│  Frontend "Cloud Export" → POST /export/csv/s3    │
│  Lambda csv_export → async batch processing       │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌─── EXPORT SERVICE ──────────────────────────────┐
│  csv_generator → HabitRepo + LogRepo → CSV       │
│  storage → boto3 → MinIO (dev) / S3 (prod)      │
└─────────────────────┬─────────────────────────────┘
                      │ optionally triggers
                      ▼
┌─── NOTIFICATIONS (Part 13) ─────────────────────┐
│  send_export_ready(email, url)                    │
│  → email: "Your export is ready! [Download →]"   │
└──────────────────────────────────────────────────┘
```

---

## 6. Export Module Summary

### What You Built (Parts 14–14c)

| Part | Files | What It Does |
|------|-------|-------------|
| **14** | — | Overview: 2 modes, MinIO/S3, architecture |
| **14a** | csv_generator, pdf_generator, storage | Generators + S3 abstraction (full source) |
| **14b** | schemas, service, router | Request/response + orchestrator + 2 endpoints (full source) |
| **14c** | (this doc) | 3 flows: sync, async S3, Lambda batch |

### By the Numbers

| Metric | Value |
|--------|-------|
| Python files | 6 |
| Endpoints | 2 (sync CSV download, async S3+URL) |
| Export formats | CSV (+ HTML report placeholder for PDF) |
| Storage providers | MinIO (dev) / AWS S3 (prod) — same boto3 API |
| Pre-signed URL expiry | 24 hours |
| In-memory generation | io.StringIO + csv.writer (no temp files) |
| Cross-module dependencies | HabitRepository, LogRepository, NotificationService |

---

## 7. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 14b: Service & Router](./phase4-part14b-export-service-router.md) |
| ➡️ Next | [Part 15: Lambda Functions Overview](./phase4-part15-lambda-overview.md) |
| 📋 Full Plan | [FINAL_DOCS_PLAN.md](./FINAL_DOCS_PLAN.md) |
| 🏠 Start | [Phase 0 Part 1: Project Overview](./phase0-part1-project-overview.md) |

### Export Module — All Sub-Parts Complete ✅

| Sub-Part | Status |
|----------|--------|
| 14a | ✅ CSV Generator, PDF Generator, Storage |
| 14b | ✅ Service, Router, Schemas |
| **14c** | ✅ **Connections & Flows** |

---

**🎉 The Export module is COMPLETE.**

*Two export modes: instant CSV download and S3 upload with pre-signed URLs. MinIO locally, AWS S3 in production. Lambda handles batch exports with email notifications. Next: the Lambda functions that power scheduled tasks — daily reminders, weekly reports, streak checks, and more.*
