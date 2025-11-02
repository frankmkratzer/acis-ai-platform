#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor

with get_psycopg2_connection() as conn:
    with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
        tables = cur.fetchall()
        print("Existing tables:")
        for table in tables:
            print(f"  - {table[0]}")
