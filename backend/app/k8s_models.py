"""
Kubernetes cluster models - intentionally NOT related to the Server table.
A K8sCluster is its own top-level entity under a Client, because unlike
PM2/Docker (which are always reached via one SSH login to one machine),
different companies reach their K8s clusters in genuinely different ways:
  - ssh_kubectl: SSH into a node that already has kubectl + a working
    kubeconfig on it, and run kubectl commands remotely (mirrors the
    Docker-over-SSH pattern).
  - kubeconfig: the full kubeconfig YAML is stored here, and the backend
    talks to the cluster's API server directly using the `kubernetes`
    Python client - no SSH involved at all.
  - api_token: just an API server URL + a bearer token (common for
    cloud-managed clusters where you don't want to hand out a full
    kubeconfig) - also talks to the API directly, no SSH.

Only the fields relevant to the chosen connection_type are populated;
the others stay NULL. This mirrors how Server already has both
ssh_password and ssh_private_key_path with only one ever actually used.
"""
import enum
import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class K8sConnectionTypeEnum(str, enum.Enum):
    def __str__(self):
        # Same Python 3.11+ str(enum) fix applied to Server.connection_type -
        # without this, auto_migrate.py would generate a broken ALTER TABLE
        # DEFAULT clause exactly like the ConnectionTypeEnum bug did.
        return str(self.value)

    ssh_kubectl = "ssh_kubectl"
    kubeconfig = "kubeconfig"
    api_token = "api_token"


class K8sClient(Base):
    """Kubernetes ke liye poori tarah alag client list - PM2/Docker ke
    `clients` table se koi link nahi. Company/organization group karne ka
    matlab jo bhi ho, K8s ke liye yahi asli source hai."""
    __tablename__ = "k8s_clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    clusters = relationship("K8sCluster", back_populates="client", cascade="all, delete-orphan")


class K8sCluster(Base):
    __tablename__ = "k8s_clusters"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("k8s_clients.id"), nullable=False)
    name = Column(String(255), nullable=False)
    environment = Column(String(50), nullable=True)  # Dev/Prod/Stg/Other, free text - reuses no enum table
    connection_type = Column(Enum(K8sConnectionTypeEnum), nullable=False, default=K8sConnectionTypeEnum.ssh_kubectl)

    # -- ssh_kubectl fields --
    ssh_ip_address = Column(String(100), nullable=True)
    ssh_port = Column(Integer, nullable=True, default=22)
    ssh_username = Column(String(100), nullable=True)
    ssh_password = Column(String(500), nullable=True)
    ssh_private_key_path = Column(String(500), nullable=True)
    kubectl_path = Column(String(500), nullable=True)  # optional, same idea as Server.pm2_path

    # -- kubeconfig field --
    kubeconfig_yaml = Column(Text, nullable=True)

    # -- api_token fields --
    api_server_url = Column(String(500), nullable=True)
    api_token = Column(Text, nullable=True)
    api_ca_cert = Column(Text, nullable=True)  # optional, for self-signed cluster CAs
    api_verify_ssl = Column(String(10), nullable=True, default="yes")  # "yes"/"no", same pattern as LogAlert.email_sent

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    client = relationship("K8sClient", back_populates="clusters")
