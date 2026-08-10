# backend/app/access_control_models.py
#
# NEW FILE. Implements requirement #9 for real: granting a user access to a
# Client grants access to all Servers under that Client (matches the
# existing Client -> Server nesting in models.py). Scoped to InfraLink only -
# does not touch servers.py/clients.py's existing "any authenticated user
# sees everything" behavior for the rest of the app.
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class UserClientAccess(Base):
    __tablename__ = "user_client_access"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_user_client_access"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    client = relationship("Client", foreign_keys=[client_id])
