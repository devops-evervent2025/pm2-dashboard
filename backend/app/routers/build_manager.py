"""
Repo-wise Build Manager. Two ways to trigger a build:

1. From Repos & Env-style navigation (scan_path_id + repo_name) - the
   original flow, see websocket_build().
2. Directly from a running PM2 process card (server_id + process_name) -
   the newer, more precise flow, see websocket_build_by_process(). This
   reads the process's own `cwd` straight from `pm2 jlist` (no fuzzy
   name matching needed to find the path OR to know what to restart
   afterwards, since we already know exactly which process we started
   from).

Branch handling in both flows: the branch is derived from the folder
layout itself (".../frontend/Development/app_dir" -> branch
"Development"), never from whatever happens to be checked out.

Safety (both flows):
  - If git fetch/checkout/pull/npm i/npm run build exits non-zero for
    ANY reason, the run stops there and PM2 is never touched.
  - Admin/developer only.
  - Every run (who, what, branch, build result, restart result) is
    written to build_run_audit, win or lose.
"""
import shlex
import asyncio
import os
import queue
import shlex
import threading
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.auth import require_admin_or_dev, get_user_from_token_str
from app.models import User, Server, RepoScanPath, RoleEnum
from app.build_run_models import BuildRunAudit
from app.deploy_target_models import DeployTargetCache
from app.routers.remote_repos import RepoCacheEntry
from app.ssh_manager import stream_build, list_pm2_processes, pm2_action, run_command, SSHConnectionError

router = APIRouter(prefix="/build-manager", tags=["build-manager"])


def _repo_exists_in_cache(db: Session, scan_path_id: int, repo_name: str) -> bool:
    return (
        db.query(RepoCacheEntry)
        .filter(RepoCacheEntry.scan_path_id == scan_path_id, RepoCacheEntry.repo_name == repo_name)
        .first()
        is not None
    )


def _branch_from_base_path(base_path: str) -> str:
    return base_path.rstrip("/").split("/")[-1]


def _branch_from_full_path(full_path: str) -> str:
    """.../backend/Development/integrations-node -> 'Development' (the
    parent folder of the repo's own directory)."""
    parts = full_path.rstrip("/").split("/")
    return parts[-2] if len(parts) >= 2 else ""


def _snapshot_server(server: Server) -> SimpleNamespace:
    return SimpleNamespace(
        id=server.id,
        ip_address=server.ip_address,
        ssh_port=server.ssh_port,
        ssh_username=server.ssh_username,
        ssh_password=server.ssh_password,
        ssh_private_key_path=server.ssh_private_key_path,
        pm2_path=getattr(server, "pm2_path", None),
    )


def _producer_thread(server, full_path, branch_name, q, stop_event):
    try:
        for line in stream_build(server, full_path, branch_name):
            if stop_event.is_set():
                break
            if line is None:
                time.sleep(0.2)
                continue
            q.put(line)
    except SSHConnectionError as exc:
        q.put(f"__ERROR__:{exc}")
    except Exception as exc:  # noqa: BLE001
        q.put(f"__ERROR__:Unexpected error: {exc}")
    finally:
        q.put(None)


async def _run_build_stream(websocket: WebSocket, server_snapshot, full_path, branch_name, audit_id):
    """Shared streaming + post-build PM2 decision logic for both entry
    points. restart_process_name: if given (the by-process flow), that
    EXACT process is restarted on success - no matching needed. If None
    (the by-repo flow), falls back to fuzzy name matching against
    pm2 jlist, same as before."""
    log_queue: "queue.Queue" = queue.Queue()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_producer_thread, args=(server_snapshot, full_path, branch_name, log_queue, stop_event), daemon=True
    )
    thread.start()

    build_exit_code: Optional[int] = None
    try:
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, log_queue.get, True, 1.0)
            except queue.Empty:
                await websocket.send_text("__PING__")
                continue
            if line is None:
                break
            if line.startswith("__EXIT__:"):
                try:
                    build_exit_code = int(line.split(":", 1)[1])
                except ValueError:
                    build_exit_code = -1
                continue
            await websocket.send_text(line)
    except WebSocketDisconnect:
        stop_event.set()
        return None
    finally:
        stop_event.set()

    return build_exit_code


