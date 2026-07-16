import datetime
from typing import Optional, List
from pydantic import BaseModel


class SSLServerCreate(BaseModel):
    name: str
    ip_address: str
    ssh_port: int = 22
    ssh_username: str = "root"
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    conf_dir: str = "/etc/nginx/conf.d"
    threshold_days: int = 7


class SSLCertificateOut(BaseModel):
    id: int
    domain_name: Optional[str] = None
    config_file: Optional[str] = None
    cert_path: Optional[str] = None
    expiry_date: Optional[datetime.datetime] = None
    days_remaining: Optional[int] = None
    last_checked_at: Optional[datetime.datetime] = None
    last_check_error: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


class SSLServerOut(BaseModel):
    id: int
    name: str
    ip_address: str
    conf_dir: str
    threshold_days: int
    certificates: List[SSLCertificateOut] = []

    class Config:
        from_attributes = True
