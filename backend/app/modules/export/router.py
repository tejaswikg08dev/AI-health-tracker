# ============================================================================
# Export Module — Router
# ============================================================================
# ENDPOINTS:
#   POST /api/v1/export/csv       → Export habit data as CSV download
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

    For small exports (< 30 days), this is instant.
    For large exports, consider using the /csv/s3 endpoint instead.
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

    The URL expires in 24 hours. Used for:
    - Large exports
    - Async processing (Lambda generates CSV, emails link to user)
    - Sharing export links
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
