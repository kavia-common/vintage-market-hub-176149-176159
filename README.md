# vintage-market-hub-176149-176159

Backend database migrations and seeds

- Alembic is configured under ecommerce_backend/alembic with env.py using Pydantic settings to read DATABASE_URL.
- Initial migration is created at ecommerce_backend/alembic/versions/20250101000000_initial.py reflecting all SQLAlchemy models.
- Seeding utilities exist to populate default regions and categories idempotently.

How to run (from ecommerce_backend directory):

1) Ensure .env contains:
   - DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME
   - JWT_SECRET=some-secret
   - (other settings as required)

2) Install dependencies:
   pip install -r requirements.txt

3) Run migrations:
   make migrate
   # or
   python -m alembic upgrade head

4) Seed default data:
   make seed
   # or
   python -m src.manage seed

5) Migrate and seed together:
   make migrate_and_seed
   # or
   python -m src.manage migrate_and_seed

Notes
- Seeding is safe to re-run; it only inserts missing regions and categories.
- To create future migrations after modifying models:
   make makemigration m="your message"
   make migrate