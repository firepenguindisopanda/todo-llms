from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.repositories.sqlalchemy_friendship_repository import SQLAlchemyFriendshipRepository
from app.infrastructure.database.models.friendship_model import FriendshipStatus
from app.infrastructure.external_services.pusher.pusher_client import pusher_service
from sqlalchemy import select
from app.infrastructure.database.models.user_model import User as UserModel

class FriendService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SQLAlchemyFriendshipRepository(db)

    async def send_friend_request(self, user_id: int, friend_username_or_email: str):
        # Find the friend
        stmt = select(UserModel).where(
            (UserModel.email == friend_username_or_email)
        )
        result = await self.db.execute(stmt)
        friend = result.scalar_one_or_none()

        if not friend:
            return {"success": False, "message": "User not found"}

        if friend.id == user_id:
            return {"success": False, "message": "You cannot add yourself as a friend"}

        # Check existing friendship
        existing = await self.repo.get_friendship(user_id, friend.id)
        if existing:
            if existing.status == FriendshipStatus.ACCEPTED:
                return {"success": False, "message": "Already friends"}
            if existing.status == FriendshipStatus.PENDING:
                if existing.user_id == user_id:
                    return {"success": False, "message": "Request already sent"}
                else:
                    # Automatic acceptance if they sent one previously?
                    # For now, let's just say "You have a pending request from this user"
                    return {"success": False, "message": "That user already sent you a friend request"}

        # Create new request
        new_request = await self.repo.send_request(user_id, friend.id)
        await self.db.commit()

        # Pusher Notification
        pusher_service.trigger_event(
            f"private-user-{friend.id}",
            "friend-request-received",
            {
                "request_id": new_request.id,
                "from_user_id": user_id,
                "message": "You have a new friend request"
            }
        )

        return {"success": True, "message": "Friend request sent"}

    async def accept_friend_request(self, user_id: int, request_id: int):
        request = await self.repo.get_by_id(request_id)
        if not request or request.friend_id != user_id or request.status != FriendshipStatus.PENDING:
            return {"success": False, "message": "Request not found or invalid"}

        success = await self.repo.update_status(request_id, FriendshipStatus.ACCEPTED)
        if success:
            await self.db.commit()
            
            # Notify the requester
            pusher_service.trigger_event(
                f"private-user-{request.user_id}",
                "friend-request-accepted",
                {
                    "friend_id": user_id,
                    "message": "Your friend request was accepted"
                }
            )
            return {"success": True, "message": "Friend request accepted"}
        
        return {"success": False, "message": "Failed to accept request"}

    async def reject_friend_request(self, user_id: int, request_id: int):
        request = await self.repo.get_by_id(request_id)
        if not request or request.friend_id != user_id or request.status != FriendshipStatus.PENDING:
            return {"success": False, "message": "Request not found or invalid"}

        success = await self.repo.delete_friendship(request_id)
        if success:
            await self.db.commit()
            return {"success": True, "message": "Friend request rejected"}
        
        return {"success": False, "message": "Failed to reject request"}

    async def list_friends(self, user_id: int):
        friends = await self.repo.get_friends(user_id)
        return friends

    async def list_pending_received(self, user_id: int):
        return await self.repo.get_received_requests(user_id)
