#!/usr/bin/env python3
"""
Market Regime Detection System

Classifies market conditions to help meta-strategy selector
choose the best strategy for current market environment.

Regimes:
- Volatility: low, medium, high, extreme
- Trend: bull, bear, sideways
- Combined: bull_low_vol, bear_high_vol, etc.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2

from utils import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


class MarketRegimeDetector:
    """
    Detects current market regime using multiple indicators
    """

    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)

    def get_spy_data(self, lookback_days=200):
        """Get SPY price data for regime analysis"""
        query = """
        SELECT date, close, volume
        FROM etf_bars
        WHERE ticker = 'SPY'
          AND date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date
        """
        df = pd.read_sql(query, self.conn, params=(lookback_days,))
        return df

    def calculate_volatility_regime(self, spy_df):
        """
        Classify volatility regime

        Returns: 'low', 'medium', 'high', 'extreme'
        """
        # Calculate realized volatility (20-day)
        spy_df["returns"] = spy_df["close"].pct_change()
        spy_df["volatility_20d"] = spy_df["returns"].rolling(20).std() * np.sqrt(252)

        current_vol = spy_df["volatility_20d"].iloc[-1]

        # Historical percentiles
        vol_25 = spy_df["volatility_20d"].quantile(0.25)
        vol_50 = spy_df["volatility_20d"].quantile(0.50)
        vol_75 = spy_df["volatility_20d"].quantile(0.75)

        if current_vol < vol_25:
            regime = "low"
        elif current_vol < vol_50:
            regime = "medium"
        elif current_vol < vol_75:
            regime = "high"
        else:
            regime = "extreme"

        logger.info(f"Volatility: {current_vol:.2%} -> {regime}")

        return regime, current_vol

    def calculate_trend_regime(self, spy_df):
        """
        Classify trend regime using moving averages

        Returns: 'bull', 'bear', 'sideways'
        """
        # Calculate moving averages
        spy_df["sma_50"] = spy_df["close"].rolling(50).mean()
        spy_df["sma_200"] = spy_df["close"].rolling(200).mean()

        current_price = spy_df["close"].iloc[-1]
        sma_50 = spy_df["sma_50"].iloc[-1]
        sma_200 = spy_df["sma_200"].iloc[-1]

        # Trend classification
        if current_price > sma_50 > sma_200:
            regime = "bull"
        elif current_price < sma_50 < sma_200:
            regime = "bear"
        else:
            regime = "sideways"

        logger.info(
            f"Trend: Price={current_price:.2f}, SMA50={sma_50:.2f}, SMA200={sma_200:.2f} -> {regime}"
        )

        return regime, sma_50, sma_200

    def calculate_market_breadth(self):
        """
        Calculate market breadth indicators

        Returns: advance/decline ratio, new highs/lows ratio
        """
        # Get all stocks' recent performance
        query = """
        WITH recent_data AS (
            SELECT
                ticker,
                date,
                close,
                LAG(close, 1) OVER (PARTITION BY ticker ORDER BY date) as prev_close,
                MAX(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) as high_52w,
                MIN(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) as low_52w
            FROM daily_bars
            WHERE date >= CURRENT_DATE - INTERVAL '2 days'
        )
        SELECT
            date,
            COUNT(*) as total_stocks,
            SUM(CASE WHEN close > prev_close THEN 1 ELSE 0 END) as advancing,
            SUM(CASE WHEN close < prev_close THEN 1 ELSE 0 END) as declining,
            SUM(CASE WHEN close >= high_52w * 0.98 THEN 1 ELSE 0 END) as near_highs,
            SUM(CASE WHEN close <= low_52w * 1.02 THEN 1 ELSE 0 END) as near_lows
        FROM recent_data
        WHERE prev_close IS NOT NULL
          AND date = (SELECT MAX(date) FROM recent_data)
        GROUP BY date
        """

        cur = self.conn.cursor()
        cur.execute(query)
        row = cur.fetchone()

        if row:
            date, total, advancing, declining, near_highs, near_lows = row

            ad_ratio = advancing / declining if declining > 0 else 5.0
            hl_ratio = near_highs / near_lows if near_lows > 0 else 5.0

            logger.info(f"Market Breadth: A/D={ad_ratio:.2f}, H/L={hl_ratio:.2f}")

            return ad_ratio, hl_ratio

        return 1.0, 1.0

    def calculate_sector_momentum(self):
        """
        Identify which sectors are leading/lagging

        Returns: dict of sector: momentum_score
        """
        # Sector ETFs mapping
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLI": "Industrials",
            "XLY": "ConsumerDiscretionary",
            "XLP": "ConsumerStaples",
            "XLU": "Utilities",
            "XLB": "Materials",
            "XLRE": "RealEstate",
        }

        query = """
        WITH sector_returns AS (
            SELECT
                ticker,
                (close / LAG(close, 20) OVER (PARTITION BY ticker ORDER BY date) - 1) as return_20d
            FROM etf_bars
            WHERE ticker IN ('XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB', 'XLRE')
              AND date >= CURRENT_DATE - INTERVAL '30 days'
        )
        SELECT ticker, return_20d
        FROM sector_returns
        WHERE return_20d IS NOT NULL
        ORDER BY return_20d DESC
        """

        df = pd.read_sql(query, self.conn)

        sector_momentum = {}
        for _, row in df.iterrows():
            if row["ticker"] in sector_etfs:
                sector_momentum[sector_etfs[row["ticker"]]] = row["return_20d"]

        if sector_momentum:
            top_sector = max(sector_momentum, key=sector_momentum.get)
            logger.info(f"Leading sector: {top_sector} ({sector_momentum[top_sector]:.2%})")

        return sector_momentum

    def classify_regime(self, volatility_regime, trend_regime, ad_ratio, hl_ratio):
        """
        Combine indicators into overall regime classification

        Returns: regime_label, confidence
        """
        # Combine trend + volatility
        regime_label = f"{trend_regime}_{volatility_regime}_vol"

        # Adjust confidence based on market breadth
        confidence = 0.7  # Base confidence

        # Strong breadth increases confidence
        if ad_ratio > 1.5 and hl_ratio > 1.5:
            confidence += 0.2
        elif ad_ratio < 0.67 and hl_ratio < 0.67:
            confidence += 0.2
        else:
            confidence += 0.0  # Neutral breadth

        # Extreme volatility reduces confidence
        if volatility_regime == "extreme":
            confidence -= 0.1

        confidence = min(max(confidence, 0.0), 1.0)

        logger.info(f"Overall regime: {regime_label} (confidence: {confidence:.2f})")

        return regime_label, confidence

    def detect_current_regime(self):
        """
        Main method: Detect current market regime

        Returns: dict with all regime indicators
        """
        logger.info("=" * 60)
        logger.info("MARKET REGIME DETECTION")
        logger.info("=" * 60)

        # Get SPY data
        spy_df = self.get_spy_data(lookback_days=300)

        # Calculate regime components
        volatility_regime, realized_vol = self.calculate_volatility_regime(spy_df)
        trend_regime, sma_50, sma_200 = self.calculate_trend_regime(spy_df)
        ad_ratio, hl_ratio = self.calculate_market_breadth()
        sector_momentum = self.calculate_sector_momentum()

        # Overall classification
        regime_label, confidence = self.classify_regime(
            volatility_regime, trend_regime, ad_ratio, hl_ratio
        )

        result = {
            "date": datetime.now().date(),
            "volatility_regime": volatility_regime,
            "realized_volatility_20d": realized_vol,
            "trend_regime": trend_regime,
            "spy_sma_50": sma_50,
            "spy_sma_200": sma_200,
            "advance_decline_ratio": ad_ratio,
            "new_highs_lows_ratio": hl_ratio,
            "sector_momentum": sector_momentum,
            "regime_label": regime_label,
            "regime_confidence": confidence,
        }

        return result

    def save_regime(self, regime_data):
        """Save regime data to database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            INSERT INTO market_regime (
                date, vix, realized_volatility_20d, volatility_regime,
                spy_sma_50, spy_sma_200, trend_regime,
                advance_decline_ratio, new_highs_lows_ratio,
                sector_momentum, regime_label, regime_confidence
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (date) DO UPDATE SET
                vix = EXCLUDED.vix,
                realized_volatility_20d = EXCLUDED.realized_volatility_20d,
                volatility_regime = EXCLUDED.volatility_regime,
                spy_sma_50 = EXCLUDED.spy_sma_50,
                spy_sma_200 = EXCLUDED.spy_sma_200,
                trend_regime = EXCLUDED.trend_regime,
                advance_decline_ratio = EXCLUDED.advance_decline_ratio,
                new_highs_lows_ratio = EXCLUDED.new_highs_lows_ratio,
                sector_momentum = EXCLUDED.sector_momentum,
                regime_label = EXCLUDED.regime_label,
                regime_confidence = EXCLUDED.regime_confidence
        """,
            (
                regime_data["date"],
                None,  # VIX (would need to fetch from external API)
                regime_data["realized_volatility_20d"],
                regime_data["volatility_regime"],
                regime_data["spy_sma_50"],
                regime_data["spy_sma_200"],
                regime_data["trend_regime"],
                regime_data["advance_decline_ratio"],
                regime_data["new_highs_lows_ratio"],
                psycopg2.extras.Json(regime_data["sector_momentum"]),
                regime_data["regime_label"],
                regime_data["regime_confidence"],
            ),
        )

        self.conn.commit()
        logger.info(f"✅ Regime saved to database: {regime_data['regime_label']}")

    def close(self):
        self.conn.close()


def main():
    """Run market regime detection"""
    detector = MarketRegimeDetector()

    try:
        # Detect current regime
        regime = detector.detect_current_regime()

        # Save to database
        detector.save_regime(regime)

        # Print summary
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Date: {regime['date']}")
        logger.info(f"Regime: {regime['regime_label']}")
        logger.info(f"Confidence: {regime['regime_confidence']:.2%}")
        logger.info(
            f"Volatility: {regime['volatility_regime']} ({regime['realized_volatility_20d']:.2%})"
        )
        logger.info(f"Trend: {regime['trend_regime']}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Error detecting market regime: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        detector.close()


if __name__ == "__main__":
    sys.exit(main())
