path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add ssl + socket imports
old_imports = "import datetime\nfrom typing import List, Optional"
new_imports = "import datetime\nimport socket\nimport ssl as ssl_lib\nfrom typing import List, Optional"
if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("imports added")
else:
    print("MISSING: import block")

# 2. Simplify the scan script to only extract domain names (not cert dates)
old_script = '''_SCAN_SCRIPT = r"""
for f in $(find /etc/nginx/sites-enabled /etc/nginx/conf.d -maxdepth 1 -type f 2>/dev/null); do
  domain=$(grep -oP '(?<=server_name\\s)[^;]+' "$f" 2>/dev/null | head -1 | awk '{print $1}')
  cert=$(grep -oP '(?<=ssl_certificate\\s)[^;]+' "$f" 2>/dev/null | head -1)
  if [ -n "$cert" ] && [ -f "$cert" ]; then
    expiry=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2)
    echo "${domain:-unknown}|$cert|$expiry"
  fi
done
""".strip()'''

new_script = '''_SCAN_SCRIPT = r"""
for f in $(find /etc/nginx/sites-enabled /etc/nginx/conf.d -maxdepth 1 -type f 2>/dev/null); do
  domain=$(grep -oP '(?<=server_name\\s)[^;]+' "$f" 2>/dev/null | head -1 | awk '{print $1}')
  cert=$(grep -oP '(?<=ssl_certificate\\s)[^;]+' "$f" 2>/dev/null | head -1)
  if [ -n "$cert" ] && [ -n "$domain" ] && [ "$domain" != "_" ]; then
    echo "${domain}|$cert"
  fi
done
""".strip()'''

if old_script in content:
    content = content.replace(old_script, new_script)
    changes.append("scan script simplified")
else:
    print("MISSING: _SCAN_SCRIPT block")

# 3. Add a direct-TLS-check helper function right before _scan_server
marker = "def _scan_server(server: Server) -> List[dict]:"
helper = '''def _check_cert_live(domain: str, port: int = 443, timeout: int = 10) -> Optional[datetime.datetime]:
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
        return None


''' + marker

if marker in content and "_check_cert_live" not in content:
    content = content.replace(marker, helper)
    changes.append("direct-check helper added")
else:
    print("MISSING or already present: _scan_server marker")

# 4. Rewrite _scan_server to use the direct check instead of parsing expiry from SSH output
old_scan_fn = '''def _scan_server(server: Server) -> List[dict]:
    try:
        output = run_command(server, _SCAN_SCRIPT, timeout=30)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    results = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        domain, cert_path, expiry_raw = parts
        results.append({
            "domain": domain,
            "cert_path": cert_path,
            "expires_at": _parse_openssl_date(expiry_raw),
        })
    return results'''

new_scan_fn = '''def _scan_server(server: Server) -> List[dict]:
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
        results.append({
            "domain": domain,
            "cert_path": cert_path.strip(),
            "expires_at": expires_at,
        })
    return results'''

if old_scan_fn in content:
    content = content.replace(old_scan_fn, new_scan_fn)
    changes.append("_scan_server rewritten to use direct check")
else:
    print("MISSING: _scan_server function body")

if len(changes) == 4:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
