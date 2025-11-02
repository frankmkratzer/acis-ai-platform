#!/usr/bin/env python3
"""
Daily update for ema table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent data (last 250 days) for all active tickers
Updates common EMA windows: 12, 26, 50, 200 days
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
API_URL_TEMPLATE = "https://api.polygon.io/v1/indicators/ema/{ticker}"

# Common EMA windows to update
EMA_WINDOWS = [12, 26, 50, 200]


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


def fetch_ema(ticker, window, from_date):
    """Fetch recent EMA for a ticker and window size"""
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
            logger.debug(f"No EMA data for {ticker} (window={window})")
        else:
            logger.error(f"HTTP error for {ticker} (window={window}): {e}")
    except Exception as e:
        logger.error(f"Error fetching EMA for {ticker} (window={window}): {e}")

    return all_values


def upsert_ema(tickers_data):
    """Fetch and upsert EMA (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO ema (
            ticker, date, window_size, series_type, timespan, value, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, date, window_size, series_type, timespan) DO UPDATE SET
            value = EXCLUDED.value,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 250 days to ensure we have enough data for 200-day EMA
    from_date = date.today() - timedelta(days=250)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM ema;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert EMA data
            logger.info(
                f"Upserting EMA data for {len(tickers_data)} tickers with windows {EMA_WINDOWS} (last 250 days)..."
            )
            processed = 0
            total_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Don't fetch data before list_date
                fetch_from = max(from_date, list_date) if list_date else from_date

                # Fetch each EMA window
                for window in EMA_WINDOWS:
                    values = fetch_ema(ticker, window, fetch_from)

                    if values:
                        for value_point in values:
                            # Parse timestamp
                            ema_date = None
                            if "timestamp" in value_point:
                                try:
                                    ema_date = datetime.fromtimestamp(
                                        value_point["timestamp"] / 1000
                                    ).date()
                                except:
                                    pass

                            # Filter by list_date
                            if list_date and ema_date and ema_date < list_date:
                                continue

                            ema_value = value_point.get("value")

                            if ema_value is not None:
                                values_tuple = (
                                    ticker,
                                    ema_date,
                                    window,
                                    "close",
                                    "day",
                                    ema_value,
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
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_upserted:,} EMA values upserted"
                    )

                # Rate limiting: 100 requests per second / 4 windows = ~25 tickers/sec
                if i % 25 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM ema;")
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
                FROM ema
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY ticker, window_size
                LIMIT 15;
            """
            )
            logger.info("\nRecently updated EMA values:")
            for row in cur.fetchall():
                ticker, ema_date, window, val, updated = row
                logger.info(f"  {ticker:8} {ema_date} EMA-{window:3}: {val:>10.2f}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_active_tickers()

        if not tickers:
            logger.warning("No active tickers found")
            return

        upsert_ema(tickers)
        logger.info("\nDaily update complete: EMA updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
