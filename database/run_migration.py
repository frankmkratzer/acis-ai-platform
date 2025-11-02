#!/usr/bin/env python3
"""
Run database migrations using existing database connection
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor


def run_migration(migration_file):
    """Run a SQL migration file"""
    print(f"Running migration: {migration_file}")

    # Read migration SQL
    with open(migration_file, "r") as f:
        sql = f.read()

    # Execute migration
    with get_psycopg2_connection() as conn:
        with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
            cur.execute(sql)

    print(f"Migration complete: {migration_file}")


if __name__ == "__main__":
    migration_file = Path(__file__).parent / "migrations" / "001_web_platform_schema.sql"
    run_migration(migration_file)