@router.websocket("/ws/{scan_path_id}/{repo_name}")
async def websocket_build(websocket: WebSocket, scan_path_id: int, repo_name: str, token: str = Query(...)):
    await websocket.accept()

    db: Session = SessionLocal()
    server_snapshot = None
    full_path = None
    branch_name = None
    audit_id = None
    try:
        user = get_user_from_token_str(token, db)
        if not user:
            await websocket.send_text("__ERROR__: Invalid or expired token")
            await websocket.close(code=4401)
            return
        if user.role not in (RoleEnum.admin, RoleEnum.developer):
            await websocket.send_text("__ERROR__: Only admin or developer roles can run builds")
            await websocket.close(code=4403)
            return
        if not repo_name or "/" in repo_name or "\\" in repo_name or repo_name in (".", ".."):
            await websocket.send_text("__ERROR__: Invalid repo name")
            await websocket.close(code=4400)
            return

        sp = db.query(RepoScanPath).filter(RepoScanPath.id == scan_path_id).first()
        if not sp:
            await websocket.send_text("__ERROR__: Scan path not found")
            await websocket.close(code=4404)
            return
        if not _repo_exists_in_cache(db, scan_path_id, repo_name):
            await websocket.send_text(
                "__ERROR__: This repo isn't in the scanned cache for this path - "
                "run 'Scan all repos now' on Repos & Env first."
            )
            await websocket.close(code=4404)
            return

        server = db.query(Server).filter(Server.id == sp.server_id).first()
        if not server:
            await websocket.send_text("__ERROR__: Server not found")
            await websocket.close(code=4404)
            return

        server_snapshot = _snapshot_server(server)
        full_path = f"{sp.base_path}/{repo_name}"
        branch_name = _branch_from_base_path(sp.base_path)

        audit = BuildRunAudit(
            scan_path_id=scan_path_id, repo_name=repo_name, server_id=server.id,
            user_id=user.id, git_branch=branch_name, started_at=datetime.datetime.utcnow(),
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        audit_id = audit.id
    finally:
        db.close()

    build_exit_code = await _run_build_stream(websocket, server_snapshot, full_path, branch_name, audit_id)
    if build_exit_code is None:
        return  # client disconnected mid-stream

    await _finish_build(websocket, server_snapshot, audit_id, build_exit_code, repo_name=repo_name, restart_process_name=None)


@router.websocket("/ws-by-process/{server_id}/{process_name}")
async def websocket_build_by_process(websocket: WebSocket, server_id: int, process_name: str, token: str = Query(...)):
    """Triggered directly from a PM2 process card. Reads the process's
    own `cwd` from `pm2 jlist` to know exactly what to build, and
    restarts that exact process (not a name match) on success."""
    await websocket.accept()

    db: Session = SessionLocal()
    server_snapshot = None
    full_path = None
    branch_name = None
    audit_id = None
    try:
        user = get_user_from_token_str(token, db)
        if not user:
            await websocket.send_text("__ERROR__: Invalid or expired token")
            await websocket.close(code=4401)
            return
        if user.role not in (RoleEnum.admin, RoleEnum.developer):
            await websocket.send_text("__ERROR__: Only admin or developer roles can run builds")
            await websocket.close(code=4403)
            return

        server = db.query(Server).filter(Server.id == server_id).first()
        if not server:
            await websocket.send_text("__ERROR__: Server not found")
            await websocket.close(code=4404)
            return
        server_snapshot = _snapshot_server(server)

        try:
            processes = list_pm2_processes(server_snapshot)
        except SSHConnectionError as exc:
            await websocket.send_text(f"__ERROR__: Could not reach pm2 list: {exc}")
            await websocket.close(code=4502)
            return

        proc = next((p for p in processes if p.get("name") == process_name), None)
        if not proc:
            await websocket.send_text(f"__ERROR__: No running pm2 process named '{process_name}' found on this server")
            await websocket.close(code=4404)
            return

        cwd = proc.get("cwd")
        if not cwd:
            await websocket.send_text(
                "__ERROR__: pm2 didn't report a working directory for this process "
                "(older pm2 version, or it was started unusually) - can't determine the repo path."
            )
            await websocket.close(code=4400)
            return

        full_path = cwd
        branch_name = _branch_from_full_path(cwd)

        audit = BuildRunAudit(
            scan_path_id=None, repo_name=process_name, server_id=server.id,
            user_id=user.id, git_branch=branch_name, started_at=datetime.datetime.utcnow(),
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        audit_id = audit.id
    finally:
        db.close()

    build_exit_code = await _run_build_stream(websocket, server_snapshot, full_path, branch_name, audit_id)
    if build_exit_code is None:
        return

    await _finish_build(websocket, server_snapshot, audit_id, build_exit_code, repo_name=process_name, restart_process_name=process_name)


async def _finish_build(websocket, server_snapshot, audit_id, build_exit_code, repo_name, restart_process_name):
    db = SessionLocal()
    try:
        audit = db.query(BuildRunAudit).filter(BuildRunAudit.id == audit_id).first() if audit_id else None
        if audit:
            audit.finished_at = datetime.datetime.utcnow()
            audit.build_succeeded = (build_exit_code == 0)

        if build_exit_code != 0:
            msg = f"__ERROR__: Build failed (exit code {build_exit_code}) - PM2 was NOT restarted."
            await websocket.send_text(msg)
            if audit:
                audit.note = msg
                db.commit()
            await websocket.send_text("__STREAM_CLOSED__")
            return

        await websocket.send_text("--- build finished, checking pm2 list ---")

        if restart_process_name:
            # Exact match already known - no fuzzy matching needed.
            await websocket.send_text(f"--- restarting pm2 process: {restart_process_name} ---")
            try:
                output = pm2_action(server_snapshot, restart_process_name, "restart")
                await websocket.send_text(output or f"{restart_process_name} restarted.")
                if audit:
                    audit.pm2_process_matched = restart_process_name
                    audit.pm2_restarted = True
                    db.commit()
            except SSHConnectionError as exc:
                msg = f"__ERROR__: Build succeeded but restart failed: {exc}"
                await websocket.send_text(msg)
                if audit:
                    audit.pm2_process_matched = restart_process_name
                    audit.note = msg
                    db.commit()
            await websocket.send_text("__STREAM_CLOSED__")
            return

        # Fuzzy-match fallback for the by-repo flow.
        try:
            processes = list_pm2_processes(server_snapshot)
        except SSHConnectionError as exc:
            msg = f"__ERROR__: Build succeeded, but could not reach pm2 list: {exc}"
            await websocket.send_text(msg)
            if audit:
                audit.note = msg
                db.commit()
            await websocket.send_text("__STREAM_CLOSED__")
            return

        repo_lower = repo_name.lower()
        matches = [
            p for p in processes
            if p.get("name") and (repo_lower in p["name"].lower() or p["name"].lower() in repo_lower)
        ]

        if len(matches) == 0:
            msg = "No pm2 process name matched this repo - build completed, nothing was restarted."
            await websocket.send_text(msg)
            if audit:
                audit.note = msg
                db.commit()
        elif len(matches) > 1:
            names = ", ".join(p["name"] for p in matches)
            msg = f"Multiple pm2 processes matched ({names}) - nothing restarted to avoid restarting the wrong one."
            await websocket.send_text(msg)
            if audit:
                audit.note = msg
                db.commit()
        else:
            proc_name = matches[0]["name"]
            await websocket.send_text(f"--- restarting pm2 process: {proc_name} ---")
            try:
                output = pm2_action(server_snapshot, proc_name, "restart")
                await websocket.send_text(output or f"{proc_name} restarted.")
                if audit:
                    audit.pm2_process_matched = proc_name
                    audit.pm2_restarted = True
                    db.commit()
            except SSHConnectionError as exc:
                msg = f"__ERROR__: Build succeeded but restart failed: {exc}"
                await websocket.send_text(msg)
                if audit:
                    audit.pm2_process_matched = proc_name
                    audit.note = msg
                    db.commit()
    finally:
        db.close()
        await websocket.send_text("__STREAM_CLOSED__")


def _git_repo_names_batch(server, base_path: str, folders) -> dict:
    """ONE SSH command that loops through every folder and prints
    "folder<TAB>origin-url" for each - replaces what used to be a
    separate SSH connection per folder (the main cause of slow scans
    when a server has many repos)."""
    if not folders:
        return {}
    parts = []
    for f in folders:
        full = f"{base_path.rstrip('/')}/{f}"
        parts.append(
            f"printf '%s\\t' {shlex.quote(f)}; "
            f"git -C {shlex.quote(full)} remote get-url origin 2>/dev/null || true; "
            f"printf '\\n'"
        )
    script = " ".join(parts)
    try:
        output = run_command(server, script, timeout=45)
    except SSHConnectionError:
        return {}

    result = {}
    for line in output.splitlines():
        if "\t" not in line:
            continue
        folder, url = line.split("\t", 1)
        url = url.strip()
        if not url:
            continue
        if url.endswith(".git"):
            url = url[:-4]
        name = url.rstrip("/").split("/")[-1].split(":")[-1]
        if name:
            result[folder] = name
    return result


def _scan_one_target(sp, server_snapshot):
    """Pure network work for ONE scan path - no DB writes here, so this
    is safe to run concurrently across many servers at once. Returns
    (scan_path_id, environment, list_of_row_dicts, error_or_None)."""
    environment = _branch_from_base_path(sp.base_path)
    try:
        processes = list_pm2_processes(server_snapshot)
    except SSHConnectionError as exc:
        return sp.id, environment, [], str(exc)

    prefix = sp.base_path.rstrip("/") + "/"
    folder_procs: dict = {}
    for proc in processes:
        cwd = proc.get("cwd")
        if not cwd or not cwd.startswith(prefix):
            continue
        folder = cwd[len(prefix):].split("/")[0]
        if folder:
            folder_procs.setdefault(folder, []).append(proc)

    repo_names = _git_repo_names_batch(server_snapshot, sp.base_path, list(folder_procs.keys()))

    now = datetime.datetime.utcnow()
    rows = []
    for folder, procs in folder_procs.items():
        full_path = f"{sp.base_path.rstrip('/')}/{folder}"
        repo_name = repo_names.get(folder) or folder
        for proc in procs:
            rows.append({
                "repo_name": repo_name, "folder_name": folder, "full_path": full_path,
                "pm2_process_name": proc.get("name"), "pm2_status": proc.get("status"),
                "last_scanned_at": now,
            })
    return sp.id, environment, rows, None


_deploy_scan_status = {
    "running": False, "started_at": None, "finished_at": None,
    "scanned": 0, "total": 0, "error": None,
}
_deploy_scan_lock = threading.Lock()

DEPLOY_SCAN_INTERVAL_SECONDS = int(os.environ.get("DEPLOY_SCAN_INTERVAL_SECONDS", 2 * 60 * 60))  # 2h default
DEPLOY_SCAN_MAX_WORKERS = int(os.environ.get("DEPLOY_SCAN_MAX_WORKERS", 8))


def _run_deploy_scan():
    """Discovery (SSH/pm2/git - the slow part) runs in parallel across
    servers via a thread pool. DB writes happen serially afterwards in
    the main thread/session, since SQLAlchemy sessions aren't safe to
    share across threads. This is what makes the scan itself much
    faster with many servers - previously every server, and every repo
    within it, was done one at a time."""
    db = SessionLocal()
    try:
        scan_paths = db.query(RepoScanPath).all()
        _deploy_scan_status["total"] = len(scan_paths)
        _deploy_scan_status["scanned"] = 0

        targets = []
        for sp in scan_paths:
            server = db.query(Server).filter(Server.id == sp.server_id).first()
            if server:
                targets.append((sp, _snapshot_server(server)))
            else:
                db.query(DeployTargetCache).filter(DeployTargetCache.scan_path_id == sp.id).delete()
                _deploy_scan_status["scanned"] += 1
        db.commit()

        with ThreadPoolExecutor(max_workers=DEPLOY_SCAN_MAX_WORKERS) as pool:
            futures = {pool.submit(_scan_one_target, sp, snap): sp for sp, snap in targets}
            for future in as_completed(futures):
                sp = futures[future]
                try:
                    sp_id, environment, rows, err = future.result()
                except Exception as exc:  # noqa: BLE001
                    sp_id, rows, err = sp.id, [], str(exc)

                db.query(DeployTargetCache).filter(DeployTargetCache.scan_path_id == sp_id).delete()
                if not err:
                    for row in rows:
                        db.add(DeployTargetCache(
                            scan_path_id=sp_id, server_id=sp.server_id, environment=_branch_from_base_path(sp.base_path),
                            repo_name=row["repo_name"], folder_name=row["folder_name"], full_path=row["full_path"],
                            pm2_process_name=row["pm2_process_name"], pm2_status=row["pm2_status"],
                            last_scanned_at=row["last_scanned_at"],
                        ))
                db.commit()
                _deploy_scan_status["scanned"] += 1
    except Exception as exc:  # noqa: BLE001
        _deploy_scan_status["error"] = str(exc)
    finally:
        db.close()
        _deploy_scan_status["running"] = False
        _deploy_scan_status["finished_at"] = datetime.datetime.utcnow().isoformat()


@router.post("/scan-deploy-targets")
def scan_deploy_targets(_admin: User = Depends(require_admin_or_dev)):
    with _deploy_scan_lock:
        if _deploy_scan_status["running"]:
            raise HTTPException(status_code=409, detail="A scan is already running.")
        _deploy_scan_status["running"] = True
        _deploy_scan_status["started_at"] = datetime.datetime.utcnow().isoformat()
        _deploy_scan_status["finished_at"] = None
        _deploy_scan_status["error"] = None

    thread = threading.Thread(target=_run_deploy_scan, daemon=True)
    thread.start()
    return {"detail": "Scan started in the background.", "status": _deploy_scan_status}


@router.get("/scan-deploy-targets/status")
def deploy_scan_status(_user: User = Depends(require_admin_or_dev)):
    return _deploy_scan_status


def _run_deploy_scan_scheduler():
    # Fire one scan shortly after startup, then every DEPLOY_SCAN_INTERVAL_SECONDS.
    time.sleep(30)
    while True:
        with _deploy_scan_lock:
            if not _deploy_scan_status["running"]:
                _deploy_scan_status["running"] = True
                _deploy_scan_status["started_at"] = datetime.datetime.utcnow().isoformat()
                _deploy_scan_status["finished_at"] = None
                _deploy_scan_status["error"] = None
        _run_deploy_scan()
        time.sleep(DEPLOY_SCAN_INTERVAL_SECONDS)


def start_deploy_scan_scheduler():
    thread = threading.Thread(target=_run_deploy_scan_scheduler, daemon=True)
    thread.start()


@router.get("/environments")
def list_available_environments(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),
):
    """Reads from the cache table only - instant, no SSH."""
    rows = db.query(DeployTargetCache.environment).distinct().all()
    return sorted({r[0] for r in rows})


@router.get("/environments/{environment}/repos")
def list_repos_for_environment(
    environment: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),
):
    rows = (
        db.query(DeployTargetCache.repo_name)
        .filter(DeployTargetCache.environment == environment)
        .distinct()
        .order_by(DeployTargetCache.repo_name.asc())
        .all()
    )
    return [r[0] for r in rows]


