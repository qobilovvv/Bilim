from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    video = Column(String, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    module = relationship("Module", back_populates="lessons")
    materials = relationship(
        "Material",
        back_populates="lesson",
        cascade="all, delete-orphan",
    )
    homework = relationship(
        "Homework",
        back_populates="lesson",
        uselist=False,
        cascade="all, delete-orphan",
    )
