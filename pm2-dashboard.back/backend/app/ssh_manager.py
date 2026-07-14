"""
Handles all SSH connections to remote servers and running PM2 commands
on them via Paramiko. Connections are opened per-request/per-stream and
closed afterwards - no long-lived pooling to keep this simple and safe
across many concurrent clients/servers.
"""
import json
import os
import shlex
from typing import List, Optional, Generator

import paramiko

from app.config import get_settings
from app.models import Server

settings = get_settings()


class SSHConnectionError(Exception):
    pass


def _connect(server: Server) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = dict(
        hostname=server.ip_address,
        port=server.ssh_port or settings.SSH_DEFAULT_PORT,
        username=server.ssh_username or settings.SSH_DEFAULT_USERNAME,
        timeout=settings.SSH_CONNECT_TIMEOUT,
        banner_timeout=settings.SSH_CONNECT_TIMEOUT,
        auth_timeout=settings.SSH_CONNECT_TIMEOUT,
    )

    key_path = server.ssh_private_key_path or settings.SSH_PRIVATE_KEY_PATH
    try:
        if server.ssh_password:
            connect_kwargs["password"] = server.ssh_password
        elif key_path:
            connect_kwargs["key_filename"] = key_path
        else:
            # try default agent / keys in ~/.ssh
            pass
        client.connect(**connect_kwargs)
    except Exception as exc:  # noqa: BLE001
        raise SSHConnectionError(f"Failed to connect to {server.ip_address}: {exc}") from exc

    return client


def _wrap_login_shell(command: str) -> str:
    """Force a login shell (bash -lc) so PATH/nvm additions are sourced,
    since paramiko exec_command otherwise uses a bare non-login shell."""
    return f"bash -lc {shlex.quote(command)}"


def _pm2_bin(server) -> str:
    """Use the per-server pm2_bin_path if configured, else bare pm2."""
    path = getattr(server, "pm2_bin_path", None)
    return shlex.quote(path) if path else "pm2"


def _path_prefix(server) -> str:
    """If a per-server pm2_bin_path is configured, pm2 (a node script)
    still needs `node` resolvable on PATH to actually run - not just its
    own absolute path. Prepend that bin directory to PATH explicitly so
    it does not depend on any profile/login-shell PATH setup at all."""
    path = getattr(server, "pm2_bin_path", None)
    if not path:
        return ""
    bin_dir = os.path.dirname(path)
    return f"export PATH={shlex.quote(bin_dir)}:$PATH && "

def run_command(server: Server, command: str, timeout: int = 20) -> str:
    """Run a single command over SSH and return combined stdout output."""
    client = _connect(server)
    try:
        stdin, stdout, stderr = client.exec_command(_wrap_login_shell(command), timeout=timeout)
        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")
        if not out and err:
            raise SSHConnectionError(err.strip())
        return out
    finally:
        client.close()


def check_online(server: Server) -> bool:
    try:
        run_command(server, "echo ok", timeout=8)
        return True
    except Exception:
        return False


def list_pm2_processes(server: Server) -> List[dict]:
    """Runs `pm2 jlist` on the remote server and parses the JSON output."""
    raw = run_command(server, f"{_path_prefix(server)}{_pm2_bin(server)} jlist")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SSHConnectionError(f"Could not parse pm2 jlist output: {exc}") from exc

    processes = []
    for proc in data:
        monit = proc.get("monit", {})
        pm2_env = proc.get("pm2_env", {})
        processes.append({
            "pm_id": proc.get("pm_id"),
            "name": proc.get("name"),
            "pid": proc.get("pid"),
            "status": pm2_env.get("status", "unknown"),
            "cpu": monit.get("cpu"),
            "memory": monit.get("memory"),
            "uptime": pm2_env.get("pm_uptime"),
            "restarts": pm2_env.get("restart_time"),
            "instances": pm2_env.get("instances", 1),
            "exec_mode": pm2_env.get("exec_mode"),
        })
    return processes


def pm2_action(server: Server, process_name: str, action: str) -> str:
    """action in: restart | stop | start | delete | reload"""
    safe_name = shlex.quote(process_name)
    return run_command(server, f"{_path_prefix(server)}{_pm2_bin(server)} {action} {safe_name}")


def stream_logs(server: Server, process_name: str) -> Generator[str, None, None]:
    """
    Opens an interactive SSH channel running `pm2 logs <name> --raw`
    and yields output lines as they arrive. Caller is responsible for
    closing the generator (client.close() happens in a finally block
    once the generator is exhausted or closed).
    """
    client = _connect(server)
    safe_name = shlex.quote(process_name)
    try:
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(_wrap_login_shell(f"{_path_prefix(server)}{_pm2_bin(server)} logs {safe_name} --raw --lines 100"))

        buffer = b""
        while True:
            if channel.recv_ready():
                chunk = channel.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode(errors="ignore")
            elif channel.exit_status_ready():
                break
            else:
                # allow the caller's loop to check for disconnects / sleep briefly
                yield None  # heartbeat / no-op signal
    finally:
        try:
            channel.close()
        except Exception:
            pass
        client.close()
