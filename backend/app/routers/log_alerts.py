"""
Real-time log alert system.

Polls every configured ServerLogSource (the same log directories your
App Logs viewer already browses via SSH) on an interval, reads only the
NEW bytes appended since last check, and raises an alert when a line
indicates:
  - level == "error" (structured JSON logs)
  - message contains: failed / exception / timeout
  - "cron failed" or "pm2 process stopped" (plain-text logs)

Every genuinely new alert is stored in `log_alerts` and emailed to the
existing NotificationRecipient list (same recipients used for PM2 crash /
SSL / replication alerts - one recipient list for everything).

Duplicate suppression: the same error (server + app + normalized message)
will not be re-emailed within DEDUP_WINDOW_MINUTES, even if it keeps
appearing in the log every cycle.

Self-contained like replication_health.py - own tables, own checker, own
endpoints, reuses app/email_utils.py for sending.
"""
import datetime
import hashlib
import json
import logging
import re
import shlex
import threading
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import User, Server, ServerLogSource
from app.notification_models import NotificationRecipient
from app.email_utils import send_email
from app.ssh_manager import run_command as ssh_run_command, SSHConnectionError
from app.log_alert_models import LogAlert, LogAlertCursor
from app.routers.server_logs import _parse_ls_line

router = APIRouter(prefix="/log-alerts", tags=["log-alerts"])
logger = logging.getLogger("log_alerts")

DEDUP_WINDOW_MINUTES = 120  # 2 hours - same error alerts once, then stays silent until this window passes
_LOG_FILE_PATTERN = re.compile(r"^(app|error)-\d{4}-\d{2}-\d{2}\.log$")

# OUR-SIDE failure signatures - the ONLY things that ever raise an alert,
# regardless of log level. This platform integrates with dozens of insurer/
# partner APIs (Universal Sompo, Royal Sundaram, Tata AIG, Adrila Lite,
# BillDesk, etc.) that fail constantly for business/data reasons ("Vehicle
# lookup failed", "premium calculation failed", "API call failed", "422
# response") - none of that is a bug in OUR code, so none of it should page
# anyone. Only genuine infra/process/cron failures on our side should.
# Add more patterns here if you spot a genuine our-side failure that slips
# through without alerting.
_OUR_SIDE_PATTERNS = [
    re.compile(r"cron\s+(job\s+)?failed", re.I),
    re.compile(r"scheduled\s+job\s+failed", re.I),
    re.compile(r"pm2\s+process\s+stopped", re.I),
    re.compile(r"\bprocess\s+(stopped|crashed|died)\b", re.I),
    re.compile(r"uncaught\s+exception", re.I),
    re.compile(r"unhandled\s+rejection", re.I),
    re.compile(r"segmentation\s+fault", re.I),
    re.compile(r"out\s+of\s+memory|heap\s+out\s+of\s+memory|\bOOM\b", re.I),
    re.compile(r"EADDRINUSE", re.I),
    re.compile(r"ENOSPC|no\s+space\s+left\s+on\s+device", re.I),
    re.compile(r"(database|db|mysql|mongo|redis|postgres)\s+connection\s+(failed|refused|lost|error)", re.I),
    re.compile(r"(sequelize|mongoose)\w*connection\w*error", re.I),
    re.compile(r"could\s+not\s+connect\s+to\s+(database|redis|db)", re.I),
    re.compile(r"lost\s+connection\s+to\s+mysql\s+server", re.I),
    re.compile(r"mysql\s+server\s+has\s+gone\s+away", re.I),
    re.compile(r"too\s+many\s+connections", re.I),
    re.compile(r"connection\s+pool\s+(exhausted|timeout|error)", re.I),
    re.compile(r"ER_CON_COUNT_ERROR|ETIMEDOUT.*3306|ECONNREFUSED.*3306", re.I),
    re.compile(r"access\s+denied\s+for\s+user", re.I),
    re.compile(r"\bflush\b.*(admin|failed|error)", re.I),
    re.compile(r"deadlock\s+found", re.I),
    re.compile(r"\bETIMEDOUT\b.*(mysql|database|db)", re.I),
    re.compile(r"migration\s+failed", re.I),
    re.compile(r"worker\s+(died|crashed|exited)", re.I),
    re.compile(r"deployment\s+failed", re.I),
]


# ---------------- detection ----------------

