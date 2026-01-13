"""Manual Redis check script

Runs a small sequence against the application (in-process ASGI) to verify
that /api/v1/auth/me is cached in Redis and that cache invalidation works.

Usage:
  - Set env vars as needed (UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN, DATABASE_URL)
  - Run:
      .venv\Scripts\python scripts/manual_redis_check.py

The script runs the app in-process (no uvicorn required) so it works in dev
without starting the server.
"""

import asyncio
import os
import sys
import pathlib
import uuid
import json
import logging

# allow running this script from the repo root
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from app.infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger("manual_redis_check")
logging.basicConfig(level=logging.INFO)


def _maybe_await(val):
    if asyncio.iscoroutine(val):
        return awaitable(val)
    return val


async def awaitable(coro):
    return await coro


async def main():
    base_url = os.getenv("BASE_URL", "http://test")  # httpx ASGI base

    # use the app in-process (ASGI) if running inside the repo
    try:
        from app.main import app
        # httpx versions vary: some support AsyncClient(app=app), others need ASGITransport
        try:
            client = httpx.AsyncClient(app=app, base_url=base_url)
        except TypeError:
            # fallback to ASGITransport
            try:
                from httpx._transports.asgi import ASGITransport
            except Exception:
                from httpx._transports.asgi import ASGITransport  # try again, keep exception visible to user
            client = httpx.AsyncClient(transport=ASGITransport(app=app), base_url=base_url)
        logger.info("Using in-process ASGI app (httpx AsyncClient).")
    except Exception as e:
        logger.warning("Could not import app in-process: %s. Will try live server at %s", e, base_url)
        client = httpx.AsyncClient(base_url=os.getenv("BASE_URL_REAL", "http://localhost:8000"))

    email = f"manual_{uuid.uuid4().hex[:8]}@example.com"
    password = "secret123"

    async with client:
        print("Registering user", email)
        r = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
        print("  register status:", r.status_code, r.text[:200])
        if r.status_code not in (201, 200):
            print("Register failed; aborting.")
            return

        # login
        rlogin = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        print("  login status:", rlogin.status_code)
        if rlogin.status_code != 200:
            print("Login failed; aborting.")
            return
        token = rlogin.json().get("access_token")
        if not token:
            print("No access token returned; aborting.")
            return

        headers = {"authorization": f"Bearer {token}"}

        # initial /me to populate cache
        rme = await client.get("/api/v1/auth/me", headers=headers)
        print("  /me status:", rme.status_code)
        if rme.status_code != 200:
            print("/me failed; aborting.")
            return
        data = rme.json()
        user_id = data.get("id")
        old_email = data.get("email")
        print("  user:", user_id, old_email)

        # check redis client presence
        rc = get_redis_client()
        if not rc:
            print("Redis client not available (no UPSTASH creds or package); behavior will reflect DB directly.")
        else:
            print("Redis client available. Checking cache key: user:%s" % user_id)
            try:
                val = rc.get(f"user:{user_id}")
                # upstash-redis get returns str or may be awaitable
                if asyncio.iscoroutine(val):
                    val = await val
                print("  raw cached value:", val)
            except Exception as e:
                print("  error reading cache key:", e)

        # change DB directly if possible (requires DATABASE_URL set)
        if os.getenv("DATABASE_URL"):
            print("Updating DB email directly to verify cache behavior...")
            try:
                from app.infrastructure.database.connection import AsyncSessionLocal
                from app.infrastructure.database.models.user_model import User as UserModel
                from sqlalchemy import select

                async with AsyncSessionLocal() as s:
                    res = await s.execute(select(UserModel).where(UserModel.id == user_id))
                    db_user = res.scalar_one_or_none()
                    if not db_user:
                        print("User not found in DB; aborting DB update.")
                    else:
                        new_email = f"changed_{uuid.uuid4().hex[:8]}@example.com"
                        db_user.email = new_email
                        await s.flush()
                        await s.commit()
                        print("  DB email changed to:", new_email)
            except Exception as e:
                print("  error updating DB:", e)
        else:
            print("DATABASE_URL not set; skipping direct DB change." )

        # re-fetch /me
        r2 = await client.get("/api/v1/auth/me", headers=headers)
        print("  second /me status:", r2.status_code)
        if r2.status_code != 200:
            print("/me failed on second fetch; aborting.")
            return
        data2 = r2.json()
        print("  second /me email:", data2.get("email"))

        if rc:
            # if cache exists and still contains old email, that's expected. If not, maybe TTL was low.
            cached = None
            try:
                cached = rc.get(f"user:{user_id}")
                if asyncio.iscoroutine(cached):
                    cached = await cached
            except Exception:
                cached = None

            print("  cache after DB change:", cached)

            if cached and data2.get("email") == old_email:
                print("Cached value served as expected.")
                # invalidate cache and re-check
                try:
                    rc.delete(f"user:{user_id}")
                    print("  cache key deleted.")
                except Exception as e:
                    print("  error deleting cache key:", e)

                r3 = await client.get("/api/v1/auth/me", headers=headers)
                print("  after deletion /me email:", r3.json().get("email"))
                if r3.json().get("email") != old_email:
                    print("Success: DB value now returned after cache eviction.")
                else:
                    print("Unexpected: still returning cached value after deletion.")
            else:
                print("Cache not present or returned DB value; behavior may be uncached or TTL expired.")
        else:
            if data2.get("email") != old_email:
                print("Success: /me returned updated DB email (no Redis configured).")
            else:
                print("Unexpected: email unchanged though no cache client present.")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
