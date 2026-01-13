import pytest
from app.config import settings
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models.user_model import User as UserModel
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def test_banner_shown_on_first_visit(client):
    r = await client.get("/")
    # root renders login for guests; ensure cookie banner markup is present
    assert r.status_code in (200, 302)
    text = r.text
    assert "We use cookies" in text or "cookie-consent" in text


async def test_accept_sets_cookie_and_shows_analytics(client):
    # accept consent
    r = await client.post("/cookies/consent", data={"action": "accept"})
    assert r.status_code == 200
    # cookie should be set in response
    sc = r.headers.get("set-cookie", "")
    assert "cookie_consent=accept" in sc

    # subsequent page should include analytics snippet
    r2 = await client.get("/")
    assert r2.status_code == 200
    assert "Analytics enabled" in r2.text


async def test_decline_sets_cookie(client):
    r = await client.post("/cookies/consent", data={"action": "decline"})
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "")
    assert "cookie_consent=decline" in sc

    r2 = await client.get("/")
    assert r2.status_code == 200
    assert "Analytics enabled" not in r2.text


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_accept_updates_user_preference(client):
    import uuid
    email = f"cc_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    rreg = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert rreg.status_code == 201

    rlogin = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert rlogin.status_code == 200
    refresh = rlogin.json().get("refresh_token")
    assert refresh

    # set refresh cookie so get_user_from_cookie can find user
    client.cookies.set("refresh_token", refresh)

    r = await client.post("/cookies/consent", data={"action": "accept"})
    assert r.status_code == 200

    # check DB
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.email == email))
        u = res.scalar_one_or_none()
        assert u is not None
        assert u.preferences.get("cookie_consent") == "accept"
