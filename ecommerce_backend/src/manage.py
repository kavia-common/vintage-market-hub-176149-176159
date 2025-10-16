from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Optional

from src.core.database import session_scope
from src.core.seed import seed_regions, seed_categories


def _run(cmd: list[str], cwd: Optional[str] = None) -> int:
    """Run a shell command and stream output."""
    proc = subprocess.Popen(cmd, cwd=cwd)
    return proc.wait()


# PUBLIC_INTERFACE
def main() -> None:
    """Simple management CLI.

    Commands:
    - migrate: Run Alembic upgrade head
    - seed: Seed default regions and categories
    - migrate_and_seed: Run migrations then seed data
    """
    parser = argparse.ArgumentParser(description="Management CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("migrate", help="Run Alembic migrations to head")
    sub.add_parser("seed", help="Seed regions and categories")
    sub.add_parser("migrate_and_seed", help="Run migrations then seed data")

    args = parser.parse_args()

    if args.command == "migrate":
        code = _run([sys.executable, "-m", "alembic", "upgrade", "head"])
        sys.exit(code)
    elif args.command == "seed":
        with session_scope() as db:
            r = seed_regions(db)
            c = seed_categories(db)
            print(f"Seed complete: regions inserted={r}, categories inserted={c}")
    elif args.command == "migrate_and_seed":
        code = _run([sys.executable, "-m", "alembic", "upgrade", "head"])
        if code != 0:
            sys.exit(code)
        with session_scope() as db:
            r = seed_regions(db)
            c = seed_categories(db)
            print(f"Migrations applied. Seed complete: regions inserted={r}, categories inserted={c}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
