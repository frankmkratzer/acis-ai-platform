#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor

with get_psycopg2_connection() as conn:
    with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
        # Check primary key on clients table
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'clients'::regclass AND i.indisprimary;
        """
        )
        clients_pk = cur.fetchall()
        print("clients table primary key:")
        for pk in clients_pk:
            print(f"  - {pk[0]}")

        # Check primary key on brokerages table
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = 'brokerages'::regclass AND i.indisprimary;
        """
        )
        brokerages_pk = cur.fetchall()
        print("\nbrokerages table primary key:")
        for pk in brokerages_pk:
            print(f"  - {pk[0]}")
