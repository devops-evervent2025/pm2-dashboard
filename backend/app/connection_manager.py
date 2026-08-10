# backend/app/connection_manager.py
#
# Wraps ssh_manager.py's ACTUAL functions - check_online(server) and
# run_restricted_command(server, command) -> {"stdout", "stderr", "exit_status"} -
# without modifying ssh_manager.py itself (requirement #6).

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Server
from app import infralink_models as models
from app import ssh_manager

settings = get_settings()


class ConnectionKind(str, Enum):
    SSH = "ssh"
    INFRALINK = "infralink"


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    exit_code: int
    via: ConnectionKind


class SSHProvider:
    """Thin wrapper around the existing, unmodified ssh_manager module."""

    def is_available(self, server_id: int, db: Session) -> bool:
        server = db.query(Server).get(server_id)
        if not server:
            return False
        return ssh_manager.check_online(server)

    def run_command(self, server_id: int, command: str, db: Session) -> CommandResult:
        server = db.query(Server).get(server_id)
        if not server:
            raise RuntimeError(f"No server found with id={server_id}")
        result = ssh_manager.run_restricted_command(server, command)
        return CommandResult(
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            exit_code=result.get("exit_status", 1),
            via=ConnectionKind.SSH,
        )


class InfraLinkProvider:
    """
    Phase 1: registration/auth/heartbeat only (requirement #10's "Phase 1
    only" scope) - run_command over InfraLink is intentionally not
    implemented until a later phase adds the command-execution channel.
    is_available() reflects whether an agent is registered AND online.
    """

    def is_available(self, server_id: int, db: Session) -> bool:
        agent = (
            db.query(models.InfraLinkAgent)
            .filter(models.InfraLinkAgent.server_id == server_id)
            .first()
        )
        return bool(agent and not agent.is_stale())

    def run_command(self, server_id: int, command: str, db: Session) -> CommandResult:
        raise NotImplementedError(
            "InfraLink command execution is a later phase; Phase 1 is "
            "registration + auth + heartbeat only."
        )


class ConnectionManager:
    """
    Requirement #6/#7: one interface over SSH and InfraLink, with InfraLink
    as primary and SSH as fallback when both are configured for a server.
    Phase 1 caveat: since InfraLinkProvider.run_command isn't implemented
    yet, command execution always falls back to SSH today - this class is
    future-proofed for when a later phase adds Agent command execution.
    """

    def __init__(self):
        self.ssh = SSHProvider()
        self.infralink = InfraLinkProvider()

    def _agent_enabled(self) -> bool:
        return get_settings().AGENT_ENABLED

    def preferred_kind(self, server_id: int, db: Session) -> Optional[ConnectionKind]:
        if self._agent_enabled() and self.infralink.is_available(server_id, db):
            return ConnectionKind.INFRALINK
        if self.ssh.is_available(server_id, db):
            return ConnectionKind.SSH
        return None

    def run_command(self, server_id: int, command: str, db: Session) -> CommandResult:
        if self._agent_enabled() and self.infralink.is_available(server_id, db):
            try:
                return self.infralink.run_command(server_id, command, db)
            except NotImplementedError:
                pass  # Phase 1: fall through to SSH
            except Exception:
                pass  # Agent primary failed at runtime -> fall back to SSH (requirement #7)

        if self.ssh.is_available(server_id, db):
            return self.ssh.run_command(server_id, command, db)

        raise RuntimeError(f"No available connection (SSH or InfraLink) for server_id={server_id}")


connection_manager = ConnectionManager()
