# FastAPI Todo API - Workspace

This repository has been restructured to follow a Clean Architecture approach. Initial configuration and scaffolding were added.

## Quick start

1. Copy `.env.example` to `.env` and fill in your values.
2. Create a virtual environment and install dependencies (poetry or pip):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # or use poetry install
```

3. Run tests:

```bash
pytest -q
```

---

What's done:
- Directory structure created for domain/application/infrastructure/api/web
- `app/config.py`, `.env.example`, and `app/logging_config.py` added
- Async SQLAlchemy connection scaffold in `app/infrastructure/database/connection.py`
- Alembic skeleton in `migrations/` and `alembic.ini`
- Basic API router and endpoints scaffolded under `app/api/v1`
- CI workflow skeleton and pre-commit config
- Basic test and pytest config

Next: implement User entity persistence (SQLAlchemy models + repository) and authentication (registration/login, refresh tokens).

---

## Logging configuration 

This project supports configurable file-based logging with optional JSON formatting, rotation, and compression.

Environment variables (or `.env`) to configure logging:

- `LOG_DIR` (default: `logs`) — path where logs are written. Can be absolute or relative to the project root.
- `LOG_LEVEL` (default: `INFO`) — root logger level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `LOG_JSON` (default: `false`) — when `true`, file logs are written in structured JSON format (requires `python-json-logger` package).
- `LOG_ROTATION_TYPE` (default: `size`) — `size` (RotatingFileHandler) or `time` (TimedRotatingFileHandler).
- `LOG_MAX_BYTES` (default: `10485760`) — maximum size in bytes before rotation when using `size` rotation.
- `LOG_ROTATION_WHEN` (default: `midnight`) — time-based rotation interval when using `time` rotation (e.g., `midnight`, `D`, `H`).
- `LOG_BACKUP_COUNT` (default: `10`) — number of backups to keep.
- `LOG_COMPRESS` (default: `true`) — whether rotated files should be compressed to `.gz`.

Example `.env` entries:

LOG_DIR=logs
LOG_LEVEL=INFO
LOG_JSON=true
LOG_ROTATION_TYPE=size
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=5
LOG_COMPRESS=true

Behavior:
- Application logs are written to `app.log` in `LOG_DIR`.
- SQL statements are written to `sqlalchemy.log`.
- Uvicorn access and error logs are written to `access.log` and `error.log` respectively.
- Rotated files are compressed to `.gz` when `LOG_COMPRESS=true`.

Notes:
- When running locally you can tail logs with: `Get-Content .\\logs\\sqlalchemy.log -Wait` (PowerShell) or `tail -f logs/sqlalchemy.log` (Unix).
- Use `LOG_JSON=true` for production if you want logs to be easily ingested by log aggregation systems.

---

## Development & testing 

Forms, Flash & CSRF (developer notes)

- This project includes small helper utilities for server-side flash messages and CSRF protection located at `app/web/helpers.py`.
  - `get_csrf_token` — FastAPI dependency you can use in GET routes to ensure a per-session CSRF token exists and return it. Example:

```py
from fastapi import Depends

@router.get('/form')
async def form(request: Request, csrf: str = Depends(get_csrf_token)):
    return templates.TemplateResponse(request, 'pages/form.html', {'request': request, 'csrf_token': csrf})
```

- `validate_csrf_token(request, token)` — validate a token from the form POST; returns True/False.
- `set_flash(request, message)` / `pop_flash(request)` — set or read a one-time flash message stored in session.

Middleware vs Dependency

- A small middleware (`app.web.middleware.TemplateContextMiddleware`) is installed and will automatically:
  - Ensure a per-session CSRF token exists and expose it as `request.state.csrf_token` for templates
  - Pop a one-time flash (`request.state.flash`) from the session and make it available in templates

- When to use which:
  - Use the middleware when rendering templates (no need to explicitly pass `csrf_token` or `flash` into `TemplateResponse`). Templates can read `request.state.csrf_token` and `request.state.flash` directly.
  - Use `get_csrf_token` (FastAPI `Depends`) in route handlers when you need to explicitly require/obtain a CSRF token in programmatic handlers, or if you want to express that dependency via a function signature.

- Internals:
  - Sessions are enabled via `starlette.middleware.sessions.SessionMiddleware` in `app/main.py` using `SESSION_SECRET_KEY` (fallback to `JWT_SECRET_KEY` if unset). In production set `SESSION_SECRET_KEY` in your env for improved separation of concern.
  - Forms include a hidden `<input name="csrf_token" value="{{ request.state.csrf_token }}">` field; POST handlers validate the token and re-render the form with errors and preserved values on failure.

- Tests:
  - `tests/test_csrf.py` exercises missing/invalid CSRF behavior and asserts the HTML error string.
  - Web UI tests cover flash messages and form repopulation (`tests/test_web_pages.py`).

---

## Running Tests 

This project uses two testing frameworks:
- **pytest** — unit and integration tests (`tests/`)
- **behave** — BDD/acceptance tests (`features/`)

> **Important:** Tests require `APP_ENV=test` to enable database truncation between test runs.

### Quick Test Commands (PowerShell)

**Run the full test suite:**

```powershell
# Set APP_ENV and run all pytest tests
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest -v

# Run all behave BDD tests (requires the server to be running)
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m behave
```

**Run pytest tests:**

```powershell
# Run all tests (quiet mode)
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest -q

# Run a single test file
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest tests/test_user_registration.py -v

# Run a single test function
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest tests/test_user_registration.py::test_register_user_e2e -v

# Run tests matching a keyword
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest -k "login" -v

# Stop on first failure
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest -x

# Run with coverage report
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

**Run behave BDD tests:**

