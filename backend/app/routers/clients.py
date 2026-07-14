from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import Client, User
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    clients = db.query(Client).all()
    result = []
    for c in clients:
        out = ClientOut.model_validate(c)
        out.server_count = len(c.servers)
        result.append(out)
    return result


@router.post("", response_model=ClientOut)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # Admin-only: add client via UI
):
    if db.query(Client).filter(Client.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Client with this name already exists")
    client = Client(name=payload.name, description=payload.description, created_by=admin.id)
    db.add(client)
    db.commit()
    db.refresh(client)
    out = ClientOut.model_validate(client)
    out.server_count = 0
    return out


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    out = ClientOut.model_validate(client)
    out.server_count = len(client.servers)
    return out


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"detail": "Client deleted"}
