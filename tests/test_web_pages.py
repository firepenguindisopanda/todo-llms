import pytest

from app.main import app


@pytest.mark.asyncio
async def test_get_pages(client):
    r = await client.get("/home")
    assert r.status_code == 200
    assert "Welcome to FastAPI Todo" in r.text

    r = await client.get("/auth/login")
    assert r.status_code == 200
    assert "Login" in r.text

    r = await client.get("/auth/register")
    assert r.status_code == 200
    assert "Register" in r.text


@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    import uuid
    email = f"testuser-{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    # register (include CSRF)
    r = await client.get("/auth/register")
    assert r.status_code == 200
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)

    r = await client.post("/auth/register", data={"email": email, "password": password, "confirm_password": password, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (303, 302)
    assert r.headers.get("location") == "/auth/login"

    # verify flash on login page
    r = await client.get("/auth/login")
    assert r.status_code == 200
    assert "Registration successful. Please log in." in r.text

    # login (include CSRF)
    r = await client.get("/auth/login")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m
    csrf = m.group(1)

    r = await client.post("/auth/login", data={"email": email, "password": password, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (303, 302)
    # should set refresh_token cookie
    set_cookie = r.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert r.headers.get("location") == "/dashboard"


@pytest.mark.asyncio
async def test_login_register_negative(client):
    # invalid login should re-render with error and preserve email (include CSRF)
    email = "nope@example.com"
    r = await client.get("/auth/login")
    import re
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    csrf = m.group(1)
    r = await client.post("/auth/login", data={"email": email, "password": "bad", "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 401
    assert "Invalid credentials" in r.text
    assert f'value="{email}"' in r.text

    # password mismatch on register should preserve email (include CSRF)
    reg_email = "u@x.com"
    r = await client.get("/auth/register")
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    csrf = m.group(1)
    r = await client.post("/auth/register", data={"email": reg_email, "password": "a", "confirm_password": "b", "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 400
    assert "Passwords do not match" in r.text
    assert f'value="{reg_email}"' in r.text

    # duplicate register (use a unique email per run)
    import uuid
    email = f"dup-{uuid.uuid4().hex[:8]}@example.com"
    pwd = "pwd123"
    # first create should succeed (include CSRF)
    r = await client.get("/auth/register")
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    csrf = m.group(1)
    r = await client.post("/auth/register", data={"email": email, "password": pwd, "confirm_password": pwd, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code in (303, 302)
    # second attempt should fail with 400 (need fresh csrf)
    r = await client.get("/auth/register")
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    csrf = m.group(1)
    r = await client.post("/auth/register", data={"email": email, "password": pwd, "confirm_password": pwd, "csrf_token": csrf}, follow_redirects=False)
    assert r.status_code == 400
    assert "Email already registered" in r.text
