#!/usr/bin/env python3
"""Add account_hash column to client_brokerage_accounts"""
import psycopg2

conn = psycopg2.connect(
    host="localhost", database="acis-ai", user="postgres", password="$@nJose420"
)

cur = conn.cursor()

# Add column if it doesn't exist
cur.execute(
    """
    ALTER TABLE client_brokerage_accounts
    ADD COLUMN IF NOT EXISTS account_hash VARCHAR(255)
"""
)

# Create index
cur.execute(
    """
    CREATE INDEX IF NOT EXISTS idx_client_brokerage_account_hash
    ON client_brokerage_accounts(account_hash)
"""
)

conn.commit()

print("✓ Added account_hash column to client_brokerage_accounts")
print("✓ Created index on account_hash")

cur.close()
conn.close()
