path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add check_error column to model
old_model = '''    expires_at = Column(DateTime, nullable=True)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)'''
new_model = '''    expires_at = Column(DateTime, nullable=True)
    check_error = Column(String(255), nullable=True)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)'''
if old_model in content:
    content = content.replace(old_model, new_model)
    changes.append("model column added")
else:
    print("MISSING: SslDomain model fields")

# 2. Add check_error to output schema
old_schema = '''    expires_at: Optional[datetime.datetime] = None
    days_remaining: Optional[int] = None
    last_scanned_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True'''
new_schema = '''    expires_at: Optional[datetime.datetime] = None
    days_remaining: Optional[int] = None
    check_error: Optional[str] = None
    last_scanned_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True'''
if old_schema in content:
    content = content.replace(old_schema, new_schema)
    changes.append("schema updated")
else:
    print("MISSING: SslDomainOut schema")

# 3. Rewrite _check_cert_live to return (expiry_or_None, error_reason_or_None)
old_check = '''_DOMAIN_NOT_PUBLIC = object()  # sentinel: domain has no public DNS record


def _check_cert_live(domain: str, port: int = 443, timeout: int = 10):
    """
    Connects directly to domain:port over TLS (the same way a browser would)
    and reads the certificate that is ACTUALLY being served right now.

    Returns:
      - a datetime (cert expiry) on success
      - _DOMAIN_NOT_PUBLIC if the domain has no public DNS record at all
        (i.e. it only resolves on a private/internal network) - these
        domains are excluded from tracking entirely, per design: this
        dashboard only tracks certificates reachable over the public
        internet, the same way an external user/browser would see them.
      - None for any other failure (connection refused, timeout, TLS
        handshake error, etc.) - domain is still tracked, just shows as
        "could not verify" rather than a certificate expiry.
    """
    try:
        socket.getaddrinfo(domain, port)
    except socket.gaierror:
        return _DOMAIN_NOT_PUBLIC

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
    except Exception:
        return None'''

new_check = '''_DOMAIN_NOT_PUBLIC = object()  # sentinel: domain has no public DNS record


def _check_cert_live(domain: str, port: int = 443, timeout: int = 10):
    """
    Connects directly to domain:port over TLS (the same way a browser would)
    and reads the certificate that is ACTUALLY being served right now.

    Returns a tuple (expires_at, error_reason):
      - (datetime, None) on success - a real certificate was read, whether
        it's expired or not. This is the only case treated as a genuine
        "SSL expiration" concern - the domain is reachable and serving a
        cert, even if that cert happens to be expired.
      - (None, "not_public") if the domain has no public DNS record at all
        (internal/private-only network) - excluded from tracking entirely.
      - (None, <reason string>) for anything else that means the site
        itself is unreachable (DNS failure, connection refused, timeout,
        TLS handshake error) - these are NOT certificate problems, they're
        the site being down, so they must never be shown as an "SSL
        expiring" alert. They get surfaced separately as "unreachable".
    """
    try:
        socket.getaddrinfo(domain, port)
    except socket.gaierror:
        return None, "not_public"

    try:
        ctx = ssl_lib.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl_lib.CERT_NONE
        with socket.create_connection((domain, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as tls_sock:
                cert = tls_sock.getpeercert()
        if not cert or "notAfter" not in cert:
            return None, "no_certificate_returned"
        expiry = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        return expiry, None
    except socket.timeout:
        return None, "timeout"
    except ConnectionRefusedError:
        return None, "connection_refused"
    except ssl_lib.SSLError as exc:
        return None, f"tls_error: {exc}"
    except OSError as exc:
        return None, f"connection_error: {exc}"
    except Exception as exc:
        return None, f"error: {exc}"'''

if old_check in content:
    content = content.replace(old_check, new_check)
    changes.append("_check_cert_live rewritten to return (expiry, error)")
else:
    print("MISSING: _check_cert_live function")

# 4. Update _scan_server to store check_error and skip only truly-private domains
old_scan_fn = '''        seen_domains.add(domain)
        # Always check the certificate as it's actually served live over
        # public HTTPS - never via SSH. Domains with no public DNS record
        # (internal/private-only) are excluded entirely below.
        check_result = _check_cert_live(domain)
        if check_result is _DOMAIN_NOT_PUBLIC:
            continue  # not publicly resolvable - leave it out entirely
        results.append({
            "domain": domain,
            "cert_path": cert_path.strip(),
            "expires_at": check_result,
        })
    return results'''

new_scan_fn = '''        seen_domains.add(domain)
        # Always check the certificate as it's actually served live over
        # public HTTPS - never via SSH. Domains with no public DNS record
        # (internal/private-only) are excluded entirely below.
        expires_at, error_reason = _check_cert_live(domain)
        if error_reason == "not_public":
            continue  # not publicly resolvable - leave it out entirely
        results.append({
            "domain": domain,
            "cert_path": cert_path.strip(),
            "expires_at": expires_at,
            "check_error": error_reason,
        })
    return results'''

if old_scan_fn in content:
    content = content.replace(old_scan_fn, new_scan_fn)
    changes.append("_scan_server updated to capture check_error")
else:
    print("MISSING: _scan_server body")

# 5. Update _to_out to pass through check_error
old_to_out = '''def _to_out(row: SslDomain, server_name: Optional[str], client_id: Optional[int] = None, client_name: Optional[str] = None) -> SslDomainOut:
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
        check_error=row.check_error,
        last_scanned_at=row.last_scanned_at,
    )'''

if old_to_out in content:
    content = content.replace(old_to_out, new_to_out)
    changes.append("_to_out updated")
else:
    print("MISSING: _to_out function")

# 6. Update _scan_and_store to persist check_error on upsert
old_store = '''        if existing:
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

new_store = '''        if existing:
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
    return scanned'''

if old_store in content:
    content = content.replace(old_store, new_store)
    changes.append("_scan_and_store updated to persist check_error")
else:
    print("MISSING: _scan_and_store upsert block")

if len(changes) == 6:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
