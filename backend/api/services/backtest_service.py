"""
Backtesting Service

Provides historical performance analysis and backtesting capabilities
for portfolio strategies.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


class BacktestService:
    """Service for backtesting portfolio strategies."""

    def __init__(self):
        self.db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

    async def get_backtest_results(
        self, portfolio_id: int = None, start_date: str = None, end_date: str = None
    ) -> Dict[str, Any]:
        """
        Get backtest results for portfolio strategies.

        Args:
            portfolio_id: Specific portfolio (1=Growth, 2=Dividend, 3=Value) or None for all
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Backtest results with performance metrics
        """

        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Check if backtest results exist in database
        backtest_data = await self._fetch_backtest_data(portfolio_id, start_date, end_date)

        if not backtest_data:
            # No backtest data yet - return simulated metrics
            return await self._generate_simulated_backtest(portfolio_id, start_date, end_date)

        # Calculate performance metrics from backtest data
        metrics = self._calculate_backtest_metrics(backtest_data)

        return {
            "portfolio_id": portfolio_id,
            "start_date": start_date,
            "end_date": end_date,
            "data": backtest_data,
            "metrics": metrics,
            "status": "actual",
        }

    async def _fetch_backtest_data(
        self, portfolio_id: int, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch backtest results from database."""

        try:
            conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
            cur = conn.cursor()

            # Create backtest_results table if it doesn't exist
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id SERIAL PRIMARY KEY,
                    portfolio_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    portfolio_value DECIMAL(15, 2),
                    cash DECIMAL(15, 2),
                    positions JSONB,
                    daily_return DECIMAL(10, 6),
                    cumulative_return DECIMAL(10, 6),
                    sharpe_ratio DECIMAL(10, 4),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(portfolio_id, date)
                )
            """
            )
            conn.commit()

            # Fetch backtest data
            sql = """
                SELECT *
                FROM backtest_results
                WHERE date >= %s AND date <= %s
            """
            params = [start_date, end_date]

            if portfolio_id:
                sql += " AND portfolio_id = %s"
                params.append(portfolio_id)

            sql += " ORDER BY portfolio_id, date"

            cur.execute(sql, params)
            results = [dict(row) for row in cur.fetchall()]

            cur.close()
            conn.close()

            return results

        except Exception as e:
            print(f"Error fetching backtest data: {e}")
            return []

    async def _generate_simulated_backtest(
        self, portfolio_id: int, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Generate simulated backtest data when actual results aren't available."""

        # Portfolio strategy parameters
        strategies = {
            1: {  # Growth/Momentum
                "name": "Growth/Momentum",
                "annual_return": 0.145,
                "volatility": 0.195,
                "sharpe": 0.68,
                "max_drawdown": -0.28,
            },
            2: {  # Dividend
                "name": "Dividend",
                "annual_return": 0.092,
                "volatility": 0.115,
                "sharpe": 0.72,
                "max_drawdown": -0.18,
            },
            3: {  # Value
                "name": "Value",
                "annual_return": 0.108,
                "volatility": 0.145,
                "sharpe": 0.66,
                "max_drawdown": -0.22,
            },
        }

        if portfolio_id and portfolio_id in strategies:
            strategy = strategies[portfolio_id]

            # Generate simulated daily returns
            days = (
                datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")
            ).days

            # Simulate returns using GBM (Geometric Brownian Motion)
            daily_return = strategy["annual_return"] / 252
            daily_vol = strategy["volatility"] / np.sqrt(252)

            np.random.seed(42)  # For reproducibility
            returns = np.random.normal(daily_return, daily_vol, days)

            # Calculate portfolio values
            initial_value = 100000
            portfolio_values = [initial_value]
            for r in returns:
                portfolio_values.append(portfolio_values[-1] * (1 + r))

            # Create time series
            dates = pd.date_range(start=start_date, end=end_date, periods=days + 1)

            return {
                "portfolio_id": portfolio_id,
                "name": strategy["name"],
                "start_date": start_date,
                "end_date": end_date,
                "time_series": [
                    {
                        "date": dates[i].strftime("%Y-%m-%d"),
                        "portfolio_value": portfolio_values[i],
                        "return": returns[i - 1] if i > 0 else 0,
                        "cumulative_return": (portfolio_values[i] / initial_value) - 1,
                    }
                    for i in range(len(portfolio_values))
                ],
                "metrics": {
                    "total_return": (portfolio_values[-1] / initial_value) - 1,
                    "annualized_return": strategy["annual_return"],
                    "volatility": strategy["volatility"],
                    "sharpe_ratio": strategy["sharpe"],
                    "max_drawdown": strategy["max_drawdown"],
                    "final_value": portfolio_values[-1],
                    "initial_value": initial_value,
                },
                "status": "simulated",
            }

        # Return all portfolios if no specific ID
        return {
            "portfolios": [
                await self._generate_simulated_backtest(pid, start_date, end_date)
                for pid in [1, 2, 3]
            ],
            "status": "simulated",
        }

    def _calculate_backtest_metrics(self, backtest_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics from backtest data."""

        if not backtest_data:
            return {}

        # Convert to pandas for easier calculation
        df = pd.DataFrame(backtest_data)

        # Calculate metrics
        returns = df["daily_return"].dropna()
        cumulative_returns = df["cumulative_return"].dropna()

        total_return = cumulative_returns.iloc[-1] if len(cumulative_returns) > 0 else 0
        annualized_return = (
            (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0
        )

        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0

        # Calculate max drawdown
        cumulative_max = (1 + df["cumulative_return"]).cummax()
        drawdown = (1 + df["cumulative_return"]) / cumulative_max - 1
        max_drawdown = drawdown.min()

        return {
            "total_return": float(total_return),
            "annualized_return": float(annualized_return),
            "volatility": float(volatility),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "num_trades": len(backtest_data),
            "final_value": float(df["portfolio_value"].iloc[-1]),
            "initial_value": float(df["portfolio_value"].iloc[0]),
        }

    async def save_backtest_results(self, portfolio_id: int, results: List[Dict[str, Any]]):
        """Save backtest results to database."""

        try:
            conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
            cur = conn.cursor()

            for result in results:
                cur.execute(
                    """
                    INSERT INTO backtest_results (
                        portfolio_id, date, portfolio_value, cash, positions,
                        daily_return, cumulative_return, sharpe_ratio
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (portfolio_id, date) DO UPDATE SET
                        portfolio_value = EXCLUDED.portfolio_value,
                        cash = EXCLUDED.cash,
                        positions = EXCLUDED.positions,
                        daily_return = EXCLUDED.daily_return,
                        cumulative_return = EXCLUDED.cumulative_return,
                        sharpe_ratio = EXCLUDED.sharpe_ratio
                """,
                    [
                        portfolio_id,
                        result["date"],
                        result.get("portfolio_value"),
                        result.get("cash"),
                        result.get("positions"),  # JSON
                        result.get("daily_return"),
                        result.get("cumulative_return"),
                        result.get("sharpe_ratio"),
                    ],
                )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Failed to save backtest results: {e}")


# Singleton instance
_backtest_service = None


def get_backtest_service() -> BacktestService:
    """Get singleton instance of backtest service."""
    global _backtest_service
    if _backtest_service is None:
        _backtest_service = BacktestService()
    return _backtest_service
