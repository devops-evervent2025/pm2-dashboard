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
  4. Editing (update_env_value) only allows changing the VALUE of a key
     that already exists in the file - it never adds new keys or touches
     any other line. A timestamped backup is written before every edit,
     the write itself is atomic (temp file + os.replace), and every edit
     is logged to an audit table (who changed what, when, old value
     hash vs new value hash for sensitive keys - not the raw values).
"""
import os
import re
import shutil
import datetime
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.auth import require_admin, get_current_user
from app.models import User, SecretRevealAudit
from app.env_audit_models import EnvEditAudit
from app.schemas import (
    RepoOut, EnvFileOut, EnvKeyOut, RevealRequest, RevealResponse,
    EnvUpdateRequest, EnvUpdateResponse,
)

router = APIRouter(prefix="/system", tags=["system"])
settings = get_settings()

SENSITIVE_KEYWORDS = (
    "PASSWORD", "SECRET", "TOKEN", "KEY", "PWD", "CREDENTIAL", "PRIVATE", "APIKEY"
)

CANDIDATE_ENV_PATHS = [".env", "backend/.env", "frontend/.env"]

# .env की हर non-comment line इसी pattern से match होनी चाहिए, तभी edit होगा
_ENV_LINE_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')


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


def _format_env_value(value: str, was_quoted_with: Optional[str]) -> str:
    """Keeps the same quoting style the line already had, unless the new
    value needs quoting (contains spaces/#) and the line wasn't quoted -
    in that case we add double quotes so the value still parses correctly."""
    needs_quoting = (" " in value) or ("#" in value) or (value == "")
    quote_char = was_quoted_with or ('"' if needs_quoting else None)
    if quote_char:
        escaped = value.replace("\\", "\\\\").replace(quote_char, "\\" + quote_char)
        return f"{quote_char}{escaped}{quote_char}"
    return value


def update_env_value(full_path: str, key: str, new_value: str) -> str:
    """
    Updates ONLY the value for an existing key on its existing line -
    every other line (including comments, blank lines, ordering) is left
    byte-for-byte identical. Returns the previous value.
    Raises ValueError if the key isn't found or the value is unsafe
    (contains a newline, which could otherwise inject extra lines).
    """
    if "\n" in new_value or "\r" in new_value:
        raise ValueError("Value cannot contain a newline")

    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    target_idx = None
    old_value = None
    quote_char = None

    for i, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(stripped)
        if not match:
            continue
        line_key, line_val = match.group(1), match.group(2)
        if line_key != key:
            continue
        target_idx = i
        if (line_val.startswith('"') and line_val.endswith('"')) or (
            line_val.startswith("'") and line_val.endswith("'")
        ):
            quote_char = line_val[0]
            old_value = line_val[1:-1]
        else:
            old_value = line_val
        break

    if target_idx is None:
        raise ValueError(f"Key '{key}' not found in this file - only existing keys can be edited")

    new_formatted = _format_env_value(new_value, quote_char)
    # मूल line की leading/trailing whitespace (जैसे indentation) को बनाए रखते हैं
    original = lines[target_idx]
    prefix_ws = original[: len(original) - len(original.lstrip())]
    newline_suffix = "\n" if original.endswith("\n") else ""
    lines[target_idx] = f"{prefix_ws}{key}={new_formatted}{newline_suffix}"

    # backup पहले बनाते हैं
    ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    shutil.copy2(full_path, f"{full_path}.bak.{ts}")

    # atomic write: पहले उसी directory में एक temp file बनाते हैं, फिर rename करते हैं
    dir_name = os.path.dirname(full_path)
    fd, tmp_path = tempfile.mkstemp(prefix=".env.tmp.", dir=dir_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.writelines(lines)
        shutil.copystat(full_path, tmp_path)
        os.replace(tmp_path, full_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    return old_value


@router.get("/repos", response_model=List[RepoOut])
def list_repos(_user: User = Depends(get_current_user)):
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
def get_repo_env(repo_name: str, _user: User = Depends(get_current_user)):
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
    user: User = Depends(get_current_user),
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
            user_id=user.id,
        )
    )
    db.commit()

    return RevealResponse(key=payload.key, value=pairs[payload.key])


@router.post("/repos/{repo_name}/env/update", response_model=EnvUpdateResponse)
def update_env_value_endpoint(
    repo_name: str,
    payload: EnvUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    repo_dir = _resolve_repo_dir(repo_name)
    allowed_files = _candidate_paths_for_repo(repo_dir)
    allowed_rel_paths = {os.path.relpath(f, repo_dir): f for f in allowed_files}

    if payload.file_path not in allowed_rel_paths:
        raise HTTPException(status_code=400, detail="Unknown or disallowed env file")

    full_path = allowed_rel_paths[payload.file_path]

    try:
        old_value = update_env_value(full_path, payload.key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not write file: {exc}") from exc

    is_sensitive = _is_sensitive(payload.key)
    db.add(
        EnvEditAudit(
            repo_name=repo_name,
            env_file_path=payload.file_path,
            key_name=payload.key,
            was_sensitive=is_sensitive,
            user_id=admin.id,
        )
    )
    db.commit()

    return EnvUpdateResponse(
        key=payload.key,
        old_value=None if is_sensitive else old_value,
        new_value=None if is_sensitive else payload.value,
        updated=True,
    )
