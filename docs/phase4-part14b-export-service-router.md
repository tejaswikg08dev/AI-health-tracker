# 📥 Phase 4 Part 14b: Export — Service, Router & Schemas

> **"The service orchestrates: generator produces CSV, storage uploads to S3. The router returns either a direct file download (StreamingResponse) or a JSON response with a pre-signed URL. Two endpoints, two modes, one service."**

---

## 📋 Document Metadata

| Field | Value |
|-------|-------|
| **Project** | AI-Powered Personal Health & Habit Tracker |
| **Phase** | 4 — Implementation |
| **Part** | 14b (Export Service + Router) |
| **Sprint** | Sprint 4 — Delivery + Lambda |
| **Previous** | [phase4-part14a-export-csv-pdf-storage.md](./phase4-part14a-export-csv-pdf-storage.md) |
| **Next** | [phase4-part14c-export-connections-and-flows.md](./phase4-part14c-export-connections-and-flows.md) |
| **Files in This Doc** | 3 files (schemas.py, service.py, router.py) |
| **Time to Type** | ~30 minutes |
| **Difficulty** | Medium (StreamingResponse for file download, Content-Disposition header, two export modes) |

---

## 1. File 1: `schemas.py` — Export Request/Response

### Type This Code: `backend/app/modules/export/schemas.py`

```python
# ============================================================================
# Export Module — Schemas
# ============================================================================

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.base_schemas import BaseSchema


class ExportRequest(BaseModel):
    """Request to export habit data as CSV."""

    start_date: date = Field(..., description="Start of date range (inclusive)")
    end_date: date = Field(..., description="End of date range (inclusive)")
    format: str = Field(
        default="csv",
        description="Export format: csv",
        examples=["csv"],
    )


class ExportResponse(BaseModel):
    """Response after requesting an export."""

    message: str
    download_url: str | None = Field(
        default=None,
        description="Direct download URL (for S3 exports)",
    )
    status: str = Field(
        default="ready",
        description="ready (sync download) or processing (async, emailed later)",
    )


class ReportMetadata(BaseModel):
    """Metadata for a stored report."""

    id: UUID
    report_type: str     # "weekly_report", "csv_export"
    title: str
    created_at: datetime
    download_url: str | None = None
```

### Key Schema Details

**`ExportRequest` — Date Range**
```python
start_date: date = Field(..., description="Start of date range (inclusive)")
end_date: date = Field(..., description="End of date range (inclusive)")
```
- Both required (`...`). Pydantic parses ISO date strings: `"2026-09-01"` → `date(2026, 9, 1)`
- `format` defaults to `"csv"` — future-proofed for PDF when WeasyPrint is installed

**`ExportResponse` — Two Modes**
```python
download_url: str | None = Field(default=None)
status: str = Field(default="ready")
```
- Sync mode: `download_url` is `None` (file is returned directly as StreamingResponse)
- Async mode: `download_url` contains the S3 pre-signed URL, `status="ready"`
- Failed export: `download_url=None`, `status="failed"`, `message="Export failed: ..."`

---

## 2. File 2: `service.py` — Export Orchestrator

### Type This Code: `backend/app/modules/export/service.py`

```python
# ============================================================================
# Export Module — Service Layer
# ============================================================================
# Handles CSV/PDF export generation, S3 storage, and download URLs.
# ============================================================================

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.export.csv_generator import CsvGenerator
from app.modules.export.pdf_generator import PdfGenerator
from app.modules.export.storage import StorageProvider
from app.shared.logging import get_logger

logger = get_logger(__name__)


class ExportService:
    """
    Data export service.

    Two modes:
    1. Sync export (small data) — generate CSV, return directly as download
    2. Async export (large data) — generate CSV, upload to S3, return download URL
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.csv_generator = CsvGenerator(session)
        self.pdf_generator = PdfGenerator()
        self.storage = StorageProvider()

    async def export_csv_sync(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> str:
        """
        Generate CSV and return content directly (for small exports).

        The router returns this as a StreamingResponse with
        Content-Disposition: attachment; filename="export.csv"
        The browser downloads it immediately.
        """
        csv_content = await self.csv_generator.generate(user_id, start_date, end_date)

        logger.info(
            "csv_export_sync",
            user_id=str(user_id),
            date_range=f"{start_date} to {end_date}",
            size=len(csv_content),
        )

        return csv_content

    async def export_csv_to_s3(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> str:
        """
        Generate CSV, upload to S3, return a pre-signed download URL.

        Used for large exports or async processing (Lambda).
        The URL expires in 24 hours.
        """
        # Generate CSV
        csv_bytes = await self.csv_generator.generate_bytes(user_id, start_date, end_date)

        # Upload to S3
        s3_key = f"exports/{user_id}/{start_date}_to_{end_date}.csv"
        await self.storage.upload_file(s3_key, csv_bytes, content_type="text/csv")

        # Generate download URL
        download_url = await self.storage.get_presigned_url(s3_key)

        logger.info(
            "csv_export_s3",
            user_id=str(user_id),
            s3_key=s3_key,
        )

        return download_url

    async def generate_report_html(
        self,
        user_name: str,
        title: str,
        content: str,
    ) -> str:
        """Generate an HTML report (viewable in browser, convertible to PDF)."""
        return self.pdf_generator.generate_html_report(title, content, user_name)
```

