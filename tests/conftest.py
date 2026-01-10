import asyncio
import sys
import os
import pytest
from httpx import ASGITransport, AsyncClient

# Ensure project root is on sys.path so tests can import `app`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    # httpx >= 0.27 requires ASGITransport for testing ASGI apps
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # Dispose of database connections after each test to prevent "another operation in progress"
    from app.infrastructure.database.connection import engine
    if engine is not None:
        await engine.dispose()
