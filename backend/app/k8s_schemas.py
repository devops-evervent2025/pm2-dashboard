from typing import Optional
from pydantic import BaseModel


class K8sClusterCreate(BaseModel):
    client_id: int
    name: str
    environment: Optional[str] = None
    connection_type: str  # "ssh_kubectl" | "kubeconfig" | "api_token"

    # ssh_kubectl
    ssh_ip_address: Optional[str] = None
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    kubectl_path: Optional[str] = None

    # kubeconfig
    kubeconfig_yaml: Optional[str] = None

    # api_token
    api_server_url: Optional[str] = None
    api_token: Optional[str] = None
    api_ca_cert: Optional[str] = None
    api_verify_ssl: Optional[str] = "yes"


class K8sClusterOut(BaseModel):
    id: int
    client_id: int
    name: str
    environment: Optional[str] = None
    connection_type: str
    online: Optional[bool] = None

    class Config:
        from_attributes = True


class K8sPodOut(BaseModel):
    name: str
    namespace: str
    phase: str
    node_name: Optional[str] = None
    restarts: int = 0
    created: str = ""


class K8sPodActionRequest(BaseModel):
    namespace: str
    action: str  # "delete" (start with just this - pods aren't "started/stopped" like PM2/Docker)
