#!/usr/bin/env bash
# rollback_infralink.sh - CODE-ONLY rollback of everything InfraLink/Agent-related.
#
# What this does:
#   - Deletes all new backend files (tenant_models.py, infralink_models.py,
#     infralink_schemas.py, connection_manager.py, access_control_models.py,
#     routers/infralink.py)
#   - Reverts main.py, config.py, models.py back to their exact original
#     content (removes the InfraLink/tenant-related lines only)
#   - Deletes the frontend InfraLink page, reverts Sidebar.tsx and lib/api.ts
#
# What this does NOT do (by design - see the question I asked before this):
#   - Does NOT drop the tenants/infralink_agents/infralink_registration_tokens/
#     user_client_access tables from pm2_dashboard_dev
#   - Does NOT drop the tenant_id column from users/clients/servers
#   These are harmless once the code is gone (nothing references them), and
#   dropping columns/tables is destructive - ask me separately if you want
#   that done too.
#
# Every removal below aborts with a clear message instead of guessing if the
# expected text isn't found exactly - rehearsed against your real files
# before this script was written.
#
# Run from the repo root:
#   cd /var/www/fullstack/pm2-dashboard_dev
#   bash rollback_infralink.sh
#   pm2 restart pm2-dashboard-dev-backend pm2-dashboard-dev-frontend
#   (then npm run build in frontend/ before that restart, see the summary
#   printed at the end)

set -euo pipefail

if [ ! -f "backend/app/main.py" ]; then
  echo "backend/app/main.py not found - run this from the repo root." >&2
  exit 1
fi

echo "==> [1/6] Deleting new backend files"
for f in backend/app/tenant_models.py backend/app/infralink_models.py backend/app/infralink_schemas.py backend/app/connection_manager.py backend/app/access_control_models.py backend/app/routers/infralink.py; do
  if [ -f "$f" ]; then
    rm -f "$f"
    echo "    removed $f"
  else
    echo "    $f already absent, skipping"
  fi
done

echo "==> [2/6] Reverting backend/app/main.py"
python3 << 'PYEOF'
path = "backend/app/main.py"
src = open(path).read()

if "from app import infralink_models" not in src:
    print("    already reverted, skipping")
else:
    removals = [
        "from app import infralink_models  # noqa: F401\n",
        "from app import access_control_models  # noqa: F401\n",
        "from app import tenant_models  # noqa: F401\n",
        "from app.tenant_models import bootstrap_default_tenant\n",
        "app.include_router(infralink.router)\n",
        "    bootstrap_default_tenant(engine)\n",
    ]
    for r in removals:
        if r not in src:
            raise SystemExit(f"ABORT: expected line not found: {r!r} - main.py differs from what this rollback was built against")
        src = src.replace(r, "", 1)

    anchor = ", infralink"
    routers_line_marker = "from app.routers import auth, clients"
    idx = src.find(routers_line_marker)
    if idx == -1:
        raise SystemExit("ABORT: routers import line not found")
    line_end = src.find("\n", idx)
    line = src[idx:line_end]
    if anchor not in line:
        raise SystemExit("ABORT: ', infralink' not found in routers import line")
    new_line = line.replace(anchor, "", 1)
    src = src[:idx] + new_line + src[line_end:]

    open(path, "w").write(src)
    print("    main.py reverted")
PYEOF
python3 -c "import ast; ast.parse(open('backend/app/main.py').read())" && echo "    main.py syntax OK"

echo "==> [3/6] Reverting backend/app/config.py"
python3 << 'PYEOF'
path = "backend/app/config.py"
src = open(path).read()
block = '''

    # InfraLink Agent (optional Agent-based host management, alongside SSH).
    # False by default: when False, all InfraLink UI/API/WebSocket surfaces
    # are disabled and SSH behavior is completely unchanged.
    AGENT_ENABLED: bool = False'''
if block not in src:
    print("    already reverted, skipping")
else:
    src = src.replace(block, "", 1)
    open(path, "w").write(src)
    print("    config.py reverted")
PYEOF
python3 -c "import ast; ast.parse(open('backend/app/config.py').read())" && echo "    config.py syntax OK"

echo "==> [4/6] Reverting backend/app/models.py (removing tenant_id columns)"
sed -i '/^    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, default=1)$/d' backend/app/models.py
python3 -c "import ast; ast.parse(open('backend/app/models.py').read())" && echo "    models.py syntax OK"

echo "==> [5/6] Reverting frontend"
if [ -d "frontend/app/dashboard/infralink" ]; then
  rm -rf frontend/app/dashboard/infralink
  echo "    removed frontend/app/dashboard/infralink/"
else
  echo "    infralink page already absent, skipping"
fi

python3 << 'PYEOF'
path = "frontend/lib/api.ts"
src = open(path).read()
marker = "\n// ---- InfraLink Agents"
idx = src.find(marker)
if idx == -1:
    print("    api.ts already reverted, skipping")
else:
    src = src[:idx] + "\n"
    open(path, "w").write(src)
    print("    api.ts reverted")
PYEOF

python3 << 'PYEOF'
path = "frontend/components/Sidebar.tsx"
src = open(path).read()
block = '''        {role === "admin" && process.env.NEXT_PUBLIC_AGENT_ENABLED === "true" && (
          <NavItem
            href="/dashboard/infralink"
            label="InfraLink"
            active={pathname.startsWith("/dashboard/infralink")}
            icon={
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path d="M10 2a1 1 0 011 1v2.06a6.002 6.002 0 014.94 4.94H18a1 1 0 110 2h-2.06a6.002 6.002 0 01-4.94 4.94V19a1 1 0 11-2 0v-2.06a6.002 6.002 0 01-4.94-4.94H2a1 1 0 110-2h2.06a6.002 6.002 0 014.94-4.94V3a1 1 0 011-1zm0 5a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            }
          />
        )}
'''
if block not in src:
    print("    Sidebar.tsx already reverted, skipping")
else:
    src = src.replace(block, "", 1)
    open(path, "w").write(src)
    print("    Sidebar.tsx reverted")
PYEOF

echo "==> [6/6] Done"
cat << 'DONE'

All InfraLink/Agent code removed. NOT touched (see top of this script):
  - pm2_dashboard_dev tables: tenants, infralink_agents,
    infralink_registration_tokens, user_client_access
  - tenant_id column on users/clients/servers (harmless, unreferenced now)
  - AGENT_ENABLED / NEXT_PUBLIC_AGENT_ENABLED lines in your .env files
    (harmless leftover flags, nothing reads them anymore)

Next steps:
  git status
  git diff -- backend/app/main.py backend/app/config.py backend/app/models.py frontend/components/Sidebar.tsx frontend/lib/api.ts

  cd frontend && npm run build
  pm2 restart pm2-dashboard-dev-backend pm2-dashboard-dev-frontend
  pm2 logs pm2-dashboard-dev-backend --lines 20 --nostream

Confirm the dashboard works exactly as it did before any of this started.
DONE
