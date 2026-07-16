import enum
import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class RoleEnum(str, enum.Enum):
    admin = "admin"
    developer = "developer"
    viewer = "viewer"


class EnvironmentEnum(str, enum.Enum):
    Dev = "Dev"
    Prod = "Prod"
    Stg = "Stg"
    Other = "Other"


def detect_environment(*hints: str) -> EnvironmentEnum:
    joined = " ".join([h or "" for h in hints]).lower()
    if any(k in joined for k in ("prod", "production", "live")):
        return EnvironmentEnum.Prod
    if any(k in joined for k in ("stg", "stag", "staging", "uat", "preprod", "pre-prod")):
        return EnvironmentEnum.Stg
    if any(k in joined for k in ("dev", "development", "local", "sandbox")):
        return EnvironmentEnum.Dev
    return EnvironmentEnum.Other


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    servers = relationship("Server", back_populates="client", cascade="all, delete-orphan")


class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String(255), nullable=False)
    ip_address = Column(String(100), nullable=False)
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100), default="root")
    ssh_password = Column(String(500), nullable=True)
    ssh_private_key_path = Column(String(500), nullable=True)
    pm2_path = Column(String(500), nullable=True)
    environment = Column(Enum(EnvironmentEnum), default=EnvironmentEnum.Other)
    tag = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    client = relationship("Client", back_populates="servers")


class ProcessLogAudit(Base):
    __tablename__ = "process_log_audit"
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    process_name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    viewed_at = Column(DateTime, default=datetime.datetime.utcnow)
    note = Column(Text, nullable=True)



class SecretRevealAudit(Base):
    """Audit trail of who revealed which .env secret value, and when.
    The actual secret value is never stored here - only what was looked at."""
    __tablename__ = "secret_reveal_audit"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False)
    env_file_path = Column(String(500), nullable=False)
    key_name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revealed_at = Column(DateTime, default=datetime.datetime.utcnow)


class RepoScanPath(Base):
    """An admin-configured directory on a managed server to scan for repos
    and their .env files, e.g. server=Amaze Dev, base_path=/var/www/frontend/Development."""
    __tablename__ = "repo_scan_paths"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    base_path = Column(String(500), nullable=False)
    label = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
