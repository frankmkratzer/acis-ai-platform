#!/usr/bin/env python3
"""
Daily update for macd table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent data (last 100 days) for all active tickers
Standard MACD parameters: 12/26/9 (short/long/signal)
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
API_URL_TEMPLATE = "https://api.polygon.io/v1/indicators/macd/{ticker}"

# Standard MACD parameters
MACD_PARAMS = {"short_window": 12, "long_window": 26, "signal_window": 9}


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


def fetch_macd(ticker, short_window, long_window, signal_window, from_date):
    """Fetch recent MACD for a ticker"""
    url = API_URL_TEMPLATE.format(ticker=ticker)
    params = {
        "short_window": short_window,
        "long_window": long_window,
        "signal_window": signal_window,
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
            logger.debug(f"No MACD data for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching MACD for {ticker}: {e}")

    return all_values


def upsert_macd(tickers_data):
    """Fetch and upsert MACD (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO macd (
            ticker, date, short_window, long_window, signal_window,
            series_type, timespan, macd_value, signal_value, histogram_value, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, date, short_window, long_window, signal_window, series_type, timespan) DO UPDATE SET
            macd_value = EXCLUDED.macd_value,
            signal_value = EXCLUDED.signal_value,
            histogram_value = EXCLUDED.histogram_value,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 100 days to ensure we have enough data for 26-day long window
    from_date = date.today() - timedelta(days=100)
    short_w = MACD_PARAMS["short_window"]
    long_w = MACD_PARAMS["long_window"]
    signal_w = MACD_PARAMS["signal_window"]

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM macd;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert MACD data
            logger.info(
                f"Upserting MACD data ({short_w}/{long_w}/{signal_w}) for {len(tickers_data)} tickers (last 100 days)..."
            )
            processed = 0
            total_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Don't fetch data before list_date
                fetch_from = max(from_date, list_date) if list_date else from_date

                # Fetch MACD values
                values = fetch_macd(ticker, short_w, long_w, signal_w, fetch_from)

                if values:
                    for value_point in values:
                        # Parse timestamp
                        macd_date = None
                        if "timestamp" in value_point:
                            try:
                                macd_date = datetime.fromtimestamp(
                                    value_point["timestamp"] / 1000
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if list_date and macd_date and macd_date < list_date:
                            continue

                        macd_value = value_point.get("value")
                        signal_value = value_point.get("signal")
                        histogram_value = value_point.get("histogram")

                        if macd_value is not None:
                            values_tuple = (
                                ticker,
                                macd_date,
                                short_w,
                                long_w,
                                signal_w,
                                "close",
                                "day",
                                macd_value,
                                signal_value,
                                histogram_value,
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
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_upserted:,} MACD values upserted"
                    )

                # Rate limiting: ~100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM macd;")
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
                SELECT ticker, date, macd_value, signal_value, histogram_value, updated_at
                FROM macd
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY ticker
                LIMIT 15;
            """
            )
            logger.info("\nRecently updated MACD values:")
            for row in cur.fetchall():
                ticker, macd_date, macd_val, signal_val, hist_val, updated = row
                logger.info(
                    f"  {ticker:8} {macd_date} MACD:{macd_val:>8.2f} Signal:{signal_val:>8.2f} Hist:{hist_val:>8.2f}"
                )


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_active_tickers()

        if not tickers:
            logger.warning("No active tickers found")
            return

        upsert_macd(tickers)
        logger.info("\nDaily update complete: MACD updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
