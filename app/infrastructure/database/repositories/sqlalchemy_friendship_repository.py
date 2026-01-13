from typing import List, Optional, Any
from sqlalchemy import select, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.interfaces.repositories.friendship_repository import IFriendshipRepository
from app.infrastructure.database.models.friendship_model import Friendship as FriendshipModel, FriendshipStatus
from app.infrastructure.database.models.user_model import User as UserModel

class SQLAlchemyFriendshipRepository(IFriendshipRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_request(self, user_id: int, friend_id: int) -> FriendshipModel:
        friendship = FriendshipModel(user_id=user_id, friend_id=friend_id, status=FriendshipStatus.PENDING)
        self.session.add(friendship)
        await self.session.flush()
        return friendship

    async def get_friendship(self, user_id: int, friend_id: int) -> Optional[FriendshipModel]:
        # Check both directions (user_id to friend_id OR friend_id to user_id)
        stmt = select(FriendshipModel).where(
            or_(
                and_(FriendshipModel.user_id == user_id, FriendshipModel.friend_id == friend_id),
                and_(FriendshipModel.user_id == friend_id, FriendshipModel.friend_id == user_id)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(self, friendship_id: int, status: str) -> bool:
        stmt = select(FriendshipModel).where(FriendshipModel.id == friendship_id)
        result = await self.session.execute(stmt)
        friendship = result.scalar_one_or_none()
        if friendship:
            friendship.status = status
            await self.session.flush()
            return True
        return False

    async def get_friends(self, user_id: int) -> List[UserModel]:
        # Finding friends where status is ACCEPTED
        # A user can be either user_id or friend_id in the table
        stmt = select(FriendshipModel).where(
            and_(
                FriendshipModel.status == FriendshipStatus.ACCEPTED,
                or_(FriendshipModel.user_id == user_id, FriendshipModel.friend_id == user_id)
            )
        ).options(
            selectinload(FriendshipModel.user),
            selectinload(FriendshipModel.friend)
        )
        result = await self.session.execute(stmt)
        friendships = result.scalars().all()
        
        friends = []
        for f in friendships:
            if f.user_id == user_id:
                friends.append(f.friend)
            else:
                friends.append(f.user)
        return friends

    async def get_pending_requests(self, user_id: int) -> List[FriendshipModel]:
        # Sent by me, but still pending
        stmt = select(FriendshipModel).where(
            and_(FriendshipModel.user_id == user_id, FriendshipModel.status == FriendshipStatus.PENDING)
        ).options(selectinload(FriendshipModel.friend))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_received_requests(self, user_id: int) -> List[FriendshipModel]:
        # Received by me, still pending
        stmt = select(FriendshipModel).where(
            and_(FriendshipModel.friend_id == user_id, FriendshipModel.status == FriendshipStatus.PENDING)
        ).options(selectinload(FriendshipModel.user))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_friendship(self, friendship_id: int) -> bool:
        stmt = delete(FriendshipModel).where(FriendshipModel.id == friendship_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_by_id(self, friendship_id: int) -> Optional[FriendshipModel]:
        stmt = select(FriendshipModel).where(FriendshipModel.id == friendship_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
