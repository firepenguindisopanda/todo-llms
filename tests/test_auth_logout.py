import pytest
import uuid
from app.config import settings

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_logout_revokes_refresh_token(client):
    email = f"logout_test_{uuid.uuid4().hex[:6]}@example.com"
    pw = "pw12345"

    # register
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 201

    # login
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r2.status_code == 200
    data = r2.json()
    refresh = data["refresh_token"]

    # logout by token (body)
    r3 = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert r3.status_code == 204

    # using the same refresh token to get new access should fail
    r4 = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r4.status_code == 401

    # If Redis is configured, the revoked token should be blacklisted
    from app.infrastructure.cache.redis_client import get_redis_client
    import hashlib
    redis = get_redis_client()
    if redis:
        h = hashlib.sha256(refresh.encode()).hexdigest()
        assert redis.get(f"revoked_refresh:{h}") is not None


@pytest.mark.skipif(not settings.DATABASE_URL, reason="No DATABASE_URL configured for integration tests")
async def test_logout_cookie_and_logout_all(client, caplog):
    email = f"logout_all_{uuid.uuid4().hex[:6]}@example.com"
    pw = "pw12345"

    r = await client.post("/api/v1/auth/register", json={"email": email, "password": pw})
    assert r.status_code == 201

    # login twice (simulate two devices)
    r1 = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r1.status_code == 200 and r2.status_code == 200
    t1 = r1.json()["refresh_token"]
    t2 = r2.json()["refresh_token"]

    # Test logout via cookie: set cookie then call logout
    client.cookies.set("refresh_token", t1)

    import logging
    # capture app logs
    caplog.set_level(logging.INFO, logger="app")

    r3 = await client.post("/api/v1/auth/logout")
    assert r3.status_code == 204

    # verify log emitted
    assert any("user.logout" in rec.getMessage() and email in rec.getMessage() for rec in caplog.records)

    # server should have asked to clear cookie
    set_cookie = r3.headers.get("set-cookie", "")
    assert "refresh_token" in set_cookie and ("Max-Age=0" in set_cookie or "expires=" in set_cookie.lower())

    # Both tokens still may allow refresh unless revoked all; refresh with t1 should fail (it was revoked by cookie logout)
    r_check = await client.post("/api/v1/auth/refresh", json={"refresh_token": t1})
    assert r_check.status_code == 401

    # If Redis is configured, check blacklist for t1
    from app.infrastructure.cache.redis_client import get_redis_client
    import hashlib
    redis = get_redis_client()
    if redis:
        h1 = hashlib.sha256(t1.encode()).hexdigest()
        assert redis.get(f"revoked_refresh:{h1}") is not None

    # clear caplog
    caplog.clear()
    # Now login again to get access token for logout-all
    r_login = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert r_login.status_code == 200
    access = r_login.json()["access_token"]

    # revoke all
    headers = {"Authorization": f"Bearer {access}"}

    import logging
    caplog.set_level(logging.INFO, logger="app")

    r_all = await client.post("/api/v1/auth/logout-all", headers=headers)
    assert r_all.status_code == 200

    # verify logout-all logged
    assert any("user.logout_all" in rec.getMessage() and email in rec.getMessage() for rec in caplog.records)

    # After logout-all, t2 should no longer refresh
    r_check2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": t2})
    assert r_check2.status_code == 401

    # If Redis is configured, check blacklist for t2
    if redis:
        h2 = hashlib.sha256(t2.encode()).hexdigest()
        assert redis.get(f"revoked_refresh:{h2}") is not None

    caplog.clear()
    caplog.clear()
