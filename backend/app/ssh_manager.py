"""
Handles all SSH connections to remote servers and running PM2 commands
on them via Paramiko.
"""
import json
import socket
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


def run_restricted_command(server: Server, command: str, timeout: int = 30) -> dict:
    """
    Like run_command, but returns stdout/stderr/exit_status separately
    instead of raising on stderr output - used by the restricted curl-only
    terminal feature. The caller is responsible for validating `command`
    before calling this.
    """
    client = _connect(server)
    try:
        wrapped = f"bash -lc {shlex.quote(command)}"
        stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout)
        try:
            out = stdout.read().decode(errors="ignore")
            err = stderr.read().decode(errors="ignore")
            exit_status = stdout.channel.recv_exit_status()
        except (socket.timeout, paramiko.buffered_pipe.PipeTimeout):
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s (remote host slow or unreachable).",
                "exit_status": -1,
            }
        return {"stdout": out, "stderr": err, "exit_status": exit_status}
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
            "cwd": pm2_env.get("pm_cwd") or pm2_env.get("cwd"),
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


# ---------------- Docker containers (mirrors the PM2 process functions above) ----------------

def list_docker_containers(server: Server) -> List[dict]:
    """Lists ALL containers (running + stopped) via `docker ps -a`, one
    JSON object per line (--format), so partial output never breaks
    parsing of the rest."""
    raw = run_command(
        server,
        "docker ps -a --format "
        "'{{json .}}'",
    )
    containers = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        containers.append({
            "id": data.get("ID"),
            "name": data.get("Names"),
            "image": data.get("Image"),
            "status": data.get("Status", ""),
            "state": data.get("State", "unknown"),
            "ports": data.get("Ports", ""),
            "created": data.get("CreatedAt", ""),
        })
    return containers


def docker_action(server: Server, container_name: str, action: str) -> str:
    safe_name = shlex.quote(container_name)
    return run_command(server, f"docker {action} {safe_name}")


def stream_docker_logs(server: Server, container_name: str) -> Generator[str, None, None]:
    client = _connect(server)
    try:
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        safe_name = shlex.quote(container_name)
        channel.exec_command(
            f"bash -lc {shlex.quote(f'docker logs -f --tail 100 {safe_name}')}"
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
        client.close()


# ---------------- Build Manager ----------------

def stream_build(server: Server, full_path: str, branch_name: str) -> Generator[str, None, None]:
    """Streams live output of, on the remote server:
        cd <full_path> && git fetch origin &&
        (git checkout <branch_name> || git checkout -b <branch_name> origin/<branch_name>) &&
        git pull origin <branch_name> && npm i -f && npm run build

    branch_name is NOT detected from whatever the folder currently has
    checked out - it's the folder's own name under base_path (e.g.
    ".../frontend/Development" -> branch "Development", ".../backend/Uat"
    -> branch "Uat"). A bare `git pull` fails outright if the folder is
    in detached HEAD or has no upstream tracking set, which is exactly
    the failure this was hitting. Explicitly fetching, checking out (or
    creating a local tracking branch if it doesn't exist locally yet),
    then pulling that named branch avoids that failure mode. If the
    branch genuinely doesn't exist on the remote, that error surfaces
    clearly in the streamed output instead of silently building whatever
    was already checked out.
    """
    client = _connect(server)
    try:
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        branch_q = shlex.quote(branch_name)
        script = (
            f"cd {shlex.quote(full_path)} && "
            f"{_path_prefix(server)}"
            f"echo '--- expected branch (from folder): {branch_name} ---' && "
            f"git fetch origin && "
            f"(git checkout {branch_q} || git checkout -b {branch_q} origin/{branch_q}) && "
            f"echo '--- discarding any local changes, hard-syncing to origin/{branch_name} ---' && "
            f"git reset --hard origin/{branch_q} && "
            f"git clean -fd && "
            f"npm i -f && "
            f"npm run build"
        )
        channel.exec_command(f"bash -lc {shlex.quote(script)}")
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
                if buffer:
                    yield buffer.decode(errors="ignore")
                    buffer = b""
                exit_status = channel.recv_exit_status()
                yield f"__EXIT__:{exit_status}"
                break
            else:
                yield None
    finally:
        try:
            channel.close()
        except Exception:
            pass
        client.close()
