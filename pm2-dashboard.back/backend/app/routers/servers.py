from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import Server, Client, User, detect_environment
from app.schemas import ServerCreate, ServerOut
from app.ssh_manager import check_online

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerOut])
def list_servers(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Server)
    if client_id is not None:
        query = query.filter(Server.client_id == client_id)
    servers = query.all()
    return [ServerOut.model_validate(s) for s in servers]


@router.post("", response_model=ServerOut)
def create_server(
    payload: ServerCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # Admin-only: add server via UI
):
    client = db.query(Client).filter(Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    environment = payload.environment or detect_environment(payload.name, payload.tag, payload.ip_address)

    server = Server(
        client_id=payload.client_id,
        name=payload.name,
        ip_address=payload.ip_address,
        ssh_port=payload.ssh_port,
        ssh_username=payload.ssh_username,
        ssh_password=payload.ssh_password,
        ssh_private_key_path=payload.ssh_private_key_path,
        tag=payload.tag,
        environment=environment,
        created_by=admin.id,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return ServerOut.model_validate(server)


@router.get("/{server_id}", response_model=ServerOut)
def get_server(server_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    out = ServerOut.model_validate(server)
    out.online = check_online(server)
    return out


@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
    return {"detail": "Server deleted"}
