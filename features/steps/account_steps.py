from behave import given, when, then
import re

BASE = "http://test"


@when('I visit the account page')
def step_visit_account(context):
    r = context.client.get(f"/account")
    context.response = r


@when('I register and login using the web UI')
def step_register_and_login_web(context):
    # Register
    r = context.client.get('/auth/register')
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    assert m
    csrf = m.group(1)
    # choose a unique email if not already set
    import uuid
    email = getattr(context, 'registered_email', f'web_{uuid.uuid4().hex[:8]}@example.com')
    context.registered_email = email
    r2 = context.client.post('/auth/register', data={'email': email, 'password': 'secret123', 'confirm_password': 'secret123', 'csrf_token': csrf})
    # Login
    r = context.client.get('/auth/login')
    m = re.search(r'name="csrf_token" value="([^\"]+)"', r.text)
    assert m
    csrf = m.group(1)
    r3 = context.client.post('/auth/login', data={'email': email, 'password': 'secret123', 'csrf_token': csrf})
    context.response = r3


@when('I set display mode to "{mode}" and items per page to "{num}"')
def step_set_prefs(context, mode, num):
    # find csrf
    m = re.search(r'name="csrf_token" value="([^\"]+)"', context.response.text)
    assert m
    csrf = m.group(1)
    r = context.client.post("/account", data={"display_mode": mode, "items_per_page": num, "csrf_token": csrf})
    context.response = r


@then('the account page should contain "{text}"')
def step_account_contains(context, text):
    assert text in context.response.text


@then('I should be redirected to "{path}"')
def step_redirected(context, path):
    # check Location header
    assert context.response.status_code in (302, 303)
    loc = context.response.headers.get("location")
    assert loc == path