### Key Service Patterns

**Constructor — Wires All Components**
```python
def __init__(self, session: AsyncSession):
    self.csv_generator = CsvGenerator(session)   # Needs DB session for queries
    self.pdf_generator = PdfGenerator()           # No dependencies (pure generation)
    self.storage = StorageProvider()               # Needs boto3 config from settings
```

**`export_csv_sync()` — Direct Return**
```python
csv_content = await self.csv_generator.generate(user_id, start_date, end_date)
return csv_content  # String — router wraps in StreamingResponse
```
One call. Generator produces the CSV string. Service returns it. Router sends it as a file download. Fastest path — no S3, no URL generation.

**`export_csv_to_s3()` — Three Steps**
```python
# 1. Generate CSV as bytes
csv_bytes = await self.csv_generator.generate_bytes(user_id, start_date, end_date)

# 2. Upload to S3
s3_key = f"exports/{user_id}/{start_date}_to_{end_date}.csv"
await self.storage.upload_file(s3_key, csv_bytes, content_type="text/csv")

# 3. Generate pre-signed download URL
download_url = await self.storage.get_presigned_url(s3_key)
return download_url
```

**S3 Key Naming Convention:**
`exports/{user_id}/{start_date}_to_{end_date}.csv`
→ `exports/abc-123/2026-09-01_to_2026-09-30.csv`

Organized by user, with date range in the filename. Easy to browse in the S3 console.

---

## 3. File 3: `router.py` — 2 Endpoints

### Type This Code: `backend/app/modules/export/router.py`

```python
# ============================================================================
# Export Module — Router
# ============================================================================
# ENDPOINTS:
#   POST /api/v1/export/csv       → Export as CSV download
#   POST /api/v1/export/csv/s3    → Export to S3, return download URL
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.auth.router import get_current_user_id
from app.modules.export.schemas import ExportRequest, ExportResponse
from app.modules.export.service import ExportService

router = APIRouter()


async def get_export_service(
    session: AsyncSession = Depends(get_async_session),
) -> ExportService:
    return ExportService(session)


@router.post(
    "/csv",
    summary="Export habit data as CSV (direct download)",
)
async def export_csv(
    data: ExportRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ExportService = Depends(get_export_service),
) -> StreamingResponse:
    """
    Export habit log data as a CSV file.

    Returns the CSV as a direct download.
    The browser will save it as a file.
    """
    csv_content = await service.export_csv_sync(user_id, data.start_date, data.end_date)

    filename = f"health-tracker-{data.start_date}-to-{data.end_date}.csv"

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post(
    "/csv/s3",
    response_model=ExportResponse,
    summary="Export CSV to S3 (returns download URL)",
)
async def export_csv_to_s3(
    data: ExportRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ExportService = Depends(get_export_service),
) -> ExportResponse:
    """
    Export habit data to S3 and return a temporary download URL.
    The URL expires in 24 hours.
    """
    try:
        download_url = await service.export_csv_to_s3(
            user_id, data.start_date, data.end_date
        )
        return ExportResponse(
            message="Export ready! Download link valid for 24 hours.",
            download_url=download_url,
            status="ready",
        )
    except Exception as e:
        return ExportResponse(
            message=f"Export failed: {str(e)}",
            download_url=None,
            status="failed",
        )
```

### Key Router Concepts

**`StreamingResponse` for File Download**
```python
return StreamingResponse(
    iter([csv_content]),                    # Content as iterable
    media_type="text/csv",                  # MIME type
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
    },
)
```
- `StreamingResponse` — sends content as an HTTP response with streaming capability
- `iter([csv_content])` — wraps the string in an iterable (StreamingResponse expects an iterator)
- `media_type="text/csv"` — tells the browser this is a CSV file
- `Content-Disposition: attachment; filename="..."` — THE key header. It tells the browser:
  - `attachment` → don't display, SAVE as file
  - `filename="health-tracker-2026-09-01-to-2026-09-30.csv"` → suggested filename

