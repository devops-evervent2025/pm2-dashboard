"""
Models for the real-time log alert feature:
  - LogAlertCursor: tracks how far we've already read into each log file
    (server_id + source_id + filename -> byte offset), so the poller only
    reads NEW lines each cycle instead of re-scanning whole files.
  - LogAlert: every alert raised (error / failed / exception / timeout /
    cron failed / pm2 process stopped), stored for the dashboard's Alerts view.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, BigInteger
from app.database import Base


class LogAlertCursor(Base):
    __tablename__ = "log_alert_cursors"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, nullable=False, index=True)
    source_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    last_offset = Column(BigInteger, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class LogAlert(Base):
    __tablename__ = "log_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_key = Column(String(64), nullable=False, index=True)  # dedup hash
    server_id = Column(Integer, nullable=False, index=True)
    server_name = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=False)     # log source label
    log_level = Column(String(50), nullable=False)      # error / cron_failed / pm2_stopped / ...
    error_message = Column(Text, nullable=False)
    full_log = Column(Text, nullable=True)
    source_file = Column(String(500), nullable=True)
    log_timestamp = Column(String(100), nullable=True)  # timestamp as it appeared in the log line
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    email_sent = Column(String(10), default="no")       # "yes"/"no" - avoids Boolean migration friction
