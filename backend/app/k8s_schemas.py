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


class K8sClientCreate(BaseModel):
    name: str
    description: Optional[str] = None


class K8sClientOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    cluster_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


class K8sClientUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class K8sClusterUpdate(BaseModel):
    name: Optional[str] = None
    environment: Optional[str] = None
    connection_type: Optional[str] = None

    ssh_ip_address: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    kubectl_path: Optional[str] = None

    kubeconfig_yaml: Optional[str] = None

    api_server_url: Optional[str] = None
    api_token: Optional[str] = None
    api_ca_cert: Optional[str] = None
    api_verify_ssl: Optional[str] = None


class K8sClusterFullOut(BaseModel):
    """Every stored field, used only to pre-fill the edit form - the
    create/list endpoints deliberately don't expose secrets like
    ssh_password/api_token, but the edit modal needs the current values
    to show the form in its current state."""
    id: int
    client_id: int
    name: str
    environment: Optional[str] = None
    connection_type: str

    ssh_ip_address: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_private_key_path: Optional[str] = None
    kubectl_path: Optional[str] = None

    kubeconfig_yaml: Optional[str] = None

    api_server_url: Optional[str] = None
    api_token: Optional[str] = None
    api_ca_cert: Optional[str] = None
    api_verify_ssl: Optional[str] = None

    class Config:
        from_attributes = True