**Without `Content-Disposition`:** browser would display the CSV as raw text.
**With `Content-Disposition: attachment`:** browser opens "Save As" dialog.

**S3 Endpoint — JSON Response with URL**
```python
return ExportResponse(
    message="Export ready! Download link valid for 24 hours.",
    download_url="https://bucket.s3.amazonaws.com/exports/...?X-Amz-Signature=...",
    status="ready",
)
```
- Returns JSON (not a file). The frontend shows the download link or auto-opens it
- `try/except` catches S3 upload failures → returns `status="failed"` (not a crash)

---

## 4. How to Verify Your Work

```bash
# Test sync CSV export
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"shreya@test.com","password":"Test123!@#"}' | jq -r '.access_token')

curl -X POST http://localhost/api/v1/export/csv \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-09-01","end_date":"2026-09-30"}' \
  -o health-data.csv

# Check the file
cat health-data.csv | head -5
# Expected:
# Date,Habit Name,Type,Value,Unit,Notes
# 2026-09-01,Water Intake,numeric,7.0,glasses,
# 2026-09-01,Sleep Hours,numeric,7.5,hours,
# ...

# Test S3 export (requires MinIO running)
curl -X POST http://localhost/api/v1/export/csv/s3 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-09-01","end_date":"2026-09-30"}'
# Expected: {"message":"Export ready!","download_url":"http://localhost:9000/...","status":"ready"}
```

---

## 5. What You Learned

| # | Concept | What It Is | Where Used |
|---|---------|-----------|------------|
| 1 | **`StreamingResponse`** | FastAPI sends content as file download | router.py CSV endpoint |
| 2 | **`Content-Disposition: attachment`** | HTTP header: save as file (not display) | router.py headers |
| 3 | **`iter([content])`** | Wrap string in iterable for StreamingResponse | router.py |
| 4 | **`media_type="text/csv"`** | MIME type tells browser it's a CSV | router.py |
| 5 | **Sync vs Async service** | Direct return (sync) vs S3+URL (async) | service.py |
| 6 | **S3 key naming** | `exports/{user_id}/{dates}.csv` — organized by user | service.py |
| 7 | **Error handling in export** | try/except → `status="failed"` (not crash) | router.py S3 endpoint |

---

## 6. Interview Q&A

### Q1: How does the CSV file download work technically?
**A:** "The service generates CSV content as a string in memory. The router wraps it in a `StreamingResponse` with `media_type='text/csv'` and a `Content-Disposition: attachment; filename='...'` header. The `Content-Disposition` header is what tells the browser to open a 'Save As' dialog instead of displaying the content. The browser saves the response body as a `.csv` file with the suggested filename."

### Q2: Why two export endpoints instead of one with a mode parameter?
**A:** "Different HTTP responses. The sync endpoint returns a `StreamingResponse` (binary file download) — no JSON body. The async endpoint returns a `ExportResponse` JSON with a download URL. FastAPI can't return both types from one endpoint with the same response_model. Two endpoints also have different use cases: sync for the browser 'Export' button, async for Lambda batch processing."

### Q3: How does the S3 export handle failures?
**A:** "The router wraps the service call in try/except. If CSV generation fails (no data), S3 upload fails (MinIO down), or URL generation fails, the response is `ExportResponse(status='failed', message='Export failed: ...')` — NOT an HTTP 500. The client gets a clean JSON response explaining what went wrong. This is the same pattern as email sending (Part 13) — exports are best-effort, not crash-worthy."

---

## 7. Navigation

| Direction | Document |
|-----------|----------|
| ⬅️ Previous | [Part 14a: CSV, PDF & Storage](./phase4-part14a-export-csv-pdf-storage.md) |
| ➡️ Next | [Part 14c: Export Connections & Flows](./phase4-part14c-export-connections-and-flows.md) |

### Export Sub-Parts Progress

| Sub-Part | Status |
|----------|--------|
| 14a | ✅ CSV Generator, PDF Generator, Storage |
| **14b** | ✅ **You are here** — Service, Router, Schemas |
| 14c | ⬜ Next — Connections & Flows |

---

**End of Phase 4 Part 14b: Export Service & Router**

*Two endpoints: sync returns a file, async returns a URL. The service orchestrates generator + storage. Next: flow diagrams for both modes and the Lambda integration.*
