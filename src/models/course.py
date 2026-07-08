from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base

class CourseType:
    FOUNDATION = "foundation"
    MIDDLE = "middle"
    SENIOR = "senior"

    ALL = (FOUNDATION, MIDDLE, SENIOR)

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    price = Column(Integer, nullable=False, default=0)
    type = Column(String, nullable=False, default=CourseType.FOUNDATION)
    preview_image = Column(String, nullable=True)
    preview_video = Column(String, nullable=True)
    about_teacher = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category")
    teacher = relationship("User")
    modules = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order_index",
    )
