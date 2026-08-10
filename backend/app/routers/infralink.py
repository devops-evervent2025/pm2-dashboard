# backend/app/routers/infralink.py
#
# Authorization: get_authorized_server_ids() now uses the real
# UserClientAccess grant table (requirement #9) - admins see every server
# (consistent with require_admin already being able to create/delete any
# server in servers.py); everyone else sees only servers under Clients
# they've been explicitly granted. New grants start empty, so a
# non-admin sees nothing until an admin grants them a client via the
# /api/infralink/access endpoints below.
#
# get_current_user confirmed against your real auth.py - imported as-is.
#
# Every route 404s when AGENT_ENABLED is false, so with the flag off this
# router (including the access-grant endpoints) is invisible - no change
# to SSH or anything else.

import secrets
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.auth import get_current_user, require_admin
from app.models import Server, Client, User, RoleEnum
from app import infralink_models as models
from app import infralink_schemas as schemas
from app.access_control_models import UserClientAccess

router = APIRouter(prefix="/api/infralink", tags=["infralink"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def _require_agent_enabled():
    """Requirement #1: AGENT_ENABLED=false disables the Agent API entirely,
    not just hides it. 404 so the feature's existence isn't even leaked."""
    if not get_settings().AGENT_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def get_authorized_server_ids(user: User, db: Session) -> List[int]:
    """Requirement #9. Admins: every server. Everyone else: servers whose
    Client has an explicit UserClientAccess grant for this user."""
    if user.role == RoleEnum.admin:
        return [s.id for (s,) in db.query(Server.id).all()]

    granted_client_ids = [
        row.client_id for row in db.query(UserClientAccess.client_id).filter(UserClientAccess.user_id == user.id).all()
    ]
    if not granted_client_ids:
        return []
    return [s.id for (s,) in db.query(Server.id).filter(Server.client_id.in_(granted_client_ids)).all()]


def _assert_owns_server(user: User, server_id: int, db: Session):
    if server_id not in get_authorized_server_ids(user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this server")


# ---------------------------------------------------------------------------
# Admin: manage which users can see which Clients' InfraLink agents
# ---------------------------------------------------------------------------
@router.post("/access/grant", response_model=schemas.AccessGrantOut, dependencies=[Depends(_require_agent_enabled)])
def grant_access(body: schemas.AccessGrantRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if not db.query(User).filter(User.id == body.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(Client).filter(Client.id == body.client_id).first():
        raise HTTPException(status_code=404, detail="Client not found")

    existing = (
        db.query(UserClientAccess)
        .filter(UserClientAccess.user_id == body.user_id, UserClientAccess.client_id == body.client_id)
        .first()
    )
    if existing:
        return existing

    grant = UserClientAccess(user_id=body.user_id, client_id=body.client_id, granted_by=admin.id)
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


@router.post("/access/revoke", dependencies=[Depends(_require_agent_enabled)])
def revoke_access(body: schemas.AccessGrantRequest, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    grant = (
        db.query(UserClientAccess)
        .filter(UserClientAccess.user_id == body.user_id, UserClientAccess.client_id == body.client_id)
        .first()
    )
    if grant:
        db.delete(grant)
        db.commit()
    return {"detail": "Access revoked"}


@router.get("/access/{user_id}", response_model=List[schemas.AccessGrantOut], dependencies=[Depends(_require_agent_enabled)])
def list_access(user_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return db.query(UserClientAccess).filter(UserClientAccess.user_id == user_id).all()


# ---------------------------------------------------------------------------
# Dashboard-side: create a registration token for a server the user owns
# ---------------------------------------------------------------------------
@router.post("/registration-tokens", response_model=schemas.RegistrationTokenOut, dependencies=[Depends(_require_agent_enabled)])
def create_registration_token(
    body: "schemas.RegistrationTokenCreate",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _assert_owns_server(user, body.server_id, db)

    existing = (
        db.query(models.InfraLinkAgent)
        .filter(models.InfraLinkAgent.server_id == body.server_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This server already has an InfraLink agent registered")

    token_row = models.InfraLinkRegistrationToken.new_for_server(
        server_id=body.server_id, created_by_user_id=user.id, ttl_minutes=body.ttl_minutes
    )
    db.add(token_row)
    db.commit()
    db.refresh(token_row)
    return token_row


# ---------------------------------------------------------------------------
# Agent-side: exchange the registration token for a permanent credential
# ---------------------------------------------------------------------------
@router.post("/agents/register", response_model=schemas.AgentRegisterResponse, dependencies=[Depends(_require_agent_enabled)])
def register_agent(body: schemas.AgentRegisterRequest, db: Session = Depends(get_db)):
    token_row = (
        db.query(models.InfraLinkRegistrationToken)
        .filter(models.InfraLinkRegistrationToken.token == body.registration_token)
        .first()
    )
    if not token_row or not token_row.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired registration token")

    raw_credential = secrets.token_urlsafe(48)
    agent = models.InfraLinkAgent(
        server_id=token_row.server_id,
        credential_hash=pwd_context.hash(raw_credential),
        status="offline",
    )
    db.add(agent)
    token_row.used_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    return schemas.AgentRegisterResponse(agent_id=agent.id, credential=raw_credential)


def _authenticate_agent(authorization: str, db: Session) -> models.InfraLinkAgent:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing agent credential")
    raw_credential = authorization.removeprefix("Bearer ").strip()

    for agent in db.query(models.InfraLinkAgent).all():
        if pwd_context.verify(raw_credential, agent.credential_hash):
            return agent
    raise HTTPException(status_code=401, detail="Invalid agent credential")


@router.get("/agents/me", response_model=schemas.AgentOut, dependencies=[Depends(_require_agent_enabled)])
def agent_me(authorization: str = Header(None), db: Session = Depends(get_db)):
    return _authenticate_agent(authorization, db)


@router.post("/agents/heartbeat", response_model=schemas.AgentOut, dependencies=[Depends(_require_agent_enabled)])
def agent_heartbeat(
    body: schemas.AgentHeartbeatRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    agent = _authenticate_agent(authorization, db)
    agent.mark_heartbeat(body.model_dump())
    db.commit()
    db.refresh(agent)
    return agent


# ---------------------------------------------------------------------------
# Dashboard-side: list/status of agents the current user is authorized for
# ---------------------------------------------------------------------------
@router.get("/agents", response_model=List[schemas.AgentOut], dependencies=[Depends(_require_agent_enabled)])
def list_agents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server_ids = get_authorized_server_ids(user, db)
    agents = db.query(models.InfraLinkAgent).filter(models.InfraLinkAgent.server_id.in_(server_ids)).all()
    for a in agents:
        if a.is_stale():
            a.status = "offline"
    db.commit()
    return agents


# ---------------------------------------------------------------------------
# WebSocket channel (Phase 1: heartbeat/status stream only, no command exec)
# ---------------------------------------------------------------------------
@router.websocket("/ws/agents/{agent_id}")
async def agent_ws(websocket: WebSocket, agent_id: str):
    if not get_settings().AGENT_ENABLED:
        await websocket.close(code=1008)
        return

    authorization = websocket.headers.get("authorization")
    db = next(get_db())
    try:
        agent = _authenticate_agent(authorization, db)
        if agent.id != agent_id:
            await websocket.close(code=1008)
            return

        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                agent.mark_heartbeat(data)
                db.commit()
                await websocket.send_json({"ok": True, "last_seen_at": agent.last_seen_at.isoformat()})
        except WebSocketDisconnect:
            agent.status = "offline"
            db.commit()
    except HTTPException:
        await websocket.close(code=1008)
    finally:
        db.close()
