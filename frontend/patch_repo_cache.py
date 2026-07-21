path = "/var/www/fullstack/pm2-dashboard/backend/app/routers/remote_repos.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add imports for DB models + datetime
old_imports = '''import os
import re
import shlex
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin, get_current_user
from app.models import User, Server, RepoScanPath, SecretRevealAudit'''

new_imports = '''import os
import re
import shlex
import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Session

from app.database import get_db, Base
from app.auth import require_admin, get_current_user
from app.models import User, Server, RepoScanPath, SecretRevealAudit'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("imports added")
else:
    print("MISSING: imports block")

# 2. Add cache table models right after the router line
old_router_line = 'router = APIRouter(prefix="/remote-repos", tags=["remote-repos"])'
new_router_line = '''router = APIRouter(prefix="/remote-repos", tags=["remote-repos"])


class RepoCacheEntry(Base):
    """One row per repo directory found under a scan path - refreshed by
    the admin-triggered scan-all endpoint. The UI reads from this table,
    never SSHes live on every page load (that's what was exhausting the
    DB connection pool under concurrent traffic)."""
    __tablename__ = "repo_cache"

    id = Column(Integer, primary_key=True, index=True)
    scan_path_id = Column(Integer, ForeignKey("repo_scan_paths.id"), nullable=False)
    repo_name = Column(String(255), nullable=False)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)


