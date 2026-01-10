import pytest
import uuid
from app.config import settings

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_todo_crud_with_auth(client):
    # 1. Register a user with unique email
    email = f"todo_auth_user_{uuid.uuid4().hex[:8]}@example.com"
    password = "pw123"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201

    # 2. Login to get access token
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create a todo (authenticated)
    payload = {"title": "Auth Test Todo", "description": "desc", "priority": 1}
    r3 = await client.post("/api/v1/todos/", json=payload, headers=headers)
    assert r3.status_code == 201
    todo = r3.json()
    assert todo["title"] == payload["title"]
    todo_id = todo["id"]

    # 4. List todos (should include the one we created)
    r4 = await client.get("/api/v1/todos/", headers=headers)
    assert r4.status_code == 200
    data = r4.json()
    assert data["total"] >= 1
    assert any(t["id"] == todo_id for t in data["items"])

    # 5. Get single todo
    r5 = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    assert r5.status_code == 200
    assert r5.json()["id"] == todo_id

    # 6. Update todo
    r6 = await client.put(f"/api/v1/todos/{todo_id}", json={"completed": True}, headers=headers)
    assert r6.status_code == 200
    assert r6.json()["completed"] is True

    # 7. Delete todo
    r7 = await client.delete(f"/api/v1/todos/{todo_id}", headers=headers)
    assert r7.status_code == 204

    # 8. Verify deletion
    r8 = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    assert r8.status_code == 404
