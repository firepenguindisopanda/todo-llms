import pytest
import json
from app.config import settings
from app.infrastructure.security.jwt_handler import create_access_token
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.database.connection import AsyncSessionLocal
from sqlalchemy import select
from app.infrastructure.database.models.user_model import User as UserModel


pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_me_cached(client):
    # register a user via API (keeps tests self-contained)
    import uuid
    email = f"me_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    rreg = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert rreg.status_code == 201

    rlogin = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert rlogin.status_code == 200
    token = rlogin.json()["access_token"]

    # first request should populate cache (if Redis configured)
    r = await client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"]
    old_email = data["email"]
    user_id = data["id"]

    # patch DB directly to change email
    import uuid as _uuid
    changed_email = f"changed_{_uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.id == user_id))
        db_user = res.scalar_one_or_none()
        assert db_user is not None
        db_user.email = changed_email
        await s.flush()
        await s.commit()

    # second request: if Redis is configured, cached email may still be old; otherwise should reflect DB
    r2 = await client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    data2 = r2.json()

    redis = get_redis_client()
    if redis:
        # when Redis is present, the response should be from cache (old email)
        assert data2["email"] == old_email
        # cleanup: invalidate cache and ensure DB value is returned
        try:
            redis.delete(f"user:{user_id}")
        except Exception:
            pass
        r3 = await client.get("/api/v1/auth/me", headers={"authorization": f"Bearer {token}"})
        assert r3.status_code == 200
        assert r3.json()["email"] == changed_email
    else:
        # no Redis configured: endpoint should reflect DB state
        assert data2["email"] == changed_email
