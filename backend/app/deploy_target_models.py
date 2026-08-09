"""
Cache of "what's actually deployed where" - populated by a background
scan (manual button OR the periodic scheduler in build_manager.py), NOT
computed live on every dropdown load. This is what made repo/process
selection slow before: every click did live SSH + pm2 jlist + git
remote calls. Now the wizard only ever reads this table; scanning is a
separate, occasional background operation.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from app.database import Base


class DeployTargetCache(Base):
    __tablename__ = "deploy_target_cache"

    id = Column(Integer, primary_key=True, index=True)
    scan_path_id = Column(Integer, ForeignKey("repo_scan_paths.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    environment = Column(String(255), nullable=False, index=True)   # folder name under base_path, e.g. "Staging"
    repo_name = Column(String(255), nullable=False, index=True)     # git remote-resolved name (falls back to folder name)
    folder_name = Column(String(255), nullable=False)               # actual directory name on disk
    full_path = Column(String(500), nullable=False)
    pm2_process_name = Column(String(255), nullable=False)
    pm2_status = Column(String(50), nullable=True)
    last_scanned_at = Column(DateTime, default=datetime.datetime.utcnow)
