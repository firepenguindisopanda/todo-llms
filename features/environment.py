import os
import httpx
import asyncio
from sqlalchemy import text
from app.config import settings
from app.infrastructure.database.connection import engine


def before_all(context):
    context.base_url = os.environ.get("BEHAVE_BASE_URL", "http://127.0.0.1:8000")

    # quick smoke check — warn if server not reachable
    try:
        r = httpx.get(f"{context.base_url}/", timeout=3)
        if r.status_code != 200:
            print(f"Warning: server returned {r.status_code} for {context.base_url}/ — start uvicorn before running behave")
    except Exception as exc:
        print(f"Warning: could not reach server at {context.base_url}: {exc}\nStart uvicorn (e.g. `uv run uvicorn app.main:app --reload`) before running behave")


def _truncate_public_tables():
    """Async helper to truncate all public tables except alembic_version.

    Safety checks:
    - Requires APP_ENV=test OR DATABASE_URL to contain the word 'test' OR BEHAVE_TEST_DB env var
    - You can bypass the safety checks with BEHAVE_FORCE=true (use carefully)
    """
    if engine is None:
        print("No DATABASE_URL configured; skipping DB reset.")
        return

    # Safety checks to avoid accidental truncation of prod DBs
    app_env = os.environ.get("APP_ENV", os.environ.get("FASTAPI_ENV", settings.APP_ENV))
    db_url = os.environ.get("BEHAVE_TEST_DB") or str(settings.DATABASE_URL)
    force = os.environ.get("BEHAVE_FORCE") == "true"

    if not force:
        if app_env != "test" and (not db_url or "test" not in db_url):
            raise RuntimeError(
                "DB reset safety check failed. Set APP_ENV=test or provide BEHAVE_TEST_DB pointing to a test database, or set BEHAVE_FORCE=true to override (not recommended)."
            )

    async def _do_truncate():
        async with engine.begin() as conn:
            # Get all user tables in public schema
            res = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
            rows = res.fetchall()
            tables = [r[0] for r in rows if r[0] != "alembic_version"]
            if not tables:
                return
            tbl_list = ", ".join(f'"{t}"' for t in tables)
            sql = f"TRUNCATE TABLE {tbl_list} RESTART IDENTITY CASCADE;"
            await conn.execute(text(sql))

    try:
        asyncio.run(_do_truncate())
        # simple confirmation print for debug convenience
        print("Database reset: truncated public tables")
    except Exception as exc:
        print(f"Warning: failed to reset database: {exc}")


def before_scenario(context, scenario):
    # Reset DB before each scenario to ensure a clean state.
    if os.environ.get("SKIP_DB_RESET"):
        print("SKIP_DB_RESET set; not truncating DB between scenarios")
    else:
        _truncate_public_tables()


def after_scenario(context, scenario):
    # Optionally reset after scenario as well to ensure no leftovers
    if not os.environ.get("SKIP_DB_RESET"):
        _truncate_public_tables()