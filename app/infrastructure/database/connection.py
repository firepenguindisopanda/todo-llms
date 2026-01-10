from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# Ensure the database URL is a plain string (Pydantic AnyUrl can be passed as object)
DATABASE_URL: Optional[str] = str(settings.DATABASE_URL) if settings.DATABASE_URL else None

engine = None
AsyncSessionLocal = None

if DATABASE_URL:
    # parse & remove query params that asyncpg.connect does not accept directly
    parsed = urlparse(DATABASE_URL)
    qs = dict(parse_qsl(parsed.query))

    connect_args = {}
    # translate sslmode into asyncpg-compatible 'ssl' connect arg
    ssl_required = False
    if "sslmode" in qs:
        if qs.get("sslmode") in ("require", "verify-ca", "verify-full"):
            ssl_required = True
        qs.pop("sslmode", None)

    # drop unsupported channel_binding param
    qs.pop("channel_binding", None)

    # build a cleaned URL without the removed query params
    new_query = urlencode(qs) if qs else ""
    cleaned_url = urlunparse(parsed._replace(query=new_query))

    if ssl_required:
        connect_args["ssl"] = True

    engine = create_async_engine(cleaned_url, echo=settings.DEBUG, future=True, connect_args=connect_args if connect_args else None)
    AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if AsyncSessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured. Set DATABASE_URL in your .env before using the DB.")
    async with AsyncSessionLocal() as session:
        yield session
