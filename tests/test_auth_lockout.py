import pytest
import uuid
from app.config import settings
from datetime import datetime, timedelta

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_login_lockout(client):
    # Use unique email for each test run
    email = f"lockout_test_{uuid.uuid4().hex[:8]}@example.com"
    pw = "wrongpassword"

    # Register a user with known password
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "correctpassword"})
    assert r.status_code == 201

    # Fail to login LOCK_THRESHOLD times
    for _ in range(5):
        r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
        assert r2.status_code == 401

    # Next attempt should be forbidden (locked)
    r3 = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r3.status_code == 403
