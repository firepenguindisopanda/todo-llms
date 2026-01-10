from app.application.interfaces.repositories.user_repository import UserRepository
from app.infrastructure.security.password_hasher import hash_password
from app.domain.entities.user import User as DomainUser


async def register_user(email: str, password: str, repository: UserRepository) -> DomainUser:
    existing = await repository.get_by_email(email)
    if existing:
        raise ValueError("Email already registered")

    hashed = hash_password(password)
    user = await repository.create(email=email, password_hash=hashed)
    return user
