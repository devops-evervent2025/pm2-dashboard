path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_import = "from app.models import User, Server"
new_import = "from app.models import User, Server, Client"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("Client import added")
else:
    print("MISSING: models import line")

old_schema = '''class SslDomainOut(BaseModel):
    id: int
    server_id: int
    server_name: Optional[str] = None
    domain: str
    cert_path: Optional[str] = None
    expires_at: Optional[datetime.datetime] = None
    days_remaining: Optional[int] = None
    last_scanned_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True'''

new_schema = '''class SslDomainOut(BaseModel):
    id: int
    server_id: int
    server_name: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    domain: str
    cert_path: Optional[str] = None
    expires_at: Optional[datetime.datetime] = None
    days_remaining: Optional[int] = None
    last_scanned_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True'''

if old_schema in content:
    content = content.replace(old_schema, new_schema)
    changes.append("schema updated")
else:
    print("MISSING: SslDomainOut schema")

old_to_out = '''def _to_out(row: SslDomain, server_name: Optional[str]) -> SslDomainOut:
    days_remaining = None
    if row.expires_at:
        days_remaining = (row.expires_at - datetime.datetime.utcnow()).days
    return SslDomainOut(
        id=row.id,
        server_id=row.server_id,
        server_name=server_name,
        domain=row.domain,
        cert_path=row.cert_path,
        expires_at=row.expires_at,
        days_remaining=days_remaining,
        last_scanned_at=row.last_scanned_at,
    )'''

new_to_out = '''def _to_out(row: SslDomain, server_name: Optional[str], client_id: Optional[int] = None, client_name: Optional[str] = None) -> SslDomainOut:
    days_remaining = None
    if row.expires_at:
        days_remaining = (row.expires_at - datetime.datetime.utcnow()).days
    return SslDomainOut(
        id=row.id,
        server_id=row.server_id,
        server_name=server_name,
        client_id=client_id,
        client_name=client_name,
        domain=row.domain,
        cert_path=row.cert_path,
        expires_at=row.expires_at,
        days_remaining=days_remaining,
        last_scanned_at=row.last_scanned_at,
    )'''

if old_to_out in content:
    content = content.replace(old_to_out, new_to_out)
    changes.append("_to_out updated")
else:
    print("MISSING: _to_out function")

old_list = '''@router.get("/domains", response_model=List[SslDomainOut])
def list_domains(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    # MySQL has no NULLS LAST syntax - order by "is null" first (False < True,
    # so non-null rows sort first), then by the actual expiry date.
    rows = (
        db.query(SslDomain)
        .order_by(SslDomain.expires_at.is_(None), SslDomain.expires_at.asc())
        .all()
    )
    server_names = {s.id: s.name for s in db.query(Server).all()}
    return [_to_out(r, server_names.get(r.server_id)) for r in rows]'''

new_list = '''@router.get("/domains", response_model=List[SslDomainOut])
def list_domains(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    # MySQL has no NULLS LAST syntax - order by "is null" first (False < True,
    # so non-null rows sort first), then by the actual expiry date.
    rows = (
        db.query(SslDomain)
        .order_by(SslDomain.expires_at.is_(None), SslDomain.expires_at.asc())
        .all()
    )
    servers = {s.id: s for s in db.query(Server).all()}
    clients = {c.id: c.name for c in db.query(Client).all()}
    out = []
    for r in rows:
        srv = servers.get(r.server_id)
        srv_name = srv.name if srv else None
        cli_id = srv.client_id if srv else None
        cli_name = clients.get(cli_id) if cli_id else None
        out.append(_to_out(r, srv_name, cli_id, cli_name))
    return out'''

if old_list in content:
    content = content.replace(old_list, new_list)
    changes.append("list_domains updated")
else:
    print("MISSING: list_domains endpoint")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
