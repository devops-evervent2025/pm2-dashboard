from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app import notification_models  # noqa: F401
from app import otp_models  # noqa: F401
from app import server_resource_models  # noqa: F401
from app import build_run_models  # noqa: F401
from app.routers import auth, clients, servers, processes, logs, system, remote_repos, terminal, ssl_dashboard, notifications, activity_log, domain_health, server_logs, replication_health, log_alerts, server_resources, build_manager

from app.routers.ssl_dashboard import start_periodic_ssl_scan
from app.routers.notifications import start_daily_digest_scheduler
from app.routers.domain_health import start_periodic_domain_health_check
from app.routers.replication_health import start_periodic_replication_health_check
from app.routers.log_alerts import start_periodic_log_alert_check
from app.routers.build_manager import start_deploy_scan_scheduler
from app.init_db import bootstrap_admin
from app.auto_migrate import run_auto_migrations

settings = get_settings()

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(servers.router)
app.include_router(processes.router)
app.include_router(logs.router)
app.include_router(system.router)
app.include_router(remote_repos.router)
app.include_router(terminal.router)
app.include_router(ssl_dashboard.router)
app.include_router(notifications.router)
app.include_router(activity_log.router)
app.include_router(domain_health.router)
app.include_router(server_logs.router)
app.include_router(replication_health.router)
app.include_router(log_alerts.router)
app.include_router(server_resources.router)
app.include_router(build_manager.router)


@app.on_event("startup")
def on_startup():
    # Dynamically create all tables (clients, servers, processes-audit, users) if missing
    Base.metadata.create_all(bind=engine)
    run_auto_migrations(engine)
    bootstrap_admin()
    start_periodic_ssl_scan()
    start_daily_digest_scheduler()
    start_deploy_scan_scheduler()
    start_periodic_domain_health_check()
    start_periodic_replication_health_check()
    start_periodic_log_alert_check()


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
