"""
Self-contained SSL certificate dashboard. Everything for this feature -
the DB model, request/response schemas, SSH scanning logic, and the
endpoints - lives in this single file. The only outside touch needed is
one import + one include_router line in main.py.
"""
import datetime
import socket
import ssl as ssl_lib
import threading
import time
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.auth import get_current_user, require_admin
from app.models import User, Server, Client
from app.ssh_manager import run_command, run_restricted_command, SSHConnectionError

router = APIRouter(prefix="/ssl", tags=["ssl"])


class SslDomain(Base):
    __tablename__ = "ssl_domains_v2"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    domain = Column(String(255), nullable=False)
    cert_path = Column(String(500), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SslDomainOut(BaseModel):
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
        from_attributes = True


class SslDomainCreate(BaseModel):
    server_id: int
    domain: str
    cert_path: Optional[str] = None


class ServerOption(BaseModel):
    id: int
    name: str
    client_id: Optional[int] = None
    client_name: Optional[str] = None


class SslScanResponse(BaseModel):
    server_id: int
    server_name: str
    domains_found: int
    domains: List[SslDomainOut]


_SCAN_SCRIPT = r"""
for f in $(find /etc/nginx/sites-enabled /etc/nginx/conf.d -maxdepth 1 -type f 2>/dev/null); do
  domain=$(grep -oP '(?<=server_name\s)[^;]+' "$f" 2>/dev/null | head -1 | awk '{print $1}')
  cert=$(grep -oP '(?<=ssl_certificate\s)[^;]+' "$f" 2>/dev/null | head -1)
  if [ -n "$cert" ] && [ -n "$domain" ] && [ "$domain" != "_" ]; then
    echo "${domain}|$cert"
  fi
done
""".strip()


def _parse_openssl_date(raw: str) -> Optional[datetime.datetime]:
    raw = raw.strip()
    if not raw:
        return None
    if raw.endswith(" GMT"):
        raw = raw[:-4]
    try:
        return datetime.datetime.strptime(raw, "%b %d %H:%M:%S %Y")
    except ValueError:
        return None


def _check_cert_live(domain: str, port: int = 443, timeout: int = 10) -> Optional[datetime.datetime]:
    """
    Connects directly to domain:port over TLS (the same way a browser would)
    and reads the certificate that is ACTUALLY being served right now -
    not whatever file happens to be referenced in an nginx conf, which can
    be stale, wrong, or unreadable over SSH. Returns the cert's expiry
    datetime, or None if the connection/handshake fails for any reason.
    """
    try:
        ctx = ssl_lib.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl_lib.CERT_NONE
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as tls_sock:
                cert = tls_sock.getpeercert()
        if not cert or "notAfter" not in cert:
            return None
        return datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    except Exception as exc:
        print(f"[ssl_check] {domain}:{port} failed: {type(exc).__name__}: {exc}")
        return None


def _check_cert_via_ssh(server: Server, domain: str, port: int = 443) -> Optional[datetime.datetime]:
    """
    Fallback for internal/private domains that don't resolve from the
    dashboard host's network - runs the TLS check FROM the target server
    itself over SSH (which is on that private network), using openssl
    s_client instead of reading a cert file (avoids file-permission
    issues and reflects what's actually being served).
    """
    cmd = (
        f"echo | openssl s_client -connect {domain}:{port} "
        f"-servername {domain} 2>/dev/null | openssl x509 -enddate -noout 2>/dev/null"
    )
    try:
        result = run_restricted_command(server, cmd, timeout=15)
    except Exception as exc:
        print(f"[ssl_check] SSH fallback for {domain} failed: {type(exc).__name__}: {exc}")
        return None
    out = (result.get("stdout") or "").strip()
    if not out or "=" not in out:
        return None
    date_str = out.split("=", 1)[1].strip()
    try:
        return datetime.datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
    except ValueError:
        return None


logger = logging.getLogger("ssl_dashboard")

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


# Shared state for a full scan-all pass, whether triggered manually or by
# the periodic loop. Lives in memory (not the DB) since it only needs to
# survive within this backend process; a restart naturally resets it,
# which is fine since any in-progress scan is gone anyway on restart.
_scan_lock = threading.Lock()
_scan_state = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "servers_total": 0,
    "servers_done": 0,
    "current_server": None,
    "error": None,
}


def _do_full_scan():
    """Runs a full scan-all pass across every eligible server. Safe to call
    from a request-triggered background thread OR the periodic loop -
    _scan_lock ensures only one of these ever runs at a time, so a manual
    "Refresh all" and the periodic 2-hour scan can never collide and
    double-write the same rows."""
    from app.database import SessionLocal

    if not _scan_lock.acquire(blocking=False):
        logger.info("[ssl_scan] scan requested but one is already running - skipping")
        return

    db = SessionLocal()
    try:
        servers = db.query(Server).all()
        eligible = [s for s in servers if _server_has_nginx(s)]
        _scan_state.update({
            "running": True,
            "started_at": datetime.datetime.utcnow().isoformat(),
            "finished_at": None,
            "servers_total": len(eligible),
            "servers_done": 0,
            "current_server": None,
            "error": None,
        })
        for server in eligible:
            _scan_state["current_server"] = server.name
            try:
                _scan_and_store(server, db)
            except Exception as exc:
                logger.warning(f"[ssl_scan] scan of {server.name} failed: {exc}")
            _scan_state["servers_done"] += 1
        _scan_state["current_server"] = None
    except Exception as exc:
        _scan_state["error"] = str(exc)
        logger.exception("[ssl_scan] full scan crashed")
    finally:
        db.close()
        _scan_state["running"] = False
        _scan_state["finished_at"] = datetime.datetime.utcnow().isoformat()
        _scan_lock.release()


