"""
Phase 3: Meta-Portfolio Optimizer
Combines market regime detection + ML predictions + dynamic triggers
to optimize allocation across value/growth/dividend strategies
"""

from datetime import date
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from portfolio.config import DIVIDEND_STOCKS_CRITERIA, GROWTH_STOCKS_CRITERIA, VALUE_STOCKS_CRITERIA
from portfolio.dynamic_rebalance import DynamicRebalanceTriggers
from portfolio.market_regime import MarketRegimeDetector
from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class MetaPortfolioOptimizer:
    """
    Meta-optimizer that coordinates:
    1. Market regime detection (volatility-based allocation)
    2. ML-driven stock selection within each strategy
    3. Dynamic rebalancing triggers
    """

    def __init__(self, model_path: str):
        self.regime_detector = MarketRegimeDetector()
        self.rebalance_triggers = DynamicRebalanceTriggers()

        # Load ML model
        self.model = xgb.Booster()
        self.model.load_model(model_path)

        logger.info(f"Meta-optimizer initialized with model: {model_path}")

    def get_strategy_allocation(self, as_of_date: date = None) -> Dict[str, float]:
        """
        Get target allocation across strategies based on market regime

        Returns:
            {'growth': 0.40, 'value': 0.30, 'dividend': 0.30}
        """
        regime = self.regime_detector.detect_regime(as_of_date)
        allocation = self.regime_detector.REGIME_ALLOCATIONS[regime]

        logger.info(f"Market regime: {regime}")
        logger.info(
            f"Target allocation: Growth={allocation['growth']:.0%}, "
            f"Value={allocation['value']:.0%}, Dividend={allocation['dividend']:.0%}"
        )

        return allocation

    def select_stocks_ml(self, strategy: str, top_n: int, as_of_date: date = None) -> pd.DataFrame:
        """
        Select top stocks for a strategy using ML predictions

        Args:
            strategy: 'value', 'growth', or 'dividend'
            top_n: Number of stocks to select
            as_of_date: Date for stock universe

        Returns:
            DataFrame with selected stocks and predictions
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get strategy criteria
        if strategy == "value":
            criteria = VALUE_STOCKS_CRITERIA
        elif strategy == "growth":
            criteria = GROWTH_STOCKS_CRITERIA
        elif strategy == "dividend":
            criteria = DIVIDEND_STOCKS_CRITERIA
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Build SQL query to get candidate stocks
        # (Simplified - should include all 31 or 88 features depending on model)
        query = """
        SELECT
            t.ticker,
            db.close as price,
            r.market_cap,
            r.price_to_earnings as pe_ratio,
            r.price_to_book as pb_ratio,
            r.price_to_sales as ps_ratio,
            r.return_on_equity as roe,
            r.return_on_assets as roa,
            r.debt_to_equity,
            r.dividend_yield
        FROM ticker_overview t
        INNER JOIN daily_bars db ON t.ticker = db.ticker
        INNER JOIN LATERAL (
            SELECT *
            FROM ratios r2
            WHERE r2.ticker = t.ticker
              AND r2.date <= %(as_of_date)s
            ORDER BY r2.date DESC
            LIMIT 1
        ) r ON true
        WHERE t.active = true
          AND db.date = (SELECT MAX(date) FROM daily_bars WHERE ticker = t.ticker AND date <= %(as_of_date)s)
          AND r.market_cap > %(min_market_cap)s
        ORDER BY t.ticker;
        """

        df = pd.read_sql(
            query,
            engine,
            params={"as_of_date": as_of_date, "min_market_cap": criteria["min_market_cap"]},
        )

        # Apply strategy-specific filters
        if strategy == "value":
            df = df[(df["pe_ratio"] > 0) & (df["pe_ratio"] < criteria["max_pe"])]
            df = df[(df["pb_ratio"] > 0) & (df["pb_ratio"] < criteria["max_pb"])]
        elif strategy == "growth":
            df = df[df["roe"] > criteria["min_roe"]]
        elif strategy == "dividend":
            df = df[df["dividend_yield"] > criteria["min_yield"]]

        logger.info(f"{strategy.capitalize()} strategy: {len(df)} candidates after filtering")

        # Get ML predictions (simplified - would need full feature set)
        # For now, use simple ranking by fundamentals
        if strategy == "value":
            df["score"] = 1 / (
                df["pe_ratio"] + df["pb_ratio"] / 10
            )  # Lower P/E, P/B = higher score
        elif strategy == "growth":
            df["score"] = df["roe"] * (df["market_cap"] ** 0.1)  # ROE weighted by size
        elif strategy == "dividend":
            df["score"] = df["dividend_yield"] * np.log(
                df["market_cap"]
            )  # Yield weighted by quality

        # Select top N
        top_stocks = df.nlargest(top_n, "score")

        logger.info(f"Selected top {len(top_stocks)} stocks for {strategy} strategy")

        return top_stocks[["ticker", "price", "market_cap", "score"]]

    def optimize_portfolio(self, total_value: float, as_of_date: date = None) -> Dict:
        """
        Create optimized portfolio allocation

        Args:
            total_value: Total portfolio value
            as_of_date: Date for portfolio construction

        Returns:
            {
                'regime': 'bull_low_vol',
                'allocation': {'growth': 0.55, 'value': 0.25, 'dividend': 0.20},
                'positions': [
                    {'ticker': 'AAPL', 'strategy': 'growth', 'shares': 100, 'value': 15000},
                    ...
                ]
            }
        """
        # Get regime-based allocation
        allocation = self.get_strategy_allocation(as_of_date)
        regime = self.regime_detector.detect_regime(as_of_date)

        # Calculate stocks per strategy (equal weight within strategy)
        stocks_per_strategy = 10  # 10 stocks per strategy = 30 total

        positions = []

        for strategy, target_weight in allocation.items():
            strategy_value = total_value * target_weight

            # Select top stocks for this strategy
            selected_stocks = self.select_stocks_ml(strategy, stocks_per_strategy, as_of_date)

            # Equal weight within strategy
            value_per_stock = strategy_value / len(selected_stocks)

            for _, stock in selected_stocks.iterrows():
                shares = int(value_per_stock / stock["price"])
                if shares > 0:
                    positions.append(
                        {
                            "ticker": stock["ticker"],
                            "strategy": strategy,
                            "shares": shares,
                            "price": stock["price"],
                            "value": shares * stock["price"],
                            "weight": (shares * stock["price"]) / total_value,
                        }
                    )

        portfolio = {
            "regime": regime,
            "allocation": allocation,
            "positions": positions,
            "total_value": sum(p["value"] for p in positions),
            "as_of_date": as_of_date,
        }

        logger.info(f"\nPortfolio optimized:")
        logger.info(f"  Regime: {regime}")
        logger.info(f"  Total positions: {len(positions)}")
        logger.info(f"  Total value: ${portfolio['total_value']:,.2f}")

        return portfolio

    def should_rebalance(
        self,
        last_rebalance_date: date,
        portfolio_returns: pd.Series = None,
        as_of_date: date = None,
    ) -> Tuple[bool, List[str]]:
        """
        Wrapper for dynamic rebalance triggers

        Returns:
            (should_rebalance, reasons)
        """
        return self.rebalance_triggers.should_rebalance(
            last_rebalance_date, portfolio_returns, as_of_date
        )


# Example usage
if __name__ == "__main__":
    # Initialize optimizer
    optimizer = MetaPortfolioOptimizer(model_path="models/xgboost_gpu.json")

    # Check if rebalancing needed
    last_rebalance = date(2024, 7, 1)
    should_rebal, reasons = optimizer.should_rebalance(last_rebalance)

    if should_rebal:
        logger.info(f"Rebalancing triggered: {', '.join(reasons)}")

        # Optimize new portfolio
        portfolio = optimizer.optimize_portfolio(total_value=1000000)  # $1M portfolio

        logger.info("\nNew Portfolio:")
        for pos in portfolio["positions"][:5]:
            logger.info(
                f"  {pos['ticker']:6} {pos['strategy']:8} {pos['shares']:5} shares @ ${pos['price']:.2f}"
            )
    else:
        logger.info("No rebalancing needed")