def _dig_error(meta: dict, depth: int = 0) -> Optional[str]:
    if depth > 4 or not isinstance(meta, dict):
        return None
    for key in ("error", "message"):
        val = meta.get(key)
        if isinstance(val, str) and val:
            return val
    for val in meta.values():
        if isinstance(val, dict):
            found = _dig_error(val, depth + 1)
            if found:
                return found
    return None


def _is_our_side_failure(message: str) -> bool:
    """True only if this line matches a KNOWN our-side infra/cron/process
    failure signature. Default is False - business/integration errors from
    insurer APIs, payment gateways, etc. never alert, no matter how scary
    the wording or what log level they're tagged with."""
    return any(p.search(message) for p in _OUR_SIDE_PATTERNS)


def _detect_from_line(line: str) -> Optional[dict]:
    """Returns {level, message, timestamp} ONLY if this line is a genuine
    OUR-SIDE failure (cron/process/infra) - see _OUR_SIDE_PATTERNS. Business
    or third-party integration errors (insurer APIs, payment gateways) never
    raise an alert here, even at level=error, since those fail constantly
    for reasons that have nothing to do with our own code."""
    line = line.strip()
    if not line:
        return None

    level = None
    message = line
    timestamp = None

    if line.startswith("{"):
        try:
            data = json.loads(line)
            level = (str(data.get("level", "")).lower() or None)
            message = data.get("message") or line
            timestamp = data.get("timestamp")
            nested = _dig_error((data.get("metadata") or {}))
            if nested:
                message = f"{message} \u2014 {nested}"
        except (json.JSONDecodeError, AttributeError):
            pass

    if not _is_our_side_failure(message):
        return None

    return {"level": level or "error", "message": message.strip(), "timestamp": timestamp}


def _make_alert_key(server_id: int, app_name: str, message: str) -> str:
    # collapse numeric IDs/refs so near-identical recurring errors still dedupe
    normalized = re.sub(r"\d+", "#", message)[:300]
    raw = f"{server_id}:{app_name}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _is_duplicate(db: Session, alert_key: str) -> bool:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=DEDUP_WINDOW_MINUTES)
    return (
        db.query(LogAlert)
        .filter(LogAlert.alert_key == alert_key, LogAlert.created_at >= cutoff)
        .first()
        is not None
    )


# ---------------- email ----------------

def _send_alert_email(db: Session, alert: LogAlert) -> bool:
    recipients = [r.email for r in db.query(NotificationRecipient).all()]
    if not recipients:
        logger.info("[log_alerts] no recipients configured - skipping email.")
        return False

    subject = f"[PM2 Dashboard] {alert.log_level.upper()} in {alert.app_name} on {alert.server_name}"
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:auto;">'
        '<div style="background:#fdecea;border-left:5px solid #c0392b;padding:10px 16px;'
        'margin-bottom:14px;border-radius:4px;">'
        f'<span style="color:#c0392b;font-weight:700;font-size:14px;">ALERT: {alert.log_level.upper()}</span>'
        '</div>'
        '<table style="font-size:14px;color:#333;line-height:1.6;">'
        f'<tr><td><strong>Server:</strong></td><td>&nbsp;{alert.server_name}</td></tr>'
        f'<tr><td><strong>Application:</strong></td><td>&nbsp;{alert.app_name}</td></tr>'
        f'<tr><td><strong>Log Level:</strong></td><td>&nbsp;{alert.log_level}</td></tr>'
        f'<tr><td><strong>Timestamp:</strong></td><td>&nbsp;{alert.log_timestamp or alert.created_at.isoformat()}</td></tr>'
        '</table>'
        f'<p style="font-size:14px;color:#333;"><strong>Error Message:</strong><br>{alert.error_message}</p>'
        '<p style="font-size:12px;color:#555;"><strong>Full Log:</strong></p>'
        '<pre style="background:#f5f5f5;padding:10px;border-radius:4px;font-size:11px;'
        f'overflow-x:auto;white-space:pre-wrap;">{(alert.full_log or "")[:4000]}</pre>'
        '<p style="font-size:12px;color:#888;margin-top:18px;">Check the Alerts page in PM2 Dashboard for details.</p>'
        '</div>'
    )
    sent = send_email(recipients, subject, body)
    alert.email_sent = "yes" if sent else "no"
    db.commit()
    return sent


# ---------------- polling ----------------

def _get_file_size(server: Server, remote_path: str) -> Optional[int]:
    try:
        out = ssh_run_command(server, f"wc -c < {shlex.quote(remote_path)}", timeout=15)
        return int(out.strip())
    except Exception:
        return None


