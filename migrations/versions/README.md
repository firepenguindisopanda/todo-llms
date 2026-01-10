This folder will contain Alembic revision files (created by `alembic revision --autogenerate -m "message"`).

Workflow example:

1. Ensure `DATABASE_URL` is set in `.env` (e.g. `postgresql+asyncpg://user:pass@localhost:5432/todo_db`).
2. Create the DB if it doesn't exist (see project README for example).
3. Run `alembic revision --autogenerate -m "create users and todos"` to create initial migration.
4. Run `alembic upgrade head` to apply migrations.

Note: We intentionally left out `is_verified` on the `users` table so you can add it to `user_model.py`, run `alembic revision --autogenerate -m "add is_verified"` and observe the generated migration that adds the column.
