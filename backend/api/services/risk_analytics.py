"""
Risk Analytics Service

Calculates professional risk metrics for portfolios:
- Sharpe Ratio: Risk-adjusted return
- Sortino Ratio: Downside risk-adjusted return
- Max Drawdown: Largest peak-to-trough decline
- Volatility: Standard deviation of returns
- Beta: Sensitivity to market movements
- Value at Risk (VaR): Expected maximum loss
- Correlation Matrix: How holdings move together
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


class RiskAnalytics:
    """Calculate portfolio risk metrics."""

    def __init__(self):
        """Initialize with database connection."""
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", "acis-ai"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "$@nJose420"),
        }

    def calculate_portfolio_risk(
        self, positions: List[Dict[str, Any]], lookback_days: int = 252  # 1 year of trading days
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics for a portfolio.

        Args:
            positions: List of portfolio positions with symbol, quantity, value
            lookback_days: Number of trading days to look back for calculations

        Returns:
            Dictionary with all risk metrics
        """

        if not positions:
            return self._empty_risk_metrics()

        # Extract symbols and weights
        symbols = [p["symbol"] for p in positions if p.get("instrument_type") == "EQUITY"]

        if not symbols:
            return self._empty_risk_metrics()

        # Convert all values to float to avoid Decimal issues
        total_value = sum(
            float(p["current_value"]) for p in positions if p.get("instrument_type") == "EQUITY"
        )

        if total_value == 0:
            return self._empty_risk_metrics()

        weights = {}
        for p in positions:
            if p.get("instrument_type") == "EQUITY":
                # Ensure both current_value and total_value are float before division
                current_val = float(p["current_value"])
                weight = current_val / total_value
                weights[p["symbol"]] = float(weight)  # Explicit float conversion

        # Get historical price data
        returns_df = self._get_historical_returns(symbols, lookback_days)

        if returns_df.empty:
            return self._empty_risk_metrics()

        # Get market returns (SPY as benchmark)
        market_returns = self._get_market_returns(lookback_days)

        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(returns_df, weights)

        # Calculate all risk metrics
        metrics = {
            "volatility": self._calculate_volatility(portfolio_returns),
            "sharpe_ratio": self._calculate_sharpe_ratio(portfolio_returns),
            "sortino_ratio": self._calculate_sortino_ratio(portfolio_returns),
            "max_drawdown": self._calculate_max_drawdown(portfolio_returns),
            "beta": self._calculate_beta(portfolio_returns, market_returns),
            "var_95": self._calculate_var(portfolio_returns, confidence=0.95),
            "var_99": self._calculate_var(portfolio_returns, confidence=0.99),
            "cvar_95": self._calculate_cvar(portfolio_returns, confidence=0.95),
            "correlation_matrix": self._calculate_correlation(returns_df),
            "diversification_score": self._calculate_diversification_score(returns_df, weights),
            "lookback_days": lookback_days,
            "analysis_date": datetime.now().isoformat(),
        }

        return metrics

    def _get_historical_returns(self, symbols: List[str], lookback_days: int) -> pd.DataFrame:
        """Fetch historical daily returns for symbols."""

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Get daily price data
        sql = """
            SELECT
                ticker,
                date,
                close,
                LAG(close) OVER (PARTITION BY ticker ORDER BY date) as prev_close
            FROM daily_bars
            WHERE ticker = ANY(%s)
              AND date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date DESC
        """

        cur.execute(sql, [symbols, lookback_days + 30])  # Extra days for lag calculation
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return pd.DataFrame()

        # Convert to DataFrame and calculate returns
        df = pd.DataFrame(rows)
        # Convert Decimal to float before calculations
        df["close"] = df["close"].astype(float)
        df["prev_close"] = df["prev_close"].astype(float)
        df["return"] = (df["close"] - df["prev_close"]) / df["prev_close"]

        # Pivot to wide format (dates x tickers)
        returns_pivot = df.pivot(index="date", columns="ticker", values="return")
        returns_pivot = returns_pivot.dropna()

        return returns_pivot

    def _get_market_returns(self, lookback_days: int) -> pd.Series:
        """Get S&P 500 (SPY) returns as market benchmark."""

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        sql = """
            SELECT
                date,
                close,
                LAG(close) OVER (ORDER BY date) as prev_close
            FROM daily_bars
            WHERE ticker = 'SPY'
              AND date >= CURRENT_DATE - INTERVAL '%s days'
            ORDER BY date DESC
        """

        cur.execute(sql, [lookback_days + 30])
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            return pd.Series()

        df = pd.DataFrame(rows)
        # Convert Decimal to float before calculations
        df["close"] = df["close"].astype(float)
        df["prev_close"] = df["prev_close"].astype(float)
        df["return"] = (df["close"] - df["prev_close"]) / df["prev_close"]

        return df.set_index("date")["return"].dropna()

    def _calculate_portfolio_returns(
        self, returns_df: pd.DataFrame, weights: Dict[str, float]
    ) -> pd.Series:
        """Calculate weighted portfolio returns."""

        portfolio_returns = pd.Series(0, index=returns_df.index)

        for symbol, weight in weights.items():
            if symbol in returns_df.columns:
                portfolio_returns += returns_df[symbol] * weight

        return portfolio_returns

    def _calculate_volatility(self, returns: pd.Series) -> float:
        """
        Calculate annualized volatility (standard deviation).

        Volatility = std(daily returns) * sqrt(252)
        """
        if len(returns) < 2:
            return 0.0

        return float(returns.std() * np.sqrt(252))

    def _calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.045  # 4.5% current risk-free rate
    ) -> float:
        """
        Calculate Sharpe Ratio (risk-adjusted return).

        Sharpe = (Portfolio Return - Risk Free Rate) / Volatility

        Interpretation:
        > 1.0 = Good
        > 2.0 = Very good
        > 3.0 = Excellent
        """
        if len(returns) < 2:
            return 0.0

        annual_return = (1 + returns.mean()) ** 252 - 1
        volatility = returns.std() * np.sqrt(252)

        if volatility == 0:
            return 0.0

        sharpe = (annual_return - risk_free_rate) / volatility
        return float(sharpe)

    def _calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: float = 0.045) -> float:
        """
        Calculate Sortino Ratio (downside risk-adjusted return).

        Like Sharpe, but only penalizes downside volatility.
        Better for portfolios with asymmetric returns.
        """
        if len(returns) < 2:
            return 0.0

        annual_return = (1 + returns.mean()) ** 252 - 1

        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            return float("inf")

        downside_std = downside_returns.std() * np.sqrt(252)

        if downside_std == 0:
            return 0.0

        sortino = (annual_return - risk_free_rate) / downside_std
        return float(sortino)

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """
        Calculate maximum drawdown (largest peak-to-trough decline).

        Max Drawdown = (Trough - Peak) / Peak

        Example: -30% means portfolio declined 30% from peak.
        """
        if len(returns) < 2:
            return 0.0

        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()

        # Calculate running maximum
        running_max = cumulative.expanding().max()

        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max

        return float(drawdown.min())

    def _calculate_beta(self, portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
        """
        Calculate Beta (sensitivity to market movements).

        Beta = Cov(Portfolio, Market) / Var(Market)

        Interpretation:
        Beta = 1.0: Moves with market
        Beta > 1.0: More volatile than market
        Beta < 1.0: Less volatile than market
        Beta < 0.0: Moves opposite to market
        """
        if len(portfolio_returns) < 2 or len(market_returns) < 2:
            return 1.0

        # Align dates
        aligned = pd.DataFrame({"portfolio": portfolio_returns, "market": market_returns}).dropna()

        if len(aligned) < 2:
            return 1.0

        covariance = aligned["portfolio"].cov(aligned["market"])
        market_variance = aligned["market"].var()

        if market_variance == 0:
            return 1.0

        beta = covariance / market_variance
        return float(beta)

    def _calculate_var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Value at Risk (VaR).

        VaR = Maximum expected loss at given confidence level

        Example: VaR(95%) = -2.5% means there's a 5% chance
        of losing more than 2.5% in a single day.
        """
        if len(returns) < 2:
            return 0.0

        var = np.percentile(returns, (1 - confidence) * 100)
        return float(var)

    def _calculate_cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """
        Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        CVaR = Average loss beyond VaR threshold

        More conservative than VaR - tells you average loss
        in worst-case scenarios.
        """
        if len(returns) < 2:
            return 0.0

        var = self._calculate_var(returns, confidence)
        cvar = returns[returns <= var].mean()

        return float(cvar)

    def _calculate_correlation(self, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate correlation matrix between holdings.

        Correlation ranges from -1 to 1:
        1.0 = Perfect positive correlation
        0.0 = No correlation
        -1.0 = Perfect negative correlation
        """
        if returns_df.empty or len(returns_df.columns) < 2:
            return {}

        corr_matrix = returns_df.corr()

        # Convert to dict format
        return corr_matrix.to_dict()

    def _calculate_diversification_score(
        self, returns_df: pd.DataFrame, weights: Dict[str, float]
    ) -> float:
        """
        Calculate portfolio diversification score (0-100).

        Higher = Better diversification
        Lower = More concentrated / correlated holdings

        Uses average correlation and concentration metrics.
        """
        if returns_df.empty or len(returns_df.columns) < 2:
            return 0.0

        # Calculate average correlation (excluding diagonal)
        corr_matrix = returns_df.corr()
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        avg_correlation = corr_matrix.where(mask).stack().mean()

        # Calculate concentration (Herfindahl index)
        weight_values = list(weights.values())
        herfindahl = sum(w**2 for w in weight_values)

        # Diversification score (0-100)
        # Lower correlation = higher score
        # Lower concentration = higher score
        correlation_score = (1 - abs(avg_correlation)) * 50
        concentration_score = (1 - herfindahl) * 50

        total_score = correlation_score + concentration_score

        return float(max(0, min(100, total_score)))

    def _empty_risk_metrics(self) -> Dict[str, Any]:
        """Return empty risk metrics when no data available."""
        return {
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "beta": 1.0,
            "var_95": 0.0,
            "var_99": 0.0,
            "cvar_95": 0.0,
            "correlation_matrix": {},
            "diversification_score": 0.0,
            "error": "Insufficient data for risk analysis",
        }


# Singleton instance
_risk_analytics_instance = None


def get_risk_analytics() -> RiskAnalytics:
    """Get or create singleton RiskAnalytics instance."""
    global _risk_analytics_instance
    if _risk_analytics_instance is None:
        _risk_analytics_instance = RiskAnalytics()
    return _risk_analytics_instance
