from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from src.infrastructure.database import Base


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    __table_args__ = (CheckConstraint("attempts >= 0", name="ck_reset_attempts"),)

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, nullable=False, index=True)
    code = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0, server_default="0")
    token = Column(String, nullable=True, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
