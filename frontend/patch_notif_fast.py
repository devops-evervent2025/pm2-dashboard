path = "/var/www/fullstack/pm2-dashboard_dev/backend/app/routers/notifications.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

changes = []

# 1. Add ThreadPoolExecutor import
old_import = "import datetime\nimport time"
new_import = "import datetime\nimport time\nfrom concurrent.futures import ThreadPoolExecutor, as_completed"
if old_import in content:
    content = content.replace(old_import, new_import)
    changes.append("import added")
else:
    print("MISSING: import line")

# 2. Replace _collect_process_alerts with a parallel version that only flags "errored"
old_fn = '''def _collect_process_alerts(db: Session) -> List[ProcessNotification]:
    alerts: List[ProcessNotification] = []
    clients = {c.id: c.name for c in db.query(Client).all()}
    for server in db.query(Server).all():
        try:
            processes = list_pm2_processes(server)
        except SSHConnectionError:
            continue  # unreachable servers are already surfaced on the Alerts page
        for proc in processes:
            status = proc.get("status", "unknown")
            if status != "online":
                alerts.append(ProcessNotification(
                    client_id=server.client_id,
                    client_name=clients.get(server.client_id, "Unknown"),
                    server_id=server.id,
                    server_name=server.name,
                    process_name=proc.get("name", "unknown"),
                    status=status,
                ))
    return alerts'''

new_fn = '''# Only these statuses count as a real crash/failure worth alerting on -
# "stopped" is usually intentional (someone stopped it on purpose), so it
# is excluded from notifications (it still shows on the Alerts page).
ALERT_STATUSES = {"errored"}

MAX_PARALLEL_SSH = 15


def _check_one_server(server: Server, client_name: str) -> List[ProcessNotification]:
    try:
        processes = list_pm2_processes(server)
    except SSHConnectionError:
        return []  # unreachable servers are already surfaced on the Alerts page
    out = []
    for proc in processes:
        status = proc.get("status", "unknown")
        if status in ALERT_STATUSES:
            out.append(ProcessNotification(
                client_id=server.client_id,
                client_name=client_name,
                server_id=server.id,
                server_name=server.name,
                process_name=proc.get("name", "unknown"),
                status=status,
            ))
    return out


def _collect_process_alerts(db: Session) -> List[ProcessNotification]:
    clients = {c.id: c.name for c in db.query(Client).all()}
    servers = db.query(Server).all()
    alerts: List[ProcessNotification] = []

    # Check every server's SSH in parallel instead of one-by-one, so total
    # time is roughly "slowest single server" rather than "sum of all of them".
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SSH) as pool:
        futures = {
            pool.submit(_check_one_server, server, clients.get(server.client_id, "Unknown")): server
            for server in servers
        }
        for future in as_completed(futures):
            alerts.extend(future.result())

    return alerts'''

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    changes.append("_collect_process_alerts rewritten (parallel + errored-only)")
else:
    print("MISSING: _collect_process_alerts function")

if len(changes) == 2:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS:", changes)
else:
    print("ABORTED - not all changes matched. Applied so far:", changes)
