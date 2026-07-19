"""
Models for the email-notification feature:
  - NotificationRecipient: list of email addresses to send alerts to
    (managed via the admin UI, not hardcoded).
  - NotificationSentLog: tracks which specific alerts we've already
    emailed about, so the same alert doesn't get re-emailed every time
    the notification summary is recomputed - only genuinely NEW alerts
    trigger a new email.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class NotificationSentLog(Base):
    __tablename__ = "notification_sent_log"

    id = Column(Integer, primary_key=True, index=True)
    alert_key = Column(String(500), unique=True, nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    first_sent_at = Column(DateTime, default=datetime.datetime.utcnow)
