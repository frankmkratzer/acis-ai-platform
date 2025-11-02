"""
ML Strategy Backtesting

Simulates portfolio performance using ML predictions vs baseline momentum.

Usage:
    python backtest_ml_strategy.py --start-date 2020-01-01 --end-date 2025-01-01
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from feature_engineering import FeatureEngineer

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


class MLBacktester:
    """Backtest ML-based stock selection strategy"""

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        top_n_stocks: int = 25,
        rebalance_frequency: str = "quarterly",  # 'monthly' or 'quarterly'
    ):
        self.initial_capital = initial_capital
        self.top_n_stocks = top_n_stocks
        self.rebalance_frequency = rebalance_frequency
        self.models_dir = Path(__file__).parent / "models"

    def load_model_for_date(self, as_of_date: str):
        """Load the appropriate model for a given date"""
        # Find the model trained before this date
        model_files = list(self.models_dir.glob("xgboost_ranker_*.pkl"))

        if not model_files:
            raise ValueError("No trained models found")

        # Get model dates
        model_dates = []
        for f in model_files:
            try:
                date_str = f.stem.split("_")[-1]
                model_dates.append((pd.to_datetime(date_str), f))
            except:
                continue

        # Find most recent model before as_of_date
        target_date = pd.to_datetime(as_of_date)
        valid_models = [(d, f) for d, f in model_dates if d <= target_date]

        if not valid_models:
            return None

        # Use most recent
        model_date, model_file = max(valid_models, key=lambda x: x[0])
        logger.info(f"Loading model from {model_date.date()} for prediction on {as_of_date}")

        return joblib.load(model_file)

    def get_stock_rankings(
        self, as_of_date: str, method: str = "ml"  # 'ml' or 'momentum'
    ) -> pd.DataFrame:
        """
        Get ranked stock list

        Args:
            as_of_date: Date to rank stocks
            method: 'ml' for ML predictions or 'momentum' for baseline

        Returns:
            DataFrame with ticker and score columns
        """
        # Create features
        engineer = FeatureEngineer(as_of_date=as_of_date)
        features = engineer.create_features()

        if len(features) == 0:
            return pd.DataFrame()

        if method == "ml":
            # Load model and predict
            model = self.load_model_for_date(as_of_date)

            if model is None:
                logger.warning(f"No model available for {as_of_date}, using momentum fallback")
                method = "momentum"
            else:
                # Prepare features (same as training)
                exclude_cols = ["ticker", "sector"]
                feature_cols = [col for col in features.columns if col not in exclude_cols]

                X = features[feature_cols].fillna(features[feature_cols].median())

                # Make predictions
                predictions = model.predict(X)
                features["score"] = predictions

        if method == "momentum":
            # Baseline: composite momentum
            features["score"] = (
                0.5 * features.get("return_3mo", 0)
                + 0.3 * features.get("return_6mo", 0)
                + 0.2 * features.get("dist_from_52w_high", 0)
            )

        # Rank stocks
        rankings = features[["ticker", "score"]].sort_values("score", ascending=False)

        return rankings

    def get_prices(self, tickers: list, start_date: str, end_date: str) -> pd.DataFrame:
        """Get historical prices for backtesting"""
        query = """
        SELECT ticker, date, close
        FROM daily_bars
        WHERE ticker = ANY(%s)
          AND date >= %s
          AND date <= %s
        ORDER BY date, ticker
        """

        with get_psycopg2_connection() as conn:
            prices = pd.read_sql(query, conn, params=(tickers, start_date, end_date))

        return prices.pivot(index="date", columns="ticker", values="close")

    def run_backtest(self, start_date: str, end_date: str, method: str = "ml") -> pd.DataFrame:
        """
        Run portfolio backtest

        Returns:
            DataFrame with daily portfolio values and holdings
        """
        logger.info(f"Running {method.upper()} backtest from {start_date} to {end_date}")

        # Generate rebalance dates
        rebalance_dates = self._generate_rebalance_dates(start_date, end_date)
        logger.info(f"Rebalancing {len(rebalance_dates)} times")

        # Track portfolio
        portfolio_values = []
        current_holdings = {}
        current_cash = self.initial_capital

        for i, rebal_date in enumerate(rebalance_dates):
            logger.info(f"\nRebalancing {i+1}/{len(rebalance_dates)}: {rebal_date}")

            # Get next rebalance date for holding period
            next_rebal = rebalance_dates[i + 1] if i + 1 < len(rebalance_dates) else end_date

            # Get stock rankings
            rankings = self.get_stock_rankings(rebal_date, method=method)

            if len(rankings) == 0:
                logger.warning(f"No rankings for {rebal_date}")
                continue

            # Select top N stocks
            selected_stocks = rankings.head(self.top_n_stocks)["ticker"].tolist()
            logger.info(f"Selected {len(selected_stocks)} stocks")

            # Get prices for holding period
            prices = self.get_prices(selected_stocks, rebal_date, next_rebal)

            if prices.empty:
                logger.warning(f"No price data for {rebal_date}")
                continue

            # Calculate portfolio value at rebalance
            portfolio_value = current_cash
            for ticker, shares in current_holdings.items():
                if ticker in prices.columns and rebal_date in prices.index:
                    portfolio_value += shares * prices.loc[rebal_date, ticker]

            # Liquidate and rebalance (equal weight)
            current_holdings = {}
            allocation_per_stock = portfolio_value / len(selected_stocks)

            for ticker in selected_stocks:
                if ticker in prices.columns and rebal_date in prices.index:
                    price = prices.loc[rebal_date, ticker]
                    shares = allocation_per_stock / price
                    current_holdings[ticker] = shares

            current_cash = 0  # Fully invested

            # Track daily values during holding period
            for date in prices.index:
                daily_value = 0
                for ticker, shares in current_holdings.items():
                    if ticker in prices.columns:
                        daily_value += shares * prices.loc[date, ticker]

                portfolio_values.append(
                    {"date": date, "portfolio_value": daily_value, "method": method}
                )

        results = pd.DataFrame(portfolio_values)
        return results

    def _generate_rebalance_dates(self, start_date: str, end_date: str) -> list:
        """Generate rebalance dates"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        dates = []
        current = start

        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))

            if self.rebalance_frequency == "monthly":
                current += relativedelta(months=1)
            elif self.rebalance_frequency == "quarterly":
                current += relativedelta(months=3)

        return dates

    def calculate_metrics(self, results: pd.DataFrame) -> dict:
        """Calculate performance metrics"""
        results = results.set_index("date").sort_index()
        results["returns"] = results["portfolio_value"].pct_change()

        # Total return
        total_return = (
            results["portfolio_value"].iloc[-1] / results["portfolio_value"].iloc[0]
        ) - 1

        # CAGR
        n_years = (results.index[-1] - results.index[0]).days / 365.25
        cagr = (1 + total_return) ** (1 / n_years) - 1

        # Sharpe ratio (annualized)
        sharpe = np.sqrt(252) * (results["returns"].mean() / results["returns"].std())

        # Max drawdown
        cummax = results["portfolio_value"].cummax()
        drawdown = (results["portfolio_value"] - cummax) / cummax
        max_drawdown = drawdown.min()

        return {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "final_value": results["portfolio_value"].iloc[-1],
        }


def main():
    parser = argparse.ArgumentParser(description="Backtest ML strategy")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--method", default="ml", choices=["ml", "momentum", "both"])
    parser.add_argument("--capital", type=float, default=1000000)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--frequency", default="quarterly", choices=["monthly", "quarterly"])

    args = parser.parse_args()

    backtester = MLBacktester(
        initial_capital=args.capital, top_n_stocks=args.top_n, rebalance_frequency=args.frequency
    )

    methods = ["ml", "momentum"] if args.method == "both" else [args.method]

    for method in methods:
        results = backtester.run_backtest(args.start_date, args.end_date, method=method)
        metrics = backtester.calculate_metrics(results)

        logger.info(f"\n{'='*80}")
        logger.info(f"{method.upper()} STRATEGY RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"Total Return: {metrics['total_return']:.2%}")
        logger.info(f"CAGR: {metrics['cagr']:.2%}")
        logger.info(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
        logger.info(f"Final Value: ${metrics['final_value']:,.0f}")


if __name__ == "__main__":
    main()
