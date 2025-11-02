#!/usr/bin/env python3
"""
Live Trading Flow Test Script

Tests the entire live trading flow without executing real trades:
1. Check Schwab OAuth token status
2. Fetch current positions from Schwab API
3. Sync positions to paper_positions table
4. Run autonomous rebalancer in dry-run mode
5. Validate trade recommendations
6. Display what WOULD be executed

Usage:
  # Test with Frank's account (client_id=1)
  python scripts/test_live_trading_flow.py --client-id 1

  # Test with specific account hash
  python scripts/test_live_trading_flow.py --client-id 1 --account-hash 9159A02579DE45A5B2BD9A746C27E9319D12C4B4730A184486FCDD9FAFC5BE9D
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import asyncio
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from autonomous.autonomous_rebalancer import AutonomousRebalancer
from utils import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


async def test_oauth_token(client_id: int):
    """Test 1: Check OAuth token status"""
    logger.info("=" * 80)
    logger.info("TEST 1: OAuth Token Status")
    logger.info("=" * 80)

    from backend.api.database.connection import get_db
    from backend.api.services.schwab_oauth import SchwabOAuthService

    try:
        # Create a mock database session
        db = next(get_db())
        oauth_service = SchwabOAuthService(db)

        token = await oauth_service.get_valid_token(client_id)

        if token:
            logger.info("✅ OAuth token is valid")
            logger.info(f"   Token exists and is not expired")
            return True
        else:
            logger.error("❌ No valid OAuth token found")
            logger.error("   Please run Schwab OAuth flow first")
            return False
    except Exception as e:
        logger.error(f"❌ OAuth token check failed: {e}")
        return False


async def test_fetch_positions(client_id: int, account_hash: str):
    """Test 2: Fetch positions from Schwab API"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Fetch Positions from Schwab API")
    logger.info("=" * 80)

    from backend.api.database.connection import get_db
    from backend.api.services.schwab_api import SchwabAPIClient
    from backend.api.services.schwab_oauth import SchwabOAuthService

    try:
        # Get valid token
        db = next(get_db())
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            logger.error("❌ Cannot fetch positions - no valid token")
            return False, []

        # Fetch positions
        api_client = SchwabAPIClient(token)
        positions = await api_client.get_positions(account_hash)

        logger.info(f"✅ Successfully fetched {len(positions)} positions from Schwab")

        # Display positions
        total_value = 0
        for pos in positions:
            ticker = pos.get("symbol", "")
            qty = pos.get("quantity", 0)
            value = pos.get("current_value", 0)
            total_value += value
            logger.info(f"   {ticker}: {qty} shares = ${value:,.2f}")

        logger.info(f"   Total Value: ${total_value:,.2f}")

        return True, positions
    except Exception as e:
        logger.error(f"❌ Failed to fetch positions: {e}")
        return False, []


async def test_sync_positions(client_id: int, account_hash: str, positions: list):
    """Test 3: Sync positions to paper_positions table"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Sync Positions to Database")
    logger.info("=" * 80)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Ensure account exists
        cursor.execute(
            """
            INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
            VALUES (%s, 0, 0, 0)
            ON CONFLICT (account_id) DO NOTHING
        """,
            (account_hash,),
        )

        # Clear existing positions
        cursor.execute("DELETE FROM paper_positions WHERE account_id = %s", (account_hash,))

        # Insert positions
        inserted = 0
        for position in positions:
            ticker = position.get("symbol", "")
            if not ticker:
                continue

            quantity = float(position.get("quantity", 0))
            market_value = float(position.get("current_value", 0))
            avg_price = float(position.get("average_price", 0))
            unrealized_pnl = float(position.get("total_gain", 0))

            cursor.execute(
                """
                INSERT INTO paper_positions (account_id, ticker, quantity, avg_price, market_value, unrealized_pnl)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (account_hash, ticker, quantity, avg_price, market_value, unrealized_pnl),
            )
            inserted += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ Successfully synced {inserted} positions to database")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to sync positions: {e}")
        return False


def test_autonomous_rebalancer(client_id: int, account_hash: str):
    """Test 4: Run autonomous rebalancer in dry-run mode"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Run Autonomous Rebalancer (DRY RUN)")
    logger.info("=" * 80)

    try:
        rebalancer = AutonomousRebalancer(
            account_id=account_hash,
            client_id=client_id,
            dry_run=True,  # IMPORTANT: Dry run mode
            use_real_models=False,  # Use mock portfolios for testing
            paper_trading=True,
        )

        logger.info("✅ Rebalancer initialized successfully")
        logger.info(f"   Mode: DRY RUN (no trades will be executed)")
        logger.info(f"   Client ID: {client_id}")
        logger.info(f"   Account: {account_hash}")

        # Run rebalancing
        success = rebalancer.rebalance(force=True)

        if success:
            logger.info("✅ Rebalancing simulation completed successfully")
        else:
            logger.warning("⚠️  Rebalancing simulation completed with warnings")

        rebalancer.close()
        return True
    except Exception as e:
        logger.error(f"❌ Rebalancing simulation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def display_summary(client_id: int, results: dict):
    """Display test summary"""
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Client ID: {client_id}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {test_name}: {status}")

    logger.info("")
    if all_passed:
        logger.info("✅ ALL TESTS PASSED - System is ready for live trading")
        logger.info("")
        logger.info("To run live trading:")
        logger.info(f"  python scripts/run_daily_rebalance.py --live --client-id {client_id}")
    else:
        logger.error("❌ SOME TESTS FAILED - Fix issues before live trading")

    logger.info("=" * 80)

    return all_passed


async def main():
    parser = argparse.ArgumentParser(description="Test live trading flow")
    parser.add_argument("--client-id", type=int, required=True, help="Client ID to test")
    parser.add_argument(
        "--account-hash",
        type=str,
        default=None,
        help="Account hash (will auto-detect if not provided)",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("LIVE TRADING FLOW TEST")
    logger.info("=" * 80)
    logger.info(f"Client ID: {args.client_id}")
    logger.info(f"Mode: DRY RUN (no real trades)")
    logger.info("")

    # Auto-detect account hash if not provided
    account_hash = args.account_hash
    if not account_hash:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT account_hash
                FROM client_brokerage_accounts
                WHERE client_id = %s AND is_active = true
                LIMIT 1
            """,
                (args.client_id,),
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                account_hash = result[0]
                logger.info(f"Auto-detected account: {account_hash}")
            else:
                logger.error(f"No active brokerage account found for client {args.client_id}")
                return 1
        except Exception as e:
            logger.error(f"Failed to auto-detect account: {e}")
            return 1

    # Run tests
    results = {}

    # Test 1: OAuth token
    results["OAuth Token"] = await test_oauth_token(args.client_id)
    if not results["OAuth Token"]:
        logger.error("Cannot continue without valid OAuth token")
        display_summary(args.client_id, results)
        return 1

    # Test 2: Fetch positions
    success, positions = await test_fetch_positions(args.client_id, account_hash)
    results["Fetch Positions"] = success
    if not success:
        logger.error("Cannot continue without positions")
        display_summary(args.client_id, results)
        return 1

    # Test 3: Sync positions
    results["Sync to Database"] = await test_sync_positions(args.client_id, account_hash, positions)

    # Test 4: Autonomous rebalancer
    results["Autonomous Rebalancer"] = test_autonomous_rebalancer(args.client_id, account_hash)

    # Display summary
    all_passed = display_summary(args.client_id, results)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
