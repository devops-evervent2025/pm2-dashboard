path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

marker = "def _scan_server(server: Server) -> List[dict]:"

restored_block = '''logger = logging.getLogger("ssl_dashboard")

_NGINX_CHECK_CMD = (
    "test -d /etc/nginx/sites-enabled -o -d /etc/nginx/conf.d && echo YES || echo NO"
)


def _server_has_nginx(server: Server) -> bool:
    """Cheap, fast check (5s timeout) so servers with no nginx conf dir at
    all are skipped entirely during scan-all, instead of spending a full
    SSH round-trip on servers that were never going to have any domains
    to find."""
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
            existing.check_error = item.get("check_error")
            existing.last_scanned_at = now
        else:
            db.add(SslDomain(
                server_id=server.id, domain=item["domain"], cert_path=item["cert_path"],
                expires_at=item["expires_at"], check_error=item.get("check_error"),
                last_scanned_at=now,
            ))
    db.commit()
    return scanned


''' + marker

if marker in content and "_server_has_nginx" not in content:
    content = content.replace(marker, restored_block)
    changes.append("functions restored with check_error support")
else:
    print("MISSING marker, or functions already present")

if len(changes) == 1:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - no changes written. Applied so far:", changes)