def _run_periodic_ssl_scan():
    """Background loop: re-scans every server with an nginx conf dir on
    an admin-configurable interval (default 2 hours), so certificate
    data stays fresh without every page load or manual click needing to
    wait on SSH to the whole fleet. Interval is re-read from the DB at
    the start of every cycle, so a saved change in Alert Settings takes
    effect on the next cycle without a restart."""
    from app.database import SessionLocal
    from app.alert_settings_models import get_interval_minutes

    while True:
        db = SessionLocal()
        try:
            interval_minutes = get_interval_minutes(db, "ssl_scan")
        finally:
            db.close()
        time.sleep(max(60, interval_minutes * 60))
        logger.info("[ssl_scan] periodic scan starting")
        _do_full_scan()
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
    return scanned


def _scan_server(server: Server) -> List[dict]:
    try:
        output = run_command(server, _SCAN_SCRIPT, timeout=30)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results = []
    seen_domains = set()
    for line in output.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        domain, cert_path = parts
        domain = domain.strip()
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        # Check the certificate as it's actually served live over HTTPS,
        # not by reading the file over SSH (avoids permission issues and
        # stale/mismatched cert files).
        expires_at = _check_cert_live(domain)
        if expires_at is None:
            # Direct check failed (likely an internal/private domain that
            # doesn't resolve from the dashboard host) - fall back to
            # checking from the target server itself over SSH.
            expires_at = _check_cert_via_ssh(server, domain)
        results.append({
            "domain": domain,
            "cert_path": cert_path.strip(),
            "expires_at": expires_at,
        })
    return results


def _to_out(row: SslDomain, server_name: Optional[str], client_id: Optional[int] = None, client_name: Optional[str] = None) -> SslDomainOut:
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
    )


def _get_server_or_404(server_id: int, db: Session) -> Server:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.get("/domains", response_model=List[SslDomainOut])
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
    return out


@router.get("/servers", response_model=List[ServerOption])
def list_servers_for_domain_add(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Lightweight server picklist (id/name/client) used by the "Add
    domain" modal on the frontend so an admin can pick which server a
    manually-added domain belongs to."""
    servers = db.query(Server).all()
    clients = {c.id: c.name for c in db.query(Client).all()}
    return [
        ServerOption(
            id=s.id,
            name=s.name,
            client_id=s.client_id,
            client_name=clients.get(s.client_id) if s.client_id else None,
        )
        for s in servers
    ]


@router.post("/domains", response_model=SslDomainOut, status_code=201)
def create_domain(payload: SslDomainCreate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Manually add a domain to track for a given server. Runs the same
    live TLS check (with SSH fallback) used by scanning, so a manually
    added domain immediately shows real expiry data instead of blanks."""
    server = _get_server_or_404(payload.server_id, db)
    domain = payload.domain.strip().lower()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain cannot be empty")

    existing = (
        db.query(SslDomain)
        .filter(SslDomain.server_id == server.id, SslDomain.domain == domain)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This domain is already tracked for this server")

    expires_at = _check_cert_live(domain)
    if expires_at is None:
        expires_at = _check_cert_via_ssh(server, domain)

    row = SslDomain(
        server_id=server.id,
        domain=domain,
        cert_path=(payload.cert_path or None),
        expires_at=expires_at,
        last_scanned_at=datetime.datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    client_name = None
    if server.client_id:
        client = db.query(Client).filter(Client.id == server.client_id).first()
        client_name = client.name if client else None

    return _to_out(row, server.name, server.client_id, client_name)


@router.post("/scan/{server_id}", response_model=SslScanResponse)
def scan_server(server_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    server = _get_server_or_404(server_id, db)
    if not _server_has_nginx(server):
        raise HTTPException(status_code=400, detail="This server has no nginx conf directory - nothing to scan.")
    scanned = _scan_and_store(server, db)

    rows = db.query(SslDomain).filter(SslDomain.server_id == server.id).all()
    return SslScanResponse(
        server_id=server.id, server_name=server.name, domains_found=len(scanned),
        domains=[_to_out(r, server.name) for r in rows],
    )


class ScanStartResponse(BaseModel):
    started: bool
    already_running: bool


class ScanStatusResponse(BaseModel):
    running: bool
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    servers_total: int
    servers_done: int
    current_server: Optional[str] = None
    error: Optional[str] = None


@router.post("/scan-all", response_model=ScanStartResponse)
def scan_all_servers(_admin: User = Depends(require_admin)):
    """Starts a full scan-all pass in the background and returns
    immediately - the scan itself keeps running on the server even if the
    browser disconnects, refreshes, or closes. Poll /ssl/scan-status to
    track progress from any browser tab, at any time."""
    if _scan_state["running"]:
        return ScanStartResponse(started=False, already_running=True)
    thread = threading.Thread(target=_do_full_scan, daemon=True)
    thread.start()
    return ScanStartResponse(started=True, already_running=False)


@router.get("/scan-status", response_model=ScanStatusResponse)
def scan_status(_user: User = Depends(get_current_user)):
    return ScanStatusResponse(**_scan_state)


@router.delete("/domains/{domain_id}")
def delete_domain(domain_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    row = db.query(SslDomain).filter(SslDomain.id == domain_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Domain entry not found")
    db.delete(row)
    db.commit()
    return {"detail": "Domain entry deleted"}
