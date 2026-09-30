# Mock S3/MinIO storage — stores files in memory

class MockStorageProvider:
    """In-memory file storage for testing — no real S3/MinIO needed."""

    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload_file(self, key: str, content: bytes, content_type: str = "") -> str:
        self.files[key] = content
        return key

    async def download_file(self, key: str) -> bytes:
        if key not in self.files:
            raise FileNotFoundError(f"Key not found: {key}")
        return self.files[key]

    async def get_presigned_url(self, key: str, expires_in: int = 86400) -> str:
        return f"https://mock-s3.local/{key}?expires={expires_in}"

    async def delete_file(self, key: str) -> None:
        self.files.pop(key, None)

    async def ensure_bucket_exists(self) -> None:
        pass
