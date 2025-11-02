"""
Phase 2: Dynamic Rebalance Triggers
Determines when to rebalance portfolio based on market conditions
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class DynamicRebalanceTriggers:
    """Detects conditions that trigger portfolio rebalancing"""

    def __init__(self):
        # Configuration
        self.volatility_spike_threshold = 1.5  # 50% increase in VIX
        self.correlation_change_threshold = 0.3  # 30% change in correlation
        self.drawdown_threshold = 0.10  # 10% drawdown triggers rebalance
        self.min_days_between_rebalances = 30  # Minimum 30 days between rebalances

    def check_volatility_spike(self, as_of_date: date = None) -> Tuple[bool, Dict]:
        """
        Detect volatility regime change

        Returns:
            (trigger: bool, metadata: dict)
        """
        if as_of_date is None:
            as_of_date = date.today()

        query = """
        SELECT date, close
        FROM daily_bars
        WHERE ticker = 'SPY'
          AND date <= %(as_of_date)s
        ORDER BY date DESC
        LIMIT 60;
        """

        df = pd.read_sql(query, engine, params={"as_of_date": as_of_date})

        if len(df) < 60:
            return False, {"reason": "Insufficient data"}

        # Calculate rolling volatility
        df["returns"] = df["close"].pct_change()
        current_vol = df["returns"].head(20).std() * np.sqrt(252)  # Last 20 days
        baseline_vol = df["returns"].tail(40).std() * np.sqrt(252)  # Previous 40 days

        vol_ratio = current_vol / baseline_vol if baseline_vol > 0 else 1.0

        trigger = vol_ratio > self.volatility_spike_threshold

        metadata = {
            "current_vol": current_vol,
            "baseline_vol": baseline_vol,
            "vol_ratio": vol_ratio,
            "threshold": self.volatility_spike_threshold,
            "reason": f"Volatility spike: {vol_ratio:.2f}x baseline" if trigger else "No spike",
        }

        return trigger, metadata

    def check_correlation_change(self, as_of_date: date = None) -> Tuple[bool, Dict]:
        """
        Detect correlation regime change between value/growth/dividend strategies

        Returns:
            (trigger: bool, metadata: dict)
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Use sector ETFs as proxies
        # Value: VTV, Growth: VUG, Dividend: VYM
        query = """
        WITH sector_returns AS (
            SELECT
                date,
                ticker,
                (close / LAG(close, 1) OVER (PARTITION BY ticker ORDER BY date) - 1) as returns
            FROM daily_bars
            WHERE ticker IN ('VTV', 'VUG', 'VYM')
              AND date <= %(as_of_date)s
            ORDER BY date DESC
            LIMIT 180
        )
        SELECT * FROM sector_returns WHERE returns IS NOT NULL;
        """

        df = pd.read_sql(query, engine, params={"as_of_date": as_of_date})

        if len(df) < 60:
            return False, {"reason": "Insufficient data"}

        # Pivot to get returns by ticker
        df_pivot = df.pivot(index="date", columns="ticker", values="returns")

        # Current correlation (last 20 days)
        current_corr = df_pivot.head(20).corr()

        # Historical correlation (previous 60 days)
        hist_corr = df_pivot.tail(60).corr()

        # Calculate change in average correlation
        current_avg_corr = current_corr.values[
            np.triu_indices_from(current_corr.values, k=1)
        ].mean()
        hist_avg_corr = hist_corr.values[np.triu_indices_from(hist_corr.values, k=1)].mean()

        corr_change = abs(current_avg_corr - hist_avg_corr)

        trigger = corr_change > self.correlation_change_threshold

        metadata = {
            "current_correlation": current_avg_corr,
            "historical_correlation": hist_avg_corr,
            "change": corr_change,
            "threshold": self.correlation_change_threshold,
            "reason": (
                f"Correlation change: {corr_change:.2f}" if trigger else "No significant change"
            ),
        }

        return trigger, metadata

    def check_drawdown(self, portfolio_returns: pd.Series) -> Tuple[bool, Dict]:
        """
        Detect significant portfolio drawdown

        Args:
            portfolio_returns: Series of daily portfolio returns

        Returns:
            (trigger: bool, metadata: dict)
        """
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max

        current_drawdown = drawdown.iloc[-1]

        trigger = current_drawdown < -self.drawdown_threshold

        metadata = {
            "current_drawdown": current_drawdown,
            "max_drawdown": drawdown.min(),
            "threshold": -self.drawdown_threshold,
            "reason": f"Drawdown: {current_drawdown:.1%}" if trigger else "No significant drawdown",
        }

        return trigger, metadata

    def check_quarterly_rebalance(
        self, last_rebalance_date: date, as_of_date: date = None
    ) -> Tuple[bool, Dict]:
        """
        Check if it's time for quarterly rebalance

        Returns:
            (trigger: bool, metadata: dict)
        """
        if as_of_date is None:
            as_of_date = date.today()

        days_since_rebalance = (as_of_date - last_rebalance_date).days

        # Check if we're at quarter-end (approximately)
        is_quarter_end = as_of_date.month % 3 == 0 and as_of_date.day >= 25

        trigger = is_quarter_end and days_since_rebalance >= self.min_days_between_rebalances

        metadata = {
            "days_since_rebalance": days_since_rebalance,
            "is_quarter_end": is_quarter_end,
            "min_days": self.min_days_between_rebalances,
            "reason": "Quarterly rebalance due" if trigger else "Not quarter-end or too soon",
        }

        return trigger, metadata

    def should_rebalance(
        self,
        last_rebalance_date: date,
        portfolio_returns: pd.Series = None,
        as_of_date: date = None,
    ) -> Tuple[bool, List[str]]:
        """
        Master function: Check all triggers and determine if rebalancing is needed

        Returns:
            (should_rebalance: bool, reasons: list)
        """
        triggers = []
        reasons = []

        # Check volatility spike
        vol_trigger, vol_meta = self.check_volatility_spike(as_of_date)
        if vol_trigger:
            triggers.append("volatility_spike")
            reasons.append(vol_meta["reason"])

        # Check correlation change
        corr_trigger, corr_meta = self.check_correlation_change(as_of_date)
        if corr_trigger:
            triggers.append("correlation_change")
            reasons.append(corr_meta["reason"])

        # Check drawdown (if portfolio returns provided)
        if portfolio_returns is not None and len(portfolio_returns) > 0:
            dd_trigger, dd_meta = self.check_drawdown(portfolio_returns)
            if dd_trigger:
                triggers.append("drawdown")
                reasons.append(dd_meta["reason"])

        # Check quarterly rebalance
        q_trigger, q_meta = self.check_quarterly_rebalance(last_rebalance_date, as_of_date)
        if q_trigger:
            triggers.append("quarterly")
            reasons.append(q_meta["reason"])

        should_rebalance = len(triggers) > 0

        logger.info(f"Rebalance check: {'TRIGGERED' if should_rebalance else 'NO TRIGGER'}")
        if should_rebalance:
            logger.info(f"Triggers: {', '.join(triggers)}")
            for reason in reasons:
                logger.info(f"  - {reason}")

        return should_rebalance, reasons
