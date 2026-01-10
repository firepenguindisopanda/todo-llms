FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# system deps for building binary packages (psycopg2) and general tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy project files needed for dependency install (cache layer)
COPY pyproject.toml /app/

# upgrade pip and install runtime deps (keeps image simple & explicit)
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
        "uvicorn[standard]" \
        "fastapi[standard]" \
        "python-jose[cryptography]" \
        "passlib[bcrypt]" \
        "sqlalchemy[asyncio]" \
        "asyncpg>=0.29.0" \
        "alembic" \
        "psycopg2-binary" \
        "pydantic-settings" \
        "python-dotenv" \
        "slowapi" \
        "structlog" \
        "email-validator" \
        "python-json-logger" \
        "itsdangerous"

# copy application
COPY . /app

EXPOSE 8000

# Use PORT env var if provided by the platform (Vercel sets it), fallback to 8000
CMD ["sh", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --loop uvloop --http httptools"]
