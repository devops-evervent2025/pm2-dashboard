path = "/var/www/fullstack/pm2-dashboard/backend/app/routers/remote_repos.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

old_imports = "import os\nimport re\nimport shlex\nimport datetime"
new_imports = "import os\nimport re\nimport shlex\nimport datetime\nimport threading"
if old_imports in content:
    content = content.replace(old_imports, new_imports)
    changes.append("threading import added")
else:
    print("MISSING: imports line")

old_scan_all = '''@router.post("/scan-all")
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
    scan_paths = db.query(RepoScanPath).all()'''

new_scan_all = '''# In-memory status for the background scan - simple and sufficient since
# only one scan runs at a time (guarded below) and this doesn't need to
# survive a backend restart.
_scan_status = {"running": False, "started_at": None, "finished_at": None, "scanned": 0, "total": 0, "error": None}
_scan_lock = threading.Lock()


def _run_scan_all_background():
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        scan_paths = db.query(RepoScanPath).all()
        _scan_status["total"] = len(scan_paths)
        _scan_status["scanned"] = 0

        for sp in scan_paths:
            server = db.query(Server).filter(Server.id == sp.server_id).first()
            if not server:
                _scan_status["scanned"] += 1
                continue

            try:
                find_cmd = (
                    f"find {shlex.quote(sp.base_path)} -mindepth 1 -maxdepth 1 "
                    f"-type d -printf '%f\\\\n' 2>/dev/null"
                )
                output = run_command(server, find_cmd)
            except SSHConnectionError:
                _scan_status["scanned"] += 1
                continue

            repo_names = sorted(line.strip() for line in output.splitlines() if line.strip())

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
            _scan_status["scanned"] += 1
    except Exception as exc:
        _scan_status["error"] = str(exc)
    finally:
        db.close()
        _scan_status["running"] = False
        _scan_status["finished_at"] = datetime.datetime.utcnow().isoformat()


@router.post("/scan-all")
def scan_all_remote_repos(_admin: User = Depends(require_admin)):
    """
    Kicks off the scan in a background thread and returns immediately -
    this avoids the request timing out against nginx's default proxy
    timeout when there are many scan paths (each one is a live SSH
    round-trip). Poll GET /remote-repos/scan-all/status for progress.
    """
    with _scan_lock:
        if _scan_status["running"]:
            raise HTTPException(status_code=409, detail="A scan is already running.")
        _scan_status["running"] = True
        _scan_status["started_at"] = datetime.datetime.utcnow().isoformat()
        _scan_status["finished_at"] = None
        _scan_status["error"] = None
        _scan_status["scanned"] = 0
        _scan_status["total"] = 0

    thread = threading.Thread(target=_run_scan_all_background, daemon=True)
    thread.start()
    return {"detail": "Scan started in the background.", "status": _scan_status}


@router.get("/scan-all/status")
def scan_all_status(_user: User = Depends(get_current_user)):
    return _scan_status


def _unused_old_scan_all_body(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    results = []
    scan_paths = db.query(RepoScanPath).all()'''

if old_scan_all in content:
    content = content.replace(old_scan_all, new_scan_all)
    changes.append("scan-all converted to background + status endpoint added")
else:
    print("MISSING: old scan_all_remote_repos function")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
