import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models import RoleEnum, EnvironmentEnum


# ---------------- Auth ----------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: RoleEnum
    username: str


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    role: RoleEnum = RoleEnum.viewer


class UserUpdate(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True


# ---------------- Clients ----------------
class ClientCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ClientOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    server_count: int = 0
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------------- Servers ----------------
class ServerCreate(BaseModel):
    client_id: int
    name: str
    ip_address: str
    ssh_port: int = 22
    ssh_username: str = "root"
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    pm2_path: Optional[str] = None
    tag: Optional[str] = None
    environment: Optional[EnvironmentEnum] = None


class ServerOut(BaseModel):
    id: int
    client_id: int
    name: str
    ip_address: str
    ssh_port: int
    ssh_username: str
    pm2_path: Optional[str] = None
    environment: EnvironmentEnum
    tag: Optional[str] = None
    online: Optional[bool] = None

    class Config:
        from_attributes = True


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    pm2_path: Optional[str] = None
    tag: Optional[str] = None
    environment: Optional[EnvironmentEnum] = None


class DetectPM2Request(BaseModel):
    ip_address: str
    ssh_port: int = 22
    ssh_username: str = "root"
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None


class DetectPM2Response(BaseModel):
    found: bool
    pm2_path: Optional[str] = None
    detail: Optional[str] = None


# ---------------- PM2 Processes ----------------
class PM2Process(BaseModel):
    pm_id: int
    name: str
    pid: Optional[int] = None
    status: str
    cpu: Optional[float] = None
    memory: Optional[int] = None
    uptime: Optional[int] = None
    restarts: Optional[int] = None
    instances: Optional[int] = None
    exec_mode: Optional[str] = None


class ProcessActionRequest(BaseModel):
    action: str = Field(..., pattern="^(restart|stop|start|delete|reload)$")
