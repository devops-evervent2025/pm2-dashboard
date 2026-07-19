path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Replace _check_cert_live to distinguish "not publicly resolvable" from other failures
old_check = '''def _check_cert_live(domain: str, port: int = 443, timeout: int = 10) -> Optional[datetime.datetime]:
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
    except Exception:
        return None'''

new_check = '''_DOMAIN_NOT_PUBLIC = object()  # sentinel: domain has no public DNS record


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

if old_check in content:
    content = content.replace(old_check, new_check)
    changes.append("_check_cert_live updated with DNS-resolution distinction")
else:
    print("MISSING: _check_cert_live function")

# 2. Remove the SSH-fallback helper entirely
import re
pattern = re.compile(
    r'def _check_cert_via_ssh.*?\n\n\n(?=def _scan_server)',
    re.DOTALL,
)
if pattern.search(content):
    content = pattern.sub("", content)
    changes.append("_check_cert_via_ssh removed")
else:
    print("MISSING: _check_cert_via_ssh block (may already be removed)")

# 3. Update _scan_server to skip non-public domains entirely, no SSH fallback
old_scan_fn = '''    results = []
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
    return results'''

new_scan_fn = '''    results = []
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

if old_scan_fn in content:
    content = content.replace(old_scan_fn, new_scan_fn)
    changes.append("_scan_server updated to exclude private-DNS domains")
else:
    print("MISSING: _scan_server body")

# 4. Remove the now-unused ssh fallback import
old_import = "from app.ssh_manager import run_command, run_restricted_command, SSHConnectionError"
new_import = "from app.ssh_manager import run_command, SSHConnectionError"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("unused import cleaned up")
else:
    print("MISSING: ssh_manager import line (may already be clean)")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
