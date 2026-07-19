import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base


class EnvEditAudit(Base):
    """हर बार जब कोई admin किसी .env key की value edit करता है (local या
    remote server पर), उसका log - sensitive keys के लिए असली values कभी
    store नहीं होतीं, सिर्फ यह कि edit हुआ (who/what/when)."""
    __tablename__ = "env_edit_audits"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(255), nullable=False)
    env_file_path = Column(String(255), nullable=False)
    key_name = Column(String(255), nullable=False)
    was_sensitive = Column(Boolean, default=False)
    server_id = Column(Integer, nullable=True)  # NULL = local (dashboard host)
    user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
