"""
Checks every known domain (from ssl_domains_v2) over HTTPS every 60
seconds and alerts admins by email if a domain returns 500, 502, 404,
or 403. Self-contained like ssl_dashboard.py - own table, own checker,
own endpoints. Reuses app/email_utils.py for sending.

Alerting behaviour: only a NEW bad status (not seen last cycle) triggers
an email - a domain stuck down does not re-email every minute. When a
domain recovers, its issue row is deleted, so a future recurrence is
treated as new and alerts again.
"""
import datetime
import logging
import ssl as ssl_lib
import threading
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.auth import require_admin
from app.models import User, Server, Client, RoleEnum
from app.notification_models import NotificationRecipient
from app.email_utils import send_email

router = APIRouter(prefix="/domain-health", tags=["domain-health"])
logger = logging.getLogger("domain_health")

CHECK_INTERVAL_SECONDS = 60
ALERT_STATUS_CODES = {500, 502, 403}
MAX_PARALLEL_HTTP = 20


class DomainHealthIssue(Base):
    __tablename__ = "domain_health_issues"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, nullable=False)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    status_code = Column(Integer, nullable=False)
    first_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_checked_at = Column(DateTime, default=datetime.datetime.utcnow)


class DomainHealthIssueOut(BaseModel):
    id: int
    server_id: int
    server_name: Optional[str] = None
    client_name: Optional[str] = None
    domain: str
    status_code: int
    first_detected_at: datetime.datetime
    last_checked_at: datetime.datetime

    class Config:
        from_attributes = True


def _check_domain_http_status(domain: str, timeout: int = 10) -> Optional[int]:
    """Returns the HTTP status code served at https://domain/, or None if
    the request failed for any other reason (DNS, timeout, refused, TLS
    handshake) - those are intentionally out of scope for this alert."""
    ctx = ssl_lib.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl_lib.CERT_NONE
    req = urllib.request.Request(
        f"https://{domain}/",
        headers={"User-Agent": "PM2Dashboard-HealthCheck/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def _get_admin_emails(db: Session) -> List[str]:
    """Every address in the Email Notification Recipients list gets
    alerts - not just ones tied to an admin login. This lets a shared
    inbox (e.g. devops@) receive alerts without needing its own
    dashboard account."""
    return sorted({r.email for r in db.query(NotificationRecipient).all()})


def _send_domain_down_email(db: Session, server_name: Optional[str], client_name: Optional[str], domain: str, status_code: int):
    admins = _get_admin_emails(db)
    if not admins:
        logger.info("[domain_health] no admin recipients with an email set - skipping send.")
        return
    subject = f"[PM2 Dashboard] {domain} is returning HTTP {status_code}"
    body = (
        f"<p><strong>{domain}</strong>"
        f"{f' on {server_name}' if server_name else ''}"
        f"{f' ({client_name})' if client_name else ''} "
        f"is currently returning <strong>HTTP {status_code}</strong>.</p>"
        f"<p>Check the SSL / Domains dashboard in PM2 Dashboard for details.</p>"
    )
    send_email(admins, subject, body)


def _send_domain_recovered_email(db: Session, server_name, client_name, domain: str, last_status_code: int):
    admins = _get_admin_emails(db)
    if not admins:
        return
    subject = f"[PM2 Dashboard] {domain} is back up"
    body = (
        f"<p><strong>{domain}</strong>"
        f"{f' on {server_name}' if server_name else ''}"
        f"{f' ({client_name})' if client_name else ''} "
        f"has recovered - it was previously returning HTTP {last_status_code}, "
        f"now responding normally.</p>"
        f"<p>Check the SSL / Domains dashboard in PM2 Dashboard for details.</p>"
    )
    send_email(admins, subject, body)


def _check_and_store_domain_health(db: Session):
    from app.routers.ssl_dashboard import SslDomain  # local import avoids circular import at module load

    servers = {s.id: s for s in db.query(Server).all()}
    clients = {c.id: c.name for c in db.query(Client).all()}

    # Dedup by domain string - same domain could theoretically appear
    # under more than one server row, we only need to check it once.
    domain_rows = {}
    for row in db.query(SslDomain).all():
        domain_rows.setdefault(row.domain, row)

    bad_this_cycle: dict = {}  # domain -> status_code
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_HTTP) as pool:
        futures = {
            pool.submit(_check_domain_http_status, domain): domain
            for domain in domain_rows.keys()
        }
        for future in as_completed(futures):
            domain = futures[future]
            status = future.result()
            if status in ALERT_STATUS_CODES:
                bad_this_cycle[domain] = status

    now = datetime.datetime.utcnow()
    existing_issues = {i.domain: i for i in db.query(DomainHealthIssue).all()}

    # New or changed-status issues -> upsert + email
    for domain, status_code in bad_this_cycle.items():
        srv = servers.get(domain_rows[domain].server_id)
        srv_name = srv.name if srv else None
        cli_name = clients.get(srv.client_id) if srv else None

        existing = existing_issues.get(domain)
        if existing is None:
            db.add(DomainHealthIssue(
                server_id=domain_rows[domain].server_id, domain=domain,
                status_code=status_code, first_detected_at=now, last_checked_at=now,
            ))
            db.commit()
            logger.info(f"[domain_health] NEW issue: {domain} -> {status_code}")
            _send_domain_down_email(db, srv_name, cli_name, domain, status_code)
        elif existing.status_code != status_code:
            existing.status_code = status_code
            existing.last_checked_at = now
            db.commit()
            logger.info(f"[domain_health] status changed: {domain} -> {status_code}")
            _send_domain_down_email(db, srv_name, cli_name, domain, status_code)
        else:
            existing.last_checked_at = now
            db.commit()

    # Recovered - no longer in the bad set. Send exactly one "back up"
    # email, then remove the issue row (a future recurrence is treated as
    # new and alerts again, same one-email-per-state-change principle as
    # the down alert).
    for domain, existing in existing_issues.items():
        if domain not in bad_this_cycle:
            srv = servers.get(existing.server_id)
            srv_name = srv.name if srv else None
            cli_name = clients.get(srv.client_id) if srv else None
            logger.info(f"[domain_health] recovered: {domain} - clearing issue")
            _send_domain_recovered_email(db, srv_name, cli_name, domain, existing.status_code)
            db.delete(existing)
    db.commit()


def _run_periodic_domain_health_check():
    from app.database import SessionLocal

    while True:
        time.sleep(CHECK_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            _check_and_store_domain_health(db)
        except Exception as exc:
            logger.warning(f"[domain_health] check cycle failed: {type(exc).__name__}: {exc}")
        finally:
            db.close()


def start_periodic_domain_health_check():
    thread = threading.Thread(target=_run_periodic_domain_health_check, daemon=True)
    thread.start()


@router.get("/issues", response_model=List[DomainHealthIssueOut])
def list_domain_issues(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    servers = {s.id: s for s in db.query(Server).all()}
    clients = {c.id: c.name for c in db.query(Client).all()}
    out = []
    for row in db.query(DomainHealthIssue).order_by(DomainHealthIssue.first_detected_at.desc()).all():
        srv = servers.get(row.server_id)
        out.append(DomainHealthIssueOut(
            id=row.id, server_id=row.server_id,
            server_name=srv.name if srv else None,
            client_name=clients.get(srv.client_id) if srv else None,
            domain=row.domain, status_code=row.status_code,
            first_detected_at=row.first_detected_at, last_checked_at=row.last_checked_at,
        ))
    return out
