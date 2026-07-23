"""
Login OTP - a one-time 6-digit code emailed to the user's registered
address after their username+password check succeeds, required before
a JWT is issued. Codes are hashed at rest (never stored in plaintext),
expire quickly, and are single-use.
"""
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from app.database import Base


class LoginOtp(Base):
    __tablename__ = "login_otps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
