#!/usr/bin/env python3
"""
Daily update for rsi table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent data (last 50 days) for all active tickers
Updates common RSI windows: 9, 14, 21 days
"""
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL_TEMPLATE = "https://api.polygon.io/v1/indicators/rsi/{ticker}"

# Common RSI windows to update
RSI_WINDOWS = [9, 14, 21]


def get_active_tickers():
    """Get all active tickers"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker, list_date
                FROM ticker_overview
                WHERE active = true
                ORDER BY ticker;
            """
            )
            tickers = cur.fetchall()
            logger.info(f"Found {len(tickers)} active tickers")
            return tickers


def fetch_rsi(ticker, window, from_date):
    """Fetch recent RSI for a ticker and window size"""
    url = API_URL_TEMPLATE.format(ticker=ticker)
    params = {
        "window": window,
        "series_type": "close",
        "timespan": "day",
        "adjusted": "true",
        "timestamp.gte": from_date.strftime("%Y-%m-%d"),
        "limit": 5000,
        "apiKey": POLYGON_API_KEY,
    }

    all_values = []

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            results = data["results"]
            if "values" in results and isinstance(results["values"], list):
                all_values.extend(results["values"])

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No RSI data for {ticker} (window={window})")
        else:
            logger.error(f"HTTP error for {ticker} (window={window}): {e}")
    except Exception as e:
        logger.error(f"Error fetching RSI for {ticker} (window={window}): {e}")

    return all_values


def upsert_rsi(tickers_data):
    """Fetch and upsert RSI (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO rsi (
            ticker, date, window_size, series_type, timespan, value, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, date, window_size, series_type, timespan) DO UPDATE SET
            value = EXCLUDED.value,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 50 days to ensure we have enough data for 21-day RSI
    from_date = date.today() - timedelta(days=50)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM rsi;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert RSI data
            logger.info(
                f"Upserting RSI data for {len(tickers_data)} tickers with windows {RSI_WINDOWS} (last 50 days)..."
            )
            processed = 0
            total_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Don't fetch data before list_date
                fetch_from = max(from_date, list_date) if list_date else from_date

                # Fetch each RSI window
                for window in RSI_WINDOWS:
                    values = fetch_rsi(ticker, window, fetch_from)

                    if values:
                        for value_point in values:
                            # Parse timestamp
                            rsi_date = None
                            if "timestamp" in value_point:
                                try:
                                    rsi_date = datetime.fromtimestamp(
                                        value_point["timestamp"] / 1000
                                    ).date()
                                except:
                                    pass

                            # Filter by list_date
                            if list_date and rsi_date and rsi_date < list_date:
                                continue

                            rsi_value = value_point.get("value")

                            if rsi_value is not None:
                                values_tuple = (
                                    ticker,
                                    rsi_date,
                                    window,
                                    "close",
                                    "day",
                                    rsi_value,
                                )
                                batch.append(values_tuple)
                                total_upserted += 1

                # Upsert batch
                if len(batch) >= batch_size:
                    cur.executemany(upsert_sql, batch)
                    batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_upserted:,} RSI values upserted"
                    )

                # Rate limiting: 100 requests per second / 3 windows = ~33 tickers/sec
                if i % 30 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM rsi;")
            count_after = cur.fetchone()[0]

            new_records = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Records before: {count_before:,}")
            logger.info(f"  Records after:  {count_after:,}")
            logger.info(f"  New records:    {new_records:,}")
            logger.info(f"  Updated:        {total_upserted - new_records:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, date, window_size, value, updated_at
                FROM rsi
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY ticker, window_size
                LIMIT 15;
            """
            )
            logger.info("\nRecently updated RSI values:")
            for row in cur.fetchall():
                ticker, rsi_date, window, val, updated = row
                logger.info(f"  {ticker:8} {rsi_date} RSI-{window:2}: {val:>6.2f}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_active_tickers()

        if not tickers:
            logger.warning("No active tickers found")
            return

        upsert_rsi(tickers)
        logger.info("\nDaily update complete: RSI updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
