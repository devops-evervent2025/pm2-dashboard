path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add threading + logging imports
old_imports = "import datetime\nimport socket\nimport ssl as ssl_lib"
new_imports = "import datetime\nimport socket\nimport ssl as ssl_lib\nimport threading\nimport time\nimport logging"
if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("imports added")
else:
    print("MISSING: import block")

# 2. Add a logger + nginx-detection helper + periodic scan loop, right before _scan_server
marker = "def _scan_server(server: Server) -> List[dict]:"
new_helpers = '''logger = logging.getLogger("ssl_dashboard")

_NGINX_CHECK_CMD = (
    "test -d /etc/nginx/sites-enabled -o -d /etc/nginx/conf.d && echo YES || echo NO"
)


def _server_has_nginx(server: Server) -> bool:
    """Cheap, fast check (5s timeout) so servers with no nginx conf dir at
    all are skipped entirely during scan-all, instead of spending a full
    SSH round-trip (and SSH-fallback TLS checks) on servers that were
    never going to have any domains to find."""
    try:
        output = run_command(server, _NGINX_CHECK_CMD, timeout=5)
    except SSHConnectionError:
        return False
    return "YES" in output


def _run_periodic_ssl_scan():
    """Background loop: re-scans every server with an nginx conf dir once
    every 6 hours, so certificate data stays fresh without every page
    load or manual click needing to wait on SSH to the whole fleet."""
    from app.database import SessionLocal

    while True:
        time.sleep(6 * 60 * 60)
        logger.info("[ssl_scan] periodic scan starting")
        db = SessionLocal()
        try:
            for server in db.query(Server).all():
                if not _server_has_nginx(server):
                    continue
                try:
                    _scan_and_store(server, db)
                except Exception as exc:
                    logger.warning(f"[ssl_scan] periodic scan of {server.name} failed: {exc}")
        finally:
            db.close()
        logger.info("[ssl_scan] periodic scan finished")


def start_periodic_ssl_scan():
    """Called once on app startup - runs the periodic loop in a daemon
    thread so it never blocks server startup or shutdown."""
    thread = threading.Thread(target=_run_periodic_ssl_scan, daemon=True)
    thread.start()


def _scan_and_store(server: Server, db: Session) -> List[dict]:
    """Scans one server and upserts results into the DB - shared by both
    the manual scan endpoints and the periodic background scan."""
    scanned = _scan_server(server)
    now = datetime.datetime.utcnow()
    for item in scanned:
        existing = (
            db.query(SslDomain)
            .filter(SslDomain.server_id == server.id, SslDomain.domain == item["domain"])
            .first()
        )
        if existing:
            existing.cert_path = item["cert_path"]
            existing.expires_at = item["expires_at"]
            existing.last_scanned_at = now
        else:
            db.add(SslDomain(
                server_id=server.id, domain=item["domain"], cert_path=item["cert_path"],
                expires_at=item["expires_at"], last_scanned_at=now,
            ))
    db.commit()
    return scanned


''' + marker

if marker in content and "_run_periodic_ssl_scan" not in content:
    content = content.replace(marker, new_helpers)
    changes.append("periodic scan + nginx-detection helpers added")
else:
    print("MISSING or already present: _scan_server marker")

# 3. Make scan_server endpoint use the shared _scan_and_store + skip non-nginx servers
old_scan_one = '''@router.post("/scan/{server_id}", response_model=SslScanResponse)
def scan_server(server_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    server = _get_server_or_404(server_id, db)
    scanned = _scan_server(server)
    now = datetime.datetime.utcnow()

    for item in scanned:
        existing = (
            db.query(SslDomain)
            .filter(SslDomain.server_id == server.id, SslDomain.domain == item["domain"])
            .first()
        )
        if existing:
            existing.cert_path = item["cert_path"]
            existing.expires_at = item["expires_at"]
            existing.last_scanned_at = now
        else:
            db.add(SslDomain(
                server_id=server.id, domain=item["domain"], cert_path=item["cert_path"],
                expires_at=item["expires_at"], last_scanned_at=now,
            ))
    db.commit()

    rows = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()
    return SslScanResponse(
        server_id=server.id, server_name=server.name, domains_found=len(scanned),
        domains=[_to_out(r, server.name) for r in rows],
    )'''

new_scan_one = '''@router.post("/scan/{server_id}", response_model=SslScanResponse)
def scan_server(server_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    server = _get_server_or_404(server_id, db)
    if not _server_has_nginx(server):
        raise HTTPException(status_code=400, detail="This server has no nginx conf directory - nothing to scan.")
    scanned = _scan_and_store(server, db)

    rows = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()
    return SslScanResponse(
        server_id=server.id, server_name=server.name, domains_found=len(scanned),
        domains=[_to_out(r, server.name) for r in rows],
    )'''

if old_scan_one in content:
    content = content.replace(old_scan_one, new_scan_one)
    changes.append("scan_server endpoint simplified")
else:
    print("MISSING: scan_server endpoint block")

# 4. Make scan_all_servers skip non-nginx servers and use shared helper
old_scan_all = '''@router.post("/scan-all", response_model=List[SslScanResponse])
def scan_all_servers(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    results = []
    for server in db.query(Server).all():
        try:
            scanned = _scan_server(server)
        except HTTPException:
            results.append(SslScanResponse(
                server_id=server.id, server_name=server.name, domains_found=0, domains=[],
            ))
            continue

        now = datetime.datetime.utcnow()
        for item in scanned:
            existing = (
                db.query(SslDomain)
                .filter(SslDomain.server_id == server.id, SslDomain.domain == item["domain"])
                .first()
            )
            if existing:
                existing.cert_path = item["cert_path"]
                existing.expires_at = item["expires_at"]
                existing.last_scanned_at = now
            else:
                db.add(SslDomain(
                    server_id=server.id, domain=item["domain"], cert_path=item["cert_path"],
                    expires_at=item["expires_at"], last_scanned_at=now,
                ))
        db.commit()

        rows = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()
        results.append(SslScanResponse(
            server_id=server.id, server_name=server.name, domains_found=len(scanned),
            domains=[_to_out(r, server.name) for r in rows],
        ))
    return results'''

new_scan_all = '''@router.post("/scan-all", response_model=List[SslScanResponse])
def scan_all_servers(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    results = []
    for server in db.query(Server).all():
        if not _server_has_nginx(server):
            continue  # skip servers with no nginx conf dir entirely - nothing to scan
        try:
            scanned = _scan_and_store(server, db)
        except HTTPException:
            results.append(SslScanResponse(
                server_id=server.id, server_name=server.name, domains_found=0, domains=[],
            ))
            continue

        rows = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()
        results.append(SslScanResponse(
            server_id=server.id, server_name=server.name, domains_found=len(scanned),
            domains=[_to_out(r, server.name) for r in rows],
        ))
    return results'''

if old_scan_all in content:
    content = content.replace(old_scan_all, new_scan_all)
    changes.append("scan_all_servers updated")
else:
    print("MISSING: scan_all_servers endpoint block")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
