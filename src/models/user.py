from sqlalchemy import Index, CheckConstraint, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.infrastructure.database import Base

class UserType:
    ADMIN = "admin"
    AUTHOR = "author"
    USER = "user"
    SELLER = "seller"

class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index('ix_users_type_created', 'type', 'created_at', 'id'),

        CheckConstraint("type IN ('admin', 'author', 'user', 'seller')", name='ck_users_role'),
        CheckConstraint('length(btrim(first_name)) BETWEEN 1 AND 200', name='ck_users_first_name'),
        CheckConstraint('auth_version >= 0', name='ck_users_auth_version'),
        CheckConstraint("phone IS NULL OR phone ~ '^[1-9][0-9]{7,14}$'", name='ck_users_phone'),
    )

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=False)

    auth_version = Column(Integer, nullable=False, default=0, server_default="0")

    avatar = Column(String, nullable=True)  # Relative path to avatar image in media/

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    type = Column(String, default=UserType.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)

    # One-to-one relationship with SellerProfile
    seller_profile = relationship(
        "SellerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    years_of_experience = Column(Integer, nullable=True)
    portfolio = Column(String, nullable=True)
    description = Column(String, nullable=True)

    # Bidirectional relationship back to User
    user = relationship("User", back_populates="seller_profile")
