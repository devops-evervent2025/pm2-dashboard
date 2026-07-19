"""
Self-contained Activity Log: surfaces the audit trails already being
recorded elsewhere in the app (SecretRevealAudit, CurlCommandAudit,
ProcessLogAudit) as one unified, human-readable feed. Admin-only.
No new tables - this only reads what other features already write.
"""
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models import User, Server, SecretRevealAudit, CurlCommandAudit, ProcessLogAudit

router = APIRouter(prefix="/activity-log", tags=["activity-log"])


class ActivityLogEntry(BaseModel):
    id: str
    type: str
    timestamp: datetime.datetime
    username: Optional[str] = None
    detail: str


@router.get("", response_model=List[ActivityLogEntry])
def get_activity_log(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    users_by_id = {u.id: u.username for u in db.query(User).all()}
    servers_by_id = {s.id: s.name for s in db.query(Server).all()}

    entries: List[ActivityLogEntry] = []

    for row in db.query(SecretRevealAudit).order_by(SecretRevealAudit.revealed_at.desc()).limit(limit).all():
        entries.append(ActivityLogEntry(
            id=f"secret-{row.id}",
            type="secret_reveal",
            timestamp=row.revealed_at,
            username=users_by_id.get(row.user_id),
            detail=f"Revealed {row.key_name} in {row.repo_name}/{row.env_file_path}",
        ))

    for row in db.query(CurlCommandAudit).order_by(CurlCommandAudit.executed_at.desc()).limit(limit).all():
        server_name = servers_by_id.get(row.server_id, f"server #{row.server_id}")
        status_note = f" (exit {row.exit_status})" if row.exit_status is not None else ""
        entries.append(ActivityLogEntry(
            id=f"curl-{row.id}",
            type="curl_command",
            timestamp=row.executed_at,
            username=users_by_id.get(row.user_id),
            detail=f"Ran on {server_name}: {row.command}{status_note}",
        ))

    for row in db.query(ProcessLogAudit).order_by(ProcessLogAudit.viewed_at.desc()).limit(limit).all():
        server_name = servers_by_id.get(row.server_id, f"server #{row.server_id}")
        entries.append(ActivityLogEntry(
            id=f"logview-{row.id}",
            type="log_view",
            timestamp=row.viewed_at,
            username=users_by_id.get(row.user_id),
            detail=f"Viewed logs for {row.process_name} on {server_name}",
        ))

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries[:limit]
