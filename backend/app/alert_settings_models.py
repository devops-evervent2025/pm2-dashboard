"""
Admin-configurable check intervals for every periodic background alert
scanner (SSL expiry, domain status, replication health, log/pm2-crash
alerts, daily digest). One row per alert_type, seeded with the
project's existing hardcoded defaults on first startup so behavior
never silently changes for anyone who doesn't touch the new settings
page. Each periodic loop re-reads its own row from this table at the
START of every cycle (not once at startup), so a saved change takes
effect on the very next cycle - no backend restart needed.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime

from app.database import Base


class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String(50), unique=True, nullable=False, index=True)
    interval_minutes = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# Existing hardcoded defaults, preserved exactly - only used to seed a
# row the FIRST time each alert_type is looked up and no row exists yet.
DEFAULT_INTERVALS_MINUTES = {
    "ssl_scan": 120,          # was: 2 * 60 * 60 seconds
    "domain_health": 1,       # was: CHECK_INTERVAL_SECONDS = 60
    "replication_health": 1,  # was: settings.MAXSCALE_CHECK_INTERVAL_SECONDS (~60s typical)
    "log_alerts": 1,          # was: settings.LOG_ALERT_CHECK_INTERVAL_SECONDS default 30s, rounded up to 1 min minimum
    "pm2_crash": 5,           # NEW: no periodic scanner existed before this - alerts only fired
                               # on-demand (bell click, 90s cache) or once/day at 9am digest.
}

# daily_digest is intentionally NOT here: it fires at a fixed clock time
# (9:00 AM daily), not on a repeating interval, so it doesn't fit this
# minutes-based settings model. It's left as-is, untouched.


def get_interval_minutes(db, alert_type: str) -> int:
    """Reads (and lazily seeds) the interval for one alert type. Never
    raises - falls back to the hardcoded default if anything's wrong,
    so a bad row can never take a whole scanner thread down."""
    try:
        row = db.query(AlertSetting).filter(AlertSetting.alert_type == alert_type).first()
        if row:
            return max(1, row.interval_minutes)
        default = DEFAULT_INTERVALS_MINUTES.get(alert_type, 60)
        db.add(AlertSetting(alert_type=alert_type, interval_minutes=default))
        db.commit()
        return default
    except Exception:
        db.rollback()
        return DEFAULT_INTERVALS_MINUTES.get(alert_type, 60)
