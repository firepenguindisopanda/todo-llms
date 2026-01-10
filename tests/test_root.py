import pytest


async def test_read_root(client):
    # Root should render the login page for unauthenticated requests
    response = await client.get("/")
    assert response.status_code == 200
    text = response.text
    assert "Welcome Back" in text or "Login" in text or "Sign In" in text
