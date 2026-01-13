from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.infrastructure.database.models import Base


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, nullable=True)
    target_user_id = Column(Integer, nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
