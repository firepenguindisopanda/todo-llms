from logging.config import fileConfig
import os
import sys
# Ensure project root is on sys.path so `app` package imports work when running alembic
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support import your Base and set target_metadata
from app.infrastructure.database.models import Base
from app.config import settings

# Set sqlalchemy.url dynamically from application settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired: config.get_main_option("some.option")
# and can be set here as well; e.g. config.set_main_option("sqlalchemy.url", "")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    url = config.get_main_option("sqlalchemy.url")

    # If using an async driver (asyncpg), use an AsyncEngine and run migrations in an
    # asyncio event loop. Otherwise fall back to the sync engine.
    if url and "+asyncpg" in url:
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncio

        connectable = create_async_engine(url, poolclass=pool.NullPool, future=True)

        async def run_async_migrations():
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)

        def do_run_migrations(connection):
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()

        asyncio.run(run_async_migrations())
    else:
        connectable = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
