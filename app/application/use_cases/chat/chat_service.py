from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, update
from app.infrastructure.database.models.message_model import Message as MessageModel
from app.infrastructure.external_services.pusher.pusher_client import pusher_service

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_message(self, sender_id: int, receiver_id: int, content: str):
        if not content.strip():
            return None
            
        message = MessageModel(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(message)

        # Trigger Pusher event for real-time delivery
        pusher_service.trigger_event(
            f"private-user-{receiver_id}",
            "new-message",
            {
                "id": message.id,
                "sender_id": sender_id,
                "content": content,
                "created_at": message.created_at.isoformat()
            }
        )
        return message

    async def get_chat_history(self, user_id: int, friend_id: int, limit: int = 50):
        stmt = select(MessageModel).where(
            or_(
                and_(MessageModel.sender_id == user_id, MessageModel.receiver_id == friend_id),
                and_(MessageModel.sender_id == friend_id, MessageModel.receiver_id == user_id)
            )
        ).order_by(MessageModel.created_at.asc()).limit(limit)
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Mark received messages as read
        await self.db.execute(
            update(MessageModel)
            .where(and_(MessageModel.sender_id == friend_id, MessageModel.receiver_id == user_id, MessageModel.is_read == False))
            .values(is_read=True)
        )
        await self.db.commit()
        
        return messages
