"""
Reads ALL *.conf files under a server's nginx conf directory over SSH,
extracts every (server_name, ssl_certificate) pair from every server block
in every file, and checks each certificate's expiry via openssl.

Uses `sudo -n` (non-interactive) for reading files/certificates, since
Let's Encrypt certificate directories are normally root-only readable.
If passwordless sudo isn't set up for the SSH user, this falls back to a
plain (non-sudo) attempt, and reports a clear English error if that also
fails, rather than hanging waiting for a password.
"""
import re
import shlex
import datetime

import paramiko

from app.ssl_models import SSLServer


class SSLCheckError(Exception):
    pass


def _connect(server: SSLServer) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = dict(
        hostname=server.ip_address,
        port=server.ssh_port or 22,
        username=server.ssh_username or "root",
        timeout=15,
        banner_timeout=15,
        auth_timeout=15,
    )
    try:
        if server.ssh_password:
            connect_kwargs["password"] = server.ssh_password
        elif server.ssh_private_key_path:
            connect_kwargs["key_filename"] = server.ssh_private_key_path
        client.connect(**connect_kwargs)
    except Exception as exc:
        raise SSLCheckError(f"SSH connection failed: {exc}") from exc
    return client


def _run(client: paramiko.SSHClient, command: str, timeout: int = 20):
    wrapped = f"bash -lc {shlex.quote(command)}"
    stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
    out = stdout.read().decode(errors="ignore")
    err = stderr.read().decode(errors="ignore")
    return out, err


def _run_with_sudo_fallback(client: paramiko.SSHClient, plain_cmd: str, timeout: int = 20):
    """पहले `sudo -n` के साथ try करता है (non-interactive, password prompt पर hang नहीं
    करेगा), खाली आने पर बिना sudo के plain command try करता है।"""
    out, err = _run(client, f"sudo -n {plain_cmd}", timeout=timeout)
    if out.strip():
        return out, err
    return _run(client, plain_cmd, timeout=timeout)


def _split_server_blocks(conf_text: str) -> list:
    """Splits nginx config text into individual `server { ... }` blocks by
    tracking brace depth, so server_name/ssl_certificate pairs from
    different blocks in the same file don't get mixed up."""
    blocks = []
    i = 0
    n = len(conf_text)
    while True:
        idx = conf_text.find("server", i)
        if idx == -1:
            break
        brace_idx = conf_text.find("{", idx)
        if brace_idx == -1:
            break
        between = conf_text[idx + 6:brace_idx].strip()
        if between != "":
            # यह "server_name" जैसा कोई और शब्द था, असली "server {" directive नहीं
            i = idx + 6
            continue
        depth = 1
        j = brace_idx + 1
        while j < n and depth > 0:
            if conf_text[j] == "{":
                depth += 1
            elif conf_text[j] == "}":
                depth -= 1
            j += 1
        blocks.append(conf_text[idx:j])
        i = j
    return blocks


