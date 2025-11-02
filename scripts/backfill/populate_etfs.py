#!/usr/bin/env python3
"""
Populate ETF data (SPY, VTV, VUG, VYM) for backtesting
Fetches historical daily bars from Polygon.io and stores in etf_bars table
"""

import os
import sys
import time
from datetime import datetime, timedelta
from typing import List

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

# ETFs to fetch
ETFS = {
    "SPY": "S&P 500 ETF",
    "VTV": "Vanguard Value ETF",
    "VUG": "Vanguard Growth ETF",
    "VYM": "Vanguard High Dividend Yield ETF",
}


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

    # Default to 10 years ago
    return datetime.now() - timedelta(days=3650)


def fetch_bars(ticker: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetch daily bars from Polygon"""
    logger.info(f"Fetching {ticker} from {start_date.date()} to {end_date.date()}")

    bars = []

    try:
        for bar in client.list_aggs(
            ticker=ticker,
            multiplier=1,
            timespan="day",
            from_=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
            limit=50000,
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
        logger.warning(f"No data returned for {ticker}")
        return pd.DataFrame()

    df = pd.DataFrame(bars)
    logger.info(f"Fetched {len(df):,} bars for {ticker}")

    return df


def insert_bars(df: pd.DataFrame) -> int:
    """Insert bars into database (UPSERT)"""
    if df.empty:
        return 0

    # Prepare data for insertion
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

    logger.info(f"Inserted/updated {len(records):,} bars")
    return len(records)


def main():
    logger.info("=" * 70)
    logger.info("ETF Data Population")
    logger.info("=" * 70)
    logger.info(f"ETFs: {', '.join(ETFS.keys())}")
    logger.info("")

    total_inserted = 0
    end_date = datetime.now()

    for ticker, name in ETFS.items():
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing: {ticker} - {name}")
        logger.info(f"{'='*70}")

        # Get last date we have data for
        last_date = get_last_date(ticker)
        start_date = last_date - timedelta(days=1)  # Overlap by 1 day

        # If we don't have any data, fetch 10 years
        if (datetime.now() - last_date).days > 3600:
            start_date = datetime.now() - timedelta(days=3650)
            logger.info(f"No existing data - fetching 10 years")
        else:
            logger.info(f"Last date in DB: {last_date.date()}")
            logger.info(f"Updating from: {start_date.date()}")

        # Fetch bars
        df = fetch_bars(ticker, start_date, end_date)

        if not df.empty:
            # Insert into database
            inserted = insert_bars(df)
            total_inserted += inserted

            # Rate limiting (100 requests per second = 0.01s per request)
            time.sleep(0.01)

        logger.info(f"Completed {ticker}")

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"ETF Population Complete!")
    logger.info(f"Total bars inserted/updated: {total_inserted:,}")
    logger.info("=" * 70)

    # Show summary
    with engine.connect() as conn:
        for ticker in ETFS.keys():
            result = conn.execute(
                text("SELECT MIN(date), MAX(date), COUNT(*) FROM etf_bars WHERE ticker = :ticker"),
                {"ticker": ticker},
            ).fetchone()
            if result and result[2] > 0:
                logger.info(f"{ticker}: {result[2]:,} bars from {result[0]} to {result[1]}")


if __name__ == "__main__":
    main()
