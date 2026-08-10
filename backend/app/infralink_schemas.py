# backend/app/infralink_schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegistrationTokenCreate(BaseModel):
    server_id: int
    ttl_minutes: int = 15


class RegistrationTokenOut(BaseModel):
    token: str
    expires_at: datetime

    class Config:
        from_attributes = True


class AgentRegisterRequest(BaseModel):
    registration_token: str


class AgentRegisterResponse(BaseModel):
    agent_id: str
    credential: str  # returned exactly once, at registration time - never again


class AgentHeartbeatRequest(BaseModel):
    hostname: str
    os: str
    os_detail: Optional[str] = None
    cpu_percent: Optional[float] = None
    cpu_cores: Optional[int] = None
    ram_total_bytes: Optional[int] = None
    ram_used_bytes: Optional[int] = None
    ram_percent: Optional[float] = None
    disk_total_bytes: Optional[int] = None
    disk_used_bytes: Optional[int] = None
    disk_percent: Optional[float] = None
    agent_version: Optional[str] = None


class AccessGrantRequest(BaseModel):
    user_id: int
    client_id: int


class AccessGrantOut(BaseModel):
    id: int
    user_id: int
    client_id: int
    granted_at: datetime

    class Config:
        from_attributes = True


class AgentOut(BaseModel):
    id: str
    server_id: int
    status: str
    hostname: Optional[str]
    os: Optional[str]
    agent_version: Optional[str]
    cpu_percent: Optional[float]
    ram_percent: Optional[float]
    disk_percent: Optional[float]
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True
