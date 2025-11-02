#!/usr/bin/env python3
"""
Backfill rsi table from Polygon.io API
Fetches historical RSI data from list_date to present
Full reload: TRUNCATE then INSERT all data
Fetches common RSI windows: 9, 14, 21 days (14 is standard)
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

# Common RSI windows to fetch (14 is the standard)
RSI_WINDOWS = [9, 14, 21]


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


def fetch_rsi(ticker, window, from_date=None):
    """Fetch RSI for a ticker and window size"""
    url = API_URL_TEMPLATE.format(ticker=ticker)
    params = {
        "window": window,
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
            logger.debug(f"No RSI data for {ticker} (window={window})")
        else:
            logger.error(f"HTTP error for {ticker} (window={window}): {e}")
    except Exception as e:
        logger.error(f"Error fetching RSI for {ticker} (window={window}): {e}")

    return all_values


def populate_table(tickers_data):
    """Fetch and insert RSI for all tickers and windows (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO rsi (
            ticker, date, window_size, series_type, timespan, value
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING rsi table...")
            cur.execute("TRUNCATE TABLE rsi RESTART IDENTITY CASCADE;")

            # Fetch and insert RSI data
            logger.info(
                f"Fetching RSI data for {len(tickers_data)} tickers with windows {RSI_WINDOWS}..."
            )
            processed = 0
            unique_records = {}  # Dictionary to deduplicate by (ticker, date, window)

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                # Fetch each RSI window
                for window in RSI_WINDOWS:
                    values = fetch_rsi(ticker, window, from_date)

                    if values:
                        for value_point in values:
                            # Parse timestamp
                            rsi_date = None
                            if "timestamp" in value_point:
                                try:
                                    # Convert milliseconds to date
                                    rsi_date = datetime.fromtimestamp(
                                        value_point["timestamp"] / 1000
                                    ).date()
                                except:
                                    pass

                            # Filter by list_date
                            if rsi_date and rsi_date < from_date:
                                continue

                            rsi_value = value_point.get("value")

                            if ticker and rsi_date and rsi_value is not None:
                                key = (ticker, rsi_date, window)

                                # Store unique record (later entries overwrite earlier ones)
                                values_tuple = (
                                    ticker,
                                    rsi_date,
                                    window,
                                    "close",  # series_type
                                    "day",  # timespan
                                    rsi_value,
                                )
                                unique_records[key] = values_tuple

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_records):,} unique RSI values collected"
                    )

                # Rate limiting: 100 requests per second / 3 windows = ~33 tickers/sec
                if i % 30 == 0:
                    time.sleep(1)

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique RSI values...")
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
                f"Final: {processed} tickers processed, {total_inserted:,} RSI values inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_values,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    COUNT(DISTINCT window_size) as unique_windows,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM rsi;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total RSI values: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Windows: {stats[2]} ({RSI_WINDOWS})")
            logger.info(f"  Date range: {stats[3]} to {stats[4]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, date, window_size, value
                FROM rsi
                WHERE date = (SELECT MAX(date) FROM rsi)
                ORDER BY ticker, window_size
                LIMIT 15;
            """
            )
            logger.info(f"\nSample RSI values on latest date:")
            for row in cur.fetchall():
                ticker, rsi_date, window, val = row
                logger.info(f"  {ticker:8} {rsi_date} RSI-{window:2}: {val:>6.2f}")


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
        logger.info("\nBackfill complete: RSI table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
