"""
Portfolio Comparison Service

Compares different portfolio strategies (Growth/Momentum, Dividend, Value)
based on historical backtesting data or simulated performance.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


class PortfolioComparisonService:
    """Service for comparing portfolio strategies."""

    def __init__(self):
        self.db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        # Portfolio strategy definitions
        self.portfolios = {
            1: {
                "name": "Growth/Momentum",
                "description": "Aggressive growth focused on tech and momentum stocks",
                "etfs": ["VUG", "MTUM", "QQQ"],
                "rebalance_frequency": "monthly",
                "target_volatility": 0.20,
                "expected_return": 0.12,
            },
            2: {
                "name": "Dividend",
                "description": "Conservative income-generating portfolio",
                "etfs": ["VYM", "SCHD", "DVY"],
                "rebalance_frequency": "quarterly",
                "target_volatility": 0.12,
                "expected_return": 0.08,
            },
            3: {
                "name": "Value",
                "description": "Contrarian value investing approach",
                "etfs": ["VTV", "IWD", "VONV"],
                "rebalance_frequency": "quarterly",
                "target_volatility": 0.15,
                "expected_return": 0.10,
            },
        }

    async def compare_portfolios(
        self, portfolio_ids: List[int] = None, lookback_days: int = 365
    ) -> Dict[str, Any]:
        """
        Compare portfolio strategies.

        For now, this returns strategy definitions and simulated metrics.
        When RL models are trained, it will use actual backtest data.
        """

        if not portfolio_ids:
            portfolio_ids = [1, 2, 3]

        comparison_data = []

        for portfolio_id in portfolio_ids:
            if portfolio_id not in self.portfolios:
                continue

            portfolio_info = self.portfolios[portfolio_id]

            # Fetch any backtest results if available
            backtest_metrics = await self._get_backtest_metrics(portfolio_id, lookback_days)

            # Combine with strategy info
            comparison_data.append(
                {
                    "portfolio_id": portfolio_id,
                    "name": portfolio_info["name"],
                    "description": portfolio_info["description"],
                    "strategy": {
                        "etfs": portfolio_info["etfs"],
                        "rebalance_frequency": portfolio_info["rebalance_frequency"],
                        "target_volatility": portfolio_info["target_volatility"],
                        "expected_return": portfolio_info["expected_return"],
                    },
                    "metrics": backtest_metrics,
                }
            )

        # Generate comparison summary
        summary = self._generate_comparison_summary(comparison_data)

        return {"portfolios": comparison_data, "summary": summary, "lookback_days": lookback_days}

    async def _get_backtest_metrics(self, portfolio_id: int, lookback_days: int) -> Dict[str, Any]:
        """
        Fetch backtest metrics for a portfolio.

        Currently returns simulated metrics.
        Will be replaced with actual backtest data once RL training completes.
        """

        # Check if backtest results exist in database
        # (table doesn't exist yet, will be created by backtesting dashboard)

        # For now, return simulated metrics based on strategy
        portfolio_info = self.portfolios[portfolio_id]

        # Simulated metrics (replace with actual data later)
        if portfolio_id == 1:  # Growth/Momentum
            return {
                "total_return": 0.145,  # 14.5% annual
                "volatility": 0.195,
                "sharpe_ratio": 0.68,
                "max_drawdown": -0.28,
                "win_rate": 0.58,
                "avg_trade_return": 0.023,
                "num_trades": 52,  # Monthly rebalancing
                "status": "simulated",
            }
        elif portfolio_id == 2:  # Dividend
            return {
                "total_return": 0.092,  # 9.2% annual
                "volatility": 0.115,
                "sharpe_ratio": 0.72,
                "max_drawdown": -0.18,
                "win_rate": 0.64,
                "avg_trade_return": 0.018,
                "num_trades": 16,  # Quarterly rebalancing
                "status": "simulated",
            }
        elif portfolio_id == 3:  # Value
            return {
                "total_return": 0.108,  # 10.8% annual
                "volatility": 0.145,
                "sharpe_ratio": 0.66,
                "max_drawdown": -0.22,
                "win_rate": 0.61,
                "avg_trade_return": 0.020,
                "num_trades": 16,  # Quarterly rebalancing
                "status": "simulated",
            }

        return {}

    def _generate_comparison_summary(self, comparison_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary comparing all portfolios."""

        if not comparison_data:
            return {}

        # Find best performers
        best_return = max(comparison_data, key=lambda x: x["metrics"].get("total_return", 0))
        best_sharpe = max(comparison_data, key=lambda x: x["metrics"].get("sharpe_ratio", 0))
        lowest_volatility = min(comparison_data, key=lambda x: x["metrics"].get("volatility", 1))
        lowest_drawdown = max(comparison_data, key=lambda x: x["metrics"].get("max_drawdown", -1))

        return {
            "best_return": {
                "portfolio": best_return["name"],
                "value": best_return["metrics"].get("total_return", 0),
            },
            "best_sharpe": {
                "portfolio": best_sharpe["name"],
                "value": best_sharpe["metrics"].get("sharpe_ratio", 0),
            },
            "lowest_volatility": {
                "portfolio": lowest_volatility["name"],
                "value": lowest_volatility["metrics"].get("volatility", 0),
            },
            "smallest_drawdown": {
                "portfolio": lowest_drawdown["name"],
                "value": lowest_drawdown["metrics"].get("max_drawdown", 0),
            },
            "recommendation": self._generate_recommendation(comparison_data),
        }

    def _generate_recommendation(self, comparison_data: List[Dict[str, Any]]) -> str:
        """Generate a recommendation based on comparison."""

        # Simple recommendation logic
        best_sharpe = max(comparison_data, key=lambda x: x["metrics"].get("sharpe_ratio", 0))

        return f"Based on risk-adjusted returns (Sharpe ratio), the {best_sharpe['name']} strategy shows the best balance of return and risk."


# Singleton instance
_portfolio_comparison_service = None


def get_portfolio_comparison_service() -> PortfolioComparisonService:
    """Get singleton instance of portfolio comparison service."""
    global _portfolio_comparison_service
    if _portfolio_comparison_service is None:
        _portfolio_comparison_service = PortfolioComparisonService()
    return _portfolio_comparison_service
