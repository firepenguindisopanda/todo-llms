import uuid
import os
import re
import httpx
from behave import given, when, then


BASE = os.environ.get("BEHAVE_BASE_URL", "http://127.0.0.1:8000")


# === Given Steps ===

@given("I have a registered user and access token")
def step_have_registered_user(context):
    # Register a unique user
    context.email = f"bdd_todo_{uuid.uuid4().hex[:8]}@example.com"
    context.password = "todopw123"
    
    # Register
    url = f"{BASE}/api/v1/auth/register"
    resp = httpx.post(url, json={"email": context.email, "password": context.password}, timeout=10)
    assert resp.status_code == 201, f"Registration failed: {resp.status_code} {resp.text}"
    
    # Login to get access token
    url = f"{BASE}/api/v1/auth/login"
    resp = httpx.post(url, json={"email": context.email, "password": context.password}, timeout=10)
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    data = resp.json()
    context.access_token = data["access_token"]
    context.auth_headers = {"Authorization": f"Bearer {context.access_token}"}
    context.created_todos = []


@given('I have created a todo with title "{title}"')
def step_have_created_todo(context, title):
    url = f"{BASE}/api/v1/todos/"
    payload = {"title": title, "description": f"Description for {title}"}
    resp = httpx.post(url, json=payload, headers=context.auth_headers, timeout=10, follow_redirects=True)
    assert resp.status_code == 201, f"Failed to create todo: {resp.status_code} {resp.text}"
    todo = resp.json()
    context.todo_id = todo["id"]
    context.created_todos.append(todo)


# === When Steps ===

@when('I create a todo with title "{title}" and description "{description}"')
def step_create_todo(context, title, description):
    url = f"{BASE}/api/v1/todos/"
    payload = {"title": title, "description": description}
    resp = httpx.post(url, json=payload, headers=context.auth_headers, timeout=10, follow_redirects=True)
    context.response = resp
    if resp.status_code == 201:
        context.todo_id = resp.json()["id"]


@when("I list all my todos")
def step_list_todos(context):
    url = f"{BASE}/api/v1/todos/"
    resp = httpx.get(url, headers=context.auth_headers, timeout=10, follow_redirects=True)
    context.response = resp


@when("I get the todo by ID")
def step_get_todo_by_id(context):
    url = f"{BASE}/api/v1/todos/{context.todo_id}"
    resp = httpx.get(url, headers=context.auth_headers, timeout=10)
    context.response = resp


@when('I update the todo title to "{title}"')
def step_update_todo_title(context, title):
    url = f"{BASE}/api/v1/todos/{context.todo_id}"
    payload = {"title": title}
    resp = httpx.put(url, json=payload, headers=context.auth_headers, timeout=10)
    context.response = resp


@when("I mark the todo as completed")
def step_mark_todo_completed(context):
    url = f"{BASE}/api/v1/todos/{context.todo_id}"
    payload = {"completed": True}
    resp = httpx.put(url, json=payload, headers=context.auth_headers, timeout=10)
    context.response = resp


@when("I delete the todo")
def step_delete_todo(context):
    url = f"{BASE}/api/v1/todos/{context.todo_id}"
    resp = httpx.delete(url, headers=context.auth_headers, timeout=10)
    context.response = resp
    context.deleted_todo_id = context.todo_id


# === Web UI steps for dashboard ===
@when("I visit the dashboard page")
def step_visit_dashboard(context):
    url = f"{BASE}/dashboard"
    # reuse existing client if one exists so cookies (refresh_token) persist
    if not hasattr(context, "client") or context.client is None:
        context.client = httpx.Client(timeout=10)
    resp = context.client.get(url)
    assert resp.status_code == 200, f"Failed to load dashboard: {resp.status_code}"
    context.csrf_token = None
    # extract CSRF token if present
    m = re.search(r'name="csrf_token" value="([^"]+)"', resp.text)
    if m:
        context.csrf_token = m.group(1)


@when('I create a todo via the dashboard with title "{title}" and description "{description}"')
def step_create_todo_via_dashboard(context, title, description):
    url = f"{BASE}/todos/create"
    data = {"title": title, "description": description}
    if getattr(context, "csrf_token", None):
        data["csrf_token"] = context.csrf_token
    resp = context.client.post(url, data=data, follow_redirects=False)
    context.response = resp
    if resp.status_code in (302, 303):
        context.redirect_location = resp.headers.get("location")
        context.response_after_redirect = context.client.get(f"{BASE}{context.redirect_location}")
    else:
        context.redirect_location = None
        context.response_after_redirect = resp

# === Then Steps ===

@then("the todo should be created successfully")
def step_todo_created(context):
    assert context.response.status_code == 201, f"Expected 201, got {context.response.status_code}: {context.response.text}"


@then('the response should include the todo title "{title}"')
def step_response_includes_title(context, title):
    data = context.response.json()
    assert data.get("title") == title, f"Expected title '{title}', got '{data.get('title')}'"


@then('I should see {count:d} todos in the list')
def step_see_todos_count(context, count):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"
    data = context.response.json()
    # Handle paginated response or list
    if isinstance(data, list):
        todos = data
    elif isinstance(data, dict) and "items" in data:
        todos = data["items"]
    else:
        todos = data
    assert len(todos) >= count, f"Expected at least {count} todos, got {len(todos)}"


@then("the todo should be updated successfully")
def step_todo_updated(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}: {context.response.text}"


@then("the todo should show completed status")
def step_todo_completed_status(context):
    assert context.response.status_code == 200, f"Expected 200, got {context.response.status_code}"
    data = context.response.json()
    assert data.get("completed") is True, f"Expected completed=True, got {data.get('completed')}"


@then("the todo should be deleted successfully")
def step_todo_deleted(context):
    assert context.response.status_code == 204, f"Expected 204, got {context.response.status_code}: {context.response.text}"


@then("the todo should no longer exist")
def step_todo_not_exist(context):
    url = f"{BASE}/api/v1/todos/{context.deleted_todo_id}"
    resp = httpx.get(url, headers=context.auth_headers, timeout=10)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
