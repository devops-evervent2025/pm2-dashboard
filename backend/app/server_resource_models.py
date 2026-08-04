import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint

from app.database import Base


class ServerResourceLog(Base):
    __tablename__ = "server_resource_logs"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    cpu_percent = Column(Float, nullable=True)
    ram_used_mb = Column(Integer, nullable=True)
    ram_total_mb = Column(Integer, nullable=True)
    ram_percent = Column(Float, nullable=True)
    disk_used = Column(String(50), nullable=True)
    disk_total = Column(String(50), nullable=True)
    disk_percent = Column(Float, nullable=True)

    status = Column(String(20), default="online")
    error_message = Column(String(500), nullable=True)

    checked_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class DiskAlertState(Base):
    """Tracks which disk-usage alert thresholds (85/90/95/100) are
    currently 'active' (already emailed, not yet reset) per server.
    A row exists only while that threshold stays breached - it's
    deleted once usage drops back below it, so the same threshold
    can fire again the next time it's crossed."""
    __tablename__ = "disk_alert_states"
    __table_args__ = (
        UniqueConstraint("server_id", "threshold", name="uq_disk_alert_server_threshold"),
    )

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False, index=True)
    threshold = Column(Integer, nullable=False)
    triggered_at = Column(DateTime, default=datetime.datetime.utcnow)
