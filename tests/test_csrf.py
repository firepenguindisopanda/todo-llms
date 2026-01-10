import pytest


@pytest.mark.asyncio
async def test_csrf_missing_and_invalid(client):
    # get login page to establish session and get CSRF token
    r = await client.get("/auth/login")
    assert r.status_code == 200
    # missing CSRF token in post should return 400
    r = await client.post("/auth/login", data={"email": "x@x.com", "password": "p"}, follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid CSRF token" in r.text

    # invalid CSRF token
    r = await client.get("/auth/login")
    assert r.status_code == 200
    # submit with wrong token
    r = await client.post("/auth/login", data={"email": "x@x.com", "password": "p", "csrf_token": "badtoken"}, follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid CSRF token" in r.text

    # same checks for register
    r = await client.get("/auth/register")
    assert r.status_code == 200
    r = await client.post("/auth/register", data={"email": "a@b.com", "password": "p", "confirm_password": "p"}, follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid CSRF token" in r.text

    r = await client.get("/auth/register")
    r = await client.post("/auth/register", data={"email": "a@b.com", "password": "p", "confirm_password": "p", "csrf_token": "bad"}, follow_redirects=False)
    assert r.status_code == 400
    assert "Invalid CSRF token" in r.text
