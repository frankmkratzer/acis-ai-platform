#!/usr/bin/env python3
"""Test database connection on DGX"""

import pandas as pd

from utils.db_config import engine

print("=" * 60)
print("Testing Database Connection on DGX")
print("=" * 60)

# Test queries
df_tables = pd.read_sql(
    "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';",
    engine,
)
print(f"\n✓ Connection successful!")
print(f"\nTables: {df_tables.iloc[0,0]}")

df_tickers = pd.read_sql("SELECT COUNT(*) as count FROM tickers;", engine)
print(f"Tickers: {df_tickers.iloc[0,0]:,}")

df_bars = pd.read_sql("SELECT COUNT(*) as count FROM daily_bars;", engine)
print(f"Daily bars: {df_bars.iloc[0,0]:,}")

print("\n" + "=" * 60)
print("✓ All tests passed! Database is ready for training.")
print("=" * 60)
