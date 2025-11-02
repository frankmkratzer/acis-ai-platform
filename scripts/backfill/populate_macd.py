#!/usr/bin/env python3
"""
Backfill macd table from Polygon.io API
Fetches historical MACD data from list_date to present
Full reload: TRUNCATE then INSERT all data
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


def fetch_macd(ticker, short_window, long_window, signal_window, from_date=None):
    """Fetch MACD for a ticker"""
    url = API_URL_TEMPLATE.format(ticker=ticker)
    params = {
        "short_window": short_window,
        "long_window": long_window,
        "signal_window": signal_window,
        "series_type": "close",
        "timespan": "day",
        "adjusted": "true",
        "limit": 5000,
        "apiKey": POLYGON_API_KEY,
    }

    # Add date filter if provided
    if from_date:
        params["timestamp.gte"] = from_date.strftime("%Y-%m-%d")

    all_values = []

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            results = data["results"]
            if "values" in results and isinstance(results["values"], list):
                all_values.extend(results["values"])

            # Handle pagination
            while data.get("next_url"):
                next_url = data["next_url"] + f"&apiKey={POLYGON_API_KEY}"
                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "OK" and "results" in data:
                    results = data["results"]
                    if "values" in results and isinstance(results["values"], list):
                        all_values.extend(results["values"])
                else:
                    break

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No MACD data for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching MACD for {ticker}: {e}")

    return all_values


def populate_table(tickers_data):
    """Fetch and insert MACD (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO macd (
            ticker, date, short_window, long_window, signal_window,
            series_type, timespan, macd_value, signal_value, histogram_value
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    today = date.today()
    short_w = MACD_PARAMS["short_window"]
    long_w = MACD_PARAMS["long_window"]
    signal_w = MACD_PARAMS["signal_window"]

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING macd table...")
            cur.execute("TRUNCATE TABLE macd RESTART IDENTITY CASCADE;")

            # Fetch and insert MACD data
            logger.info(
                f"Fetching MACD data ({short_w}/{long_w}/{signal_w}) for {len(tickers_data)} tickers..."
            )
            processed = 0
            unique_records = {}  # Dictionary to deduplicate by (ticker, date, params)

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                # Fetch MACD values
                values = fetch_macd(ticker, short_w, long_w, signal_w, from_date)

                if values:
                    for value_point in values:
                        # Parse timestamp
                        macd_date = None
                        if "timestamp" in value_point:
                            try:
                                # Convert milliseconds to date
                                macd_date = datetime.fromtimestamp(
                                    value_point["timestamp"] / 1000
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if macd_date and macd_date < from_date:
                            continue

                        macd_value = value_point.get("value")
                        signal_value = value_point.get("signal")
                        histogram_value = value_point.get("histogram")

                        if ticker and macd_date and macd_value is not None:
                            key = (ticker, macd_date, short_w, long_w, signal_w)

                            # Store unique record
                            values_tuple = (
                                ticker,
                                macd_date,
                                short_w,
                                long_w,
                                signal_w,
                                "close",  # series_type
                                "day",  # timespan
                                macd_value,
                                signal_value,
                                histogram_value,
                            )
                            unique_records[key] = values_tuple

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_records):,} unique MACD values collected"
                    )

                # Rate limiting: ~100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique MACD values...")
            batch = []
            batch_size = 1000
            total_inserted = 0

            for values_tuple in unique_records.values():
                batch.append(values_tuple)
                total_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_inserted:,} MACD values inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_values,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM macd;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total MACD values: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Parameters: {short_w}/{long_w}/{signal_w}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, date, macd_value, signal_value, histogram_value
                FROM macd
                WHERE date = (SELECT MAX(date) FROM macd)
                ORDER BY ticker
                LIMIT 15;
            """
            )
            logger.info(f"\nSample MACD values on latest date:")
            for row in cur.fetchall():
                ticker, macd_date, macd_val, signal_val, hist_val = row
                logger.info(
                    f"  {ticker:8} {macd_date} MACD:{macd_val:>8.2f} Signal:{signal_val:>8.2f} Hist:{hist_val:>8.2f}"
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
        logger.info("\nBackfill complete: MACD table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
