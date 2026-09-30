# ============================================================================
# Notifications Module — Router
# ============================================================================
# ENDPOINTS:
#   GET  /api/v1/notifications/settings     → Get notification preferences
#   PUT  /api/v1/notifications/settings     → Update preferences
#   POST /api/v1/notifications/test-email   → Send a test email
# ============================================================================

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.modules.auth.router import get_current_user_id
from app.modules.auth.service import AuthService
from app.modules.notifications.schemas import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    TestEmailRequest,
)
from app.modules.notifications.service import NotificationService
from app.redis_client import get_redis_client
from app.shared.base_schemas import SuccessResponse

router = APIRouter()


async def get_notification_service(
    session: AsyncSession = Depends(get_async_session),
) -> NotificationService:
    return NotificationService(session)


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Get notification preferences",
)
async def get_settings(
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationSettingsResponse:
    """Get the current user's notification preferences."""
    settings = await service.get_settings(user_id)
    return NotificationSettingsResponse.model_validate(settings)


@router.put(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Update notification preferences",
)
async def update_settings(
    data: NotificationSettingsUpdate,
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationSettingsResponse:
    """Update notification preferences. Only provided fields are changed."""
    settings = await service.update_settings(user_id, data)
    return NotificationSettingsResponse.model_validate(settings)


@router.post(
    "/test-email",
    response_model=SuccessResponse,
    summary="Send a test email",
)
async def send_test_email(
    data: TestEmailRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    redis_client=Depends(get_redis_client),
) -> SuccessResponse:
    """Send a test email to verify email settings are working."""
    from app.shared.date_utils import today_utc

    auth_service = AuthService(session, redis_client)
    user = await auth_service.get_current_user(user_id)
    service = NotificationService(session)

    sent = await service.send_daily_reminder(
        user_email=user.email,
        user_name=user.full_name,
        date_str=str(today_utc()),
    )

    if sent:
        return SuccessResponse(message="Test email sent successfully! Check your inbox.")
    return SuccessResponse(message="Failed to send test email. Check email provider settings.")