class RepoEnvCacheEntry(Base):
    """One row per env-file key found for a repo. Sensitive keys' VALUES
    are never stored here (value stays NULL for those) - only the key
    name and the is_sensitive flag. Actual sensitive values are still
    only ever fetched live, one at a time, via the reveal endpoint - this
    cache is purely for the list/browse view."""
    __tablename__ = "repo_env_cache"

    id = Column(Integer, primary_key=True, index=True)
    scan_path_id = Column(Integer, ForeignKey("repo_scan_paths.id"), nullable=False)
    repo_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    key_name = Column(String(255), nullable=False)
    is_sensitive = Column(Boolean, default=False)
    value = Column(Text, nullable=True)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)'''

if old_router_line in content:
    content = content.replace(old_router_line, new_router_line)
    changes.append("cache table models added")
else:
    print("MISSING: router line")

# 3. Replace GET .../repos to read from cache instead of live SSH
old_list_repos = '''@router.get("/scan-paths/{scan_path_id}/repos", response_model=List[RemoteRepoOut])
def list_remote_repos(
    scan_path_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    sp = _get_scan_path_or_404(scan_path_id, db)
    server = _get_server_or_404(sp.server_id, db)

    command = (
        f"find {shlex.quote(sp.base_path)} -mindepth 1 -maxdepth 1 "
        f"-type d -printf '%f\\\\n' 2>/dev/null"
    )
    try:
        output = run_command(server, command)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    names = sorted(line.strip() for line in output.splitlines() if line.strip())
    return [RemoteRepoOut(name=n) for n in names]'''

new_list_repos = '''@router.get("/scan-paths/{scan_path_id}/repos", response_model=List[RemoteRepoOut])
def list_remote_repos(
    scan_path_id: int, db: Session = Depends(get_db), _user: User = Depends(get_current_user)
):
    # Reads from the cache table - NEVER connects over SSH here. This is
    # what every page load/refresh hits, so it must stay a cheap DB read
    # regardless of how many users are on the page at once.
    _get_scan_path_or_404(scan_path_id, db)
    rows = (
        db.query(RepoCacheEntry)
        .filter(RepoCacheEntry.scan_path_id == scan_path_id)
        .order_by(RepoCacheEntry.repo_name.asc())
        .all()
    )
    return [RemoteRepoOut(name=r.repo_name) for r in rows]'''

if old_list_repos in content:
    content = content.replace(old_list_repos, new_list_repos)
    changes.append("list_remote_repos switched to DB read")
else:
    print("MISSING: list_remote_repos function")

# 4. Replace GET .../env to read from cache instead of live SSH
old_get_env = '''@router.get("/scan-paths/{scan_path_id}/repos/{repo_name}/env", response_model=List[EnvFileOut])
def get_remote_repo_env(
    scan_path_id: int,
    repo_name: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
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

    return result'''

new_get_env = '''@router.get("/scan-paths/{scan_path_id}/repos/{repo_name}/env", response_model=List[EnvFileOut])
def get_remote_repo_env(
    scan_path_id: int,
    repo_name: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    # Reads from the cache table - NEVER connects over SSH here.
    _validate_repo_name(repo_name)
    _get_scan_path_or_404(scan_path_id, db)

    rows = (
        db.query(RepoEnvCacheEntry)
        .filter(
            RepoEnvCacheEntry.scan_path_id == scan_path_id,
            RepoEnvCacheEntry.repo_name == repo_name,
        )
        .all()
    )

    by_file: dict = {}
    for r in rows:
        by_file.setdefault(r.file_path, []).append(
            EnvKeyOut(key=r.key_name, is_sensitive=r.is_sensitive, value=None if r.is_sensitive else r.value)
        )

    return [EnvFileOut(file_path=fp, keys=keys) for fp, keys in by_file.items()]'''

if old_get_env in content:
    content = content.replace(old_get_env, new_get_env)
    changes.append("get_remote_repo_env switched to DB read")
else:
    print("MISSING: get_remote_repo_env function")

# 5. Add the scan-all endpoint (does the actual SSH work, admin-triggered only), at end of file
scan_all_endpoint = '''


@router.post("/scan-all")
def scan_all_remote_repos(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """
    The ONLY place in this router that connects over SSH for listing
    purposes. Scans every configured scan-path, lists its repo
    directories, and for each repo reads the candidate .env files -
    storing key names (and non-sensitive values) in the cache tables.
    Sensitive values are NEVER stored - only their key name and a
    is_sensitive=True flag, so the reveal endpoint is still required to
    see them, same as before.
    """
    results = []
    scan_paths = db.query(RepoScanPath).all()

    for sp in scan_paths:
        server = db.query(Server).filter(Server.id == sp.server_id).first()
        if not server:
            continue

        try:
            find_cmd = (
                f"find {shlex.quote(sp.base_path)} -mindepth 1 -maxdepth 1 "
                f"-type d -printf '%f\\n' 2>/dev/null"
            )
            output = run_command(server, find_cmd)
        except SSHConnectionError as exc:
            results.append({"scan_path_id": sp.id, "server_name": server.name, "error": str(exc)})
            continue

        repo_names = sorted(line.strip() for line in output.splitlines() if line.strip())

        # Clear old cache for this scan path, then repopulate
        db.query(RepoCacheEntry).filter(RepoCacheEntry.scan_path_id == sp.id).delete()
        db.query(RepoEnvCacheEntry).filter(RepoEnvCacheEntry.scan_path_id == sp.id).delete()

        now = datetime.datetime.utcnow()
        for repo_name in repo_names:
            db.add(RepoCacheEntry(scan_path_id=sp.id, repo_name=repo_name, last_scanned_at=now))

            repo_dir = f"{sp.base_path}/{repo_name}"
            for rel in CANDIDATE_ENV_PATHS:
                full_path = f"{repo_dir}/{rel}"
                command = f"test -f {shlex.quote(full_path)} && cat {shlex.quote(full_path)} || true"
                try:
                    env_output = run_command(server, command)
                except SSHConnectionError:
                    continue
                if not env_output.strip():
                    continue
                pairs = _parse_env_text(env_output)
                for k, v in pairs:
                    sensitive = _is_sensitive(k)
                    db.add(RepoEnvCacheEntry(
                        scan_path_id=sp.id, repo_name=repo_name, file_path=rel,
                        key_name=k, is_sensitive=sensitive,
                        value=None if sensitive else v, last_scanned_at=now,
                    ))

        db.commit()
        results.append({"scan_path_id": sp.id, "server_name": server.name, "repos_found": len(repo_names)})

    return {"scanned": results}'''

if "scan_all_remote_repos" not in content:
    content = content.rstrip() + scan_all_endpoint + "\n"
    changes.append("scan-all endpoint added")
else:
    print("ALREADY present: scan-all endpoint")

if len(changes) == 5:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
