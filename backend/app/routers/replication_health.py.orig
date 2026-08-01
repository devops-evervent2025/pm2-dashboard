"""
Polls the MaxScale REST API every 30 seconds and alerts admins by email
if replication breaks on any monitored server - i.e. a non-master server
whose state no longer includes "Slave" (IO/SQL thread stopped), or any
server reported as "Down". Self-contained like domain_health.py - own
table, own checker, own endpoints. Reuses app/email_utils.py for sending.

Alerting behaviour: only a NEW bad state (not seen last cycle) triggers
an email - a server stuck broken does not re-email every 30 seconds.
When a server recovers, its issue row is deleted, so a future recurrence
is treated as new and alerts again.

If MAXSCALE_API_URL is not configured, this feature is a no-op - the
periodic check simply skips each cycle instead of failing.
"""
import base64
import datetime
import json
import logging
import ssl as ssl_lib
import threading
import time
import urllib.error
import urllib.request
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, get_db
from app.auth import require_admin
from app.models import User, RoleEnum
from app.notification_models import NotificationRecipient
from app.email_utils import send_email

router = APIRouter(prefix="/replication", tags=["replication"])
logger = logging.getLogger("replication_health")


class ReplicationHealthIssue(Base):
    __tablename__ = "replication_health_issues"

    id = Column(Integer, primary_key=True, index=True)
    server_name = Column(String(255), nullable=False, unique=True, index=True)
    issue_type = Column(String(50), nullable=False)  # "replication_broken" or "down"
    state = Column(String(255), nullable=True)
    first_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_checked_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReplicationHealthIssueOut(BaseModel):
    id: int
    server_name: str
    issue_type: str
    state: Optional[str] = None
    first_detected_at: datetime.datetime
    last_checked_at: datetime.datetime

    class Config:
        from_attributes = True


class ReplicationServerStatus(BaseModel):
    server_name: str
    state: str
    issue_type: Optional[str] = None


def _fetch_maxscale_servers() -> Optional[list]:
    """Returns the raw `data` list from GET /v1/servers, or None if
    MaxScale isn't configured or couldn't be reached this cycle."""
    settings = get_settings()
    if not settings.MAXSCALE_API_URL or not settings.MAXSCALE_API_USERNAME:
        return None

    url = settings.MAXSCALE_API_URL.rstrip("/") + "/v1/servers"
    creds = f"{settings.MAXSCALE_API_USERNAME}:{settings.MAXSCALE_API_PASSWORD}"
    auth_header = "Basic " + base64.b64encode(creds.encode()).decode()
    req = urllib.request.Request(
        url, headers={"Authorization": auth_header, "Accept": "application/json"}
    )
    ctx = ssl_lib.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl_lib.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            payload = json.loads(resp.read().decode())
        return payload.get("data", [])
    except Exception as exc:
        logger.warning(f"[replication_health] could not reach MaxScale API: {type(exc).__name__}: {exc}")
        return None


def _classify_server(state: str) -> Optional[str]:
    """None means healthy. A master is healthy as long as it isn't Down.
    A non-master (slave) is only healthy if its state still includes
    "Slave" - if MaxScale demoted it to bare "Running", replication has
    stopped on that node even though the server itself is reachable."""
    if "Down" in state:
        return "down"
    if "Master" in state:
        return None
    if "Slave" not in state:
        return "replication_broken"
    return None


def _get_admin_emails(db: Session) -> List[str]:
    admin_emails = {
        u.email for u in db.query(User)
        .filter(User.role == RoleEnum.admin, User.email.isnot(None), User.email != "")
        .all()
    }
    recipient_emails = {r.email for r in db.query(NotificationRecipient).all()}
    return sorted(admin_emails & recipient_emails)


