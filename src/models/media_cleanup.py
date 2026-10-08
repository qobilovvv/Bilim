from sqlalchemy import Column, DateTime, String
from sqlalchemy.sql import func

from src.infrastructure.database import Base


class MediaCleanup(Base):
    __tablename__ = "media_cleanup_queue"

    path = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