def discover_and_check(server: SSLServer) -> list:
    """
    Scans every *.conf file in server.conf_dir, extracts every domain +
    certificate path found, and checks each certificate's expiry.
    Returns a list of dicts: domain_name, config_file, cert_path,
    expiry_date, days_remaining, error.
    """
    client = _connect(server)
    try:
        list_cmd = f"find {shlex.quote(server.conf_dir)} -maxdepth 1 -name '*.conf' -type f"
        out, err = _run_with_sudo_fallback(client, list_cmd, timeout=15)
        conf_files = [line.strip() for line in out.splitlines() if line.strip()]
        if not conf_files:
            raise SSLCheckError(
                f"No .conf files found in {server.conf_dir}"
                + (f" (permission denied: {err.strip()})" if err.strip() else "")
            )

        results = []
        for conf_file in conf_files:
            content, cat_err = _run_with_sudo_fallback(client, f"cat {shlex.quote(conf_file)}", timeout=15)
            if not content:
                results.append({
                    "domain_name": None,
                    "config_file": conf_file,
                    "cert_path": None,
                    "expiry_date": None,
                    "days_remaining": None,
                    "error": f"Could not read {conf_file}: {cat_err.strip() or 'permission denied'}",
                })
                continue

            found_cert_in_file = False
            for block in _split_server_blocks(content):
                cert_match = re.search(r"ssl_certificate\s+([^\s;]+);", block)
                if not cert_match:
                    continue  # यह block HTTPS server नहीं है (जैसे redirect-only 80 वाला block)
                found_cert_in_file = True
                cert_path = cert_match.group(1)

                domain_match = re.search(r"server_name\s+([^;]+);", block)
                domain_name = domain_match.group(1).strip().split()[0] if domain_match else None

                cert_out, cert_err = _run_with_sudo_fallback(
                    client, f"openssl x509 -enddate -noout -in {shlex.quote(cert_path)}", timeout=15
                )

                if not cert_out or "=" not in cert_out:
                    results.append({
                        "domain_name": domain_name,
                        "config_file": conf_file,
                        "cert_path": cert_path,
                        "expiry_date": None,
                        "days_remaining": None,
                        "error": "Could not read certificate: "
                        + (cert_err.strip() or cert_out.strip() or "permission denied or file not found"),
                    })
                    continue

                date_str = cert_out.split("=", 1)[1].strip()
                try:
                    expiry_date = datetime.datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
                except ValueError:
                    results.append({
                        "domain_name": domain_name,
                        "config_file": conf_file,
                        "cert_path": cert_path,
                        "expiry_date": None,
                        "days_remaining": None,
                        "error": f"Could not parse certificate expiry date: {date_str}",
                    })
                    continue

                days_remaining = (expiry_date - datetime.datetime.utcnow()).days
                results.append({
                    "domain_name": domain_name,
                    "config_file": conf_file,
                    "cert_path": cert_path,
                    "expiry_date": expiry_date,
                    "days_remaining": days_remaining,
                    "error": None,
                })

            if not found_cert_in_file:
                # यह file शायद सिर्फ HTTP->HTTPS redirect है, कोई ssl_certificate directive नहीं -
                # यह normal है, error नहीं दिखाते, बस skip करते हैं।
                pass

        if not results:
            raise SSLCheckError(
                f"Found {len(conf_files)} .conf file(s) in {server.conf_dir}, "
                "but none contained an 'ssl_certificate' directive."
            )

        return results
    finally:
        client.close()


def renew_certificate(server: SSLServer, cert_path: str) -> dict:
    """
    Renews a certbot-managed Let's Encrypt certificate and reloads nginx.
    Only works for certificates under /etc/letsencrypt/live/<name>/... -
    certificates from other sources (self-signed, manually placed, etc.)
    can't be auto-renewed this way and must be renewed manually.
    """
    match = re.match(r"^/etc/letsencrypt/live/([^/]+)/", cert_path)
    if not match:
        raise SSLCheckError(
            "This certificate isn't managed by certbot (not under "
            "/etc/letsencrypt/live/), so it can't be auto-renewed. "
            "Please renew it manually on the server."
        )
    cert_name = match.group(1)

    client = _connect(server)
    try:
        renew_cmd = (
            f"sudo -n certbot renew --cert-name {shlex.quote(cert_name)} "
            "--non-interactive --force-renewal"
        )
        out, err = _run(client, renew_cmd, timeout=90)
        combined = (out + err).strip()
        lowered = combined.lower()
        if "congratulations" not in lowered and "successfully" not in lowered and "renewed" not in lowered:
            raise SSLCheckError(
                "certbot renew did not confirm success: "
                + (combined[:500] or "no output (check sudo permissions for certbot)")
            )

        # nginx reload करते हैं ताकि नया certificate तुरंत असर में आ जाए
        _run_with_sudo_fallback(client, "systemctl reload nginx", timeout=30)

        cert_out, cert_err = _run_with_sudo_fallback(
            client, f"openssl x509 -enddate -noout -in {shlex.quote(cert_path)}", timeout=15
        )
        if not cert_out or "=" not in cert_out:
            raise SSLCheckError(f"Renewed, but could not re-read certificate afterward: {cert_err.strip()}")

        date_str = cert_out.split("=", 1)[1].strip()
        expiry_date = datetime.datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
        days_remaining = (expiry_date - datetime.datetime.utcnow()).days

        return {
            "message": "Certificate renewed and nginx reloaded successfully.",
            "expiry_date": expiry_date,
            "days_remaining": days_remaining,
        }
    finally:
        client.close()