def _send_replication_broken_email(db: Session, server_name: str, issue_type: str, state: str):
    admins = _get_admin_emails(db)
    if not admins:
        logger.info("[replication_health] no admin recipients with an email set - skipping send.")
        return
    if issue_type == "down":
        subject = f"[PM2 Dashboard] MaxScale server {server_name} is DOWN"
        detail = f"MaxScale reports <strong>{server_name}</strong> as unreachable (state: {state})."
    else:
        subject = f"[PM2 Dashboard] Replication broken on {server_name}"
        detail = (
            f"<strong>{server_name}</strong> is no longer replicating - "
            f"MaxScale reports its state as <strong>{state}</strong> "
            f"(expected it to include \"Slave\")."
        )
    body = f"<p>{detail}</p><p>Check the MaxScale dashboard for details.</p>"
    send_email(admins, subject, body)


def _send_replication_recovered_email(db: Session, server_name: str, issue_type: str):
    admins = _get_admin_emails(db)
    if not admins:
        return
    label = "back up" if issue_type == "down" else "replicating again"
    subject = f"[PM2 Dashboard] {server_name} is {label}"
    body = f"<p><strong>{server_name}</strong> has recovered and is {label}.</p>"
    send_email(admins, subject, body)


def _check_and_store_replication_health(db: Session):
    servers_data = _fetch_maxscale_servers()
    if servers_data is None:
        return  # not configured or unreachable this cycle - skip, don't spam

    bad_this_cycle: dict = {}
    for item in servers_data:
        name = item.get("id")
        state = (item.get("attributes") or {}).get("state", "")
        issue = _classify_server(state)
        if name and issue:
            bad_this_cycle[name] = {"issue": issue, "state": state}

    now = datetime.datetime.utcnow()
    existing_issues = {i.server_name: i for i in db.query(ReplicationHealthIssue).all()}

    for name, info in bad_this_cycle.items():
        existing = existing_issues.get(name)
        if existing is None:
            db.add(ReplicationHealthIssue(
                server_name=name, issue_type=info["issue"], state=info["state"],
                first_detected_at=now, last_checked_at=now,
            ))
            db.commit()
            logger.info(f"[replication_health] NEW issue: {name} -> {info['issue']} ({info['state']})")
            _send_replication_broken_email(db, name, info["issue"], info["state"])
        elif existing.issue_type != info["issue"] or existing.state != info["state"]:
            existing.issue_type = info["issue"]
            existing.state = info["state"]
            existing.last_checked_at = now
            db.commit()
            logger.info(f"[replication_health] status changed: {name} -> {info['issue']} ({info['state']})")
            _send_replication_broken_email(db, name, info["issue"], info["state"])
        else:
            existing.last_checked_at = now
            db.commit()

    for name, existing in existing_issues.items():
        if name not in bad_this_cycle:
            logger.info(f"[replication_health] recovered: {name}")
            _send_replication_recovered_email(db, name, existing.issue_type)
            db.delete(existing)
    db.commit()


def _run_periodic_replication_health_check():
    from app.database import SessionLocal

    while True:
        settings = get_settings()
        time.sleep(max(10, settings.MAXSCALE_CHECK_INTERVAL_SECONDS))
        db = SessionLocal()
        try:
            _check_and_store_replication_health(db)
        except Exception as exc:
            logger.warning(f"[replication_health] check cycle failed: {type(exc).__name__}: {exc}")
        finally:
            db.close()


def start_periodic_replication_health_check():
    thread = threading.Thread(target=_run_periodic_replication_health_check, daemon=True)
    thread.start()


@router.get("/issues", response_model=List[ReplicationHealthIssueOut])
def list_replication_issues(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return (
        db.query(ReplicationHealthIssue)
        .order_by(ReplicationHealthIssue.first_detected_at.desc())
        .all()
    )


@router.get("/status", response_model=List[ReplicationServerStatus])
def get_live_status(_admin: User = Depends(require_admin)):
    """On-demand live check (bypasses the periodic cache) - useful for a
    status widget or for verifying MAXSCALE_* settings are correct."""
    data = _fetch_maxscale_servers()
    if data is None:
        raise HTTPException(502, "Could not reach MaxScale API - check MAXSCALE_* settings in .env")
    out = []
    for item in data:
        name = item.get("id")
        state = (item.get("attributes") or {}).get("state", "")
        out.append(ReplicationServerStatus(server_name=name, state=state, issue_type=_classify_server(state)))
    return out
