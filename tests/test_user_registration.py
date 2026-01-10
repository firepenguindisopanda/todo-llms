import pytest
import uuid
from app.config import settings


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_register_user_e2e(client):
    # Requires local Postgres DB and migrations applied (use unique email for each run)
    email = f"register_test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": "securepassword"}
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert "id" in data
