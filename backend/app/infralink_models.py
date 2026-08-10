# backend/app/infralink_models.py
#
# Keyed off `servers.id`, not `clients.id`: your SSH credentials (ip_address,
# ssh_port, ssh_username, ...) live on the Server row, and ssh_manager.py's
# functions take a Server object - a Client can have many Servers, so an
# Agent (which corresponds to one physical/virtual host) maps 1:1 to a
# Server, matching requirement #8 (reuse the existing dynamic tables, no
# duplicate Client/Server tables).
import uuid
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class InfraLinkRegistrationToken(Base):
    """
    Short-lived, single-use token the dashboard generates and shows to the
    user, for them to hand to `infralink-agent register --token ...` on the
    target server. Requirement #4.
    """
    __tablename__ = "infralink_registration_tokens"

    id = Column(String(36), primary_key=True, default=_uuid)
    token = Column(String(128), unique=True, nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False, nullable=False)

    @classmethod
    def new_for_server(cls, server_id: int, created_by_user_id: int, ttl_minutes: int = 15):
        return cls(
            token=uuid.uuid4().hex + uuid.uuid4().hex,  # 64 hex chars, unguessable
            server_id=server_id,
            created_by_user_id=created_by_user_id,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )

    def is_valid(self) -> bool:
        return not self.revoked and not self.used_at and datetime.utcnow() < self.expires_at


class InfraLinkAgent(Base):
    """
    The permanent Agent identity created on successful registration.
    One row per InfraLink-enabled server, linked to the SAME `servers` row
    the existing SSH system already uses (requirement #8).
    """
    __tablename__ = "infralink_agents"

    id = Column(String(36), primary_key=True, default=_uuid)  # this is the "agent_id" returned to the CLI
    server_id = Column(Integer, ForeignKey("servers.id"), unique=True, nullable=False)

    credential_hash = Column(String(128), nullable=False)  # bcrypt hash - raw credential never stored
    status = Column(String(16), default="offline", nullable=False)  # "online" | "offline"

    hostname = Column(String(255), nullable=True)
    os = Column(String(255), nullable=True)
    os_detail = Column(Text, nullable=True)
    agent_version = Column(String(32), nullable=True)

    cpu_percent = Column(Float, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_bytes = Column(Integer, nullable=True)
    ram_used_bytes = Column(Integer, nullable=True)
    ram_percent = Column(Float, nullable=True)
    disk_total_bytes = Column(Integer, nullable=True)
    disk_used_bytes = Column(Integer, nullable=True)
    disk_percent = Column(Float, nullable=True)

    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)

    server = relationship("Server", backref="infralink_agent", uselist=False)

    def mark_heartbeat(self, metrics: dict) -> None:
        self.hostname = metrics.get("hostname", self.hostname)
        self.os = metrics.get("os", self.os)
        self.os_detail = metrics.get("os_detail", self.os_detail)
        self.agent_version = metrics.get("agent_version", self.agent_version)
        self.cpu_percent = metrics.get("cpu_percent", self.cpu_percent)
        self.cpu_cores = metrics.get("cpu_cores", self.cpu_cores)
        self.ram_total_bytes = metrics.get("ram_total_bytes", self.ram_total_bytes)
        self.ram_used_bytes = metrics.get("ram_used_bytes", self.ram_used_bytes)
        self.ram_percent = metrics.get("ram_percent", self.ram_percent)
        self.disk_total_bytes = metrics.get("disk_total_bytes", self.disk_total_bytes)
        self.disk_used_bytes = metrics.get("disk_used_bytes", self.disk_used_bytes)
        self.disk_percent = metrics.get("disk_percent", self.disk_percent)
        self.last_seen_at = datetime.utcnow()
        self.status = "online"

    def is_stale(self, stale_after_seconds: int = 45) -> bool:
        if not self.last_seen_at:
            return True
        return (datetime.utcnow() - self.last_seen_at).total_seconds() > stale_after_seconds
