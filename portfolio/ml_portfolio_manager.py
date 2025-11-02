#!/usr/bin/env python3
"""
ML-Based Portfolio Manager
Uses trained XGBoost model to generate trading signals and manage portfolio rebalancing
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class MLPortfolioManager:
    """
    Production portfolio manager using trained XGBoost model

    Features:
    - Load trained model
    - Generate predictions for universe of stocks
    - Rank stocks by predicted returns
    - Portfolio construction with risk management
    - Rebalancing logic
    """

    def __init__(
        self, model_path: str = None, strategy: str = None, market_cap_segment: str = None
    ):
        """
        Initialize portfolio manager with trained model

        Args:
            model_path: Path to trained XGBoost model (absolute or relative to project root)
            strategy: Strategy type ('dividend', 'growth', 'value', None for default)
            market_cap_segment: Market cap segment ('small', 'mid', 'large', 'all', None for default)
        """
        # Determine model path based on strategy
        if model_path is None:
            project_root = Path(__file__).parent.parent

            if strategy and market_cap_segment:
                # Strategy-specific model
                if strategy == "dividend":
                    model_name = "dividend_strategy"
                else:  # growth or value
                    model_name = f"{strategy}_{market_cap_segment}cap"

                model_path = str(project_root / "models" / model_name / "model.json")
                logger.info(f"Using strategy model: {model_name}")
            else:
                # Default model
                model_path = str(project_root / "models" / "xgboost_optimized" / "model.json")
                logger.info("Using default model")

        self.model_path = model_path
        self.strategy = strategy
        self.market_cap_segment = market_cap_segment
        self.model = None
        self.feature_names = None
        self.metadata = None
        self.load_model()

    def load_model(self):
        """Load trained XGBoost model"""
        logger.info(f"Loading trained model from {self.model_path}")

        # Load model
        self.model = xgb.XGBRegressor()
        self.model.load_model(self.model_path)

        # Load feature names
        feature_path = Path(self.model_path).parent / "feature_names.json"
        with open(feature_path, "r") as f:
            self.feature_names = json.load(f)

        # Load metadata if available
        metadata_path = Path(self.model_path).parent / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)
            logger.info(
                f"Model metadata: {self.metadata.get('strategy', 'default')} strategy, "
                f"IC: {self.metadata.get('spearman_ic', 'N/A')}"
            )

        logger.info(f"Model loaded successfully with {len(self.feature_names)} features")

    def _load_strategy_config(self):
        """Load strategy-specific configuration from JSON files"""
        if not self.strategy or not self.market_cap_segment:
            return None

        # Determine config file name
        if self.strategy == "dividend":
            config_name = "dividend_strategy.json"
        else:
            config_name = f"{self.strategy}_{self.market_cap_segment}_strategy.json"

        config_path = Path(__file__).parent.parent / "rl_trading" / "configs" / config_name

        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded strategy config: {config_name}")
            return config
        else:
            logger.warning(f"Strategy config not found: {config_path}")
            return None

    def get_latest_features(
        self,
        tickers: List[str] = None,
        as_of_date: date = None,
        min_market_cap: float = None,
        max_market_cap: float = None,
        min_price: float = None,
    ) -> pd.DataFrame:
        """
        Get latest features for stock universe from materialized view

        Args:
            tickers: List of tickers (None = all tickers)
            as_of_date: Date to get features for (None = latest)
            min_market_cap: Minimum market cap filter in dollars (e.g., 10e9 for $10B)
            max_market_cap: Maximum market cap filter in dollars
            min_price: Minimum price filter

        Returns:
            DataFrame with latest features for each ticker
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Load strategy config and apply filters if not explicitly provided
        strategy_config = self._load_strategy_config()
        if strategy_config and "ml_filters" in strategy_config:
            ml_filters = strategy_config["ml_filters"]
            # Only apply strategy config filters if not explicitly overridden
            if min_market_cap is None and "min_market_cap" in ml_filters:
                min_market_cap = ml_filters["min_market_cap"]
            if max_market_cap is None and "max_market_cap" in ml_filters:
                max_market_cap = ml_filters["max_market_cap"]
            if min_price is None and "min_price" in ml_filters:
                min_price = ml_filters["min_price"]

        filter_desc = []
        if min_market_cap:
            filter_desc.append(f"min_cap: ${min_market_cap/1e9:.1f}B")
        if max_market_cap:
            filter_desc.append(f"max_cap: ${max_market_cap/1e9:.1f}B")
        if min_price:
            filter_desc.append(f"min_price: ${min_price:.2f}")

        logger.info(
            f"Loading latest features as of {as_of_date}"
            + (f" ({', '.join(filter_desc)})" if filter_desc else "")
        )

        # Query materialized view for latest features
        filters = []
        if tickers:
            ticker_list = "','".join(tickers)
            filters.append(f"ticker IN ('{ticker_list}')")
        if min_market_cap:
            filters.append(f"market_cap >= {min_market_cap}")
        if max_market_cap:
            filters.append(f"market_cap <= {max_market_cap}")
        if min_price:
            filters.append(f"close >= {min_price}")

        where_clause = "AND " + " AND ".join(filters) if filters else ""

        query = f"""
        WITH latest_date AS (
            SELECT MAX(date) as max_date
            FROM ml_training_features
            WHERE date <= %(as_of_date)s
        )
        SELECT *
        FROM ml_training_features
        WHERE date = (SELECT max_date FROM latest_date)
          {where_clause}
        ORDER BY ticker
        """

        df = pd.read_sql(query, engine, params={"as_of_date": as_of_date})

        logger.info(
            f"Loaded features for {len(df)} tickers as of {df['date'].iloc[0] if len(df) > 0 else 'N/A'}"
        )

        return df

    def generate_predictions(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate return predictions for stock universe

        Args:
            features_df: DataFrame with features from get_latest_features()

        Returns:
            DataFrame with ticker, date, predicted_return, and features
        """
        logger.info(f"Generating predictions for {len(features_df)} stocks...")

        # Prepare features (same as training)
        exclude_cols = ["ticker", "date", "target_return"]
        feature_cols = [col for col in features_df.columns if col not in exclude_cols]

        # Ensure we have the same features as training
        X = features_df[feature_cols].fillna(0)

        # Generate predictions
        predictions = self.model.predict(X)

        # Create results DataFrame
        results = pd.DataFrame(
            {
                "ticker": features_df["ticker"],
                "date": features_df["date"],
                "predicted_return": predictions,
            }
        )

        # Add ranking
        results["rank"] = results["predicted_return"].rank(ascending=False, method="first")
        results = results.sort_values("predicted_return", ascending=False)

        logger.info(f"Generated predictions. Top 5 stocks:")
        logger.info(results[["ticker", "predicted_return", "rank"]].head().to_string())

        return results

    def construct_portfolio(
        self,
        predictions: pd.DataFrame,
        top_n: int = 50,
        weighting: str = "equal",
        max_position: float = 0.10,
    ) -> pd.DataFrame:
        """
        Construct portfolio from predictions

        Args:
            predictions: DataFrame from generate_predictions()
            top_n: Number of top stocks to hold
            weighting: 'equal', 'rank', or 'signal' weighted
            max_position: Maximum weight per position (e.g., 0.10 = 10%)

        Returns:
            DataFrame with ticker and target_weight
        """
        logger.info(f"Constructing portfolio: top {top_n} stocks, {weighting} weighting")

        # Select top N stocks
        top_stocks = predictions.head(top_n).copy()

        # Calculate weights based on weighting scheme
        if weighting == "equal":
            # Equal weight
            top_stocks["target_weight"] = 1.0 / top_n

        elif weighting == "rank":
            # Inverse rank weighting (rank 1 gets highest weight)
            ranks = top_stocks["rank"].values
            weights = 1.0 / ranks
            top_stocks["target_weight"] = weights / weights.sum()

        elif weighting == "signal":
            # Signal strength weighting (proportional to predicted return)
            # Only use positive predictions
            signals = np.maximum(top_stocks["predicted_return"].values, 0)
            if signals.sum() > 0:
                top_stocks["target_weight"] = signals / signals.sum()
            else:
                # Fallback to equal weight if all predictions are negative
                top_stocks["target_weight"] = 1.0 / top_n

        # Apply maximum position size constraint
        top_stocks["target_weight"] = top_stocks["target_weight"].clip(upper=max_position)

        # Renormalize weights to sum to 1.0
        top_stocks["target_weight"] = (
            top_stocks["target_weight"] / top_stocks["target_weight"].sum()
        )

        portfolio = top_stocks[["ticker", "predicted_return", "target_weight"]].copy()

        logger.info(f"Portfolio constructed. Top 10 positions:")
        logger.info(portfolio.head(10).to_string())
        logger.info(f"Total weight: {portfolio['target_weight'].sum():.4f}")

        return portfolio

    def calculate_rebalance_trades(
        self,
        current_portfolio: Dict[str, float],
        target_portfolio: pd.DataFrame,
        cash_available: float,
        prices: Dict[str, float],
        min_trade_size: float = 100.0,
    ) -> pd.DataFrame:
        """
        Calculate trades needed to rebalance from current to target portfolio

        Args:
            current_portfolio: Dict of {ticker: shares}
            target_portfolio: DataFrame from construct_portfolio()
            cash_available: Cash available for investing
            prices: Dict of {ticker: current_price}
            min_trade_size: Minimum trade value ($)

        Returns:
            DataFrame with ticker, current_shares, target_shares, trade_shares, trade_value
        """
        logger.info("Calculating rebalancing trades...")

        # Calculate total portfolio value
        current_value = sum(
            shares * prices.get(ticker, 0) for ticker, shares in current_portfolio.items()
        )
        total_value = current_value + cash_available

        logger.info(f"Current portfolio value: ${current_value:,.2f}")
        logger.info(f"Cash available: ${cash_available:,.2f}")
        logger.info(f"Total portfolio value: ${total_value:,.2f}")

        # Build trades DataFrame
        trades = []

        # Get all tickers (current + target)
        all_tickers = set(current_portfolio.keys()) | set(target_portfolio["ticker"])

        for ticker in all_tickers:
            current_shares = current_portfolio.get(ticker, 0)
            price = prices.get(ticker, 0)

            # Get target weight
            target_weight = (
                target_portfolio[target_portfolio["ticker"] == ticker]["target_weight"].iloc[0]
                if ticker in target_portfolio["ticker"].values
                else 0.0
            )

            # Calculate target shares
            target_value = total_value * target_weight
            target_shares = target_value / price if price > 0 else 0

            # Calculate trade
            trade_shares = target_shares - current_shares
            trade_value = trade_shares * price

            # Only include if trade size exceeds minimum
            if abs(trade_value) >= min_trade_size:
                trades.append(
                    {
                        "ticker": ticker,
                        "current_shares": current_shares,
                        "target_shares": target_shares,
                        "trade_shares": trade_shares,
                        "price": price,
                        "trade_value": trade_value,
                        "target_weight": target_weight,
                    }
                )

        trades_df = pd.DataFrame(trades)

        if len(trades_df) > 0:
            trades_df = trades_df.sort_values("trade_value", ascending=False)

            logger.info(f"\nRebalancing trades ({len(trades_df)} positions):")
            logger.info(
                f"Total buy value: ${trades_df[trades_df['trade_value'] > 0]['trade_value'].sum():,.2f}"
            )
            logger.info(
                f"Total sell value: ${abs(trades_df[trades_df['trade_value'] < 0]['trade_value'].sum()):,.2f}"
            )
            logger.info(f"\nTop 10 trades:")
            logger.info(trades_df.head(10).to_string())
        else:
            logger.info("No trades needed (all positions within tolerance)")

        return trades_df

    def execute_rebalance(
        self,
        tickers: List[str] = None,
        current_portfolio: Dict[str, float] = None,
        cash_available: float = 100000.0,
        top_n: int = 50,
        weighting: str = "signal",
        max_position: float = 0.10,
        as_of_date: date = None,
        min_market_cap: float = None,
    ) -> Dict:
        """
        Full rebalancing workflow

        Args:
            tickers: Stock universe (None = use all from view)
            current_portfolio: Current holdings {ticker: shares}
            cash_available: Cash available
            top_n: Number of stocks to hold
            weighting: Portfolio weighting scheme
            max_position: Max position size
            as_of_date: Date for rebalancing (None = today)
            min_market_cap: Minimum market cap in dollars (e.g., 10e9 for $10B mid-cap)

        Returns:
            Dict with portfolio, trades, and metadata
        """
        if current_portfolio is None:
            current_portfolio = {}

        logger.info("=" * 60)
        logger.info("PORTFOLIO REBALANCING WORKFLOW")
        logger.info("=" * 60)

        # Step 1: Load latest features
        features_df = self.get_latest_features(
            tickers=tickers, as_of_date=as_of_date, min_market_cap=min_market_cap
        )

        if len(features_df) == 0:
            logger.error("No features found! Cannot rebalance.")
            return None

        # Step 2: Generate predictions
        predictions = self.generate_predictions(features_df)

        # Step 3: Construct target portfolio
        target_portfolio = self.construct_portfolio(
            predictions=predictions, top_n=top_n, weighting=weighting, max_position=max_position
        )

        # Step 4: Get current prices
        prices = {}
        for ticker in set(current_portfolio.keys()) | set(target_portfolio["ticker"]):
            price_row = features_df[features_df["ticker"] == ticker]
            if len(price_row) > 0:
                # Use most recent close price (would need to add this to query)
                prices[ticker] = 100.0  # Placeholder - need actual prices

        # Step 5: Calculate trades
        trades = self.calculate_rebalance_trades(
            current_portfolio=current_portfolio,
            target_portfolio=target_portfolio,
            cash_available=cash_available,
            prices=prices,
        )

        logger.info("=" * 60)
        logger.info("REBALANCING COMPLETE")
        logger.info("=" * 60)

        return {
            "rebalance_date": as_of_date or date.today(),
            "target_portfolio": target_portfolio,
            "trades": trades,
            "predictions": predictions,
            "num_positions": len(target_portfolio),
            "universe_size": len(predictions),
        }


def main():
    """Example usage"""
    import argparse

    parser = argparse.ArgumentParser(description="ML Portfolio Manager")
    parser.add_argument("--top-n", type=int, default=50, help="Number of stocks to hold")
    parser.add_argument(
        "--weighting", type=str, default="signal", choices=["equal", "rank", "signal"]
    )
    parser.add_argument("--cash", type=float, default=100000.0, help="Cash available")
    parser.add_argument("--max-position", type=float, default=0.10, help="Max position size")

    args = parser.parse_args()

    # Initialize manager
    manager = MLPortfolioManager()

    # Example: Starting from scratch with cash
    result = manager.execute_rebalance(
        current_portfolio={},
        cash_available=args.cash,
        top_n=args.top_n,
        weighting=args.weighting,
        max_position=args.max_position,
    )

    if result:
        # Save results
        output_dir = Path("portfolio/rebalance_results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save target portfolio
        result["target_portfolio"].to_csv(
            output_dir / f"target_portfolio_{timestamp}.csv", index=False
        )

        # Save trades
        if len(result["trades"]) > 0:
            result["trades"].to_csv(output_dir / f"rebalance_trades_{timestamp}.csv", index=False)

        logger.info(f"\nResults saved to {output_dir}/")
        logger.info(f"  - target_portfolio_{timestamp}.csv")
        logger.info(f"  - rebalance_trades_{timestamp}.csv")


if __name__ == "__main__":
    main()
