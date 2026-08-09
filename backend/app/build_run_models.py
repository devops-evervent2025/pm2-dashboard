"""
Audit trail for the Build Manager feature: one row per build/restart run
triggered from the "Build Manager" sidebar page. Kept in its own file,
imported (noqa) from main.py exactly like env_audit_models.py, so
Base.metadata.create_all() picks up the table automatically on the next
backend restart - no manual migration needed.
"""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey

from app.database import Base


class BuildRunAudit(Base):
    __tablename__ = "build_run_audit"

    id = Column(Integer, primary_key=True, index=True)
    scan_path_id = Column(Integer, ForeignKey("repo_scan_paths.id"), nullable=True)
    repo_name = Column(String(255), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    git_branch = Column(String(255), nullable=True)
    build_succeeded = Column(Boolean, nullable=True)
    pm2_process_matched = Column(String(255), nullable=True)
    pm2_restarted = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)
