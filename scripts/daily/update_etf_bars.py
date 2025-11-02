#!/usr/bin/env python3
"""
Daily ETF Bars Update
Updates ETF data (SPY, VTV, VUG, VYM) with latest daily bars
"""

import os
import sys
import time
from datetime import datetime, timedelta

import pandas as pd
from polygon import RESTClient
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)

# Polygon API setup
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable not set")

client = RESTClient(POLYGON_API_KEY)

# ETFs to update
ETFS = ["SPY", "VTV", "VUG", "VYM"]


def get_last_date(ticker: str) -> datetime:
    """Get the last date we have data for this ticker"""
    query = text(
        """
        SELECT MAX(date) as last_date
        FROM etf_bars
        WHERE ticker = :ticker
    """
    )

    with engine.connect() as conn:
        result = conn.execute(query, {"ticker": ticker}).fetchone()
        if result and result[0]:
            return result[0]

    # Default to 30 days ago if no data
    return datetime.now() - timedelta(days=30)


def fetch_recent_bars(ticker: str, start_date: datetime) -> pd.DataFrame:
    """Fetch recent bars from Polygon"""
    end_date = datetime.now()

    logger.info(f"Fetching {ticker} from {start_date.date()} to {end_date.date()}")

    bars = []

    try:
        for bar in client.list_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="day",
            from_=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
            limit=1000,
        ):
            bars.append(
                {
                    "ticker": ticker,
                    "date": datetime.fromtimestamp(bar.timestamp / 1000).date(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "vwap": bar.vwap if hasattr(bar, "vwap") else None,
                    "transactions": bar.transactions if hasattr(bar, "transactions") else None,
                }
            )

    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return pd.DataFrame()

    if not bars:
        logger.warning(f"No new data for {ticker}")
        return pd.DataFrame()

    df = pd.DataFrame(bars)
    logger.info(f"Fetched {len(df)} new bars for {ticker}")

    return df


def insert_bars(df: pd.DataFrame) -> int:
    """Insert/update bars in database"""
    if df.empty:
        return 0

    records = df.to_dict("records")

    insert_query = text(
        """
        INSERT INTO etf_bars (ticker, date, open, high, low, close, volume, vwap, transactions)
        VALUES (:ticker, :date, :open, :high, :low, :close, :volume, :vwap, :transactions)
        ON CONFLICT (ticker, date)
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            vwap = EXCLUDED.vwap,
            transactions = EXCLUDED.transactions
    """
    )

    with engine.begin() as conn:
        conn.execute(insert_query, records)

    logger.info(f"Inserted/updated {len(records)} bars")
    return len(records)


def main():
    logger.info("=" * 70)
    logger.info("Daily ETF Bars Update")
    logger.info("=" * 70)
    logger.info(f"ETFs: {', '.join(ETFS)}")
    logger.info("")

    total_updated = 0

    for ticker in ETFS:
        logger.info(f"\nProcessing {ticker}...")

        # Get last date
        last_date = get_last_date(ticker)
        start_date = last_date - timedelta(days=1)  # Overlap by 1 day

        logger.info(f"Last date in DB: {last_date.date()}")
        logger.info(f"Fetching from: {start_date.date()}")

        # Fetch recent bars
        df = fetch_recent_bars(ticker, start_date)

        if not df.empty:
            # Insert into database
            updated = insert_bars(df)
            total_updated += updated

            # Rate limiting
            time.sleep(0.01)

        logger.info(f"Completed {ticker}")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"ETF Update Complete!")
    logger.info(f"Total bars updated: {total_updated}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
