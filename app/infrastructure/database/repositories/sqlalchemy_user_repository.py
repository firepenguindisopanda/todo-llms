from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories.user_repository import UserRepository
from app.infrastructure.database.models.user_model import User as UserModel
from app.domain.entities.user import User as DomainUser


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[DomainUser]:
        result = await self.session.execute(select(UserModel).where(UserModel.email == email))
        user: Optional[UserModel] = result.scalar_one_or_none()
        if user is None:
            return None
        return DomainUser(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_verified=getattr(user, "is_verified", False),
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def get_by_id(self, id: int) -> Optional[DomainUser]:
        result = await self.session.execute(select(UserModel).where(UserModel.id == id))
        user: Optional[UserModel] = result.scalar_one_or_none()
        if user is None:
            return None
        return DomainUser(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_verified=getattr(user, "is_verified", False),
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def create(self, email: str, password_hash: str, role: str = "user") -> DomainUser:
        user = UserModel(email=email, password_hash=password_hash, role=role)
        self.session.add(user)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(user)

        return DomainUser(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_verified=getattr(user, "is_verified", False),
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
