#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor

migration_file = (
    sys.argv[1] if len(sys.argv) > 1 else "database/migrations/000_add_primary_keys.sql"
)

print(f"Running migration: {migration_file}")

with open(migration_file, "r") as f:
    sql = f.read()

with get_psycopg2_connection() as conn:
    with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
        cur.execute(sql)

print(f"✅ Migration complete: {migration_file}")
