import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SSLServer(Base):
    """एक row = एक server, जिसके nginx conf directory के सारे *.conf files scan होते हैं।"""
    __tablename__ = "ssl_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ip_address = Column(String(100), nullable=False)
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100), default="root")
    ssh_password = Column(String(500), nullable=True)
    ssh_private_key_path = Column(String(500), nullable=True)
    conf_dir = Column(String(500), default="/etc/nginx/conf.d")
    threshold_days = Column(Integer, default=7)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    certificates = relationship(
        "SSLCertificate", back_populates="server", cascade="all, delete-orphan"
    )


class SSLCertificate(Base):
    """conf_dir के अंदर मिला हर domain/certificate - अपने आप discover होता है check के वक़्त।"""
    __tablename__ = "ssl_certificates"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("ssl_servers.id"), nullable=False)
    domain_name = Column(String(255), nullable=True)
    config_file = Column(String(500), nullable=True)
    cert_path = Column(String(500), nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    days_remaining = Column(Integer, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    last_check_error = Column(String(1000), nullable=True)

    server = relationship("SSLServer", back_populates="certificates")
