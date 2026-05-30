import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_reset_password_email(to_email: str, token: str) -> None:
    if settings.PASSWORD_RESET_BASE_URL.strip():
        base = settings.PASSWORD_RESET_BASE_URL.rstrip("/")
        reset_link = f"{base}/reset-password?token={token}"
        logger.info("Password reset link for %s: %s", to_email, reset_link)
    else:
        logger.info(
            "Password reset token for %s — use POST /api/v1/auth/reset-password: %s",
            to_email,
            token,
        )
