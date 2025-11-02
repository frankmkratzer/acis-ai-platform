#!/usr/bin/env python3
"""
Backtest: Adaptive Portfolio vs Fixed Allocation
Compares regime-based adaptive allocation against fixed 33/33/33 allocation
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import date, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd

from portfolio.market_regime import MarketRegimeDetector
from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class PortfolioBacktest:
    """Backtest framework for comparing portfolio strategies"""

    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date
        self.regime_detector = MarketRegimeDetector()

    def get_strategy_returns(self, strategy: str, start: date, end: date) -> pd.Series:
        """
        Get returns for a specific strategy (value/growth/dividend)
        Uses sector ETFs as proxies for strategies
        """
        # Strategy to ETF mapping
        etf_map = {
            "value": "VTV",  # Vanguard Value ETF
            "growth": "VUG",  # Vanguard Growth ETF
            "dividend": "VYM",  # Vanguard High Dividend Yield ETF
        }

        ticker = etf_map.get(strategy, "SPY")

        query = """
        SELECT
            date,
            (close / LAG(close, 1) OVER (ORDER BY date) - 1) as daily_return
        FROM etf_bars
        WHERE ticker = %(ticker)s
          AND date >= %(start_date)s
          AND date <= %(end_date)s
        ORDER BY date;
        """

        df = pd.read_sql(
            query, engine, params={"ticker": ticker, "start_date": start, "end_date": end}
        )

        df = df.dropna()
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        return df["daily_return"]

    def backtest_fixed_allocation(self) -> Dict:
        """
        Backtest fixed 33/33/33 allocation

        Returns:
            dict with performance metrics
        """
        logger.info("Backtesting Fixed Allocation (33/33/33)...")

        # Get returns for each strategy
        value_returns = self.get_strategy_returns("value", self.start_date, self.end_date)
        growth_returns = self.get_strategy_returns("growth", self.start_date, self.end_date)
        dividend_returns = self.get_strategy_returns("dividend", self.start_date, self.end_date)

        # Align dates
        aligned_dates = value_returns.index.intersection(growth_returns.index).intersection(
            dividend_returns.index
        )
        value_returns = value_returns.loc[aligned_dates]
        growth_returns = growth_returns.loc[aligned_dates]
        dividend_returns = dividend_returns.loc[aligned_dates]

        # Fixed allocation: 33% each
        portfolio_returns = (
            0.333 * value_returns + 0.333 * growth_returns + 0.333 * dividend_returns
        )

        # Calculate metrics
        metrics = self._calculate_metrics(portfolio_returns, "Fixed 33/33/33")

        return metrics

    def backtest_adaptive_allocation(self) -> Dict:
        """
        Backtest adaptive regime-based allocation

        Returns:
            dict with performance metrics
        """
        logger.info("Backtesting Adaptive Allocation (Regime-Based)...")

        # Get returns for each strategy
        value_returns = self.get_strategy_returns("value", self.start_date, self.end_date)
        growth_returns = self.get_strategy_returns("growth", self.start_date, self.end_date)
        dividend_returns = self.get_strategy_returns("dividend", self.start_date, self.end_date)

        # Align dates
        aligned_dates = value_returns.index.intersection(growth_returns.index).intersection(
            dividend_returns.index
        )
        value_returns = value_returns.loc[aligned_dates]
        growth_returns = growth_returns.loc[aligned_dates]
        dividend_returns = dividend_returns.loc[aligned_dates]

        # Calculate adaptive portfolio returns
        portfolio_returns = pd.Series(index=aligned_dates, dtype=float)

        for trade_date in aligned_dates:
            # Detect regime for this date
            regime = self.regime_detector.detect_regime(trade_date)
            allocation = self.regime_detector.REGIME_ALLOCATIONS[regime]

            # Calculate weighted return
            portfolio_returns[trade_date] = (
                allocation["value"] * value_returns[trade_date]
                + allocation["growth"] * growth_returns[trade_date]
                + allocation["dividend"] * dividend_returns[trade_date]
            )

        # Calculate metrics
        metrics = self._calculate_metrics(portfolio_returns, "Adaptive (Regime-Based)")

        return metrics

    def _calculate_metrics(self, returns: pd.Series, strategy_name: str) -> Dict:
        """Calculate performance metrics"""

        cumulative_returns = (1 + returns).cumprod()
        total_return = cumulative_returns.iloc[-1] - 1

        # Annualized return
        days = (returns.index[-1] - returns.index[0]).days
        years = days / 365.25
        annualized_return = (1 + total_return) ** (1 / years) - 1

        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)

        # Sharpe ratio (assuming 0% risk-free rate)
        sharpe = (annualized_return / volatility) if volatility > 0 else 0

        # Maximum drawdown
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()

        # Downside deviation (semi-deviation)
        negative_returns = returns[returns < 0]
        downside_deviation = (
            negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        )

        # Sortino ratio
        sortino = (annualized_return / downside_deviation) if downside_deviation > 0 else 0

        # Win rate
        win_rate = (returns > 0).mean()

        # Monthly returns for analysis
        monthly_returns = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        best_month = monthly_returns.max()
        worst_month = monthly_returns.min()

        metrics = {
            "strategy": strategy_name,
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "best_month": best_month,
            "worst_month": worst_month,
            "downside_deviation": downside_deviation,
            "num_periods": len(returns),
            "returns": returns,
            "cumulative": cumulative_returns,
        }

        return metrics

    def compare_strategies(self) -> pd.DataFrame:
        """
        Run backtest for both strategies and compare

        Returns:
            DataFrame with comparison metrics
        """
        logger.info("=" * 70)
        logger.info("PORTFOLIO BACKTEST COMPARISON")
        logger.info("=" * 70)
        logger.info(f"Period: {self.start_date} to {self.end_date}")
        logger.info("")

        # Run backtests
        fixed_metrics = self.backtest_fixed_allocation()
        adaptive_metrics = self.backtest_adaptive_allocation()

        # Create comparison dataframe
        comparison = pd.DataFrame(
            {
                "Fixed 33/33/33": [
                    f"{fixed_metrics['total_return']:.2%}",
                    f"{fixed_metrics['annualized_return']:.2%}",
                    f"{fixed_metrics['volatility']:.2%}",
                    f"{fixed_metrics['sharpe_ratio']:.3f}",
                    f"{fixed_metrics['sortino_ratio']:.3f}",
                    f"{fixed_metrics['max_drawdown']:.2%}",
                    f"{fixed_metrics['win_rate']:.1%}",
                    f"{fixed_metrics['best_month']:.2%}",
                    f"{fixed_metrics['worst_month']:.2%}",
                ],
                "Adaptive (Regime)": [
                    f"{adaptive_metrics['total_return']:.2%}",
                    f"{adaptive_metrics['annualized_return']:.2%}",
                    f"{adaptive_metrics['volatility']:.2%}",
                    f"{adaptive_metrics['sharpe_ratio']:.3f}",
                    f"{adaptive_metrics['sortino_ratio']:.3f}",
                    f"{adaptive_metrics['max_drawdown']:.2%}",
                    f"{adaptive_metrics['win_rate']:.1%}",
                    f"{adaptive_metrics['best_month']:.2%}",
                    f"{adaptive_metrics['worst_month']:.2%}",
                ],
            },
            index=[
                "Total Return",
                "Annualized Return",
                "Volatility",
                "Sharpe Ratio",
                "Sortino Ratio",
                "Max Drawdown",
                "Win Rate",
                "Best Month",
                "Worst Month",
            ],
        )

        logger.info("\n" + comparison.to_string())
        logger.info("\n" + "=" * 70)

        # Calculate improvement
        sharpe_improvement = (
            (
                (adaptive_metrics["sharpe_ratio"] - fixed_metrics["sharpe_ratio"])
                / abs(fixed_metrics["sharpe_ratio"])
                * 100
            )
            if fixed_metrics["sharpe_ratio"] != 0
            else 0
        )

        logger.info(f"\nSharpe Ratio Improvement: {sharpe_improvement:+.1f}%")

        if adaptive_metrics["sharpe_ratio"] > fixed_metrics["sharpe_ratio"]:
            logger.info("✅ Adaptive strategy outperforms fixed allocation")
        else:
            logger.info("❌ Fixed allocation outperforms adaptive strategy")

        logger.info("=" * 70)

        return comparison, fixed_metrics, adaptive_metrics


def main():
    parser = argparse.ArgumentParser(description="Backtest adaptive vs fixed allocation")
    parser.add_argument(
        "--start-date", type=str, default="2020-01-01", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument("--end-date", type=str, default="2024-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, help="Output CSV path for results")

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)

    # Run backtest
    backtest = PortfolioBacktest(start_date, end_date)
    comparison, fixed, adaptive = backtest.compare_strategies()

    # Save results if requested
    if args.output:
        comparison.to_csv(args.output)
        logger.info(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
