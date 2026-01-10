"""Create an ephemeral test DB, migrate it, run behave, then drop the DB.

Usage (from repo root):
.\.venv\Scripts\python.exe scripts\behave_ci.py

Requirements: PostgreSQL server reachable via DATABASE_URL environment variable. The user
in DATABASE_URL must have permission to create/drop databases.

This script:
- Reads DATABASE_URL from env
- Creates a new DB with a unique name derived from the original DB
- Sets DATABASE_URL and BEHAVE_TEST_DB to the new DB for the subprocesses
- Runs `alembic upgrade head`
- Runs `behave`
- Drops the ephemeral DB afterward

If anything fails, the DB is dropped in a best-effort finally block.
"""
from __future__ import annotations

import os
import sys
import uuid
import subprocess
import urllib.parse
import time
import shutil

try:
    import psycopg2
except Exception:
    print("psycopg2 is required for scripts/behave_ci.py. Ensure psycopg2-binary is installed.")
    raise


def parse_db_url(url: str):
    p = urllib.parse.urlparse(url)
    # scheme might be 'postgresql+asyncpg' -> use 'postgresql' for psycopg2
    scheme = p.scheme.split("+")[0]
    if scheme not in ("postgresql", "postgres"):
        raise RuntimeError("Only PostgreSQL DATABASE_URL is supported for behave-ci")
    user = urllib.parse.unquote(p.username) if p.username else None
    password = urllib.parse.unquote(p.password) if p.password else None
    host = p.hostname or "localhost"
    port = p.port or 5432
    dbname = p.path.lstrip("/")
    return dict(user=user, password=password, host=host, port=port, dbname=dbname)


def make_admin_conn_info(parsed):
    # Connect to the server-level DB (postgres) to run CREATE/DROP
    return dict(user=parsed["user"], password=parsed["password"], host=parsed["host"], port=parsed["port"], dbname="postgres")


def create_database(admin_conn_info, new_db_name, owner=None):
    # Optionally use system `createdb` if requested via env var
    use_createdb = os.environ.get("BEHAVE_USE_CREATEDB", "false").lower() == "true"
    host = admin_conn_info.get("host")
    port = admin_conn_info.get("port")
    user = admin_conn_info.get("user")
    password = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD") or ""

    if use_createdb:
        cmd = [
            "createdb",
            "-h",
            host,
            "-p",
            str(port),
            "-U",
            user,
            new_db_name,
        ]
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        print("Creating DB via createdb command")
        run_subprocess(cmd, env=env)
        print(f"Created test DB {new_db_name} (createdb)")
        return

    # Fallback to psycopg2
    conn = psycopg2.connect(**admin_conn_info)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        sql = f"CREATE DATABASE \"{new_db_name}\""
        if owner:
            sql += f" OWNER \"{owner}\""
        cur.execute(sql)
        cur.close()
        print(f"Created test DB {new_db_name}")
    finally:
        conn.close()


def drop_database(admin_conn_info, db_name):
    # Optionally use system `dropdb` if requested via env var
    use_dropdb = os.environ.get("BEHAVE_USE_CREATEDB", "false").lower() == "true"
    host = admin_conn_info.get("host")
    port = admin_conn_info.get("port")
    user = admin_conn_info.get("user")
    password = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD") or ""

    if use_dropdb:
        cmd = ["dropdb", "--if-exists", "-h", host, "-p", str(port), "-U", user, db_name]
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        try:
            run_subprocess(cmd, env=env)
            print(f"Dropped test DB {db_name} (dropdb)")
            return
        except Exception as exc:
            print(f"dropdb failed: {exc}; falling back to psycopg2 drop")

    # Fallback to psycopg2 drop (terminate connections, then drop)
    conn = psycopg2.connect(**admin_conn_info)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        # terminate connections
        cur.execute(f"SELECT pid, pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (db_name,))
        cur.execute(f"DROP DATABASE IF EXISTS \"{db_name}\"")
        cur.close()
        print(f"Dropped test DB {db_name}")
    finally:
        conn.close()

def run_subprocess(cmd, env=None):
    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)} (rc={r.returncode})")


def main():
    base_url = os.environ.get("DATABASE_URL") or os.environ.get("BEHAVE_BASE_DATABASE_URL")
    if not base_url:
        print("DATABASE_URL must be set in the environment to run behave-ci")
        sys.exit(1)

    parsed = parse_db_url(base_url)
    admin_info = make_admin_conn_info(parsed)

    orig_db = parsed["dbname"]
    # Determine test DB name:
    # - If BEHAVE_TEST_DB_NAME provided, use it
    # - If BEHAVE_USE_CREATEDB=true, default to a predictable suffix (e.g., todo_db -> todo_db_test)
    # - Otherwise, create a unique ephemeral name
    env_test_name = os.environ.get("BEHAVE_TEST_DB_NAME")
    use_createdb = os.environ.get("BEHAVE_USE_CREATEDB", "false").lower() == "true"
    if env_test_name:
        new_db_name = env_test_name
    elif use_createdb:
        new_db_name = f"{orig_db}_test"
    else:
        new_db_name = f"{orig_db}_behave_{uuid.uuid4().hex[:8]}"

    vendor_user = parsed.get("user")

    try:
        # If using createdb/dropdb mode, ensure the tools are available
        if use_createdb:
            if shutil.which("createdb") is None or shutil.which("dropdb") is None:
                raise RuntimeError(
                    "BEHAVE_USE_CREATEDB=true, but 'createdb' and/or 'dropdb' are not available on PATH. "
                    "Install PostgreSQL client tools (e.g., 'postgresql-client' on Debian/Ubuntu, or ensure 'createdb'/'dropdb' are on PATH), "
                    "or unset BEHAVE_USE_CREATEDB."
                )

        create_database(admin_info, new_db_name, owner=vendor_user)

        # Construct asyncpg-compatible DATABASE_URL for SQLAlchemy
        scheme = "postgresql+asyncpg"
        user = urllib.parse.quote(parsed["user"]) if parsed.get("user") else ""
        pw = urllib.parse.quote(parsed["password"]) if parsed.get("password") else ""
        host = parsed["host"]
        port = parsed["port"]
        new_db_url = f"{scheme}://{user}:{pw}@{host}:{port}/{new_db_name}"

        # Prepare environment for subprocesses
        env = os.environ.copy()
        env["DATABASE_URL"] = new_db_url
        env["BEHAVE_TEST_DB"] = new_db_url
        env["APP_ENV"] = env.get("APP_ENV", "test")

        # 1) Run migrations
        venv_python = os.path.join(os.path.dirname(sys.executable), os.path.basename(sys.executable))
        # Use -m alembic to pick up alembic in the venv
        run_subprocess([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)

        # 2) Run behave
        run_subprocess([sys.executable, "-m", "behave"], env=env)

    except Exception as exc:
        print(f"behave-ci error: {exc}")
        raise

    finally:
        # Best-effort drop DB
        try:
            drop_database(admin_info, new_db_name)
        except Exception as exc:
            print(f"Failed to drop temp DB {new_db_name}: {exc}")


if __name__ == "__main__":
    main()
