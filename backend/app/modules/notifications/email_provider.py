# ============================================================================
# Notifications — Email Provider (Abstract + Implementations)
# ============================================================================
# WHAT THIS FILE DOES:
#   Sends emails using the configured provider.
#   Same Strategy pattern as LLM clients — swap provider via config.
#
# PROVIDERS:
#   ConsoleProvider → prints to terminal (dev — no real emails)
#   ResendProvider  → Resend.com API (free tier: 100 emails/day)
#   SESProvider     → AWS SES (production: 3K emails/month free from EC2)
#
# WHY ABSTRACT:
#   Development: console (see emails in terminal, no API key needed)
#   Staging: Resend (free, easy setup)
#   Production: SES (reliable, cheap, integrates with AWS)
#   Swap via EMAIL_PROVIDER config — zero code changes.
# ============================================================================

from abc import ABC, abstractmethod

import httpx

from app.config import get_settings
from app.shared.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseEmailProvider(ABC):
    """Abstract email provider — all implementations send emails the same way."""

    @abstractmethod
    async def send(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Send an email.

        Returns True if sent successfully, False on failure.
        Never raises — email failures shouldn't crash the app.
        """
        ...


class ConsoleProvider(BaseEmailProvider):
    """
    Development email provider — prints emails to the terminal.

    No API keys, no external services. You see the email content in logs.
    Perfect for development and testing.
    """

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        logger.info(
            "email_sent_console",
            to=to_email,
            subject=subject,
            body_preview=html_body[:200],
        )
        print(f"\n{'='*60}")
        print(f"📧 EMAIL (console mode)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"{'─'*60}")
        print(html_body[:500])
        if len(html_body) > 500:
            print(f"... ({len(html_body)} chars total)")
        print(f"{'='*60}\n")
        return True


class ResendProvider(BaseEmailProvider):
    """
    Resend.com email provider — free tier: 100 emails/day.

    Simple API, great for staging deployments.
    Sign up at resend.com, get an API key, set RESEND_API_KEY in .env.
    """

    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.SES_FROM_EMAIL

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "from": self.from_email,
                        "to": [to_email],
                        "subject": subject,
                        "html": html_body,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                logger.info("email_sent_resend", to=to_email, subject=subject)
                return True
        except Exception as e:
            logger.error("email_send_error_resend", to=to_email, error=str(e))
            return False


class SESProvider(BaseEmailProvider):
    """
    AWS SES email provider — production use.

    Free tier: 3,000 emails/month when sending from EC2.
    Requires: verified sender email/domain in SES console.
    """

    def __init__(self):
        import boto3
        self.ses_client = boto3.client("ses", region_name=settings.AWS_REGION)
        self.from_email = settings.SES_FROM_EMAIL

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            # boto3 is synchronous — run in thread pool for async compatibility
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.ses_client.send_email(
                    Source=self.from_email,
                    Destination={"ToAddresses": [to_email]},
                    Message={
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                    },
                ),
            )
            logger.info("email_sent_ses", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("email_send_error_ses", to=to_email, error=str(e))
            return False


def get_email_provider() -> BaseEmailProvider:
    """Factory — returns the configured email provider."""
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        return ResendProvider()
    elif provider == "ses":
        return SESProvider()
    else:
        return ConsoleProvider()
