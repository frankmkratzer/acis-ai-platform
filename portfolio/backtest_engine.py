#!/usr/bin/env python3
"""
Backtesting Engine for ML Portfolio Strategies

Simulates historical performance of the ML portfolio manager by:
1. Rolling forward through time
2. Generating predictions at each rebalance date
3. Tracking actual returns vs predicted returns
4. Calculating performance metrics (Sharpe, drawdown, etc.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from portfolio.ml_portfolio_manager import MLPortfolioManager
from utils.db_config import engine


class BacktestEngine:
    """
    Backtesting engine for portfolio strategies
    """

    def __init__(
        self,
        model_path: str = None,
        rebalance_frequency: int = 20,  # days between rebalances
        transaction_cost: float = 0.001,
    ):  # 10 bps per trade
        """
        Initialize backtest engine

        Args:
            model_path: Path to trained model
            rebalance_frequency: Days between portfolio rebalances (default 20 = monthly)
            transaction_cost: Transaction cost as fraction (default 0.001 = 10 bps)
        """
        self.manager = MLPortfolioManager(model_path=model_path)
        self.rebalance_frequency = rebalance_frequency
        self.transaction_cost = transaction_cost

    def get_actual_returns(
        self, tickers: List[str], start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Get actual historical returns for tickers

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with columns: ticker, date, actual_return_20d
        """
        ticker_list = "','".join(tickers)

        query = f"""
        WITH price_data AS (
            SELECT
                ticker,
                date,
                close,
                LEAD(close, 20) OVER (PARTITION BY ticker ORDER BY date) as future_close_20d
            FROM bars
            WHERE ticker IN ('{ticker_list}')
              AND date >= %(start_date)s
              AND date <= %(end_date)s
        )
        SELECT
            ticker,
            date,
            CASE
                WHEN future_close_20d IS NOT NULL AND close > 0
                THEN (future_close_20d - close) / close
                ELSE NULL
            END as actual_return_20d
        FROM price_data
        WHERE future_close_20d IS NOT NULL
        ORDER BY date, ticker
        """

        df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})

        return df

    def calculate_portfolio_return(
        self, portfolio: pd.DataFrame, actual_returns: pd.DataFrame, rebalance_date: date
    ) -> Tuple[float, Dict]:
        """
        Calculate realized portfolio return for a rebalance period

        Args:
            portfolio: Portfolio with ticker and target_weight
            actual_returns: DataFrame with ticker, date, actual_return_20d
            rebalance_date: Date of rebalancing

        Returns:
            Tuple of (portfolio_return, detailed_stats)
        """
        # Get returns for this rebalance date
        period_returns = actual_returns[actual_returns["date"] == rebalance_date].copy()

        # Merge with portfolio weights
        merged = portfolio.merge(period_returns, on="ticker", how="inner")

        if len(merged) == 0:
            return 0.0, {"realized_stocks": 0, "predicted_return": 0.0}

        # Calculate weighted return
        merged["weighted_return"] = merged["target_weight"] * merged["actual_return_20d"]
        portfolio_return = merged["weighted_return"].sum()

        # Calculate predicted return
        merged["weighted_predicted"] = merged["target_weight"] * merged["predicted_return"]
        predicted_return = merged["weighted_predicted"].sum()

        stats = {
            "realized_stocks": len(merged),
            "predicted_return": float(predicted_return),
            "actual_return": float(portfolio_return),
            "prediction_error": float(portfolio_return - predicted_return),
        }

        return float(portfolio_return), stats

    def run_backtest(
        self,
        start_date: date,
        end_date: date,
        initial_capital: float = 100000.0,
        top_n: int = 50,
        weighting: str = "signal",
        max_position: float = 0.10,
        min_market_cap: float = None,
    ) -> Dict:
        """
        Run full backtest simulation

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            top_n: Number of stocks in portfolio
            weighting: Weighting scheme
            max_position: Max position size
            min_market_cap: Minimum market cap filter

        Returns:
            Dict with backtest results and performance metrics
        """
        logger.info("=" * 60)
        logger.info("STARTING BACKTEST")
        logger.info("=" * 60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Rebalance Frequency: {self.rebalance_frequency} days")
        logger.info(f"Transaction Cost: {self.transaction_cost * 10000:.0f} bps")

        # Generate rebalance dates
        current_date = start_date
        rebalance_dates = []
        while current_date <= end_date:
            rebalance_dates.append(current_date)
            current_date += timedelta(days=self.rebalance_frequency)

        logger.info(f"Total rebalance periods: {len(rebalance_dates)}")

        # Track portfolio over time
        portfolio_values = []
        daily_returns = []
        rebalance_history = []

        current_capital = initial_capital
        current_holdings = {}  # {ticker: shares}

        for i, rebalance_date in enumerate(rebalance_dates):
            logger.info(f"\n[{i+1}/{len(rebalance_dates)}] Rebalancing on {rebalance_date}")

            # Generate portfolio for this date
            try:
                result = self.manager.execute_rebalance(
                    tickers=None,
                    current_portfolio=current_holdings,
                    cash_available=current_capital,
                    top_n=top_n,
                    weighting=weighting,
                    max_position=max_position,
                    as_of_date=rebalance_date,
                    min_market_cap=min_market_cap,
                )

                if result is None:
                    logger.warning(f"No portfolio generated for {rebalance_date}, skipping")
                    continue

                target_portfolio = result["target_portfolio"]
                trades = result["trades"]

                # Calculate transaction costs
                trade_value = trades["trade_value"].abs().sum() if len(trades) > 0 else 0.0
                transaction_costs = trade_value * self.transaction_cost
                current_capital -= transaction_costs

                # Update holdings
                for _, trade in trades.iterrows():
                    ticker = trade["ticker"]
                    current_holdings[ticker] = (
                        current_holdings.get(ticker, 0) + trade["trade_shares"]
                    )
                    if current_holdings[ticker] <= 0.01:  # Close small positions
                        current_holdings.pop(ticker, None)

                # Get actual returns for next period (if not last period)
                if i < len(rebalance_dates) - 1:
                    tickers = list(target_portfolio["ticker"])
                    actual_returns = self.get_actual_returns(
                        tickers=tickers,
                        start_date=rebalance_date,
                        end_date=rebalance_date + timedelta(days=self.rebalance_frequency + 5),
                    )

                    # Calculate portfolio return
                    portfolio_return, stats = self.calculate_portfolio_return(
                        target_portfolio, actual_returns, rebalance_date
                    )

                    # Update capital
                    period_pnl = current_capital * portfolio_return
                    current_capital += period_pnl

                    # Record history
                    rebalance_history.append(
                        {
                            "date": rebalance_date,
                            "capital": current_capital,
                            "portfolio_return": portfolio_return,
                            "predicted_return": stats["predicted_return"],
                            "prediction_error": stats["prediction_error"],
                            "transaction_costs": transaction_costs,
                            "num_positions": len(target_portfolio),
                            "realized_stocks": stats["realized_stocks"],
                        }
                    )

                    daily_returns.append(portfolio_return)

                    logger.info(f"  Actual Return: {portfolio_return*100:.2f}%")
                    logger.info(f"  Predicted Return: {stats['predicted_return']*100:.2f}%")
                    logger.info(f"  Capital: ${current_capital:,.2f}")

            except Exception as e:
                logger.error(f"Error on {rebalance_date}: {e}")
                continue

        # Calculate performance metrics
        returns_series = pd.Series(daily_returns)

        total_return = (current_capital - initial_capital) / initial_capital
        annualized_return = (1 + total_return) ** (
            252 / (self.rebalance_frequency * len(daily_returns))
        ) - 1

        sharpe_ratio = 0.0
        if len(returns_series) > 0 and returns_series.std() > 0:
            sharpe_ratio = (returns_series.mean() / returns_series.std()) * np.sqrt(
                252 / self.rebalance_frequency
            )

        # Calculate drawdown
        capital_series = pd.Series([r["capital"] for r in rebalance_history])
        cummax = capital_series.cummax()
        drawdown = (capital_series - cummax) / cummax
        max_drawdown = drawdown.min()

        # Win rate
        win_rate = (
            (returns_series > 0).sum() / len(returns_series) if len(returns_series) > 0 else 0.0
        )

        performance_metrics = {
            "total_return": float(total_return),
            "annualized_return": float(annualized_return),
            "sharpe_ratio": float(sharpe_ratio),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "num_trades": len(rebalance_history),
            "final_capital": float(current_capital),
            "total_pnl": float(current_capital - initial_capital),
        }

        logger.info("\n" + "=" * 60)
        logger.info("BACKTEST COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total Return: {total_return*100:.2f}%")
        logger.info(f"Annualized Return: {annualized_return*100:.2f}%")
        logger.info(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {max_drawdown*100:.2f}%")
        logger.info(f"Win Rate: {win_rate*100:.1f}%")
        logger.info(f"Final Capital: ${current_capital:,.2f}")

        return {
            "performance_metrics": performance_metrics,
            "rebalance_history": rebalance_history,
            "config": {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "initial_capital": initial_capital,
                "top_n": top_n,
                "weighting": weighting,
                "max_position": max_position,
                "rebalance_frequency": self.rebalance_frequency,
                "transaction_cost": self.transaction_cost,
                "min_market_cap": min_market_cap,
            },
        }


if __name__ == "__main__":
    # Example usage
    engine = BacktestEngine()

    results = engine.run_backtest(
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31),
        initial_capital=100000.0,
        top_n=50,
        weighting="signal",
        min_market_cap=2e9,  # $2B+ only
    )

    print("\nPerformance Summary:")
    for key, value in results["performance_metrics"].items():
        print(f"  {key}: {value}")
