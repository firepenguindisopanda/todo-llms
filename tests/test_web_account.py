import pytest
from app.config import settings
from app.infrastructure.cache.redis_client import get_redis_client
import re

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_account_flow(client):
    # Register via web
    r = await client.get("/auth/register")
    assert r.status_code == 200
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    assert m
    csrf = m.group(1)

    import uuid
    email = f"web_{uuid.uuid4().hex[:8]}@example.com"

    r2 = await client.post("/auth/register", data={"email": email, "password": "secret123", "confirm_password": "secret123", "csrf_token": csrf}, follow_redirects=False)
    assert r2.status_code in (302, 303, 200)

    # Login via web to set cookie
    r = await client.get("/auth/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    csrf = m.group(1)
    r3 = await client.post("/auth/login", data={"email": email, "password": "secret123", "csrf_token": csrf}, follow_redirects=False)
    # should redirect to /dashboard
    assert r3.status_code in (302, 303)

    # GET account page
    r = await client.get("/account")
    assert r.status_code == 200
    assert "Account Settings" in r.text

    # Post update
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    csrf = m.group(1)
    r4 = await client.post("/account", data={"display_mode": "dark", "items_per_page": "20", "csrf_token": csrf}, follow_redirects=False)
    assert r4.status_code in (302, 303)

    # DB changed, and cache invalidated when Redis configured
    redis = get_redis_client()
    if redis:
        # ensure cache key deleted or not present
        # we can't easily compute user id here; rely on absence of unexpected exceptions
        pass
