"""
Minimal SMTP email sender for the notification feature. If SMTP_HOST is
not configured in .env, sending is silently skipped (logged, not raised)
so the rest of the app keeps working normally with in-app notifications
only - email is an optional add-on, never a hard dependency.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import get_settings

logger = logging.getLogger("email_utils")


def send_email(to_addresses: list[str], subject: str, body_html: str) -> bool:
    settings = get_settings()

    if not settings.SMTP_HOST or not to_addresses:
        logger.info("[email] SMTP not configured or no recipients - skipping send.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg["To"] = ", ".join(to_addresses)
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], to_addresses, msg.as_string())
        logger.info(f"[email] sent '{subject}' to {len(to_addresses)} recipient(s).")
        return True
    except Exception as exc:
        logger.warning(f"[email] failed to send '{subject}': {type(exc).__name__}: {exc}")
        return False
