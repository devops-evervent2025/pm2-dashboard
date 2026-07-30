import shutil
from datetime import datetime

path = "main.py"
backup = f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
shutil.copy(path, backup)
print(f"Backed up to {backup}")

with open(path) as f:
    content = f.read()

old_import_routers = "from app.routers import auth, clients, servers, processes, logs, system, remote_repos, terminal, ssl_dashboard, notifications, activity_log"
new_import_routers = "from app.routers import auth, clients, servers, processes, logs, system, remote_repos, terminal, ssl_dashboard, notifications, activity_log, domain_health"

old_import_funcs = "from app.routers.notifications import start_daily_digest_scheduler"
new_import_funcs = "from app.routers.notifications import start_daily_digest_scheduler\nfrom app.routers.domain_health import start_periodic_domain_health_check"

old_include = "app.include_router(activity_log.router)"
new_include = "app.include_router(activity_log.router)\napp.include_router(domain_health.router)"

old_startup = "    start_periodic_ssl_scan()\n    start_daily_digest_scheduler()"
new_startup = "    start_periodic_ssl_scan()\n    start_daily_digest_scheduler()\n    start_periodic_domain_health_check()"

changes = [
    (old_import_routers, new_import_routers),
    (old_import_funcs, new_import_funcs),
    (old_include, new_include),
    (old_startup, new_startup),
]

for old, new in changes:
    count = content.count(old)
    if count != 1:
        print(f"ERROR: expected 1 occurrence of block, found {count}. Aborting, nothing changed. Block was:\n{old}")
        raise SystemExit(1)

for old, new in changes:
    content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)
print("Patched main.py successfully.")
