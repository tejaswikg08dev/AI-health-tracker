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
