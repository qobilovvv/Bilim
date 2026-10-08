from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.infrastructure.database import Base


class Category(Base):
    __tablename__ = "categories"

    __table_args__ = (
        CheckConstraint(
            "(parent_id IS NULL AND level = 1) OR (parent_id IS NOT NULL AND level = 2 AND parent_id <> id)",
            name="ck_categories_hierarchy",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        JSONB, nullable=False
    )  # Localized dictionary: {"ru": "...", "uz": "...", "en": "..."}
    path = Column(String, unique=True, index=True, nullable=False)
    parent_id = Column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True
    )
    level = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Self-referential relationships
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship(
        "Category", back_populates="parent", cascade="all, delete-orphan", lazy="select"
    )
