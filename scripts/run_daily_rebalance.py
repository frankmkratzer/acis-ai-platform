#!/usr/bin/env python3
"""
Daily Autonomous Rebalancing Script

Runs daily to:
1. Update market regime
2. Select optimal strategy
3. Generate target portfolio using ML+RL
4. Execute rebalancing trades
5. Log results

Usage:
  # Dry run (no trades executed)
  python scripts/run_daily_rebalance.py --dry-run

  # Paper trading (simulated trades in database)
  python scripts/run_daily_rebalance.py --paper-trading

  # LIVE trading (REAL money - be careful!)
  python scripts/run_daily_rebalance.py --live

  # Specify account
  python scripts/run_daily_rebalance.py --account-id PAPER_AUTONOMOUS_FUND --paper-trading
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

from autonomous.autonomous_rebalancer import AutonomousRebalancer
from utils import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run daily autonomous rebalancing")

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--dry-run", action="store_true", help="Dry run mode - analyze but don't execute trades"
    )
    mode_group.add_argument(
        "--paper-trading", action="store_true", help="Paper trading mode - execute simulated trades"
    )
    mode_group.add_argument(
        "--live", action="store_true", help="LIVE trading mode - execute REAL trades (BE CAREFUL!)"
    )

    # Configuration
    parser.add_argument(
        "--account-id", type=str, default="PAPER_AUTONOMOUS_FUND", help="Account ID to rebalance"
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=None,
        help="Client ID (will check trading_mode and auto_trading_enabled)",
    )
    parser.add_argument(
        "--use-mock", action="store_true", help="Use mock portfolios instead of real ML/RL models"
    )
    parser.add_argument("--force", action="store_true", help="Force rebalance even if not needed")

    args = parser.parse_args()

    # Determine run mode
    if args.dry_run:
        dry_run = True
        paper_trading = True
        mode_name = "DRY RUN"
    elif args.paper_trading:
        dry_run = False
        paper_trading = True
        mode_name = "PAPER TRADING"
    else:  # --live
        dry_run = False
        paper_trading = False
        mode_name = "🚨 LIVE TRADING 🚨"

    logger.info("=" * 80)
    logger.info(f"AUTONOMOUS FUND DAILY REBALANCING - {mode_name}")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Account: {args.account_id}")
    logger.info(f"Client ID: {args.client_id if args.client_id else 'Not specified'}")
    logger.info(f"Models: {'MOCK' if args.use_mock else 'REAL ML/RL'}")
    logger.info("=" * 80)

    # Safety check for live trading
    if args.live and not args.force:
        logger.warning("⚠️  LIVE TRADING MODE - This will execute REAL trades with REAL money!")
        response = input("Are you absolutely sure you want to proceed? Type 'YES' to continue: ")
        if response != "YES":
            logger.info("Live trading cancelled by user")
            return 1

    try:
        # Initialize rebalancer
        rebalancer = AutonomousRebalancer(
            account_id=args.account_id,
            client_id=args.client_id,
            dry_run=dry_run,
            use_real_models=not args.use_mock,
            paper_trading=paper_trading,
        )

        # Run rebalancing
        logger.info("Starting rebalancing process...")

        success = rebalancer.rebalance(force=args.force)

        if success:
            logger.info("=" * 80)
            logger.info("✅ REBALANCING COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            return 0
        else:
            logger.error("=" * 80)
            logger.error("❌ REBALANCING FAILED OR SKIPPED")
            logger.error("=" * 80)
            return 1

    except KeyboardInterrupt:
        logger.warning("Rebalancing interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Error during rebalancing: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        if "rebalancer" in locals():
            rebalancer.close()


if __name__ == "__main__":
    sys.exit(main())
