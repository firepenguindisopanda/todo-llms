import pytest
import uuid
from app.config import settings

pytestmark = pytest.mark.asyncio

@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_free_user_todo_limit(client):
    email = f"free_limit_{uuid.uuid4().hex[:8]}@example.com"
    password = "pw123"
    # Register and login
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create 10 todos (should succeed)
    for i in range(10):
        payload = {"title": f"Todo {i}", "description": "desc"}
        r = await client.post("/api/v1/todos/", json=payload, headers=headers)
        assert r.status_code == 201
    # 11th todo should fail
    payload = {"title": "Todo 11", "description": "desc"}
    r = await client.post("/api/v1/todos/", json=payload, headers=headers)
    assert r.status_code == 403
    assert "only create up to 10 todos" in r.json()["detail"]
