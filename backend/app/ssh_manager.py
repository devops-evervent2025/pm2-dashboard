"""
Handles all SSH connections to remote servers and running PM2 commands
on them via Paramiko.
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
        client.connect(**connect_kwargs)
    except Exception as exc:
        raise SSHConnectionError(f"Failed to connect to {server.ip_address}: {exc}") from exc

    return client


def _pm2_bin(server: Server) -> str:
    return shlex.quote(server.pm2_path) if server.pm2_path else "pm2"


def _path_prefix(server: Server) -> str:
    """pm2 खुद एक Node script है (#!/usr/bin/env node), इसलिए सिर्फ pm2 का
    absolute path काफी नहीं - node भी PATH में मिलना चाहिए। अगर pm2_path सेट
    है, तो उसकी bin directory (जिसमें node भी नवम के तहत होता है) को PATH में
    prepend करते हैं, ताकि यह nvm/PATH-in-profile setup पर निर्भर न रहे।"""
    if not server.pm2_path:
        return ""
    bin_dir = os.path.dirname(server.pm2_path)
    return f"export PATH={shlex.quote(bin_dir)}:$PATH && "


class _ConnParams:
    def __init__(self, ip_address, ssh_port, ssh_username, ssh_password, ssh_private_key_path):
        self.ip_address = ip_address
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.ssh_private_key_path = ssh_private_key_path


def detect_pm2_path(ip_address, ssh_port, ssh_username, ssh_password, ssh_private_key_path):
    conn = _ConnParams(ip_address, ssh_port, ssh_username, ssh_password, ssh_private_key_path)
    client = _connect(conn)
    try:
        stdin, stdout, stderr = client.exec_command(
            "bash -lc 'command -v pm2'", timeout=settings.SSH_CONNECT_TIMEOUT
        )
        out = stdout.read().decode(errors="ignore").strip()
        return out or None
    finally:
        client.close()


def run_command(server: Server, command: str, timeout: int = 20) -> str:
    client = _connect(server)
    try:
        wrapped = f"bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
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
    safe_name = shlex.quote(process_name)
    return run_command(server, f"{_path_prefix(server)}{_pm2_bin(server)} {action} {safe_name}")


def stream_logs(server: Server, process_name: str) -> Generator[str, None, None]:
    client = _connect(server)
    try:
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.exec_command(
            f"bash -lc {shlex.quote(f'{_path_prefix(server)}{_pm2_bin(server)} logs {shlex.quote(process_name)} --raw --lines 100')}"
        )
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
                yield None
    finally:
        try:
            channel.close()
        except Exception:
            pass
        client.close()
