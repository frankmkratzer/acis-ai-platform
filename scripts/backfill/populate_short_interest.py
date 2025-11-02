#!/usr/bin/env python3
"""
Backfill short_interest table from Polygon.io API
Fetches historical short interest data from list_date to present
Full reload: TRUNCATE then INSERT all data
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
API_URL = "https://api.polygon.io/stocks/v1/short-interest"


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


def fetch_short_interest(ticker, from_date=None):
    """Fetch short interest for a ticker"""
    params = {"ticker": ticker, "limit": 1000, "apiKey": POLYGON_API_KEY}

    # Add date filter if provided
    if from_date:
        params["settlement_date.gte"] = from_date.strftime("%Y-%m-%d")

    all_results = []

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_results.extend(data["results"])

            # Handle pagination
            while data.get("next_url"):
                next_url = data["next_url"] + f"&apiKey={POLYGON_API_KEY}"
                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "OK" and "results" in data:
                    all_results.extend(data["results"])
                else:
                    break

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No short interest for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching short interest for {ticker}: {e}")

    return all_results


def populate_table(tickers_data):
    """Fetch and insert short interest for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO short_interest (
            ticker, settlement_date, short_interest, avg_daily_volume, days_to_cover
        ) VALUES (
            %s, %s, %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING short_interest table...")
            cur.execute("TRUNCATE TABLE short_interest RESTART IDENTITY CASCADE;")

            # Fetch and insert short interest
            logger.info(f"Fetching short interest for {len(tickers_data)} tickers...")
            processed = 0
            unique_records = {}  # Dictionary to deduplicate by (ticker, settlement_date)

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                results = fetch_short_interest(ticker, from_date)

                if results:
                    for result in results:
                        # Parse settlement_date
                        settlement_date = None
                        if result.get("settlement_date"):
                            try:
                                settlement_date = datetime.strptime(
                                    result["settlement_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if settlement_date and settlement_date < from_date:
                            continue

                        if ticker and settlement_date:
                            key = (ticker, settlement_date)

                            # Store unique record (later entries overwrite earlier ones)
                            values = (
                                ticker,
                                settlement_date,
                                result.get("short_interest"),
                                result.get("avg_daily_volume"),
                                result.get("days_to_cover"),
                            )
                            unique_records[key] = values

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_records):,} unique records collected"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique records...")
            batch = []
            batch_size = 1000
            total_inserted = 0

            for values in unique_records.values():
                batch.append(values)
                total_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_inserted:,} records inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(settlement_date) as earliest_date,
                    MAX(settlement_date) as latest_date,
                    AVG(days_to_cover) as avg_days_to_cover
                FROM short_interest;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total records: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")
            avg_days_str = f"{stats[4]:.2f}" if stats[4] else "N/A"
            logger.info(f"  Avg days to cover: {avg_days_str}")

            # Sample recent data with high days_to_cover
            cur.execute(
                """
                SELECT ticker, settlement_date, short_interest, avg_daily_volume, days_to_cover
                FROM short_interest
                WHERE settlement_date = (SELECT MAX(settlement_date) FROM short_interest)
                  AND days_to_cover IS NOT NULL
                ORDER BY days_to_cover DESC
                LIMIT 10;
            """
            )
            logger.info(f"\nTop 10 by days to cover on latest settlement date:")
            for row in cur.fetchall():
                ticker, settle_date, short_int, avg_vol, days = row
                logger.info(
                    f"  {ticker:8} {settle_date} Short: {short_int:>12,} Avg Vol: {avg_vol:>12,} Days: {days:>6.2f}"
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
        logger.info("\nBackfill complete: Short interest table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
