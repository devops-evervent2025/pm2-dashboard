from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin_or_dev
from app.models import Server, User, ConnectionTypeEnum
from app.schemas import DockerContainer, DockerActionRequest
from app.ssh_manager import list_docker_containers, docker_action, SSHConnectionError

router = APIRouter(prefix="/servers/{server_id}/containers", tags=["docker"])

ALLOWED_ACTIONS = {"start", "stop", "restart"}


def _get_server_or_404(server_id: int, db: Session) -> Server:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


def _ensure_ssh_capable(server: Server):
    if server.connection_type == ConnectionTypeEnum.docker_api:
        raise HTTPException(
            status_code=501,
            detail="Docker API connection type isn't implemented yet for this server.",
        )


@router.get("", response_model=list[DockerContainer])
def get_containers(server_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    server = _get_server_or_404(server_id, db)
    _ensure_ssh_capable(server)
    try:
        return list_docker_containers(server)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{container_name}/action")
def container_action(
    server_id: int,
    container_name: str,
    payload: DockerActionRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),
):
    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {payload.action}")

    server = _get_server_or_404(server_id, db)
    _ensure_ssh_capable(server)
    try:
        output = docker_action(server, container_name, payload.action)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"detail": f"{payload.action} executed on {container_name}", "output": output}
