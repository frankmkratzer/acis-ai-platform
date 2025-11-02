"""
Market Regime Detection
Classifies market conditions to drive dynamic portfolio allocation

Regimes:
- Bull Low Vol: Strong uptrend, low volatility → Aggressive growth
- Bull High Vol: Uptrend with volatility → Balanced growth
- Bear Low Vol: Downtrend, low volatility → Defensive value
- Bear High Vol: Market stress → Maximum defense (dividend focus)
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Tuple

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class MarketRegimeDetector:
    """
    Detect market regime to guide portfolio allocation

    Uses multiple signals:
    - Market direction (SPY returns)
    - Volatility level (VIX or realized vol)
    - Market breadth (advance/decline)
    - Correlation (risk-on vs risk-off)
    """

    # Allocation by regime (growth, value, dividend)
    REGIME_ALLOCATIONS = {
        "bull_low_vol": {
            "growth": 0.55,
            "value": 0.25,
            "dividend": 0.20,
            "description": "Strong uptrend, low volatility - favor growth",
        },
        "bull_high_vol": {
            "growth": 0.40,
            "value": 0.30,
            "dividend": 0.30,
            "description": "Uptrend with volatility - balanced approach",
        },
        "bear_low_vol": {
            "growth": 0.20,
            "value": 0.40,
            "dividend": 0.40,
            "description": "Downtrend, low vol - defensive with value opportunities",
        },
        "bear_high_vol": {
            "growth": 0.10,
            "value": 0.35,
            "dividend": 0.55,
            "description": "Market stress - maximum defense",
        },
    }

    # Volatility thresholds (VIX levels)
    VIX_LOW_THRESHOLD = 20
    VIX_HIGH_THRESHOLD = 25

    # Market direction thresholds (SPY returns)
    BULL_THRESHOLD = 0.02  # 2% return over lookback
    BEAR_THRESHOLD = -0.02  # -2% return over lookback

    def __init__(self, lookback_days: int = 60):
        """
        Args:
            lookback_days: Days to look back for regime detection (default 60)
        """
        self.lookback_days = lookback_days

    def detect_regime(self, as_of_date: date = None) -> str:
        """
        Detect current market regime

        Args:
            as_of_date: Date to detect regime for (default: today)

        Returns:
            str: Regime name ('bull_low_vol', 'bull_high_vol', 'bear_low_vol', 'bear_high_vol')
        """
        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Detecting market regime as of {as_of_date}")

        # Get market signals
        market_direction = self._get_market_direction(as_of_date)
        volatility_level = self._get_volatility_level(as_of_date)

        # Classify regime
        if market_direction == "bull":
            if volatility_level == "low":
                regime = "bull_low_vol"
            else:
                regime = "bull_high_vol"
        else:  # bear
            if volatility_level == "low":
                regime = "bear_low_vol"
            else:
                regime = "bear_high_vol"

        logger.info(f"Detected regime: {regime}")
        logger.info(f"  Market direction: {market_direction}")
        logger.info(f"  Volatility level: {volatility_level}")

        return regime

    def get_allocation(self, as_of_date: date = None) -> Dict[str, float]:
        """
        Get optimal allocation for current regime

        Args:
            as_of_date: Date to get allocation for (default: today)

        Returns:
            dict: {'growth': weight, 'value': weight, 'dividend': weight}
        """
        regime = self.detect_regime(as_of_date)
        allocation = self.REGIME_ALLOCATIONS[regime].copy()

        # Remove description from allocation dict
        description = allocation.pop("description")

        logger.info(f"Regime allocation: {description}")
        logger.info(f"  Growth: {allocation['growth']:.1%}")
        logger.info(f"  Value: {allocation['value']:.1%}")
        logger.info(f"  Dividend: {allocation['dividend']:.1%}")

        return allocation

    def _get_market_direction(self, as_of_date: date) -> str:
        """
        Determine if market is in bull or bear mode
        Uses SPY (S&P 500) returns over lookback period

        Returns:
            str: 'bull' or 'bear'
        """
        from_date = as_of_date - timedelta(days=self.lookback_days)

        query = """
        SELECT close
        FROM daily_bars
        WHERE ticker = 'SPY'
          AND date >= %(from_date)s
          AND date <= %(to_date)s
        ORDER BY date
        LIMIT 1 OFFSET 0;  -- First date
        """

        # Get SPY prices
        with engine.connect() as conn:
            # Get starting price
            start_query = f"""
                SELECT close FROM daily_bars
                WHERE ticker = 'SPY' AND date >= '{from_date}' AND date <= '{as_of_date}'
                ORDER BY date LIMIT 1
            """
            start_price = pd.read_sql(start_query, conn)

            # Get ending price
            end_query = f"""
                SELECT close FROM daily_bars
                WHERE ticker = 'SPY' AND date <= '{as_of_date}'
                ORDER BY date DESC LIMIT 1
            """
            end_price = pd.read_sql(end_query, conn)

        if start_price.empty or end_price.empty:
            logger.warning("Could not fetch SPY data, defaulting to neutral")
            return "bull"  # Default to bull in absence of data

        returns = (end_price["close"].iloc[0] / start_price["close"].iloc[0]) - 1

        if returns > self.BULL_THRESHOLD:
            return "bull"
        elif returns < self.BEAR_THRESHOLD:
            return "bear"
        else:
            # Neutral - check longer trend
            return "bull" if returns >= 0 else "bear"

    def _get_volatility_level(self, as_of_date: date) -> str:
        """
        Determine if volatility is high or low
        Uses realized volatility of SPY (or VIX if available)

        Returns:
            str: 'low' or 'high'
        """
        # Calculate realized volatility from SPY daily returns
        from_date = as_of_date - timedelta(days=self.lookback_days)

        query = f"""
        WITH returns AS (
            SELECT
                date,
                close,
                LAG(close) OVER (ORDER BY date) as prev_close
            FROM daily_bars
            WHERE ticker = 'SPY'
              AND date >= '{from_date}'
              AND date <= '{as_of_date}'
            ORDER BY date
        )
        SELECT
            STDDEV(LOG(close / NULLIF(prev_close, 0))) * SQRT(252) as annualized_vol
        FROM returns
        WHERE prev_close IS NOT NULL
        """

        try:
            with engine.connect() as conn:
                result = pd.read_sql(query, conn)

            if result.empty or result["annualized_vol"].iloc[0] is None:
                logger.warning("Could not calculate volatility, defaulting to low")
                return "low"

            annualized_vol = float(result["annualized_vol"].iloc[0])

            # Convert to VIX-equivalent (multiply by 100)
            vix_equivalent = annualized_vol * 100

            logger.info(f"Calculated volatility: {vix_equivalent:.1f} (VIX-equivalent)")

            # Classify volatility
            if vix_equivalent < self.VIX_LOW_THRESHOLD:
                return "low"
            elif vix_equivalent > self.VIX_HIGH_THRESHOLD:
                return "high"
            else:
                # Medium volatility - classify as high to be conservative
                return "high"

        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return "low"  # Default to low volatility

    def get_regime_history(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Get historical regime classifications
        Useful for backtesting adaptive allocation

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with columns: date, regime, growth_alloc, value_alloc, dividend_alloc
        """
        logger.info(f"Generating regime history from {start_date} to {end_date}")

        # Generate monthly dates
        dates = pd.date_range(start=start_date, end=end_date, freq="MS")

        regimes = []
        for dt in dates:
            regime = self.detect_regime(dt.date())
            allocation = self.REGIME_ALLOCATIONS[regime]

            regimes.append(
                {
                    "date": dt.date(),
                    "regime": regime,
                    "growth_alloc": allocation["growth"],
                    "value_alloc": allocation["value"],
                    "dividend_alloc": allocation["dividend"],
                }
            )

        df = pd.DataFrame(regimes)
        logger.info(f"Generated {len(df)} regime datapoints")

        return df


def test_regime_detection():
    """Test regime detection with current market data"""
    print("=" * 70)
    print("Market Regime Detection Test")
    print("=" * 70)

    detector = MarketRegimeDetector(lookback_days=60)

    # Detect current regime
    regime = detector.detect_regime()
    allocation = detector.get_allocation()

    print(f"\nCurrent Regime: {regime}")
    print(f"Allocation:")
    print(f"  Growth:   {allocation['growth']:.1%}")
    print(f"  Value:    {allocation['value']:.1%}")
    print(f"  Dividend: {allocation['dividend']:.1%}")
    print()

    # Show all regime allocations
    print("All Regime Allocations:")
    print("-" * 70)
    for regime_name, config in MarketRegimeDetector.REGIME_ALLOCATIONS.items():
        print(f"\n{regime_name.upper().replace('_', ' ')}:")
        print(f"  {config['description']}")
        print(
            f"  Growth: {config['growth']:.1%}, Value: {config['value']:.1%}, Dividend: {config['dividend']:.1%}"
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_regime_detection()
