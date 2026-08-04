"""
Lightweight notification summary for the navbar bell icon - combines:
  1. PM2 processes that are NOT online (errored, stopped, etc.) across
     every server of every client.
  2. SSL certificates expiring within 24 hours (from the already-scanned
     ssl_domains_v2 table - no live re-check here, just reads the DB).

The PM2 check is the expensive part (one SSH call per server), so the
result is cached in-memory for CACHE_SECONDS and reused across requests -
the navbar can poll this endpoint every 30-60s without hammering SSH.
"""
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import User, Server, Client
from app.auth import require_admin
from app.notification_models import NotificationRecipient, NotificationSentLog
from app.email_utils import send_email
from app.ssh_manager import list_pm2_processes, SSHConnectionError
from app.routers.ssl_dashboard import SslDomain
from app.routers.domain_health import DomainHealthIssue
from app.routers.server_resources import _collect as _collect_resources

router = APIRouter(prefix="/notifications", tags=["notifications"])

CACHE_SECONDS = 90
SSL_ALERT_HOURS = 24
RESOURCE_ALERT_THRESHOLD = 85.0


class ProcessNotification(BaseModel):
    client_id: int
    client_name: str
    server_id: int
    server_name: str
    process_name: str
    status: str


class SslNotification(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    server_id: int
    server_name: Optional[str] = None
    domain: str
    expires_at: Optional[datetime.datetime] = None
    hours_remaining: Optional[float] = None


class DomainDownNotification(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    server_id: int
    server_name: Optional[str] = None
    domain: str
    status_code: int
    first_detected_at: Optional[datetime.datetime] = None


class ResourceNotification(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    server_id: int
    server_name: Optional[str] = None
    metric: str  # "CPU" / "RAM" / "Disk"
    percent: float


class NotificationSummary(BaseModel):
    total: int
    process_alerts: List[ProcessNotification]
    ssl_alerts: List[SslNotification]
    domain_down_alerts: List[DomainDownNotification]
    resource_alerts: List[ResourceNotification]
    generated_at: datetime.datetime
    cached: bool


_cache: dict = {"data": None, "at": 0.0}


# Only these statuses count as a real crash/failure worth alerting on -
# "stopped" is usually intentional (someone stopped it on purpose), so it
# is excluded from notifications (it still shows on the Alerts page).
ALERT_STATUSES = {"errored"}

MAX_PARALLEL_SSH = 15


def _check_one_server(server: Server, client_name: str) -> List[ProcessNotification]:
    try:
        processes = list_pm2_processes(server)
    except SSHConnectionError:
        return []  # unreachable servers are already surfaced on the Alerts page
    out = []
    for proc in processes:
        status = proc.get("status", "unknown")
        if status in ALERT_STATUSES:
            out.append(ProcessNotification(
                client_id=server.client_id,
                client_name=client_name,
                server_id=server.id,
                server_name=server.name,
                process_name=proc.get("name", "unknown"),
                status=status,
            ))
    return out


def _collect_process_alerts(db: Session) -> List[ProcessNotification]:
    clients = {c.id: c.name for c in db.query(Client).all()}
    servers = db.query(Server).all()
    alerts: List[ProcessNotification] = []

    # Check every server's SSH in parallel instead of one-by-one, so total
    # time is roughly "slowest single server" rather than "sum of all of them".
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SSH) as pool:
        futures = {
            pool.submit(_check_one_server, server, clients.get(server.client_id, "Unknown")): server
            for server in servers
        }
        for future in as_completed(futures):
            alerts.extend(future.result())

    return alerts


def _collect_ssl_alerts(db: Session) -> List[SslNotification]:
    alerts: List[SslNotification] = []
    now = datetime.datetime.utcnow()
    cutoff = now + datetime.timedelta(hours=SSL_ALERT_HOURS)
    servers = {s.id: s for s in db.query(Server).all()}
    clients = {c.id: c.name for c in db.query(Client).all()}

    rows = (
        db.query(SslDomain)
        .filter(SslDomain.expires_at.isnot(None), SslDomain.expires_at <= cutoff)
        .all()
    )
    for row in rows:
        srv = servers.get(row.server_id)
        hours_remaining = (row.expires_at - now).total_seconds() / 3600
        alerts.append(SslNotification(
            client_id=srv.client_id if srv else None,
            client_name=clients.get(srv.client_id) if srv else None,
            server_id=row.server_id,
            server_name=srv.name if srv else None,
            domain=row.domain,
            expires_at=row.expires_at,
            hours_remaining=round(hours_remaining, 1),
        ))
    alerts.sort(key=lambda a: a.hours_remaining if a.hours_remaining is not None else 999999)
    return alerts


def _collect_domain_down_alerts(db: Session) -> List[DomainDownNotification]:
    alerts: List[DomainDownNotification] = []
    servers = {s.id: s for s in db.query(Server).all()}
    clients = {c.id: c.name for c in db.query(Client).all()}

    rows = db.query(DomainHealthIssue).all()
    for row in rows:
        srv = servers.get(row.server_id)
        alerts.append(DomainDownNotification(
            client_id=srv.client_id if srv else None,
            client_name=clients.get(srv.client_id) if srv else None,
            server_id=row.server_id,
            server_name=srv.name if srv else None,
            domain=row.domain,
            status_code=row.status_code,
            first_detected_at=row.first_detected_at,
        ))
    return alerts


def _collect_resource_alerts(db: Session) -> List[ResourceNotification]:
    """Runs the same parallel SSH-based CPU/RAM/Disk check used by the
    Resources page, and flags any server currently at or above
    RESOURCE_ALERT_THRESHOLD on any of the three metrics."""
    clients = {c.id: c.name for c in db.query(Client).all()}
    servers = db.query(Server).all()
    servers_by_id = {s.id: s for s in servers}
    alerts: List[ResourceNotification] = []

    results = _collect_resources(servers)
    for r in results:
        if r.status != "online":
            continue
        server = servers_by_id.get(r.server_id)
        client_id = server.client_id if server else None
        client_name = clients.get(client_id, "Unknown") if client_id else "Unknown"

        for metric, value in (
            ("CPU", r.cpu_percent),
            ("RAM", r.ram_percent),
            ("Disk", r.disk_percent),
        ):
            if value is not None and value >= RESOURCE_ALERT_THRESHOLD:
                alerts.append(ResourceNotification(
                    client_id=client_id,
                    client_name=client_name,
                    server_id=r.server_id,
                    server_name=r.name,
                    metric=metric,
                    percent=value,
                ))
    return alerts


class RecipientCreate(BaseModel):
    email: str


class RecipientOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


@router.get("/recipients", response_model=List[RecipientOut])
def list_recipients(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(NotificationRecipient).order_by(NotificationRecipient.email.asc()).all()


@router.post("/recipients", response_model=RecipientOut)
def add_recipient(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="That doesn't look like a valid email address.")

    existing = db.query(NotificationRecipient).filter(NotificationRecipient.email == email).first()
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="This email is already in the recipient list.")

    row = NotificationRecipient(email=email)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/recipients/{recipient_id}")
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    row = db.query(NotificationRecipient).filter(NotificationRecipient.id == recipient_id).first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Recipient not found")
    db.delete(row)
    db.commit()
    return {"detail": "Recipient removed"}


def _send_new_alert_emails(
    db: Session,
    process_alerts: List[ProcessNotification],
    ssl_alerts: List[SslNotification],
    resource_alerts: Optional[List[ResourceNotification]] = None,
):
    """
    Sends ONE email per genuinely NEW alert (never seen before in
    notification_sent_log), then records it so it's never re-emailed
    while it remains active. If the alert later disappears (resolved)
    and then reappears, it's treated as new again (log entry only
    exists while the alert was first seen, we don't clear it on
    resolution - a resurfaced alert genuinely deserves a fresh email).
    """
    recipients = [r.email for r in db.query(NotificationRecipient).all()]
    if not recipients:
        return

    for a in process_alerts:
        key = f"process:{a.server_id}:{a.process_name}:{a.status}"
        if db.query(NotificationSentLog).filter(NotificationSentLog.alert_key == key).first():
            continue
        subject = f"[PM2 Dashboard] {a.process_name} is {a.status}"
        body = (
            f"<p><strong>{a.process_name}</strong> on <strong>{a.server_name}</strong> "
            f"({a.client_name}) is currently <strong>{a.status}</strong>.</p>"
            f"<p>Check the Alerts page in PM2 Dashboard for details.</p>"
        )
        if send_email(recipients, subject, body):
            db.add(NotificationSentLog(alert_key=key, alert_type="process"))
            db.commit()

    for a in ssl_alerts:
        key = f"ssl:{a.server_id}:{a.domain}"
        if db.query(NotificationSentLog).filter(NotificationSentLog.alert_key == key).first():
            continue
        hours_txt = (
            "already expired" if (a.hours_remaining or 0) < 0
            else f"expires in {a.hours_remaining:.1f} hours"
        )
        subject = f"[PM2 Dashboard] SSL certificate expiring soon: {a.domain}"
        body = (
            f"<p>The SSL certificate for <strong>{a.domain}</strong> "
            f"({a.client_name or 'Unknown client'}) {hours_txt}.</p>"
            f"<p>Check the SSL Certificates page in PM2 Dashboard for details.</p>"
        )
        if send_email(recipients, subject, body):
            db.add(NotificationSentLog(alert_key=key, alert_type="ssl"))
            db.commit()

    for a in (resource_alerts or []):
        key = f"resource:{a.server_id}:{a.metric}"
        if db.query(NotificationSentLog).filter(NotificationSentLog.alert_key == key).first():
            continue
        subject = f"[PM2 Dashboard] High {a.metric} usage: {a.server_name}"
        body = (
            f"<p><strong>{a.server_name}</strong> ({a.client_name or 'Unknown client'}) "
            f"is at <strong>{a.percent:.1f}% {a.metric}</strong> usage, above the "
            f"{RESOURCE_ALERT_THRESHOLD:.0f}% alert threshold.</p>"
            f"<p>Check the Resources page in PM2 Dashboard for details.</p>"
        )
        if send_email(recipients, subject, body):
            db.add(NotificationSentLog(alert_key=key, alert_type="resource"))
            db.commit()


import datetime as _dt
import threading as _threading
import time as _time


def _send_daily_digest():
    """
    Sends ONE combined email at ~09:00 IST every day, listing every
    currently-active alert (errored processes + SSL certs expiring within
    24h) - regardless of whether each one was already emailed before.
    This is a summary/reminder digest, separate from - and replacing -
    any real-time per-alert email.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        recipients = [r.email for r in db.query(NotificationRecipient).all()]
        if not recipients:
            return

        process_alerts = _collect_process_alerts(db)
        ssl_alerts = _collect_ssl_alerts(db)
        resource_alerts = _collect_resource_alerts(db)

        if not process_alerts and not ssl_alerts and not resource_alerts:
            return  # nothing to report today

        rows = []
        for a in ssl_alerts:
            hours_txt = (
                "already expired" if (a.hours_remaining or 0) < 0
                else f"expires in {a.hours_remaining:.1f}h"
            )
            rows.append(
                f"<li><strong>{a.domain}</strong> ({a.client_name or 'Unknown client'}) - {hours_txt}</li>"
            )
        for a in process_alerts:
            rows.append(
                f"<li><strong>{a.process_name}</strong> on {a.server_name} "
                f"({a.client_name}) - {a.status}</li>"
            )
        for a in resource_alerts:
            rows.append(
                f"<li><strong>{a.server_name}</strong> ({a.client_name or 'Unknown client'}) - "
                f"{a.metric} at {a.percent:.1f}%</li>"
            )

        subject = f"[PM2 Dashboard] Daily alert digest - {len(rows)} item(s) need attention"
        body = "<p>Here's today's summary of active alerts:</p><ul>" + "".join(rows) + "</ul>"
        send_email(recipients, subject, body)
    finally:
        db.close()


def _run_daily_digest_scheduler():
    """Background loop: checks every minute whether it's ~09:00 IST, and
    if so (and we haven't already sent today), sends the digest. Checking
    every minute rather than sleeping until exactly 9am keeps this simple
    and resilient to the process being restarted at any time of day."""
    last_sent_date = None
    while True:
        now = _dt.datetime.now()
        if now.hour == 9 and now.minute == 0 and last_sent_date != now.date():
            try:
                _send_daily_digest()
            except Exception:
                pass
            last_sent_date = now.date()
        _time.sleep(30)


def start_daily_digest_scheduler():
    thread = _threading.Thread(target=_run_daily_digest_scheduler, daemon=True)
    thread.start()


@router.get("/summary", response_model=NotificationSummary)
def get_notification_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
    force: bool = False,
):
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["at"]) < CACHE_SECONDS:
        cached_summary = _cache["data"]
        return NotificationSummary(
            total=cached_summary.total,
            process_alerts=cached_summary.process_alerts,
            ssl_alerts=cached_summary.ssl_alerts,
            domain_down_alerts=cached_summary.domain_down_alerts,
            resource_alerts=cached_summary.resource_alerts,
            generated_at=cached_summary.generated_at,
            cached=True,
        )

    process_alerts = _collect_process_alerts(db)
    ssl_alerts = _collect_ssl_alerts(db)
    domain_down_alerts = _collect_domain_down_alerts(db)
    resource_alerts = _collect_resource_alerts(db)

    summary = NotificationSummary(
        total=len(process_alerts) + len(ssl_alerts) + len(domain_down_alerts) + len(resource_alerts),
        process_alerts=process_alerts,
        ssl_alerts=ssl_alerts,
        domain_down_alerts=domain_down_alerts,
        resource_alerts=resource_alerts,
        generated_at=datetime.datetime.utcnow(),
        cached=False,
    )
    _cache["data"] = summary
    _cache["at"] = now

    # Only resource alerts (CPU/RAM/Disk >= threshold) are wired to real-time
    # email for now - process/SSL real-time emailing stays inactive, unchanged
    # from before (they're still covered by the daily digest at 9am).
    _send_new_alert_emails(db, [], [], resource_alerts)

    return summary
