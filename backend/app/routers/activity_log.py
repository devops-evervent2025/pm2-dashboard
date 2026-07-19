"""
Self-contained Activity Log: surfaces the audit trails already being
recorded elsewhere in the app (SecretRevealAudit, CurlCommandAudit,
ProcessLogAudit) as one unified, human-readable, searchable feed.
Admin-only, since it shows what every user has been doing.

Retention: every time this endpoint is called, entries older than
RETENTION_DAYS are purged from all three audit tables first.
"""
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models import User, Server, Client, SecretRevealAudit, CurlCommandAudit, ProcessLogAudit

router = APIRouter(prefix="/activity-log", tags=["activity-log"])

RETENTION_DAYS = 7


class ActivityLogEntry(BaseModel):
    id: str
    type: str
    timestamp: datetime.datetime
    username: Optional[str] = None
    role: Optional[str] = None
    client_name: Optional[str] = None
    environment: Optional[str] = None
    detail: str


def _purge_old_entries(db: Session):
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=RETENTION_DAYS)
    db.query(SecretRevealAudit).filter(SecretRevealAudit.revealed_at < cutoff).delete()
    db.query(CurlCommandAudit).filter(CurlCommandAudit.executed_at < cutoff).delete()
    db.query(ProcessLogAudit).filter(ProcessLogAudit.viewed_at < cutoff).delete()
    db.commit()


@router.get("", response_model=List[ActivityLogEntry])
def get_activity_log(
    limit: int = Query(200, ge=1, le=1000),
    username: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    client: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    _purge_old_entries(db)

    users_by_id = {u.id: (u.username, u.role.value if hasattr(u.role, "value") else u.role) for u in db.query(User).all()}
    clients_by_id = {c.id: c.name for c in db.query(Client).all()}
    servers_by_id = {
        s.id: (s.name, s.environment.value if hasattr(s.environment, "value") else s.environment, clients_by_id.get(s.client_id))
        for s in db.query(Server).all()
    }

    entries: List[ActivityLogEntry] = []

    for row in db.query(SecretRevealAudit).order_by(SecretRevealAudit.revealed_at.desc()).all():
        uname, urole = users_by_id.get(row.user_id, (None, None))
        env, client_name = None, None
        if row.server_id is not None:
            srv = servers_by_id.get(row.server_id)
            if srv:
                _, env, client_name = srv
        entries.append(ActivityLogEntry(
            id=f"secret-{row.id}", type="secret_reveal", timestamp=row.revealed_at,
            username=uname, role=urole, client_name=client_name, environment=env,
            detail=f"Revealed {row.key_name} in {row.repo_name}/{row.env_file_path}",
        ))

    for row in db.query(CurlCommandAudit).order_by(CurlCommandAudit.executed_at.desc()).all():
        uname, urole = users_by_id.get(row.user_id, (None, None))
        srv = servers_by_id.get(row.server_id)
        server_name, env, client_name = srv if srv else (f"server #{row.server_id}", None, None)
        status_note = f" (exit {row.exit_status})" if row.exit_status is not None else ""
        entries.append(ActivityLogEntry(
            id=f"curl-{row.id}", type="curl_command", timestamp=row.executed_at,
            username=uname, role=urole, client_name=client_name, environment=env,
            detail=f"Ran on {server_name}: {row.command}{status_note}",
        ))

    for row in db.query(ProcessLogAudit).order_by(ProcessLogAudit.viewed_at.desc()).all():
        uname, urole = users_by_id.get(row.user_id, (None, None))
        srv = servers_by_id.get(row.server_id)
        server_name, env, client_name = srv if srv else (f"server #{row.server_id}", None, None)
        entries.append(ActivityLogEntry(
            id=f"logview-{row.id}", type="log_view", timestamp=row.viewed_at,
            username=uname, role=urole, client_name=client_name, environment=env,
            detail=f"Viewed logs for {row.process_name} on {server_name}",
        ))

    def matches(e: ActivityLogEntry) -> bool:
        if username and (not e.username or username.lower() not in e.username.lower()):
            return False
        if role and e.role != role:
            return False
        if client and (not e.client_name or client.lower() not in e.client_name.lower()):
            return False
        if environment and e.environment != environment:
            return False
        return True

    filtered = [e for e in entries if matches(e)]
    filtered.sort(key=lambda e: e.timestamp, reverse=True)
    return filtered[:limit]
