# Makefile for common developer tasks

.PHONY: help install test test-unit test-bdd test-file lint lint-flake8 lint-pylint format run run-uv migrate migrate-up logs-tail clean-logs

help:
	@echo "Available targets:"
	@echo "  install        - sync project deps with uv"
	@echo "  test           - run full pytest suite"
	@echo "  test-unit      - run pytest (non-BDD tests)"
	@echo "  test-bdd       - run BDD tests (behave)"
	@echo "  test-file      - run pytest for a specific file: make test-file FILE=tests/test_x.py"
	@echo "  lint           - run pylint and flake8"
	@echo "  format         - format code with black"
	@echo "  run            - run uvicorn with uv"
	@echo "  run-uv         - run uvicorn using venv python"
	@echo "  migrate        - run alembic upgrade head"
	@echo "  logs-tail      - tail logs (platform dependent)"
	@echo "  clean-logs     - remove rotated/compressed logs in logs dir"

install:
	uv sync

# Run each test target through the project's uv runner so the project venv is used
test:
	uv run pytest -q

test-unit:
	uv run pytest -q -m "not bdd"

test-bdd:
	uv run behave

# Example: make test-file FILE=tests/test_user_registration.py
test-file:
	if [ -z "$(FILE)" ]; then echo "Please provide FILE=path/to/test_file.py"; exit 1; fi
	uv run pytest -q $(FILE)

lint:
	uv run pylint app || true
	uv run flake8 || true

lint-flake8:
	uv run flake8

lint-pylint:
	uv run pylint app

format:
	uv run black .

# Run server
run:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run-uv:
	.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Database migrations
migrate:
	uv run alembic upgrade head

migrate-up:
	.\.venv\Scripts\python.exe -m alembic upgrade head

behave-ci:
	.\.venv\Scripts\python.exe scripts\behave_ci.py

# Tail logs (platform dependent)
logs-tail:
	@echo "On Unix: tail -f logs/app.log"
	@echo "On Windows PowerShell: Get-Content .\\logs\\app.log -Wait"

clean-logs:
	@echo "Removing rotated/compressed logs in logs/"
	rm -f logs/*.gz || true
	rm -f logs/*.1 || true
