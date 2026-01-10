import pytest
import re

from app.main import app


@pytest.mark.asyncio
async def test_dashboard_requires_login(client):
    r = await client.get("/dashboard", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/auth/login"


@pytest.mark.asyncio
async def test_create_todo_form(client):
    import uuid
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    pwd = "secret123"

    # register
    r = await client.get("/auth/register")
    assert r.status_code == 200
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)

    r = await client.post("/auth/register", data={"email": email, "password": pwd, "confirm_password": pwd, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/auth/login"

    # login
    r = await client.get("/auth/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)

    r = await client.post("/auth/login", data={"email": email, "password": pwd, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/dashboard"

    # GET dashboard and extract CSRF
    r = await client.get("/dashboard")
    assert r.status_code == 200
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)

    # submit create todo
    r = await client.post("/todos/create", data={"title": "Buy milk", "description": "2L", "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (302, 303)
    assert r.headers.get("location") == "/dashboard"

    # GET dashboard again to see flash and todo title
    r = await client.get("/dashboard")
    assert "Todo created successfully." in r.text
    assert "Buy milk" in r.text
