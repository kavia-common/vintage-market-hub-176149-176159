# Ecommerce Backend - Database Setup, Migrations, and Seeding

## Overview
This backend uses FastAPI, SQLAlchemy 2.x, and Alembic for migrations, backed by PostgreSQL. Configuration is read from environment variables via Pydantic Settings. This guide explains how to configure the database connection, run migrations, seed initial data (regions and categories), and set up Stripe in test mode.

## Prerequisites
- Python 3.11+ with pip
- PostgreSQL 13+ reachable from your environment
- Recommended: a virtual environment

Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### Environment variables
The application reads configuration from environment variables (via src/core/config.py). Create an .env file in ecommerce_backend (same directory as this README) with at least:

```env
# Database: you can use DATABASE_URL or individual parts (see below)
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME

# Security / JWT
JWT_SECRET=replace-with-a-long-random-string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# CORS
# Comma-separated list (no spaces) or JSON-style list. Leave empty to allow all in dev.
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Payments
PAYMENT_PROVIDER=stripe
# For Stripe test mode, set your test secret key (starts with sk_test_)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
# If receiving webhooks locally (via Stripe CLI), set webhook secret from the CLI output (starts with whsec_)
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxx

# File storage (stubbed local storage by default)
FILE_STORAGE_PROVIDER=local
FILE_STORAGE_DIR=./storage

# Misc
ENVIRONMENT=development
DEBUG=true
```

Required variables to run the app:
- DATABASE_URL: PostgreSQL connection string using psycopg2 driver.
- JWT_SECRET: Secret used to sign JWTs.
- CORS_ORIGINS: Comma-separated list of allowed origins, or leave empty in development to allow all.
- PAYMENT_PROVIDER: Typically stripe. If stripe keys are not set, the payments service falls back to a mock intent with test behavior.
- STRIPE_SECRET_KEY: Required to create real test mode intents via Stripe. If not set, a mock provider response is used.
- STRIPE_WEBHOOK_SECRET: Required to verify Stripe webhooks cryptographically; otherwise webhooks are accepted in test/unverified mode.

Note on DATABASE_URL format:
- Example: postgresql+psycopg2://myuser:mypassword@localhost:5432/mydb
- Ensure the psycopg2-binary package is installed (already in requirements.txt).

If you prefer individual DB_* parts (compose-style), construct DATABASE_URL accordingly before launching. This project expects DATABASE_URL to be present at runtime.

## Database Migrations (Alembic)

Alembic is configured in:
- alembic.ini
- alembic/env.py (overrides sqlalchemy.url from .env via Settings)
- alembic/versions/* (initial migration provided)

Common commands (run from ecommerce_backend):

- Upgrade to latest:
```bash
make migrate
# or
python -m alembic upgrade head
```

- Downgrade one revision:
```bash
python -m alembic downgrade -1
```

- Create a new revision after changing models:
```bash
make makemigration m="describe your changes"
# then apply
make migrate
```

## Seeding Regions and Categories

Seeding utilities are implemented in src/core/seed.py and exposed via a simple CLI in src/manage.py.

- Seed only:
```bash
make seed
# or
python -m src.manage seed
```

- Migrate and seed in sequence:
```bash
make migrate_and_seed
# or
python -m src.manage migrate_and_seed
```

Seeding is idempotent: it inserts only missing regions and categories. It is safe to re-run.

## Stripe Test Mode Notes

- To use real Stripe test mode, set STRIPE_SECRET_KEY to your test secret key (sk_test_...) and keep PAYMENT_PROVIDER=stripe.
- If STRIPE_SECRET_KEY is unset or the stripe library is unavailable, the payments service returns a mock PaymentIntentResult with provider=mock or stripe, a synthetic payment_intent_id, and a mock client_secret. This is suitable for local UI workflows without contacting Stripe.
- To verify webhooks cryptographically, set STRIPE_WEBHOOK_SECRET. Without it, webhooks are accepted in test mode but marked unverified.
- Example using Stripe CLI for local webhooks:
  - stripe listen --forward-to localhost:8000/api/v1/webhooks/payments
  - Use the printed webhook signing secret for STRIPE_WEBHOOK_SECRET.

## Example End-to-End (Local)
1) Create .env with correct DATABASE_URL, JWT_SECRET, and optionally Stripe keys.
2) Install deps:
```bash
pip install -r requirements.txt
```
3) Apply migrations:
```bash
make migrate
```
4) Seed defaults:
```bash
make seed
```
5) Start the API (example):
```bash
uvicorn src.api.main:app --reload --port 8000
```

## Troubleshooting

- Connection refused to Postgres:
  - Confirm HOST and PORT in DATABASE_URL.
  - Ensure Postgres is running and accessible from your environment.
  - Verify that your user/password and database name are correct and that the user has privileges.

- Missing driver / No module named psycopg2:
  - Ensure psycopg2-binary is installed: pip install psycopg2-binary
  - Confirm your DATABASE_URL uses the psycopg2 driver: postgresql+psycopg2://...

- SSL / certificate issues:
  - If your Postgres requires SSL params, include them in the connection string (e.g., ?sslmode=require).

- Timezone issues:
  - Models use timezone-aware DateTime. Ensure your application and database timezone settings are consistent as needed.

- UUID support:
  - The models use PostgreSQL UUID type via sqlalchemy.dialects.postgresql.UUID. No special extension installation is required when using SQLAlchemy with PostgreSQL, but ensure your database supports UUID (standard in modern PostgreSQL).

- Alembic not picking up DATABASE_URL:
  - Make sure .env resides in ecommerce_backend directory and that you are executing commands from this directory so env loading works.
  - alembic/env.py programmatically sets sqlalchemy.url from Settings; confirm DATABASE_URL is visible in your environment.

- Autogenerate does not detect changes:
  - Ensure all models are imported into src/models/__init__.py and that Alembic target_metadata points to Base.metadata (it does).
  - Run: make makemigration m="..." then make migrate.

## Reference Paths
- Alembic config: alembic.ini
- Alembic env: alembic/env.py
- Initial migration: alembic/versions/20250101000000_initial.py
- Makefile tasks: Makefile
- Management CLI: src/manage.py
- Settings: src/core/config.py
- Database: src/core/database.py
- Seeding utilities: src/core/seed.py
