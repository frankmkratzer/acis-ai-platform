#!/usr/bin/env python3
"""
Backfill daily_bars table from Polygon.io API
Fetches historical daily OHLCV data from list_date to present
Full reload: TRUNCATE then INSERT all data
"""
import os
import sys
import time
from datetime import date as date_class
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"


def get_tickers_with_list_dates():
    """Get tickers and their list dates from ticker_overview"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker, list_date
                FROM ticker_overview
                WHERE active = true
                  AND list_date IS NOT NULL
                ORDER BY ticker;
            """
            )
            tickers = cur.fetchall()
            logger.info(f"Found {len(tickers)} active tickers with list dates")
            return tickers


def fetch_daily_bars(ticker, from_date, to_date):
    """Fetch daily bars for a ticker between dates"""
    url = API_URL.format(
        ticker=ticker,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
    )
    params = {"apiKey": POLYGON_API_KEY, "adjusted": "true", "sort": "asc", "limit": 50000}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            return data["results"]
        else:
            return []

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No data for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return []


def populate_table(tickers_data):
    """Fetch and insert daily bars for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO daily_bars (
            ticker, date, open, high, low, close, volume, vwap, transactions
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    today = date_class.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING daily_bars table...")
            cur.execute("TRUNCATE TABLE daily_bars RESTART IDENTITY CASCADE;")

            # Fetch and insert daily bars
            logger.info(f"Fetching daily bars for {len(tickers_data)} tickers...")
            processed = 0
            total_bars_inserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                bars = fetch_daily_bars(ticker, from_date, today)

                if bars:
                    for bar in bars:
                        # Convert timestamp to date
                        bar_date = datetime.fromtimestamp(bar["t"] / 1000).date()

                        values = (
                            ticker,
                            bar_date,
                            bar.get("o"),  # open
                            bar.get("h"),  # high
                            bar.get("l"),  # low
                            bar.get("c"),  # close
                            bar.get("v"),  # volume
                            bar.get("vw"),  # vwap
                            bar.get("n"),  # transactions
                        )
                        batch.append(values)
                        total_bars_inserted += 1

                    # Insert batch
                    if len(batch) >= batch_size:
                        cur.executemany(insert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_bars_inserted:,} bars inserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_bars_inserted:,} daily bars inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_bars,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM daily_bars;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total bars: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, date, open, high, low, close, volume
                FROM daily_bars
                WHERE date = (SELECT MAX(date) FROM daily_bars)
                ORDER BY volume DESC
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by volume on latest date:")
            for row in cur.fetchall():
                ticker, bar_date, o, h, l, c, vol = row
                logger.info(
                    f"  {ticker:8} {bar_date} O:{o:>8.2f} H:{h:>8.2f} L:{l:>8.2f} C:{c:>8.2f} Vol:{vol:>15,.0f}"
                )


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers_data = get_tickers_with_list_dates()

        if not tickers_data:
            logger.warning("No tickers found with list dates")
            return

        populate_table(tickers_data)
        logger.info("\nBackfill complete: Daily bars table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
