from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.infrastructure.database.models import Base

class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False) # Store enum as string for compatibility
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Ensure a user can't have duplicate friendship records with the same person
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='uq_friendship_user_friend'),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="initiated_friendships")
    friend = relationship("User", foreign_keys=[friend_id], backref="received_friendships")
