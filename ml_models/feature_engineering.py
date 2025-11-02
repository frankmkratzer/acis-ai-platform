"""
Feature Engineering for XGBoost Stock Ranking Model

This module creates features from raw financial data including:
- Technical indicators
- Fundamental metrics
- Momentum indicators
- Interaction features
- Sector-relative metrics
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


class FeatureEngineer:
    """Creates ML-ready features from database tables"""

    def __init__(self, as_of_date: str):
        """
        Args:
            as_of_date: Date to create features for (YYYY-MM-DD format)
        """
        self.as_of_date = pd.to_datetime(as_of_date)
        self.lookback_days = 252  # 1 year of trading days

    def create_features(self, min_price: float = 5.0, min_volume: int = 100000) -> pd.DataFrame:
        """
        Create all features for stocks as of the given date

        Args:
            min_price: Minimum stock price filter
            min_volume: Minimum average daily volume filter

        Returns:
            DataFrame with ticker and all features
        """
        logger.info(f"Creating features for date: {self.as_of_date.date()}")

        # Get universe of eligible stocks
        tickers = self._get_eligible_tickers(min_price, min_volume)
        logger.info(f"Found {len(tickers)} eligible tickers")

        if len(tickers) == 0:
            logger.warning("No eligible tickers found!")
            return pd.DataFrame()

        # Build feature dataframe
        features = pd.DataFrame({"ticker": tickers})

        # Add each feature group
        features = self._add_price_features(features)
        features = self._add_technical_features(features)
        features = self._add_fundamental_features(features)
        features = self._add_momentum_features(features)
        features = self._add_quality_features(features)
        features = self._add_interaction_features(features)
        # Sector-relative features disabled - sector column not in database
        # features = self._add_sector_relative_features(features)

        # Drop rows with too many missing values
        missing_threshold = 0.5  # Drop if >50% features are missing
        missing_pct = features.isnull().sum(axis=1) / len(features.columns)
        features = features[missing_pct < missing_threshold]

        logger.info(f"Created {len(features)} feature rows with {len(features.columns)} columns")
        return features

    def _get_eligible_tickers(self, min_price: float, min_volume: int) -> List[str]:
        """Get list of eligible tickers based on filters"""
        query = """
        SELECT DISTINCT t.ticker
        FROM ticker_overview t
        INNER JOIN daily_bars d ON t.ticker = d.ticker
        WHERE t.market_cap >= 2000000000  -- $2B+ market cap
          AND t.type = 'CS'  -- Common stock
          AND d.date = (
              SELECT MAX(date)
              FROM daily_bars
              WHERE ticker = t.ticker
                AND date <= %s
          )
          AND d.close >= %s
          AND d.volume >= %s
        ORDER BY t.ticker
        """

        with get_psycopg2_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (self.as_of_date, min_price, min_volume))
                return [row[0] for row in cur.fetchall()]

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add current price and volume features"""
        query = """
        SELECT ticker, close, volume,
               (high - low) / close as daily_range,
               volume * close as dollar_volume
        FROM daily_bars
        WHERE date = (
            SELECT MAX(date)
            FROM daily_bars
            WHERE ticker = daily_bars.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        """

        with get_psycopg2_connection() as conn:
            price_df = pd.read_sql(query, conn, params=(self.as_of_date, df["ticker"].tolist()))

        return df.merge(price_df, on="ticker", how="left")

    def _add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features"""
        tickers = df["ticker"].tolist()

        # SMA features
        sma_query = """
        SELECT ticker,
               AVG(CASE WHEN window_size = 20 THEN value END) as sma_20,
               AVG(CASE WHEN window_size = 50 THEN value END) as sma_50,
               AVG(CASE WHEN window_size = 200 THEN value END) as sma_200
        FROM sma
        WHERE date = (
            SELECT MAX(date)
            FROM sma
            WHERE ticker = sma.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        GROUP BY ticker
        """

        # EMA features
        ema_query = """
        SELECT ticker,
               AVG(CASE WHEN window_size = 12 THEN value END) as ema_12,
               AVG(CASE WHEN window_size = 26 THEN value END) as ema_26,
               AVG(CASE WHEN window_size = 50 THEN value END) as ema_50
        FROM ema
        WHERE date = (
            SELECT MAX(date)
            FROM ema
            WHERE ticker = ema.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        GROUP BY ticker
        """

        # RSI features
        rsi_query = """
        SELECT ticker,
               AVG(CASE WHEN window_size = 14 THEN value END) as rsi_14
        FROM rsi
        WHERE date = (
            SELECT MAX(date)
            FROM rsi
            WHERE ticker = rsi.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        GROUP BY ticker
        """

        # MACD features
        macd_query = """
        SELECT ticker,
               macd_value as macd_line,
               signal_value as signal_line,
               histogram_value as macd_histogram
        FROM macd
        WHERE date = (
            SELECT MAX(date)
            FROM macd
            WHERE ticker = macd.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        """

        with get_psycopg2_connection() as conn:
            sma_df = pd.read_sql(sma_query, conn, params=(self.as_of_date, tickers))
            ema_df = pd.read_sql(ema_query, conn, params=(self.as_of_date, tickers))
            rsi_df = pd.read_sql(rsi_query, conn, params=(self.as_of_date, tickers))
            macd_df = pd.read_sql(macd_query, conn, params=(self.as_of_date, tickers))

        # Merge all technical indicators
        df = df.merge(sma_df, on="ticker", how="left")
        df = df.merge(ema_df, on="ticker", how="left")
        df = df.merge(rsi_df, on="ticker", how="left")
        df = df.merge(macd_df, on="ticker", how="left")

        # Create derived technical features
        df["price_to_sma_50"] = df["close"] / df["sma_50"]
        df["price_to_sma_200"] = df["close"] / df["sma_200"]
        df["sma_50_to_200"] = df["sma_50"] / df["sma_200"]
        df["ema_12_26_diff"] = df["ema_12"] - df["ema_26"]

        return df

    def _add_fundamental_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add fundamental metrics from ratios table"""
        query = """
        SELECT
            ticker,
            market_cap,
            price_to_earnings as pe_ratio,
            price_to_book as pb_ratio,
            price_to_sales as ps_ratio,
            price_to_cash_flow as pcf_ratio,
            price_to_free_cash_flow as pfcf_ratio,
            ev_to_sales,
            ev_to_ebitda,
            earnings_per_share as eps,
            return_on_assets as roa,
            return_on_equity as roe,
            dividend_yield,
            current as current_ratio,
            quick as quick_ratio,
            debt_to_equity,
            free_cash_flow as fcf,
            free_cash_flow / NULLIF(market_cap, 0) as fcf_yield
        FROM ratios
        WHERE date = (
            SELECT MAX(date)
            FROM ratios
            WHERE ticker = ratios.ticker
              AND date <= %s
        )
        AND ticker = ANY(%s)
        """

        with get_psycopg2_connection() as conn:
            fund_df = pd.read_sql(query, conn, params=(self.as_of_date, df["ticker"].tolist()))

        return df.merge(fund_df, on="ticker", how="left")

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum features (returns over various periods)"""
        query = """
        WITH price_history AS (
            SELECT
                ticker,
                date,
                close,
                LAG(close, 21) OVER (PARTITION BY ticker ORDER BY date) as close_1mo_ago,
                LAG(close, 63) OVER (PARTITION BY ticker ORDER BY date) as close_3mo_ago,
                LAG(close, 126) OVER (PARTITION BY ticker ORDER BY date) as close_6mo_ago,
                LAG(close, 252) OVER (PARTITION BY ticker ORDER BY date) as close_12mo_ago,
                MAX(close) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 252 PRECEDING AND CURRENT ROW) as high_52w
            FROM daily_bars
            WHERE ticker = ANY(%s)
              AND date <= %s
        )
        SELECT
            ticker,
            (close / NULLIF(close_1mo_ago, 0) - 1) as return_1mo,
            (close / NULLIF(close_3mo_ago, 0) - 1) as return_3mo,
            (close / NULLIF(close_6mo_ago, 0) - 1) as return_6mo,
            (close / NULLIF(close_12mo_ago, 0) - 1) as return_12mo,
            (close / NULLIF(high_52w, 0) - 1) as dist_from_52w_high
        FROM price_history
        WHERE date = (SELECT MAX(date) FROM price_history WHERE ticker = price_history.ticker)
        """

        with get_psycopg2_connection() as conn:
            mom_df = pd.read_sql(query, conn, params=(df["ticker"].tolist(), self.as_of_date))

        return df.merge(mom_df, on="ticker", how="left")

    def _add_quality_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add quality scores (Piotroski F-Score, Altman Z, etc)"""
        # Note: This assumes you have scoring tables populated
        # For now, we'll create placeholder - you can implement actual scores later
        df["piotroski_score"] = np.nan  # Placeholder
        df["altman_z_score"] = np.nan  # Placeholder

        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add interaction features (combinations of other features)"""
        # Momentum × Quality
        if "return_6mo" in df.columns and "roe" in df.columns:
            df["momentum_quality"] = df["return_6mo"] * df["roe"]

        # Value × Momentum
        if "fcf_yield" in df.columns and "return_3mo" in df.columns:
            df["value_momentum"] = df["fcf_yield"] * df["return_3mo"]

        # Volatility-adjusted momentum
        if "return_12mo" in df.columns and "daily_range" in df.columns:
            df["vol_adj_momentum"] = df["return_12mo"] / (
                df["daily_range"] + 0.01
            )  # +0.01 to avoid division by zero

        return df

    def _add_sector_relative_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add sector-relative metrics"""
        query = """
        SELECT ticker, sector
        FROM ticker_overview
        WHERE ticker = ANY(%s)
        """

        with get_psycopg2_connection() as conn:
            sector_df = pd.read_sql(query, conn, params=(df["ticker"].tolist(),))

        df = df.merge(sector_df, on="ticker", how="left")

        # Calculate sector medians for key metrics
        sector_metrics = ["pe_ratio", "ps_ratio", "roe", "return_3mo", "return_6mo"]

        for metric in sector_metrics:
            if metric in df.columns:
                sector_medians = df.groupby("sector")[metric].transform("median")
                df[f"{metric}_sector_relative"] = df[metric] / (
                    sector_medians + 0.001
                )  # Avoid division by zero

        return df

    def create_forward_returns(self, df: pd.DataFrame, horizon_days: int = 63) -> pd.DataFrame:
        """
        Create forward return targets for training

        Args:
            df: DataFrame with tickers
            horizon_days: Number of trading days forward (default 63 = 3 months)

        Returns:
            DataFrame with forward_return column added
        """
        future_date = self.as_of_date + timedelta(days=horizon_days * 1.4)  # Account for weekends

        query = """
        WITH current_prices AS (
            SELECT ticker, close as current_close
            FROM daily_bars
            WHERE date = (
                SELECT MAX(date)
                FROM daily_bars
                WHERE ticker = daily_bars.ticker
                  AND date <= %s
            )
            AND ticker = ANY(%s)
        ),
        future_prices AS (
            SELECT ticker, close as future_close
            FROM daily_bars
            WHERE date = (
                SELECT MIN(date)
                FROM daily_bars
                WHERE ticker = daily_bars.ticker
                  AND date >= %s
            )
            AND ticker = ANY(%s)
        )
        SELECT
            c.ticker,
            (f.future_close / NULLIF(c.current_close, 0) - 1) as forward_return
        FROM current_prices c
        LEFT JOIN future_prices f ON c.ticker = f.ticker
        """

        with get_psycopg2_connection() as conn:
            returns_df = pd.read_sql(
                query,
                conn,
                params=(self.as_of_date, df["ticker"].tolist(), future_date, df["ticker"].tolist()),
            )

        return df.merge(returns_df, on="ticker", how="left")


if __name__ == "__main__":
    # Test the feature engineering
    test_date = "2024-01-31"

    engineer = FeatureEngineer(as_of_date=test_date)
    features = engineer.create_features()

    logger.info(f"\nFeature summary for {test_date}:")
    logger.info(f"Total stocks: {len(features)}")
    logger.info(f"Total features: {len(features.columns)}")
    logger.info(f"\nFeature columns:\n{features.columns.tolist()}")
    logger.info(f"\nSample data:\n{features.head()}")
    logger.info(f"\nMissing values:\n{features.isnull().sum()}")
