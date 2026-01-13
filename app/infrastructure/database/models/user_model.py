from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.infrastructure.database.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # NOTE: intentionally leaving out `is_verified` column so you can
    # add it later and test Alembic autogenerate / migrations as requested.

    # Brute-force protection fields
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    role = Column(String(50), default="user", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Stripe integration fields
    stripe_customer_id = Column(String(255), nullable=True)
    subscription_status = Column(String(50), default="free", nullable=False)  # 'free', 'active', 'canceled'

    # Social & Presence
    last_seen = Column(DateTime(timezone=True), nullable=True)

    # JSON column for user preferences (stored as JSON object)
    preferences = Column(JSON(), nullable=True, default=dict)

    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")
