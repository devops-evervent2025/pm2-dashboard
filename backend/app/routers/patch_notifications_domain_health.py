import shutil
from datetime import datetime

path = "notifications.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

changes = []

# 1. Import the DomainHealthIssue model
old = "from app.routers.ssl_dashboard import SslDomain"
new = "from app.routers.ssl_dashboard import SslDomain\nfrom app.routers.domain_health import DomainHealthIssue"
changes.append((old, new))

# 2. New response model for a domain-down alert
old = '''class SslNotification(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    server_id: int
    server_name: Optional[str] = None
    domain: str
    expires_at: Optional[datetime.datetime] = None
    hours_remaining: Optional[float] = None'''
new = '''class SslNotification(BaseModel):
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
    first_detected_at: Optional[datetime.datetime] = None'''
changes.append((old, new))

# 3. Add the new list + total count into NotificationSummary
old = '''class NotificationSummary(BaseModel):
    total: int
    process_alerts: List[ProcessNotification]
    ssl_alerts: List[SslNotification]
    generated_at: datetime.datetime
    cached: bool'''
new = '''class NotificationSummary(BaseModel):
    total: int
    process_alerts: List[ProcessNotification]
    ssl_alerts: List[SslNotification]
    domain_down_alerts: List[DomainDownNotification]
    generated_at: datetime.datetime
    cached: bool'''
changes.append((old, new))

# 4. New collector function, placed right after _collect_ssl_alerts
old = '''class RecipientCreate(BaseModel):'''
new = '''def _collect_domain_down_alerts(db: Session) -> List[DomainDownNotification]:
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


class RecipientCreate(BaseModel):'''
changes.append((old, new))

# 5. Wire it into the /summary endpoint - both the cache-hit branch and the fresh-computation branch
old = '''    if not force and _cache["data"] is not None and (now - _cache["at"]) < CACHE_SECONDS:
        cached_summary = _cache["data"]
        return NotificationSummary(
            total=cached_summary.total,
            process_alerts=cached_summary.process_alerts,
            ssl_alerts=cached_summary.ssl_alerts,
            generated_at=cached_summary.generated_at,
            cached=True,
        )

    process_alerts = _collect_process_alerts(db)
    ssl_alerts = _collect_ssl_alerts(db)

    summary = NotificationSummary(
        total=len(process_alerts) + len(ssl_alerts),
        process_alerts=process_alerts,
        ssl_alerts=ssl_alerts,
        generated_at=datetime.datetime.utcnow(),
        cached=False,
    )'''
new = '''    if not force and _cache["data"] is not None and (now - _cache["at"]) < CACHE_SECONDS:
        cached_summary = _cache["data"]
        return NotificationSummary(
            total=cached_summary.total,
            process_alerts=cached_summary.process_alerts,
            ssl_alerts=cached_summary.ssl_alerts,
            domain_down_alerts=cached_summary.domain_down_alerts,
            generated_at=cached_summary.generated_at,
            cached=True,
        )

    process_alerts = _collect_process_alerts(db)
    ssl_alerts = _collect_ssl_alerts(db)
    domain_down_alerts = _collect_domain_down_alerts(db)

    summary = NotificationSummary(
        total=len(process_alerts) + len(ssl_alerts) + len(domain_down_alerts),
        process_alerts=process_alerts,
        ssl_alerts=ssl_alerts,
        domain_down_alerts=domain_down_alerts,
        generated_at=datetime.datetime.utcnow(),
        cached=False,
    )'''
changes.append((old, new))

for old, new in changes:
    count = content.count(old)
    if count != 1:
        print(f"ERROR: expected 1 occurrence, found {count}. Aborting, nothing changed. Block:\n{old[:100]}...")
        raise SystemExit(1)

for old, new in changes:
    content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)
print("Patched notifications.py successfully.")
