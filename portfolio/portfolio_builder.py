#!/usr/bin/env python3
"""
Portfolio Builder
Constructs 8 portfolios (2 Dividend, 3 Growth, 3 Value) using screened candidates
"""
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import PORTFOLIO_CONFIG, RISK_MANAGEMENT
from portfolio.screener import StockScreener
from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


class PortfolioBuilder:
    """Build and manage 8 portfolios"""

    def __init__(self):
        self.screener = None
        self.conn = None

    def __enter__(self):
        self.screener = StockScreener().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.screener:
            self.screener.__exit__(exc_type, exc_val, exc_tb)

    def rank_candidates(
        self, candidates: List[str], strategy: str, as_of_date: Optional[date] = None
    ) -> List[tuple]:
        """
        Rank candidates by strategy-specific scoring

        For now, uses simple momentum-based ranking.
        Later: replace with ML model predictions

        Args:
            candidates: List of ticker symbols
            strategy: 'dividend', 'growth', or 'value'
            as_of_date: Date for ranking (default: today)

        Returns:
            List of (ticker, score) tuples sorted by score descending
        """
        if not candidates:
            return []

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Ranking {len(candidates)} candidates for {strategy} strategy...")

        # Get scoring data based on strategy
        if strategy == "dividend":
            ranking_query = """
                SELECT
                    r.ticker,
                    r.dividend_yield,
                    r.payout_ratio,
                    r.return_on_equity
                FROM ratios r
                WHERE r.ticker = ANY(%s)
                  AND r.period_ending <= %s
                ORDER BY r.ticker, r.period_ending DESC;
            """

            scores = {}
            with self.screener.conn.cursor() as cur:
                cur.execute(ranking_query, [candidates, as_of_date])

                seen = set()
                for row in cur.fetchall():
                    ticker, div_yield, payout, roe = row
                    if ticker in seen:
                        continue
                    seen.add(ticker)

                    if div_yield and payout and roe:
                        # Higher yield, lower payout, higher ROE = better score
                        score = (div_yield * 2) + (roe * 1) - (payout * 0.5)
                        scores[ticker] = score

        elif strategy == "growth":
            ranking_query = """
                SELECT
                    r.ticker,
                    r.revenue_growth,
                    r.earnings_growth,
                    r.peg_ratio
                FROM ratios r
                WHERE r.ticker = ANY(%s)
                  AND r.period_ending <= %s
                ORDER BY r.ticker, r.period_ending DESC;
            """

            scores = {}
            with self.screener.conn.cursor() as cur:
                cur.execute(ranking_query, [candidates, as_of_date])

                seen = set()
                for row in cur.fetchall():
                    ticker, rev_growth, earn_growth, peg = row
                    if ticker in seen:
                        continue
                    seen.add(ticker)

                    if rev_growth and earn_growth and peg:
                        # Higher growth, lower PEG = better score
                        score = (rev_growth * 2) + (earn_growth * 2) - (peg * 0.5)
                        scores[ticker] = score

        elif strategy == "value":
            ranking_query = """
                SELECT
                    r.ticker,
                    r.price_to_earnings_ratio,
                    r.price_to_book_ratio,
                    r.free_cash_flow_per_share,
                    r.close_price
                FROM ratios r
                WHERE r.ticker = ANY(%s)
                  AND r.period_ending <= %s
                ORDER BY r.ticker, r.period_ending DESC;
            """

            scores = {}
            with self.screener.conn.cursor() as cur:
                cur.execute(ranking_query, [candidates, as_of_date])

                seen = set()
                for row in cur.fetchall():
                    ticker, pe, pb, fcf, price = row
                    if ticker in seen:
                        continue
                    seen.add(ticker)

                    if pe and pb and fcf and price and price > 0:
                        fcf_yield = fcf / price
                        # Lower ratios, higher FCF yield = better score
                        score = -(pe * 0.3) - (pb * 0.2) + (fcf_yield * 5)
                        scores[ticker] = score

        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        logger.info(f"Ranked {len(ranked)} candidates (top score: {ranked[0][1]:.2f})")

        return ranked

    def build_portfolio(self, portfolio_id: str, as_of_date: Optional[date] = None) -> Dict:
        """
        Build a single portfolio

        Args:
            portfolio_id: Portfolio identifier from PORTFOLIO_CONFIG
            as_of_date: Date for portfolio construction (default: today)

        Returns:
            Dictionary with portfolio details
        """
        if portfolio_id not in PORTFOLIO_CONFIG:
            raise ValueError(f"Unknown portfolio ID: {portfolio_id}")

        config = PORTFOLIO_CONFIG[portfolio_id]
        logger.info(f"\n{'='*70}")
        logger.info(f"Building Portfolio: {config['name']}")
        logger.info(f"{'='*70}")

        # Screen candidates
        candidates = self.screener.screen(config["strategy"], config["market_cap"], as_of_date)

        if not candidates:
            logger.warning(f"No candidates found for {config['name']}")
            return {
                "portfolio_id": portfolio_id,
                "name": config["name"],
                "strategy": config["strategy"],
                "market_cap": config["market_cap"],
                "as_of_date": as_of_date or date.today(),
                "holdings": [],
                "position_count": 0,
                "error": "No candidates passed screening",
            }

        # Rank candidates
        ranked = self.rank_candidates(candidates, config["strategy"], as_of_date)

        # Select top N positions
        target_count = config["criteria"]["position_count"]
        selected = ranked[:target_count]

        # Calculate equal-weight positions
        position_size = 1.0 / len(selected) if selected else 0

        holdings = []
        for ticker, score in selected:
            holdings.append({"ticker": ticker, "weight": position_size, "score": round(score, 4)})

        portfolio = {
            "portfolio_id": portfolio_id,
            "name": config["name"],
            "strategy": config["strategy"],
            "market_cap": config["market_cap"],
            "as_of_date": as_of_date or date.today(),
            "holdings": holdings,
            "position_count": len(holdings),
            "target_count": target_count,
            "candidates_screened": len(candidates),
            "rebalance_frequency": config["criteria"]["rebalance_frequency"],
        }

        logger.info(f"\nPortfolio Summary:")
        logger.info(f"  Selected: {len(holdings)}/{target_count} positions")
        logger.info(f"  Position size: {position_size*100:.2f}% each")

        if holdings:
            logger.info(f"\nTop 5 Holdings:")
            for i, holding in enumerate(holdings[:5], 1):
                logger.info(
                    f"  {i}. {holding['ticker']:6} - Weight: {holding['weight']*100:5.2f}% - Score: {holding['score']:7.2f}"
                )

        return portfolio

    def build_all_portfolios(self, as_of_date: Optional[date] = None) -> Dict[str, Dict]:
        """
        Build all 8 portfolios

        Args:
            as_of_date: Date for portfolio construction (default: today)

        Returns:
            Dictionary mapping portfolio_id to portfolio details
        """
        logger.info(f"\n{'#'*70}")
        logger.info(f"# Building All 8 Portfolios")
        logger.info(f"# As of: {as_of_date or date.today()}")
        logger.info(f"{'#'*70}\n")

        portfolios = {}

        # Build each portfolio
        for portfolio_id in PORTFOLIO_CONFIG.keys():
            try:
                portfolio = self.build_portfolio(portfolio_id, as_of_date)
                portfolios[portfolio_id] = portfolio
            except Exception as e:
                logger.error(f"Error building {portfolio_id}: {e}", exc_info=True)
                portfolios[portfolio_id] = {"portfolio_id": portfolio_id, "error": str(e)}

        # Summary
        logger.info(f"\n{'#'*70}")
        logger.info(f"# Portfolio Construction Summary")
        logger.info(f"{'#'*70}")

        total_positions = 0
        for pid, portfolio in portfolios.items():
            if "error" not in portfolio:
                count = portfolio["position_count"]
                target = portfolio["target_count"]
                pct = (count / target * 100) if target > 0 else 0
                logger.info(
                    f"  {portfolio['name']:30} {count:2}/{target:2} positions ({pct:5.1f}%)"
                )
                total_positions += count
            else:
                logger.error(f"  {pid:30} ERROR: {portfolio['error']}")

        logger.info(f"\n  Total Positions Across All Portfolios: {total_positions}")

        return portfolios

    def save_portfolios_to_db(self, portfolios: Dict[str, Dict]):
        """Save portfolios to database"""
        logger.info("\nSaving portfolios to database...")

        with get_psycopg2_connection() as conn:
            with conn.cursor() as cur:
                total_saved = 0

                for portfolio_id, portfolio in portfolios.items():
                    if "error" in portfolio:
                        logger.warning(f"  Skipping {portfolio_id}: {portfolio['error']}")
                        continue

                    snapshot_date = portfolio["as_of_date"]
                    holdings = portfolio["holdings"]

                    # Create snapshot
                    cur.execute(
                        """
                        INSERT INTO portfolio_snapshots (
                            portfolio_id, snapshot_date, snapshot_type,
                            position_count, candidates_screened, notes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (portfolio_id, snapshot_date, snapshot_type) DO UPDATE SET
                            position_count = EXCLUDED.position_count,
                            candidates_screened = EXCLUDED.candidates_screened,
                            notes = EXCLUDED.notes
                        RETURNING snapshot_id;
                    """,
                        [
                            portfolio_id,
                            snapshot_date,
                            "rebalance",
                            portfolio["position_count"],
                            portfolio.get("candidates_screened", 0),
                            f"Rebalance: {portfolio['position_count']}/{portfolio['target_count']} positions",
                        ],
                    )
                    snapshot_id = cur.fetchone()[0]

                    # Delete existing holdings for this snapshot
                    cur.execute(
                        """
                        DELETE FROM portfolio_holdings
                        WHERE snapshot_id = %s;
                    """,
                        [snapshot_id],
                    )

                    # Insert holdings
                    if holdings:
                        holdings_data = [
                            (
                                snapshot_id,
                                portfolio_id,
                                h["ticker"],
                                h["weight"],
                                h["score"],
                                i + 1,  # rank
                            )
                            for i, h in enumerate(holdings)
                        ]

                        cur.executemany(
                            """
                            INSERT INTO portfolio_holdings (
                                snapshot_id, portfolio_id, ticker, weight, score, rank
                            )
                            VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                            holdings_data,
                        )

                        total_saved += len(holdings)

                    logger.info(f"  Saved {portfolio['name']}: {len(holdings)} positions")

        logger.info(f"\nTotal positions saved: {total_saved}")

    def save_portfolios(self, portfolios: Dict[str, Dict], output_path: str):
        """Save portfolios to JSON file (legacy method)"""
        # Convert date objects to strings for JSON serialization
        serializable = {}
        for pid, portfolio in portfolios.items():
            p_copy = portfolio.copy()
            if "as_of_date" in p_copy:
                p_copy["as_of_date"] = p_copy["as_of_date"].isoformat()
            serializable[pid] = p_copy

        with open(output_path, "w") as f:
            json.dump(serializable, f, indent=2)

        logger.info(f"\nPortfolios also saved to: {output_path}")


if __name__ == "__main__":
    # Build all portfolios
    with PortfolioBuilder() as builder:
        portfolios = builder.build_all_portfolios()

        # Save to database (primary method)
        builder.save_portfolios_to_db(portfolios)

        # Also save to JSON file (backup/reference)
        output_file = f"portfolios_{date.today().isoformat()}.json"
        builder.save_portfolios(portfolios, output_file)

        print(f"\n{'='*70}")
        print(f"Portfolio construction complete!")
        print(f"Results saved to database and {output_file}")
        print(f"{'='*70}")
