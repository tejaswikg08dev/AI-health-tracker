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
