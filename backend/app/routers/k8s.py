from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import User, Client
from app.k8s_models import K8sCluster, K8sConnectionTypeEnum
from app.k8s_schemas import K8sClusterCreate, K8sClusterOut, K8sPodOut, K8sPodActionRequest
from app.k8s_manager import list_pods, pod_action, check_online, K8sConnectionError

router = APIRouter(prefix="/k8s-clusters", tags=["k8s"])

ALLOWED_ACTIONS = {"delete"}


def _get_cluster_or_404(cluster_id: int, db: Session) -> K8sCluster:
    cluster = db.query(K8sCluster).filter(K8sCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.get("", response_model=list[K8sClusterOut])
def list_clusters(client_id: int | None = None, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    query = db.query(K8sCluster)
    if client_id is not None:
        query = query.filter(K8sCluster.client_id == client_id)
    return [K8sClusterOut.model_validate(c) for c in query.all()]


@router.post("", response_model=K8sClusterOut)
def create_cluster(payload: K8sClusterCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        conn_type = K8sConnectionTypeEnum(payload.connection_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported connection_type: {payload.connection_type}")

    cluster = K8sCluster(
        client_id=payload.client_id,
        name=payload.name,
        environment=payload.environment,
        connection_type=conn_type,
        ssh_ip_address=payload.ssh_ip_address,
        ssh_port=payload.ssh_port,
        ssh_username=payload.ssh_username,
        ssh_password=payload.ssh_password,
        ssh_private_key_path=payload.ssh_private_key_path,
        kubectl_path=payload.kubectl_path,
        kubeconfig_yaml=payload.kubeconfig_yaml,
        api_server_url=payload.api_server_url,
        api_token=payload.api_token,
        api_ca_cert=payload.api_ca_cert,
        api_verify_ssl=payload.api_verify_ssl,
        created_by=admin.id,
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return K8sClusterOut.model_validate(cluster)


@router.get("/{cluster_id}", response_model=K8sClusterOut)
def get_cluster(cluster_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    cluster = _get_cluster_or_404(cluster_id, db)
    out = K8sClusterOut.model_validate(cluster)
    out.online = check_online(cluster)
    return out


@router.delete("/{cluster_id}")
def delete_cluster(cluster_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    cluster = _get_cluster_or_404(cluster_id, db)
    db.delete(cluster)
    db.commit()
    return {"detail": "Cluster deleted"}


@router.get("/{cluster_id}/pods", response_model=list[K8sPodOut])
def get_pods(cluster_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    cluster = _get_cluster_or_404(cluster_id, db)
    try:
        return list_pods(cluster)
    except K8sConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{cluster_id}/pods/{pod_name}/action")
def pod_action_endpoint(
    cluster_id: int,
    pod_name: str,
    payload: K8sPodActionRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),  # pod delete is destructive - admin only, stricter than PM2/Docker's admin-or-dev
):
    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")
    cluster = _get_cluster_or_404(cluster_id, db)
    try:
        output = pod_action(cluster, payload.namespace, pod_name, payload.action)
    except K8sConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"detail": f"{payload.action} executed on {pod_name}", "output": output}
