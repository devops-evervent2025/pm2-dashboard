"""
Admin-only endpoints to view/update the check interval (in minutes) for
each periodic alert scanner. Reading these values never touches the
scanners directly - each scanner loop re-reads its own row from the DB
at the start of every cycle, so a save here takes effect on the very
next cycle automatically, no restart needed.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models import User
from app.alert_settings_models import AlertSetting, DEFAULT_INTERVALS_MINUTES

router = APIRouter(prefix="/alert-settings", tags=["alert-settings"])

ALERT_TYPE_LABELS = {
    "ssl_scan": "SSL Certificate Expiry",
    "domain_health": "Domain Status (down/error)",
    "replication_health": "Database Replication Health",
    "log_alerts": "Application Log Errors",
    "pm2_crash": "PM2 Process Crash",
}


class AlertSettingOut(BaseModel):
    alert_type: str
    label: str
    interval_minutes: int

    class Config:
        from_attributes = True


class AlertSettingUpdate(BaseModel):
    interval_minutes: int = Field(..., ge=1, le=10080)  # 1 minute to 1 week


@router.get("", response_model=List[AlertSettingOut])
def list_alert_settings(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Returns all known alert types with their current interval - seeds
    any missing row with its hardcoded default first, so the list is
    always complete even before any scanner has run yet."""
    existing = {row.alert_type: row for row in db.query(AlertSetting).all()}
    result = []
    for alert_type, label in ALERT_TYPE_LABELS.items():
        row = existing.get(alert_type)
        if not row:
            row = AlertSetting(
                alert_type=alert_type,
                interval_minutes=DEFAULT_INTERVALS_MINUTES.get(alert_type, 60),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
        result.append(AlertSettingOut(alert_type=alert_type, label=label, interval_minutes=row.interval_minutes))
    return result


@router.put("/{alert_type}", response_model=AlertSettingOut)
def update_alert_setting(
    alert_type: str,
    payload: AlertSettingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if alert_type not in ALERT_TYPE_LABELS:
        raise HTTPException(status_code=404, detail="Unknown alert type")

    row = db.query(AlertSetting).filter(AlertSetting.alert_type == alert_type).first()
    if not row:
        row = AlertSetting(alert_type=alert_type, interval_minutes=payload.interval_minutes)
        db.add(row)
    else:
        row.interval_minutes = payload.interval_minutes
    db.commit()
    db.refresh(row)

    return AlertSettingOut(
        alert_type=alert_type,
        label=ALERT_TYPE_LABELS[alert_type],
        interval_minutes=row.interval_minutes,
    )
