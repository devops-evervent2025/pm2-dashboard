import shutil
from datetime import datetime

path = "ssl_dashboard.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

old = '''def _scan_and_store(server: Server, db: Session) -> List[dict]:
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
    return scanned'''

new = '''def _scan_and_store(server: Server, db: Session) -> List[dict]:
    """Scans one server and upserts results into the DB - shared by both
    the manual scan endpoints and the periodic background scan."""
    scanned = _scan_server(server)
    now = datetime.datetime.utcnow()
    scanned_domains = set()
    for item in scanned:
        scanned_domains.add(item["domain"])
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

    # Remove DB entries for this server that no longer exist in the
    # latest scan (e.g. nginx conf was deleted) - keeps DB in sync with
    # what's actually on the server right now.
    if scanned_domains:
        stale = (
            db.query(SslDomain)
            .filter(SslDomain.server_id == server.id, ~SslDomain.domain.in_(scanned_domains))
            .all()
        )
    else:
        stale = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()

    for row in stale:
        logger.info(f"[ssl_scan] removing stale domain {row.domain} (server {server.name}) - not found in latest scan")
        db.delete(row)

    db.commit()
    return scanned'''

count = content.count(old)
if count == 0:
    print("ERROR: expected block not found — aborting, nothing changed.")
elif count != 1:
    print(f"WARNING: expected 1 occurrence, found {count}. Aborting to be safe.")
else:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Patched successfully.")
