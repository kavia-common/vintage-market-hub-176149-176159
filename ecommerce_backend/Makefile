.PHONY: migrate seed migrate_and_seed makemigration

# Run migrations to head
migrate:
\tpython -m alembic upgrade head

# Generate a new revision with message (usage: make makemigration m="add new table")
makemigration:
\tpython -m alembic revision --autogenerate -m "$(m)"

# Seed default data
seed:
\tpython -m src.manage seed

# Apply migrations and seed
migrate_and_seed:
\tpython -m src.manage migrate_and_seed
