"""
Admin-only browser for repo directories and their .env files, on the
BACKEND's own host (not a remote SSH target). Safety measures:

  1. Only ever lists/reads inside settings.REPOS_BASE_DIR - repo names are
     validated to contain no path separators or ".." before being joined,
     and the resulting real path is re-checked to still be inside the base
     directory (defends against symlink or encoding tricks).
  2. Only a fixed, small set of candidate .env file locations per repo are
     ever read (repo/.env, repo/backend/.env, repo/frontend/.env) - never
     an arbitrary client-supplied path.
  3. Listing endpoint never returns sensitive values in bulk - only key
     names + a redacted placeholder. A separate reveal endpoint returns
     ONE actual value at a time, and every reveal is written to an audit
     table (who revealed what, when).
"""
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.auth import require_admin
from app.models import User, SecretRevealAudit
from app.schemas import RepoOut, EnvFileOut, EnvKeyOut, RevealRequest, RevealResponse

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()

SENSITIVE_KEYWORDS = (
    "PASSWORD", "SECRET", "TOKEN", "KEY", "PWD", "CREDENTIAL", "PRIVATE", "APIKEY"
)

CANDIDATE_ENV_PATHS = [".env", "backend/.env", "frontend/.env"]


def _is_sensitive(key: str) -> bool:
    upper = key.upper()
    return any(kw in upper for kw in SENSITIVE_KEYWORDS)


def _parse_env_file(path: str) -> List[tuple]:
    pairs = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
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
    except OSError:
        pass
    return pairs


def _resolve_repo_dir(repo_name: str) -> str:
    base = os.path.realpath(settings.REPOS_BASE_DIR)
    if not repo_name or "/" in repo_name or "\\" in repo_name or repo_name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid repo name")

    candidate = os.path.realpath(os.path.join(base, repo_name))
    if not (candidate == base or candidate.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid repo path")
    if not os.path.isdir(candidate):
        raise HTTPException(status_code=404, detail="Repo not found")
    return candidate


def _candidate_paths_for_repo(repo_dir: str) -> List[str]:
    existing = []
    for rel in CANDIDATE_ENV_PATHS:
        full = os.path.realpath(os.path.join(repo_dir, rel))
        if full.startswith(repo_dir + os.sep) or full == repo_dir:
            if os.path.isfile(full):
                existing.append(full)
    return existing


@router.get("/repos", response_model=List[RepoOut])
def list_repos(_admin: User = Depends(require_admin)):
    base = settings.REPOS_BASE_DIR
    if not os.path.isdir(base):
        raise HTTPException(status_code=404, detail=f"REPOS_BASE_DIR '{base}' does not exist on the server")

    entries = []
    for name in sorted(os.listdir(base)):
        full = os.path.join(base, name)
        if os.path.isdir(full) and not name.startswith("."):
            entries.append(RepoOut(name=name))
    return entries


@router.get("/repos/{repo_name}/env", response_model=List[EnvFileOut])
def get_repo_env(repo_name: str, _admin: User = Depends(require_admin)):
    repo_dir = _resolve_repo_dir(repo_name)
    files = _candidate_paths_for_repo(repo_dir)

    result = []
    for file_path in files:
        pairs = _parse_env_file(file_path)
        keys = [
            EnvKeyOut(
                key=k,
                is_sensitive=_is_sensitive(k),
                value=None if _is_sensitive(k) else v,
            )
            for k, v in pairs
        ]
        rel_path = os.path.relpath(file_path, repo_dir)
        result.append(EnvFileOut(file_path=rel_path, keys=keys))
    return result


@router.post("/repos/{repo_name}/env/reveal", response_model=RevealResponse)
def reveal_env_value(
    repo_name: str,
    payload: RevealRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    repo_dir = _resolve_repo_dir(repo_name)
    allowed_files = _candidate_paths_for_repo(repo_dir)
    allowed_rel_paths = {os.path.relpath(f, repo_dir): f for f in allowed_files}

    if payload.file_path not in allowed_rel_paths:
        raise HTTPException(status_code=400, detail="Unknown or disallowed env file")

    full_path = allowed_rel_paths[payload.file_path]
    pairs = dict(_parse_env_file(full_path))
    if payload.key not in pairs:
        raise HTTPException(status_code=404, detail="Key not found in this file")

    db.add(
        SecretRevealAudit(
            repo_name=repo_name,
            env_file_path=payload.file_path,
            key_name=payload.key,
            user_id=admin.id,
        )
    )
    db.commit()

    return RevealResponse(key=payload.key, value=pairs[payload.key])
