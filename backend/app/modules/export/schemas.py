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
        description="Direct download URL (for sync exports)",
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
