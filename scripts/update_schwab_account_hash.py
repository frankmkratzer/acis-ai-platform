#!/usr/bin/env python3
"""
Update Schwab Account Hash in Database

This script fetches account information from the Schwab API and updates
the account_hash field in the client_brokerage_accounts table.

The account hash is required for placing orders via Schwab's API.
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import asyncio

import psycopg2
from dotenv import load_dotenv

from backend.api.services.schwab_api import SchwabAPIClient

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


async def main():
    """Update account_hash for all Schwab accounts"""

    # Database connection
    db_config = {
        "dbname": os.getenv("DB_NAME", "acis-ai"),
        "user": "postgres",
        "password": os.getenv("DB_PASSWORD", "$@nJose420"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }

    print("[INFO] Connecting to database...")
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Get OAuth token for client 1
    print("[INFO] Getting OAuth token from database...")
    cur.execute(
        """
        SELECT access_token, client_id
        FROM brokerage_oauth_tokens
        WHERE brokerage_id = 1
        ORDER BY updated_at DESC
        LIMIT 1
    """
    )

    token_result = cur.fetchone()

    if not token_result:
        print("[ERROR] No OAuth token found in database")
        print("[INFO] Please complete OAuth flow first at /brokerages/1")
        return

    access_token, client_id = token_result
    print(f"[INFO] Found token for client {client_id}")

    # Initialize Schwab API
    print("[INFO] Fetching accounts from Schwab API...")
    api = SchwabAPIClient(access_token)

    try:
        # Get all accounts from Schwab
        schwab_accounts = await api.get_account_numbers()

        if not schwab_accounts:
            print("[ERROR] Failed to retrieve accounts from Schwab API")
            print("[INFO] The OAuth token may be invalid or expired")
            return

        print(f"[INFO] Found {len(schwab_accounts)} accounts from Schwab API")

        # Process each account
        updated_count = 0
        created_count = 0

        for account_data in schwab_accounts:
            account_number = account_data.get("accountNumber")
            account_hash = account_data.get("hashValue")  # The encrypted hash for API calls

            if not account_number or not account_hash:
                print("[WARN] Skipping account with missing data")
                continue

            print(f"\n[INFO] Processing account: {account_number}")
            print(f"[INFO] Account hash: {account_hash}")

            # Check if this account exists in our database
            cur.execute(
                """
                SELECT id, account_hash
                FROM client_brokerage_accounts
                WHERE account_number = %s AND brokerage_id = 1
            """,
                (account_number,),
            )

            result = cur.fetchone()

            if result:
                # Account exists - update hash if different
                account_id, current_hash = result

                if current_hash == account_hash:
                    print(f"[INFO] Account {account_number} hash is already up to date")
                    continue

                # Update the hash
                print(f"[INFO] Updating hash for account {account_number}...")
                cur.execute(
                    """
                    UPDATE client_brokerage_accounts
                    SET account_hash = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """,
                    (account_hash, account_id),
                )

                print(f"[SUCCESS] Updated account {account_number}")
                updated_count += 1

            else:
                # Account doesn't exist - create it
                print(f"[INFO] Creating new account record for {account_number}...")
                cur.execute(
                    """
                    INSERT INTO client_brokerage_accounts (
                        client_id, brokerage_id, account_number, account_hash,
                        account_type, is_active, created_at, updated_at
                    )
                    VALUES (
                        %s, 1, %s, %s, 'individual', TRUE, NOW(), NOW()
                    )
                    RETURNING id
                """,
                    (client_id, account_number, account_hash),
                )

                new_id = cur.fetchone()[0]
                print(f"[SUCCESS] Created account {account_number} (ID: {new_id})")
                created_count += 1

                # Link OAuth token to this account if not already linked
                cur.execute(
                    """
                    UPDATE brokerage_oauth_tokens
                    SET account_id = %s, updated_at = NOW()
                    WHERE client_id = %s AND brokerage_id = 1 AND account_id IS NULL
                """,
                    (new_id, client_id),
                )

        # Commit changes
        conn.commit()

        print(f"\n[SUCCESS] Updated {updated_count} account(s)")
        print(f"[SUCCESS] Created {created_count} new account(s)")

        # Show final status
        cur.execute(
            """
            SELECT
                cba.account_number,
                cba.account_hash,
                CASE
                    WHEN cba.account_hash IS NOT NULL THEN 'Configured'
                    ELSE 'Missing'
                END as hash_status,
                CASE
                    WHEN bot.id IS NOT NULL THEN 'Linked'
                    ELSE 'Not Linked'
                END as oauth_status
            FROM client_brokerage_accounts cba
            LEFT JOIN brokerage_oauth_tokens bot ON bot.account_id = cba.id
            WHERE cba.brokerage_id = 1
        """
        )

        print("\n[INFO] Final Account Status:")
        print("-" * 80)
        for account_number, account_hash, hash_status, oauth_status in cur.fetchall():
            hash_preview = account_hash[:20] + "..." if account_hash else "None"
            print(f"  Account {account_number}:")
            print(f"    Hash: {hash_preview} ({hash_status})")
            print(f"    OAuth: {oauth_status}")

    except Exception as e:
        print(f"[ERROR] Failed to fetch accounts from Schwab API: {str(e)}")
        print("[INFO] Make sure you have a valid OAuth token")
        conn.rollback()
        return

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
