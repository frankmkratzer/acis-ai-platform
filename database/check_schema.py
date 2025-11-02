#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_config import get_psycopg2_connection, get_psycopg2_cursor

tables_to_check = ["clients", "brokerages", "portfolios", "portfolio_holdings"]

with get_psycopg2_connection() as conn:
    with get_psycopg2_cursor(conn, dict_cursor=False) as cur:
        for table in tables_to_check:
            print(f"\n{'='*60}")
            print(f"TABLE: {table}")
            print("=" * 60)

            # Get columns
            cur.execute(
                f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = '{table}'
                ORDER BY ordinal_position;
            """
            )
            columns = cur.fetchall()

            for col in columns:
                col_name, data_type, max_len = col
                if max_len:
                    print(f"  {col_name:30} {data_type}({max_len})")
                else:
                    print(f"  {col_name:30} {data_type}")
