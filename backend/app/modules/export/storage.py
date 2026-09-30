# ============================================================================
# Export — Object Storage (S3 / MinIO Abstraction)
# ============================================================================
# WHAT THIS FILE DOES:
#   Uploads and downloads files to S3-compatible storage.
#   MinIO in development, AWS S3 in production — same API (boto3).
#
# WHY MINIO LOCALLY:
#   MinIO is an S3-compatible server you run in Docker.
#   It speaks the exact same API as AWS S3 (same boto3 calls).
#   Your code works identically in dev (MinIO) and production (S3).
#   The only difference: the endpoint URL.
#
# OPERATIONS:
#   upload_file     → store a file (CSV, PDF) in S3
#   download_file   → get file content from S3
#   get_presigned_url → temporary download link (expires in 24h)
#   delete_file     → remove a file from S3
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
    Uses boto3 — the official AWS SDK for Python.

    The only difference between MinIO and S3:
    - MinIO: endpoint_url = "http://localhost:9000"
    - S3:    endpoint_url = None (boto3 defaults to AWS)
    """

    def __init__(self):
        # Configure boto3 for S3 or MinIO
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

        The URL is valid for `expires_in` seconds (default: 24 hours).
        Anyone with the URL can download the file — no auth needed.
        After expiry, the URL stops working.

        Used for: emailing download links to users.
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
