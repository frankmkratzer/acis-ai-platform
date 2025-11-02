#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor

with get_psycopg2_connection() as conn:
    with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
        # Get all tables
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
        tables = cur.fetchall()

        print("=" * 60)
        print("EXISTING TABLES IN acis-ai DATABASE")
        print("=" * 60)
        for table in tables:
            print(f"  ✓ {table[0]}")

        print()
        print(f"Total: {len(tables)} tables")
        print()

        # Check for clients and brokerages specifically
        table_names = [t[0] for t in tables]
        if "clients" in table_names:
            print("✓ clients table EXISTS")
            cur.execute("SELECT COUNT(*) FROM clients;")
            count = cur.fetchone()[0]
            print(f"  → {count} clients in database")

        if "brokerages" in table_names:
            print("✓ brokerages table EXISTS")
            cur.execute("SELECT COUNT(*) FROM brokerages;")
            count = cur.fetchone()[0]
            print(f"  → {count} brokerages in database")
