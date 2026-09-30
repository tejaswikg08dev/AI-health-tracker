# Mock email provider — captures sent emails for assertion

from dataclasses import dataclass, field


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


class MockEmailProvider:
    """Fake email provider that stores emails in a list for testing."""

    def __init__(self):
        self.sent_emails: list[SentEmail] = []

    async def send(self, to_email: str, subject: str, html_body: str) -> bool:
        self.sent_emails.append(SentEmail(to=to_email, subject=subject, body=html_body))
        return True

    @property
    def last_email(self) -> SentEmail | None:
        return self.sent_emails[-1] if self.sent_emails else None

    @property
    def email_count(self) -> int:
        return len(self.sent_emails)
