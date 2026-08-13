#!/usr/bin/env bash
# apply_infralink_tenants.sh - multi-tenant rebuild, step 1: data model
#
# WHAT THIS DOES (touches real data via ALTER TABLE on next backend restart):
#   1. Adds backend/app/tenant_models.py (new Tenant table + bootstrap_default_tenant)
#   2. Adds tenant_id column to User, Client, Server in models.py (nullable=False,
#      default=1) - your auto_migrate.py will ALTER TABLE ADD COLUMN this in
#      automatically on next restart, backfilling ALL existing rows to
#      tenant_id=1 (the "Default" tenant created by bootstrap_default_tenant).
#   3. Wires main.py so bootstrap_default_tenant() runs BEFORE
#      run_auto_migrations() - ordering matters, see tenant_models.py docstring.
#
# TESTED: I rehearsed the full sequence (existing rows -> new tenants table ->
# default tenant bootstrap -> ALTER TABLE ADD COLUMN tenant_id DEFAULT 1) with
# real pre-existing data before writing this script - zero data loss, all rows
# correctly backfilled to tenant_id=1. This script's models.py/main.py edits
# were also tested against your exact real file content, not guessed.
#
# NOT YET DONE (later steps): tenant-scoping the ~15 existing routers,
# registration/login UI changes. This step only adds the data model.
#
# Run from the repo root, then RESTART THE BACKEND to actually apply the
# ALTER TABLE migration (this script alone only edits files, it does not
# touch your database):
#   cd /var/www/fullstack/pm2-dashboard_dev
#   bash apply_infralink_tenants.sh
#   pm2 restart pm2-dashboard-dev-backend
#   pm2 logs pm2-dashboard-dev-backend --lines 30 --nostream

set -euo pipefail

if [ ! -f "backend/app/models.py" ]; then
  echo "backend/app/models.py not found - run this from the repo root." >&2
  exit 1
fi

echo "==> [1/4] Writing backend/app/tenant_models.py"
cat > backend/app/tenant_models.py << 'TENANT_MODELS_EOF'
# backend/app/tenant_models.py
#
# NEW FILE. Step 1 of the multi-tenant rebuild: the Tenant table itself,
# plus a bootstrap step that MUST run before run_auto_migrations() adds
# tenant_id columns to users/clients/servers - see bootstrap_default_tenant
# docstring for why the ordering matters.
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import relationship

from app.database import Base

# Every row that existed before multi-tenancy was added gets backfilled
# into this one tenant, so nothing changes for today's users when
# AGENT_ENABLED=false (single shared environment, exactly as now).
DEFAULT_TENANT_ID = 1


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    # Nullable: the default/legacy tenant (id=1) has no single owner - it's
    # the pre-existing shared environment. New InfraLink-registered tenants
    # will have this set to their registering user.
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_user_id])


def bootstrap_default_tenant(engine: Engine) -> None:
    """
    Ensures the default tenant (id=1) exists BEFORE run_auto_migrations()
    runs. auto_migrate.py's ALTER TABLE ... ADD COLUMN only sets the
    column's type/nullable/default - it does not add a real FK constraint
    for retroactively-added columns (checked: it never emits REFERENCES).
    So this isn't required to avoid a DB-level FK error, but it IS required
    for application-level correctness: every existing row is about to be
    backfilled with tenant_id=1, and that tenant needs to actually exist
    the moment the app queries it (e.g. the very first request after
    startup), not just eventually.
    """
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM tenants WHERE id = :id"), {"id": DEFAULT_TENANT_ID}
        ).first()
        if existing:
            return
        conn.execute(
            text(
                "INSERT INTO tenants (id, name, owner_user_id, created_at) "
                "VALUES (:id, :name, NULL, :created_at)"
            ),
            {"id": DEFAULT_TENANT_ID, "name": "Default", "created_at": datetime.utcnow()},
        )
        print(f"[bootstrap_default_tenant] Created default tenant id={DEFAULT_TENANT_ID}")
