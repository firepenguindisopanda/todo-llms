from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.user import User as DomainUser


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[DomainUser]:
        """Return a domain User or None if not found"""

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[DomainUser]:
        """Return a domain User by id"""

    @abstractmethod
    async def create(self, email: str, password_hash: str, role: str = "user") -> DomainUser:
        """Create a new user and return a DomainUser instance"""
