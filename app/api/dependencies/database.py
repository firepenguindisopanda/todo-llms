from typing import AsyncGenerator
from app.infrastructure.database.connection import get_async_session


async def get_db() -> AsyncGenerator:
    async for session in get_async_session():
        yield session
