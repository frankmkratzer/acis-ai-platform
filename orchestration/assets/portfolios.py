"""
Portfolio Management Assets for Dagster
Builds and rebalances 8 portfolios based on screening criteria
"""

import sys
from datetime import date
from pathlib import Path

from dagster import AssetExecutionContext, AssetIn, Output, asset

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from portfolio.portfolio_builder import PortfolioBuilder


@asset(
    name="portfolios_snapshot",
    group_name="portfolios",
    description="8-portfolio snapshot (2 Dividend, 3 Growth, 3 Value)",
    compute_kind="python",
    ins={
        "fundamentals": AssetIn(),
        "sma": AssetIn(),
        "ema": AssetIn(),
        "rsi": AssetIn(),
        "macd": AssetIn(),
    },
)
def portfolios_snapshot(
    context: AssetExecutionContext, fundamentals: dict, sma: dict, ema: dict, rsi: dict, macd: dict
) -> Output[dict]:
    """
    Build all 8 portfolios based on current market data

    Dependencies:
    - fundamentals (for dividend/growth/value screening)
    - sma, ema, rsi, macd (for technical filters)

    Portfolios:
    - Dividend: Large Cap, Mid Cap (2 total)
    - Growth: Large Cap, Mid Cap, Small Cap (3 total)
    - Value: Large Cap, Mid Cap, Small Cap (3 total)
    """
    context.log.info("Building all 8 portfolios...")

    with PortfolioBuilder() as builder:
        portfolios = builder.build_all_portfolios()

        # Save to database
        builder.save_portfolios_to_db(portfolios)

        # Count positions
        total_positions = sum(
            p.get("position_count", 0) for p in portfolios.values() if "error" not in p
        )

        context.log.info(
            f"Built {len(portfolios)} portfolios with {total_positions} total positions"
        )

        return Output(
            value=portfolios,
            metadata={
                "portfolio_count": len(portfolios),
                "total_positions": total_positions,
                "snapshot_date": str(date.today()),
            },
        )
