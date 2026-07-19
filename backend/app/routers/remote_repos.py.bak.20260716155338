"""
Admin-only browser for repo directories and their .env files on MANAGED
SERVERS (the ones already added under Clients -> Servers), accessed over
SSH using that server's own stored credentials - no new credentials needed.

Safety measures (mirrors app/routers/system.py's local-filesystem version):
  1. repo_name is validated to contain no path separators or ".." before
     being joined with the (admin-configured, trusted) base_path.
  2. Only a small fixed set of candidate .env locations are ever read per
     repo (.env, .env.local, backend/.env, frontend/.env).
  3. Listing never returns sensitive values in bulk - only key names +
     redacted placeholders. A separate reveal endpoint returns ONE value
     at a time and every reveal is written to an audit table.
  4. All remote commands go through ssh_manager.run_command(), which
     already wraps everything in a quoted login shell (bash -lc) - no
     raw string concatenation of untrusted input into a shell command.
"""
import shlex
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin
from app.models import User, Server, RepoScanPath, SecretRevealAudit
from app.schemas import (
    RepoScanPathCreate, RepoScanPathOut, RemoteRepoOut,
    EnvFileOut, EnvKeyOut, RevealRequest, RevealResponse,
)
from app.ssh_manager import run_command, SSHConnectionError

router = APIRouter(prefix="/remote-repos", tags=["remote-repos"])

SENSITIVE_KEYWORDS = (
    "PASSWORD", "SECRET", "TOKEN", "KEY", "PWD", "CREDENTIAL", "PRIVATE", "APIKEY"
)
CANDIDATE_ENV_PATHS = [".env", ".env.local", "backend/.env", "frontend/.env"]


def _is_sensitive(key: str) -> bool:
    upper = key.upper()
    return any(kw in upper for kw in SENSITIVE_KEYWORDS)


def _parse_env_text(text: str) -> List[tuple]:
    pairs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if key:
            pairs.append((key, value))
    return pairs


def _validate_repo_name(repo_name: str):
    if not repo_name or "/" in repo_name or "\\" in repo_name or repo_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid repo name")


def _get_scan_path_or_404(scan_path_id: int, db: Session) -> RepoScanPath:
    sp = db.query(RepoScanPath).filter(RepoScanPath.id == scan_path_id).first()
    if not sp:
        raise HTTPException(status_code=404, detail="Scan path not found")
    return sp


def _get_server_or_404(server_id: int, db: Session) -> Server:
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.get("/scan-paths", response_model=List[RepoScanPathOut])
def list_scan_paths(
    server_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    query = db.query(RepoScanPath)
    if server_id is not None:
        query = query.filter(RepoScanPath.server_id == server_id)
    scan_paths = query.all()

    result = []
    for sp in scan_paths:
        server = db.query(Server).filter(Server.id == sp.server_id).first()
        result.append(
            RepoScanPathOut(
                id=sp.id,
                server_id=sp.server_id,
                server_name=server.name if server else None,
                base_path=sp.base_path,
                label=sp.label,
            )
        )
    return result


@router.post("/scan-paths", response_model=RepoScanPathOut)
def create_scan_path(
    payload: RepoScanPathCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    server = _get_server_or_404(payload.server_id, db)
    sp = RepoScanPath(
        server_id=payload.server_id,
        base_path=payload.base_path.rstrip("/") or "/",
        label=payload.label,
        created_by=admin.id,
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return RepoScanPathOut(
        id=sp.id, server_id=sp.server_id, server_name=server.name,
        base_path=sp.base_path, label=sp.label,
    )


@router.delete("/scan-paths/{scan_path_id}")
def delete_scan_path(
    scan_path_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    sp = _get_scan_path_or_404(scan_path_id, db)
    db.delete(sp)
    db.commit()
    return {"detail": "Scan path deleted"}


@router.get("/scan-paths/{scan_path_id}/repos", response_model=List[RemoteRepoOut])
def list_remote_repos(
    scan_path_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    sp = _get_scan_path_or_404(scan_path_id, db)
    server = _get_server_or_404(sp.server_id, db)

    command = (
        f"find {shlex.quote(sp.base_path)} -mindepth 1 -maxdepth 1 "
        f"-type d -printf '%f\\n' 2>/dev/null"
    )
    try:
        output = run_command(server, command)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    names = sorted(line.strip() for line in output.splitlines() if line.strip())
    return [RemoteRepoOut(name=n) for n in names]


@router.get("/scan-paths/{scan_path_id}/repos/{repo_name}/env", response_model=List[EnvFileOut])
def get_remote_repo_env(
    scan_path_id: int,
    repo_name: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    _validate_repo_name(repo_name)
    sp = _get_scan_path_or_404(scan_path_id, db)
    server = _get_server_or_404(sp.server_id, db)

    repo_dir = f"{sp.base_path}/{repo_name}"
    result = []
    for rel in CANDIDATE_ENV_PATHS:
        full_path = f"{repo_dir}/{rel}"
        command = f"test -f {shlex.quote(full_path)} && cat {shlex.quote(full_path)} || true"
        try:
            output = run_command(server, command)
        except SSHConnectionError:
            continue

        if not output.strip():
            continue

        pairs = _parse_env_text(output)
        if not pairs:
            continue

        keys = [
            EnvKeyOut(key=k, is_sensitive=_is_sensitive(k), value=None if _is_sensitive(k) else v)
            for k, v in pairs
        ]
        result.append(EnvFileOut(file_path=rel, keys=keys))

    return result


@router.post("/scan-paths/{scan_path_id}/repos/{repo_name}/env/reveal", response_model=RevealResponse)
def reveal_remote_env_value(
    scan_path_id: int,
    repo_name: str,
    payload: RevealRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    _validate_repo_name(repo_name)
    if payload.file_path not in CANDIDATE_ENV_PATHS:
        raise HTTPException(status_code=400, detail="Unknown or disallowed env file")

    sp = _get_scan_path_or_404(scan_path_id, db)
    server = _get_server_or_404(sp.server_id, db)

    full_path = f"{sp.base_path}/{repo_name}/{payload.file_path}"
    command = f"test -f {shlex.quote(full_path)} && cat {shlex.quote(full_path)} || true"
    try:
        output = run_command(server, command)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    pairs = dict(_parse_env_text(output))
    if payload.key not in pairs:
        raise HTTPException(status_code=404, detail="Key not found in this file")

    db.add(
        SecretRevealAudit(
            repo_name=f"{server.name}:{repo_name}",
            env_file_path=payload.file_path,
            key_name=payload.key,
            user_id=admin.id,
            server_id=server.id,
        )
    )
    db.commit()

    return RevealResponse(key=payload.key, value=pairs[payload.key])
