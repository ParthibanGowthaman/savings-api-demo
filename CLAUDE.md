# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Savings Account API — a RESTful API for managing savings accounts built with FastAPI. Supports account creation, deposits, withdrawals, balance inquiries, and interest calculations.

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI with Uvicorn
- **Database**: PostgreSQL with SQLAlchemy (async) and Alembic for migrations
- **Testing**: pytest with pytest-asyncio, pytest-cov
- **Linting**: ruff

## Architecture

REST API using the **repository pattern**:

```
app/
├── main.py              # FastAPI app entrypoint
├── api/                 # Route handlers (thin controllers)
│   └── v1/
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── repositories/        # Database access layer (all SQL lives here)
├── services/            # Business logic layer
├── core/                # Config, security, dependencies
└── db/                  # Database session, Alembic migrations
tests/
├── conftest.py          # Shared fixtures (test DB, async client)
├── unit/
└── integration/
```

- **Routes** → **Services** → **Repositories** → **Database**
- Routes handle HTTP concerns only (status codes, response models)
- Services contain business logic and validation
- Repositories encapsulate all database queries — no raw SQL in services or routes

## Run Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start dev server
uvicorn app.main:app --reload --port 8000

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_account_service.py

# Run a single test by name
pytest -k "test_withdraw_insufficient_funds"

# Run tests with coverage
pytest --cov=app --cov-report=term-missing --cov-fail-under=80

# Lint
ruff check .

# Format
ruff format .

# Run database migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"
```

## Coding Standards

- **Type hints are required** on all function signatures (parameters and return types)
- Follow PEP 8 — enforced by ruff
- Use `async def` for all route handlers and database operations
- Pydantic models for all API input/output — no raw dicts in responses
- Use dependency injection via FastAPI's `Depends()` for services and repos

## Common Mistakes to Avoid

- **Always use `Decimal` (not `float`) for monetary values.** This applies everywhere: models, schemas, services, tests. Use `from decimal import Decimal` and configure Pydantic fields with `Decimal` type.
- **Never commit directly to `main`.** Always work on a feature branch and open a PR.
- Do not put business logic in route handlers — it belongs in the service layer.
- Do not import repository functions directly in routes — go through services.
- Do not use synchronous database calls — always use async SQLAlchemy sessions.

## Testing

- Every new feature or bugfix must include tests
- Minimum **80% code coverage** enforced (`--cov-fail-under=80`)
- Unit tests for services (mock the repository layer)
- Integration tests for API endpoints (use `httpx.AsyncClient` with a test database)
- Use factories or fixtures for test data — no hardcoded IDs
- Test both success paths and error cases (validation errors, not found, insufficient funds, etc.)

## PR Guidelines

- PR titles should be concise and descriptive
- PR descriptions must explain **why** the change is being made, not just what changed
- Link to the relevant issue if one exists
- Include test plan or evidence that tests pass
