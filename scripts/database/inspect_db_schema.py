#!/usr/bin/env python3
"""Inspect the acis-ai database schema to map tables for RL training."""

import psycopg2

db_config = {
    "dbname": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
    "host": "localhost",
    "port": 5432,
}

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# Get all tables
cursor.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
"""
)

tables = cursor.fetchall()

print("=" * 80)
print("ACIS-AI DATABASE SCHEMA")
print("=" * 80)
print()

# Show tables that might be relevant for RL training
relevant_keywords = ["bar", "sma", "rsi", "macd", "ema", "etf", "dividend", "ratio"]

print("RELEVANT TABLES FOR RL TRAINING:")
print("-" * 80)
for table in tables:
    table_name = table[0]
    if any(kw in table_name.lower() for kw in relevant_keywords):
        # Get column info
        cursor.execute(
            f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        )
        columns = cursor.fetchall()

        print(f"\n{table_name}:")
        for col in columns[:10]:  # Show first 10 columns
            print(f"  - {col[0]} ({col[1]})")
        if len(columns) > 10:
            print(f"  ... and {len(columns) - 10} more columns")

print("\n" + "=" * 80)
print("ALL TABLES:")
print("-" * 80)
for table in tables:
    print(f"  - {table[0]}")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total tables: {len(tables)}")