```powershell
# First, start the server in a separate terminal
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Then run behave in another terminal
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m behave

# Run with detailed output
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m behave --no-capture

# Run a specific feature file
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m behave features/auth.feature

# Run scenarios by tag
$env:APP_ENV="test"; .\.venv\Scripts\python.exe -m behave --tags=@auth
```

**Using `uv` (alternative):**

```powershell
# pytest
$env:APP_ENV="test"; uv run pytest -v

# behave
$env:APP_ENV="test"; uv run behave
```

### Test Structure

```
tests/                      # pytest unit/integration tests
├── conftest.py             # Shared fixtures
├── test_auth_*.py          # Auth-related tests
├── test_todos_crud.py      # Todo CRUD tests
├── test_web_pages.py       # Web UI tests
└── test_csrf.py            # CSRF protection tests

features/                   # behave BDD tests
├── auth.feature            # Auth scenarios (API + Web UI)
├── todos.feature           # Todo CRUD scenarios
├── environment.py          # Behave hooks (DB reset, etc.)
└── steps/                  # Step definitions
    ├── auth_steps.py
    └── todo_steps.py
```

Running the app locally:

- With `uv` (recommended if you use `uv` for dependency management):

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- With venv's Python directly:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Database & migrations:

- Apply Alembic migrations:

```powershell
uv run alembic upgrade head
# or
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Environment variables (PowerShell):

```powershell
# For integration tests that require a DB
$env:DATABASE_URL = "postgresql+asyncpg://user:password@localhost/todo_db"
# Or edit .env from the repo root and run tests
```


Writing unit tests (pytest) 

- Files: name test modules `tests/test_*.py` and test functions `test_*`.
- Async tests: use `pytest-asyncio` and decorate async test functions with `@pytest.mark.asyncio`.
- HTTP tests: use `httpx.AsyncClient` with `ASGITransport(app=app)` in fixtures (see `tests/conftest.py`).
- Fixtures: reuse `client`, `db`, and factories for test data (consider `factory_boy` for model factories).
- Assertions: keep tests deterministic and idempotent; use unique data (UUIDs) for integration tests that touch the DB.

Example async test skeleton:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_read_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/")
        assert r.status_code == 200
```

Behavior-driven tests (BDD) — `behave` 

The project includes comprehensive BDD tests covering:
- **Auth flows:** API registration/login, Web UI registration/login with CSRF and flash messages
- **Todo CRUD:** Create, list, get, update, mark complete, delete todos via API

Feature files use Gherkin syntax and live in `features/`. See the [Running Tests](#running-tests-) section above for commands.

Example feature (`features/auth.feature`):

```gherkin
Feature: User registration and login
  Scenario: Register new user and login via API
    Given the API server is reachable
    And I use a unique email
    When I POST /api/v1/auth/register with valid payload
    Then I receive 201 Created and the user's email is returned
    And I can login with the same credentials
```

Testing tips
- Use `pytest -k <expr>` to run a subset of tests by keyword.
- Mark long-running integration tests with a custom marker (e.g., `@pytest.mark.integration`) and skip unless `DATABASE_URL` is set.
- Use factories and fixtures to keep tests readable and maintainable.

Linting & formatting 

- Formatting: `black .` — automatic code formatting
- Linting:
  - `flake8` for style and quick checks
  - `pylint` for more thorough static analysis

Commands (examples):

```powershell
uv run black .
uv run flake8
uv run pylint app
```

Makefile targets

- `make test` — run all tests
- `make test-file FILE=path/to/test.py` — run a single file
- `make test-bdd` — run behave features
- `make lint` — run both pylint and flake8
- `make format` — run `black` across the repo
- `make migrate` — apply alembic migrations

Tips
- If a test uses the DB, ensure `DATABASE_URL` is set and the DB is accessible; many integration tests are skipped when `DATABASE_URL` is not set.
- Use `LOG_JSON=true` in `.env` for structured logs in production.

---

DB reset safety & CI ephemeral DB

To avoid accidental truncation of non-test databases, the BDD environment includes safety checks.

- Automatic DB truncation between scenarios will only run if **one of** the following is true:
  - `APP_ENV` is set to `test`, OR
  - `DATABASE_URL` contains the substring `test`, OR
  - `BEHAVE_TEST_DB` environment variable is set, OR
  - `BEHAVE_FORCE=true` (unsafe; use only for debugging)

- For CI, use `make behave-ci` which will:
  1. Create an ephemeral Postgres database derived from your `DATABASE_URL` (requires create/drop privileges) — or if you prefer, use `createdb`/`dropdb` by setting `BEHAVE_USE_CREATEDB=true`.
  2. Run `alembic upgrade head` against the ephemeral DB
  3. Run `behave` with `DATABASE_URL` and `BEHAVE_TEST_DB` set to the ephemeral DB
  4. Drop the ephemeral DB when done (best-effort)

Usage example (CI):

```bash
# Ensure DATABASE_URL points to a Postgres server where the user can create databases.
# Option A: Allow script to create a random ephemeral DB
make behave-ci

# Option B: Use createdb/dropdb and a deterministic test DB name (e.g., todo_db -> todo_db_test)
BEHAVE_USE_CREATEDB=true make behave-ci

# Option C: Provide a specific test DB name
BEHAVE_TEST_DB_NAME=todo_db_test make behave-ci
```

Notes:
- The `behave-ci` script uses either `psycopg2` (default) or system `createdb`/`dropdb` when `BEHAVE_USE_CREATEDB=true`.
- If your DB user lacks create/drop privileges you can instead create a dedicated test DB in CI and set `DATABASE_URL` to point to it before running `make behave-ci`.
- The script runs migrations in the ephemeral DB before running behave so you get a realistic schema state.

