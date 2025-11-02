#!/usr/bin/env python3
"""
Link OAuth token to brokerage account

Creates client_brokerage_accounts record and links it to the OAuth token.
"""
import os

import psycopg2

# Get from .env
DB_PASSWORD = "$@nJose420"
SCHWAB_ACCOUNT_ID = "42993812"

# Connect to database
conn = psycopg2.connect(host="localhost", database="acis-ai", user="postgres", password=DB_PASSWORD)

cur = conn.cursor()

# Create or get the brokerage account record
cur.execute(
    """
    INSERT INTO client_brokerage_accounts (
        client_id, brokerage_id, account_number, account_type,
        is_active, notes, created_at, updated_at
    )
    VALUES (
        1, 1, %s, 'individual',
        TRUE, 'Primary Schwab account', NOW(), NOW()
    )
    ON CONFLICT (client_id, brokerage_id, account_number)
    DO UPDATE SET
        is_active = TRUE,
        updated_at = NOW()
    RETURNING id
""",
    (SCHWAB_ACCOUNT_ID,),
)

account_id = cur.fetchone()[0]
conn.commit()

print(f"✓ Created/updated client_brokerage_accounts record")
print(f"  Account ID: {account_id}")
print(f"  Account Number: {SCHWAB_ACCOUNT_ID}")

# Update the OAuth token to link to this account
cur.execute(
    """
    UPDATE brokerage_oauth_tokens
    SET account_id = %s,
        updated_at = NOW()
    WHERE client_id = 1 AND brokerage_id = 1
    RETURNING id, client_id, brokerage_id, account_id
""",
    (account_id,),
)

token_row = cur.fetchone()
conn.commit()

if token_row:
    print(f"\n✓ Updated OAuth token to link to brokerage account")
    print(f"  Token ID: {token_row[0]}")
    print(f"  Client ID: {token_row[1]}")
    print(f"  Brokerage ID: {token_row[2]}")
    print(f"  Account ID: {token_row[3]}")
else:
    print("\n✗ No OAuth token found to update")

# Verify the link
cur.execute(
    """
    SELECT
        bot.id as token_id,
        bot.client_id,
        bot.brokerage_id,
        bot.account_id,
        cba.account_number,
        cba.account_type,
        cba.notes
    FROM brokerage_oauth_tokens bot
    LEFT JOIN client_brokerage_accounts cba ON cba.id = bot.account_id
    WHERE bot.client_id = 1 AND bot.brokerage_id = 1
"""
)

row = cur.fetchone()

if row:
    print(f"\n✓ Verification - Token is now properly linked:")
    print(f"  Token ID: {row[0]}")
    print(f"  Client ID: {row[1]}")
    print(f"  Brokerage ID: {row[2]}")
    print(f"  Account ID: {row[3]}")
    print(f"  Account Number: {row[4]}")
    print(f"  Account Type: {row[5]}")
    print(f"  Notes: {row[6]}")

cur.close()
conn.close()

print("\n✓ OAuth token successfully linked to brokerage account!")
