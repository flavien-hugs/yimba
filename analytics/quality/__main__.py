"""python -m quality: check the marts, exit 1 when a check fails."""

import os
import sys

from quality.checks import DAYS, load, validate
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def main() -> int:
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )
    engine = create_engine(url)
    try:
        problems = validate(load(engine))
    finally:
        engine.dispose()
    if problems:
        print(f"Data quality: {len(problems)} mart(s) failing over the last {DAYS} days\n", file=sys.stderr)
        print("\n\n".join(problems), file=sys.stderr)
        return 1
    print(f"Data quality: all checks passed over the last {DAYS} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
