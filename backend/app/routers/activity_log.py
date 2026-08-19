"""
Self-contained Activity Log: surfaces the audit trails already being
recorded elsewhere in the app (SecretRevealAudit, CurlCommandAudit,
ProcessLogAudit) as one unified, human-readable, searchable feed.
Admin-only, since it shows what every user has been doing.

Retention: every time this endpoint is called, entries older than
RETENTION_DAYS are purged from all three audit tables first.
"""
import datetime
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, require_any_role, get_current_user
from app.models import User, Server, Client, SecretRevealAudit, CurlCommandAudit, ProcessLogAudit, RoleEnum
from app.env_audit_models import EnvEditAudit
from app.build_run_models import BuildRunAudit

router = APIRouter(prefix="/activity-log", tags=["activity-log"])

RETENTION_DAYS = 7

# Five clear activity categories shown in usage graphs.
ACTIVITY_TYPES = ["log_view", "curl_command", "env_edit", "build_run", "secret_reveal"]


def _empty_type_counts() -> dict[str, int]:
    return {t: 0 for t in ACTIVITY_TYPES}


class ActivityLogEntry(BaseModel):
    id: str
    type: str
    timestamp: datetime.datetime
    username: Optional[str] = None
    role: Optional[str] = None
    client_name: Optional[str] = None
    environment: Optional[str] = None
    detail: str


class ActivityStatsDay(BaseModel):
    date: str
    counts: Dict[str, int]
    total: int


class ActivityStatsUser(BaseModel):
    username: str
    role: str
    counts: Dict[str, int]
    total: int


class ActivityStatsResponse(BaseModel):
    days: int
    username_filter: Optional[str] = None
    viewing_as_admin: bool
    total_actions: int
    totals_by_type: Dict[str, int]
    timeline: List[ActivityStatsDay]
    by_user: List[ActivityStatsUser]
    available_users: List[str]


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


def _role_value(role) -> str:
    return role.value if hasattr(role, "value") else str(role)


@router.get("/stats", response_model=ActivityStatsResponse)
def get_activity_stats(
    days: int = Query(7, ge=1, le=30),
    username: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role),
):
    """Usage stats for charts. Admins can filter any user; others see only themselves."""
    is_admin = current_user.role == RoleEnum.admin
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    users = db.query(User).all()
    users_by_id = {u.id: u for u in users}

    target_user_id: Optional[int] = None
    username_filter: Optional[str] = None

    if is_admin:
        if username and username.strip():
            match = next((u for u in users if u.username.lower() == username.strip().lower()), None)
            if not match:
                raise HTTPException(status_code=404, detail="User not found.")
            target_user_id = match.id
            username_filter = match.username
    else:
        target_user_id = current_user.id
        username_filter = current_user.username

    timeline_map: dict[str, dict[str, int]] = defaultdict(_empty_type_counts)
    user_map: dict[int, dict[str, int]] = defaultdict(_empty_type_counts)
    totals_by_type = _empty_type_counts()

    def bump(user_id: Optional[int], event_type: str, when: datetime.datetime):
        if not user_id:
            return
        if target_user_id is not None and user_id != target_user_id:
            return
        if event_type not in totals_by_type:
            return
        day = when.strftime("%Y-%m-%d")
        timeline_map[day][event_type] += 1
        user_map[user_id][event_type] += 1
        totals_by_type[event_type] += 1

    secret_q = db.query(SecretRevealAudit).filter(SecretRevealAudit.revealed_at >= cutoff)
    curl_q = db.query(CurlCommandAudit).filter(CurlCommandAudit.executed_at >= cutoff)
    log_q = db.query(ProcessLogAudit).filter(ProcessLogAudit.viewed_at >= cutoff)
    env_edit_q = db.query(EnvEditAudit).filter(EnvEditAudit.created_at >= cutoff)
    build_q = db.query(BuildRunAudit).filter(BuildRunAudit.started_at >= cutoff)

    if target_user_id is not None:
        secret_q = secret_q.filter(SecretRevealAudit.user_id == target_user_id)
        curl_q = curl_q.filter(CurlCommandAudit.user_id == target_user_id)
        log_q = log_q.filter(ProcessLogAudit.user_id == target_user_id)
        env_edit_q = env_edit_q.filter(EnvEditAudit.user_id == target_user_id)
        build_q = build_q.filter(BuildRunAudit.user_id == target_user_id)

    for row in secret_q.all():
        bump(row.user_id, "secret_reveal", row.revealed_at)
    for row in curl_q.all():
        bump(row.user_id, "curl_command", row.executed_at)
    for row in log_q.all():
        bump(row.user_id, "log_view", row.viewed_at)
    for row in env_edit_q.all():
        bump(row.user_id, "env_edit", row.created_at)
    for row in build_q.all():
        bump(row.user_id, "build_run", row.started_at)

    start = datetime.datetime.utcnow().date() - datetime.timedelta(days=days - 1)
    timeline: List[ActivityStatsDay] = []
    for i in range(days):
        day = (start + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        counts = dict(timeline_map[day])
        total = sum(counts.values())
        timeline.append(ActivityStatsDay(date=day, counts=counts, total=total))

    by_user: List[ActivityStatsUser] = []
    if is_admin and not username_filter:
        for uid, counts in user_map.items():
            user = users_by_id.get(uid)
            if not user:
                continue
            total = sum(counts.values())
            if total == 0:
                continue
            by_user.append(ActivityStatsUser(
                username=user.username,
                role=_role_value(user.role),
                counts=dict(counts),
                total=total,
            ))
        by_user.sort(key=lambda u: u.total, reverse=True)

    available_users = sorted(u.username for u in users if u.is_active)
    total_actions = sum(totals_by_type.values())

    return ActivityStatsResponse(
        days=days,
        username_filter=username_filter,
        viewing_as_admin=is_admin,
        total_actions=total_actions,
        totals_by_type=totals_by_type,
        timeline=timeline,
        by_user=by_user,
        available_users=available_users if is_admin else [],
    )
