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
    2. Async export (large data) — generate CSV, upload to S3, email download link
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