def _read_new_lines(server: Server, remote_path: str, offset: int):
    size = _get_file_size(server, remote_path)
    if size is None:
        return "", offset
    if size < offset:
        offset = 0  # rotated/truncated - start fresh
    if size == offset:
        return "", offset
    out = ssh_run_command(server, f"tail -c +{offset + 1} {shlex.quote(remote_path)}", timeout=20)
    return out, size


def _list_active_log_files(server: Server, remote_path: str) -> List[str]:
    try:
        out = ssh_run_command(server, f"ls -la --time-style=full-iso {shlex.quote(remote_path)}", timeout=20)
    except SSHConnectionError:
        return []
    names = []
    for line in out.splitlines():
        parsed = _parse_ls_line(line)
        if parsed and _LOG_FILE_PATTERN.match(parsed.name):
            names.append(parsed.name)
    return names


def _poll_source(db: Session, server: Server, source: ServerLogSource):
    for filename in _list_active_log_files(server, source.remote_path):
        full_path = f"{source.remote_path.rstrip('/')}/{filename}"
        cursor = (
            db.query(LogAlertCursor)
            .filter_by(server_id=server.id, source_id=source.id, filename=filename)
            .first()
        )
        offset = cursor.last_offset if cursor else 0
        text, new_offset = _read_new_lines(server, full_path, offset)

        if text:
            app_name = source.label or source.remote_path
            for line in text.splitlines():
                hit = _detect_from_line(line)
                if not hit:
                    continue
                alert_key = _make_alert_key(server.id, app_name, hit["message"])
                if _is_duplicate(db, alert_key):
                    continue
                alert = LogAlert(
                    alert_key=alert_key,
                    server_id=server.id,
                    server_name=server.name,
                    app_name=app_name,
                    log_level=hit["level"],
                    error_message=hit["message"][:2000],
                    full_log=line[:4000],
                    source_file=filename,
                    log_timestamp=hit["timestamp"],
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)
                try:
                    _send_alert_email(db, alert)
                except Exception as exc:
                    logger.warning(f"[log_alerts] email failed for alert {alert.id}: {exc}")

        if cursor:
            cursor.last_offset = new_offset
            cursor.updated_at = datetime.datetime.utcnow()
        else:
            db.add(LogAlertCursor(server_id=server.id, source_id=source.id, filename=filename, last_offset=new_offset))
        db.commit()


def _check_all_sources():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        servers = {s.id: s for s in db.query(Server).all()}
        for source in db.query(ServerLogSource).all():
            server = servers.get(source.server_id)
            if not server:
                continue
            try:
                _poll_source(db, server, source)
            except SSHConnectionError:
                continue
            except Exception as exc:
                logger.warning(f"[log_alerts] error polling source {source.id} on {server.name}: {exc}")
    finally:
        db.close()


def _run_periodic_log_alert_check():
    from app.database import SessionLocal
    from app.alert_settings_models import get_interval_minutes

    while True:
        db = SessionLocal()
        try:
            interval_minutes = get_interval_minutes(db, "log_alerts")
        except Exception:
            interval_minutes = 1
        finally:
            db.close()
        time.sleep(max(10, interval_minutes * 60))
        try:
            _check_all_sources()
        except Exception as exc:
            logger.warning(f"[log_alerts] check cycle failed: {type(exc).__name__}: {exc}")


def start_periodic_log_alert_check():
    thread = threading.Thread(target=_run_periodic_log_alert_check, daemon=True)
    thread.start()


# ---------------- endpoints ----------------

class LogAlertOut(BaseModel):
    id: int
    server_name: str
    app_name: str
    log_level: str
    error_message: str
    full_log: Optional[str] = None
    source_file: Optional[str] = None
    log_timestamp: Optional[str] = None
    created_at: datetime.datetime
    email_sent: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[LogAlertOut])
def list_log_alerts(
    server_id: Optional[int] = None,
    log_level: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(LogAlert)
    if server_id:
        q = q.filter(LogAlert.server_id == server_id)
    if log_level:
        q = q.filter(LogAlert.log_level == log_level)
    return q.order_by(LogAlert.created_at.desc()).limit(min(limit, 500)).all()


@router.get("/{alert_id}", response_model=LogAlertOut)
def get_log_alert(alert_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    alert = db.query(LogAlert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@router.delete("/{alert_id}")
def delete_log_alert(alert_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    alert = db.query(LogAlert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    db.delete(alert)
    db.commit()
    return {"detail": "Alert removed"}
