from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin_or_dev
from app.models import Server, User
from app.schemas import PM2Process, ProcessActionRequest
from app.ssh_manager import list_pm2_processes, pm2_action, SSHConnectionError

router = APIRouter(prefix="/servers/{server_id}/processes", tags=["processes"])


def _get_server_or_404(server_id: int, db: Session) -> Server:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.get("", response_model=list[PM2Process])
def get_processes(server_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    server = _get_server_or_404(server_id, db)
    try:
        return list_pm2_processes(server)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{process_name}/action")
def process_action(
    server_id: int,
    process_name: str,
    payload: ProcessActionRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),  # Viewers are read-only
):
    server = _get_server_or_404(server_id, db)
    try:
        output = pm2_action(server, process_name, payload.action)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"detail": f"{payload.action} executed on {process_name}", "output": output}
