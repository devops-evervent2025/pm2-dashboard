path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Replace _check_cert_live (and remove _check_cert_via_ssh entirely)
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
    out = (result.get("stdout") or "").strip()'''

new_check = '''_DOMAIN_NOT_PUBLIC = object()  # sentinel: domain has no public DNS record


def _check_cert_live(domain: str, port: int = 443, timeout: int = 10):
    """
    Connects directly to domain:port over TLS (the same way a browser would)
    and reads the certificate that is ACTUALLY being served right now.
    Never uses SSH - only ever checks over the public internet, the same
    way an external user/browser would see the site.

    Returns a tuple (expires_at, error_reason):
      - (datetime, None) on success - real cert read, whether expired or not.
      - (None, "not_public") if the domain has no public DNS record at all
        (internal/private-only) - excluded from tracking entirely.
      - (None, <reason string>) for any other failure meaning the site
        itself is unreachable (DNS failure, connection refused, timeout,
        TLS handshake error) - NOT a certificate problem, so this must
        never be shown as an "SSL expiring" alert. Surfaced separately
        as "unreachable" instead.
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
        return None, f"error: {exc}"


def _unused_ssh_fallback_removed(server, domain, port=443):
    out = ""'''

if old_check in content:
    content = content.replace(old_check, new_check)
    changes.append("_check_cert_live rewritten, SSH fallback removed")
else:
    print("MISSING: old _check_cert_live/_check_cert_via_ssh block")

# 2. Remove the rest of the old _check_cert_via_ssh body (everything up to the next "def _scan_server")
import re
pattern = re.compile(
    r'def _unused_ssh_fallback_removed\(server, domain, port=443\):\n    out = ""\n.*?\n\n\n(?=def _scan_server)',
    re.DOTALL,
)
if pattern.search(content):
    content = pattern.sub("", content)
    changes.append("leftover SSH-fallback body removed")
else:
    print("MISSING: leftover ssh fallback tail (may already be clean)")

# 3. Update _scan_server call site
old_scan_fn = '''        seen_domains.add(domain)
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

new_scan_fn = '''        seen_domains.add(domain)
        # Always check the certificate as it's actually served live over
        # public HTTPS - never via SSH. Domains with no public DNS record
        # are excluded entirely; other failures are recorded separately.
        expires_at, error_reason = _check_cert_live(domain)
        if error_reason == "not_public":
            continue
        results.append({
            "domain": domain,
            "cert_path": cert_path.strip(),
            "expires_at": expires_at,
            "check_error": error_reason,
        })
    return results'''

if old_scan_fn in content:
    content = content.replace(old_scan_fn, new_scan_fn)
    changes.append("_scan_server updated")
else:
    print("MISSING: _scan_server body")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
