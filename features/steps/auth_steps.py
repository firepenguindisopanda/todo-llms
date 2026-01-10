import uuid
import os
import re
import httpx
from behave import given, when, then


BASE = os.environ.get("BEHAVE_BASE_URL", "http://127.0.0.1:8000")


# === Helpers ===

def extract_csrf_token(html: str) -> str | None:
    """Extract CSRF token from HTML form."""
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    return m.group(1) if m else None


# === Given Steps ===

@given("the API server is reachable")
def step_server_reachable(context):
    # Already checked in environment.py before_all, but we can re-verify
    pass


@given("I use a unique email")
def step_use_unique_email(context):
    context.email = f"bdd_{uuid.uuid4().hex[:8]}@example.com"
    context.password = "pw12345"


@given("I register the user via API")
def step_register_user_via_api(context):
    url = f"{BASE}/api/v1/auth/register"
    resp = httpx.post(url, json={"email": context.email, "password": context.password}, timeout=10)
    assert resp.status_code == 201, f"Registration failed: {resp.status_code} {resp.text}"
    context.registered_email = context.email
    context.registered_password = context.password


# === When Steps (API) ===

@when("I POST /api/v1/auth/register with valid payload")
def step_post_register(context):
    url = f"{BASE}/api/v1/auth/register"
    resp = httpx.post(url, json={"email": context.email, "password": context.password}, timeout=10)
    context.response = resp


# === When Steps (Web UI) ===

@when("I visit the registration page")
def step_visit_registration_page(context):
    url = f"{BASE}/auth/register"
    context.client = httpx.Client(timeout=10)
    resp = context.client.get(url)
    assert resp.status_code == 200, f"Failed to load registration page: {resp.status_code}"
    context.csrf_token = extract_csrf_token(resp.text)
    assert context.csrf_token, "No CSRF token found on registration page"


@when("I visit the login page")
def step_visit_login_page(context):
    url = f"{BASE}/auth/login"
    context.client = httpx.Client(timeout=10)
    resp = context.client.get(url)
    assert resp.status_code == 200, f"Failed to load login page: {resp.status_code}"
    context.csrf_token = extract_csrf_token(resp.text)
    assert context.csrf_token, "No CSRF token found on login page"


@when('I fill in the registration form with the unique email and password "{password}"')
def step_fill_registration_form(context, password):
    context.form_data = {
        "email": context.email,
        "password": password,
        "confirm_password": password,
        "csrf_token": context.csrf_token,
    }


@when("I fill in the registration form with the unique email and mismatched passwords")
def step_fill_registration_form_mismatched(context):
    context.form_data = {
        "email": context.email,
        "password": "password1",
        "confirm_password": "password2",
        "csrf_token": context.csrf_token,
    }


@when("I fill in the login form with the registered credentials")
def step_fill_login_form_registered(context):
    context.form_data = {
        "email": context.registered_email,
        "password": context.registered_password,
        "csrf_token": context.csrf_token,
    }


@when('I fill in the login form with email "{email}" and password "{password}"')
def step_fill_login_form(context, email, password):
    context.form_data = {
        "email": email,
        "password": password,
        "csrf_token": context.csrf_token,
    }


@when("I submit the registration form")
def step_submit_registration_form(context):
    url = f"{BASE}/auth/register"
    resp = context.client.post(url, data=context.form_data, follow_redirects=False)
    context.response = resp
    # If redirect, follow it to get the final page content
    if resp.status_code in (302, 303):
        # record the registered credentials so subsequent login steps can use them
        try:
            context.registered_email = context.form_data.get("email")
            context.registered_password = context.form_data.get("password")
        except Exception:
            pass
        context.redirect_location = resp.headers.get("location")
        context.response_after_redirect = context.client.get(f"{BASE}{context.redirect_location}")
    else:
        context.redirect_location = None
        context.response_after_redirect = resp


@when("I submit the login form")
def step_submit_login_form(context):
    url = f"{BASE}/auth/login"
    resp = context.client.post(url, data=context.form_data, follow_redirects=False)
    context.response = resp
    if resp.status_code in (302, 303):
        context.redirect_location = resp.headers.get("location")
    else:
        context.redirect_location = None


# === Then Steps (API) ===

@then("I receive 201 Created and the user's email is returned")
def step_assert_registered(context):
    assert context.response is not None, "No response captured; ensure register step ran"
    assert context.response.status_code == 201, f"Expected 201, got {context.response.status_code}: {context.response.text}"
    data = context.response.json()
    assert data.get("email") == context.email


@then("I can login with the same credentials")
def step_login(context):
    url = f"{BASE}/api/v1/auth/login"
    resp = httpx.post(url, json={"email": context.email, "password": context.password}, timeout=10)
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    assert "access_token" in data and data.get("refresh_token") is not None
    context.access_token = data["access_token"]


# === Then Steps (Web UI) ===

@then('I should be redirected to "{path}"')
def step_should_be_redirected(context, path):
    assert context.redirect_location == path, f"Expected redirect to {path}, got {context.redirect_location}"


@then('the response should contain "{text}"')
def step_response_contains(context, text):
    # Check in either the redirect response or the original response
    content = ""
    if hasattr(context, "response_after_redirect") and context.response_after_redirect:
        content = context.response_after_redirect.text
    elif context.response:
        content = context.response.text
    assert text in content, f"Expected '{text}' in response, but got:\n{content[:500]}"