TENANT_MODELS_EOF

echo "==> [2/4] Adding tenant_id column to User, Client, Server in models.py"
if grep -q "tenant_id = Column" backend/app/models.py; then
  echo "    already present, skipping"
else
  sed -i 's/    username = Column(String(100), unique=True, index=True, nullable=False)/    username = Column(String(100), unique=True, index=True, nullable=False)\n    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, default=1)/' backend/app/models.py
  sed -i 's/    name = Column(String(255), unique=True, nullable=False, index=True)/    name = Column(String(255), unique=True, nullable=False, index=True)\n    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, default=1)/' backend/app/models.py
  sed -i 's/    ip_address = Column(String(100), nullable=False)/    ip_address = Column(String(100), nullable=False)\n    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, default=1)/' backend/app/models.py
fi

echo "==> [3/4] Wiring main.py: register tenant_models, import + call bootstrap_default_tenant before run_auto_migrations"
if grep -q "from app import tenant_models" backend/app/main.py; then
  echo "    already present, skipping"
else
  sed -i 's/from app import access_control_models  # noqa: F401/from app import access_control_models  # noqa: F401\nfrom app import tenant_models  # noqa: F401/' backend/app/main.py
  sed -i 's/from app.auto_migrate import run_auto_migrations/from app.auto_migrate import run_auto_migrations\nfrom app.tenant_models import bootstrap_default_tenant/' backend/app/main.py
  python3 << 'PYEOF'
path = "backend/app/main.py"
src = open(path).read()
anchor = "    Base.metadata.create_all(bind=engine)\n    run_auto_migrations(engine)"
if anchor not in src:
    raise SystemExit("ABORT: expected create_all/run_auto_migrations sequence not found - main.py differs from what this patch was built against, not applying")
replacement = "    Base.metadata.create_all(bind=engine)\n    bootstrap_default_tenant(engine)\n    run_auto_migrations(engine)"
open(path, "w").write(src.replace(anchor, replacement, 1))
PYEOF
fi

echo "==> [4/4] Verifying syntax"
python3 -c "import ast; ast.parse(open('backend/app/tenant_models.py').read())" && echo "    tenant_models.py syntax OK"
python3 -c "import ast; ast.parse(open('backend/app/models.py').read())" && echo "    models.py syntax OK"
python3 -c "import ast; ast.parse(open('backend/app/main.py').read())" && echo "    main.py syntax OK"

cat << 'DONE'

Files updated. NOTHING has touched the database yet - that only happens
when you restart the backend. Recommended order:

  1. git diff -- backend/app/models.py backend/app/main.py
     (review before restarting - should be exactly: 3 tenant_id lines in
     models.py, 3 small additions in main.py)

  2. mysqldump -u pm2dash -p pm2_dashboard_dev > ~/pm2_dashboard_dev_backup_$(date +%Y%m%d_%H%M%S).sql
     (backup the DEV database before the ALTER TABLE runs - cheap insurance)

  3. pm2 restart pm2-dashboard-dev-backend
     pm2 logs pm2-dashboard-dev-backend --lines 30 --nostream
     Look for:
       [bootstrap_default_tenant] Created default tenant id=1
       [auto_migrate] Added missing column: users.tenant_id
       [auto_migrate] Added missing column: clients.tenant_id
       [auto_migrate] Added missing column: servers.tenant_id
     and NO "FAILED to add" lines.

  4. Confirm existing data is intact and backfilled:
     mysql -u pm2dash -p pm2_dashboard_dev -e "SELECT id, username, tenant_id FROM users;"
     mysql -u pm2dash -p pm2_dashboard_dev -e "SELECT id, name, tenant_id FROM clients;"
     Every row should show tenant_id=1.

This only touches pm2_dashboard_dev - prod (pm2_dashboard) is untouched.
DONE

