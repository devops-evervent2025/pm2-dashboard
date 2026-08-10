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
