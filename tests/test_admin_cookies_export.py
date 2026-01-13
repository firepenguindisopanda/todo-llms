import pytest
from app.config import settings
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models.user_model import User as UserModel
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not settings.DATABASE_URL, reason="Requires DATABASE_URL")
async def test_export_csv_and_filter(client):
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

    # create a user with a known email
    email = f"export_{uuid.uuid4().hex[:8]}@example.com"
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201

    # set consent for that user
    rlogin2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    refresh2 = rlogin2.json().get("refresh_token")
    client.cookies.set("refresh_token", refresh2)
    rcons = await client.post("/cookies/consent", data={"action": "accept"})
    assert rcons.status_code == 200

    client.cookies.set("refresh_token", refresh)

    # export CSV (no filter) - ensure our user present
    rcsv = await client.get("/admin/cookies/export")
    assert rcsv.status_code == 200
    assert "text/csv" in rcsv.headers.get("content-type", "")
    assert email in rcsv.text

    # export CSV with filter 'export_' should include only matching rows
    rcsv2 = await client.get(f"/admin/cookies/export?q=export_")
    assert rcsv2.status_code == 200
    assert email in rcsv2.text
