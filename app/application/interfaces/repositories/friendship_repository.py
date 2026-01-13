from abc import ABC, abstractmethod
from typing import List, Optional, Any
from app.infrastructure.database.models.friendship_model import FriendshipStatus

class IFriendshipRepository(ABC):
    @abstractmethod
    async def send_request(self, user_id: int, friend_id: int) -> Any:
        pass

    @abstractmethod
    async def get_friendship(self, user_id: int, friend_id: int) -> Optional[Any]:
        pass

    @abstractmethod
    async def update_status(self, friendship_id: int, status: str) -> bool:
        pass

    @abstractmethod
    async def get_friends(self, user_id: int) -> List[Any]:
        pass

    @abstractmethod
    async def get_pending_requests(self, user_id: int) -> List[Any]:
        pass

    @abstractmethod
    async def get_received_requests(self, user_id: int) -> List[Any]:
        pass

    @abstractmethod
    async def delete_friendship(self, friendship_id: int) -> bool:
        pass