@router.get("/environments/{environment}/repos/{repo_name}/servers")
def list_servers_for_repo(
    environment: str,
    repo_name: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),
):
    rows = (
        db.query(DeployTargetCache)
        .filter(DeployTargetCache.environment == environment, DeployTargetCache.repo_name == repo_name)
        .all()
    )
    server_ids = {r.server_id for r in rows}
    servers = {s.id: s for s in db.query(Server).filter(Server.id.in_(server_ids)).all()} if server_ids else {}
    return [
        {
            "scan_path_id": r.scan_path_id,
            "server_id": r.server_id,
            "server_name": servers[r.server_id].name if r.server_id in servers else None,
            "process_name": r.pm2_process_name,
            "status": r.pm2_status,
            "cwd": r.full_path,
            "branch": r.environment,
            "last_scanned_at": r.last_scanned_at,
        }
        for r in rows
    ]


@router.get("/history")
def build_history(
    limit: int = 100,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin_or_dev),
):
    rows = db.query(BuildRunAudit).order_by(BuildRunAudit.started_at.desc()).limit(limit).all()
    users_by_id = {u.id: u.username for u in db.query(User).all()}
    servers_by_id = {s.id: s.name for s in db.query(Server).all()}
    return [
        {
            "id": r.id, "repo_name": r.repo_name, "server_name": servers_by_id.get(r.server_id),
            "username": users_by_id.get(r.user_id), "git_branch": r.git_branch,
            "build_succeeded": r.build_succeeded, "pm2_process_matched": r.pm2_process_matched,
            "pm2_restarted": r.pm2_restarted, "started_at": r.started_at, "finished_at": r.finished_at,
            "note": r.note,
        }
        for r in rows
    ]
