import pytest
import uuid
from app.config import settings


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_register_and_login_e2e(client):
    # register with unique email
    email = f"login_test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "securepassword"}
    r = await client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201

    # login
    r2 = await client.post("/api/v1/auth/login", json=payload)
    assert r2.status_code == 200
    data = r2.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # refresh
    r3 = await client.post("/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]})
    assert r3.status_code == 200
    data2 = r3.json()
    assert "access_token" in data2
    assert "refresh_token" in data2
