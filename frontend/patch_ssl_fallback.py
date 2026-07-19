path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/ssl_dashboard.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_import = "from app.ssh_manager import run_command, SSHConnectionError"
new_import = "from app.ssh_manager import run_command, run_restricted_command, SSHConnectionError"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("import updated")
else:
    print("MISSING: ssh_manager import line")

marker = "def _scan_server(server: Server) -> List[dict]:"
fallback_helper = '''def _check_cert_via_ssh(server: Server, domain: str, port: int = 443) -> Optional[datetime.datetime]:
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


''' + marker

if marker in content and "_check_cert_via_ssh" not in content:
    content = content.replace(marker, fallback_helper)
    changes.append("SSH fallback helper added")
else:
    print("MISSING or already present: _scan_server marker")

old_check_call = "        expires_at = _check_cert_live(domain)"
new_check_call = '''        expires_at = _check_cert_live(domain)
        if expires_at is None:
            # Direct check failed (likely an internal/private domain that
            # doesn't resolve from the dashboard host) - fall back to
            # checking from the target server itself over SSH.
            expires_at = _check_cert_via_ssh(server, domain)'''

if old_check_call in content:
    content = content.replace(old_check_call, new_check_call)
    changes.append("fallback call wired in")
else:
    print("MISSING: _check_cert_live call site")

if len(changes) == 3:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
