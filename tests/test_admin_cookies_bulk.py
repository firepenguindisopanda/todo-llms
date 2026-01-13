import pytest
from app.config import settings
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models.user_model import User as UserModel
from app.infrastructure.database.models.audit_log_model import AuditLog
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_bulk_clear_and_audit(client):
    import uuid
    password = "secret123"

    # create admin
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    rreg = await client.post("/api/v1/auth/register", json={"email": admin_email, "password": password})
    assert rreg.status_code == 201
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(UserModel).where(UserModel.email == admin_email))
        admin = res.scalar_one_or_none()
        admin.role = 'admin'
        await s.flush()
        await s.commit()

    rlogin = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": password})
    assert rlogin.status_code == 200
    refresh = rlogin.json().get("refresh_token")
    client.cookies.set("refresh_token", refresh)

    # create two users and set consents
    u_emails = []
    u_ids = []
    for _ in range(2):
        email = f"u_{uuid.uuid4().hex[:8]}@example.com"
        r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert r.status_code == 201
        rlogin2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert rlogin2.status_code == 200
        refresh2 = rlogin2.json().get("refresh_token")
        client.cookies.set("refresh_token", refresh2)
        rcons = await client.post("/cookies/consent", data={"action": "accept"})
        assert rcons.status_code == 200
        u_emails.append(email)

    # get ids
    async with AsyncSessionLocal() as s:
        for e in u_emails:
            res = await s.execute(select(UserModel).where(UserModel.email == e))
            u = res.scalar_one_or_none()
            u_ids.append(u.id)

    # switch back to admin cookie
    client.cookies.set("refresh_token", refresh)

    # get csrf token from page
    rpage = await client.get("/admin/cookies")
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', rpage.text)
    assert m
    csrf = m.group(1)

    # bulk clear
    form = {"csrf_token": csrf, "user_ids": [str(uid) for uid in u_ids]}
    r = await client.post("/admin/cookies/bulk_clear", data=form)
    assert r.status_code in (200, 302, 303)

    # audit rows should exist
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(AuditLog).where(AuditLog.action == 'clear_cookie_consent'))
        audits = res.scalars().all()
        assert len(audits) >= 2

    # ensure users' preferences cleared
    async with AsyncSessionLocal() as s:
        for uid in u_ids:
            res = await s.execute(select(UserModel).where(UserModel.id == uid))
            u = res.scalar_one_or_none()
            assert 'cookie_consent' not in (u.preferences or {})
