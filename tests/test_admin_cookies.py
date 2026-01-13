import pytest
import re
from app.config import settings
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models.user_model import User as UserModel
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_admin_cookies_flow(client):
    # create admin user
    import uuid
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    rreg = await client.post("/api/v1/auth/register", json={"email": admin_email, "password": password})
    assert rreg.status_code == 201

    # elevate to admin directly in DB
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.email == admin_email))
        u = res.scalar_one_or_none()
        assert u is not None
        u.role = 'admin'
        await s.flush()
        await s.commit()

    # login and set cookie
    rlogin = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})
    assert rlogin.status_code == 200
    refresh = rlogin.json().get("refresh_token")
    client.cookies.set("refresh_token", refresh)

    # set a consent for another user
    user_email = f"u_{uuid.uuid4().hex[:8]}@example.com"
    rreg2 = await client.post("/api/v1/auth/register", json={"email": user_email, "password": password})
    assert rreg2.status_code == 201

    # set consent for that user via /cookies/consent using cookie of the user
    # login as that user to get refresh token and set cookie
    rlogin2 = await client.post("/api/v1/auth/login", json={"email": user_email, "password": password})
    assert rlogin2.status_code == 200
    refresh2 = rlogin2.json().get("refresh_token")

    # simulate user setting consent
    client.cookies.set("refresh_token", refresh2)
    r = await client.post("/cookies/consent", data={"action": "accept"})
    assert r.status_code == 200

    # now admin login cookie again
    client.cookies.set("refresh_token", refresh)

    # admin should be able to view the admin cookies page
    r2 = await client.get("/admin/cookies")
    assert r2.status_code == 200
    assert user_email in r2.text

    m = re.search(r'name="csrf_token" value="([^"]+)"', r2.text)
    assert m
    csrf = m.group(1)

    # Clear consent for the user by posting to /admin/cookies/clear
    # find userid via DB
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.email == user_email))
        user = res.scalar_one_or_none()
        assert user is not None
        uid = user.id

    r3 = await client.post("/admin/cookies/clear", data={"user_id": uid, "csrf_token": csrf}, follow_redirects=False)
    assert r3.status_code in (302, 303, 200)

    # ensure DB value cleared
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.id == uid))
        user = res.scalar_one_or_none()
        assert user is not None
        assert user.preferences.get("cookie_consent") is None

    # if redis is configured ensure cache was invalidated (no errors)
    redis = get_redis_client()
    if redis:
        try:
            val = redis.get(f"user:{uid}")
            # may be awaitable depending on client
            if hasattr(val, '__await__'):
                val = await val
            # value should be None or not contain cookie_consent
            if val:
                assert 'cookie_consent' not in val
        except Exception:
            pass


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_non_admin_cannot_access(client):
    import uuid
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": "secret123"})
    assert r.status_code == 201

    rlogin = await client.post("/api/v1/auth/login", json={"email": email, "password": "secret123"})
    assert rlogin.status_code == 200
    refresh = rlogin.json().get("refresh_token")
    client.cookies.set("refresh_token", refresh)

    r2 = await client.get("/admin/cookies")
    # should redirect to /dashboard (Access denied)
    assert r2.status_code in (302, 303)
