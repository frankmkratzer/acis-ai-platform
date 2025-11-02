#!/usr/bin/env python3
"""
Backfill splits table from Polygon.io API
Fetches historical stock split data from list_date to present
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
API_URL = "https://api.polygon.io/v3/reference/splits"


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


def fetch_splits(ticker, from_date, to_date):
    """Fetch splits for a ticker between dates"""
    params = {
        "ticker": ticker,
        "execution_date.gte": from_date.strftime("%Y-%m-%d"),
        "execution_date.lte": to_date.strftime("%Y-%m-%d"),
        "apiKey": POLYGON_API_KEY,
        "limit": 1000,
        "sort": "execution_date",
        "order": "asc",
    }

    all_results = []

    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_results.extend(data["results"])

            # Handle pagination if there are more results
            while data.get("next_url"):
                next_url = data["next_url"] + f"&apiKey={POLYGON_API_KEY}"
                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "OK" and "results" in data:
                    all_results.extend(data["results"])
                else:
                    break

        return all_results

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No splits for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching splits for {ticker}: {e}")
        return []


def populate_table(tickers_data):
    """Fetch and insert splits for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO splits (
            id, ticker, execution_date, split_from, split_to
        ) VALUES (
            %s, %s, %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING splits table...")
            cur.execute("TRUNCATE TABLE splits RESTART IDENTITY CASCADE;")

            # Fetch and insert splits
            logger.info(f"Fetching splits for {len(tickers_data)} tickers...")
            processed = 0
            total_splits_inserted = 0
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

                splits = fetch_splits(ticker, from_date, today)

                if splits:
                    for split in splits:
                        # Parse execution date
                        execution_date = None
                        if split.get("execution_date"):
                            try:
                                execution_date = datetime.strptime(
                                    split["execution_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        values = (
                            split.get("id"),
                            split.get("ticker"),
                            execution_date,
                            split.get("split_from"),
                            split.get("split_to"),
                        )
                        batch.append(values)
                        total_splits_inserted += 1

                    # Insert batch
                    if len(batch) >= batch_size:
                        cur.executemany(insert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_splits_inserted:,} splits inserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_splits_inserted:,} splits inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_splits,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(execution_date) as earliest_date,
                    MAX(execution_date) as latest_date
                FROM splits;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total splits: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, execution_date, split_from, split_to
                FROM splits
                WHERE execution_date = (SELECT MAX(execution_date) FROM splits)
                ORDER BY split_from DESC
                LIMIT 5;
            """
            )
            logger.info(f"\nRecent splits on latest execution date:")
            for row in cur.fetchall():
                ticker, exec_date, split_from, split_to = row
                split_ratio = (
                    f"{int(split_to)}:{int(split_from)}" if split_from and split_to else "N/A"
                )
                logger.info(
                    f"  {ticker:8} Date: {exec_date} Split: {split_ratio} ({split_from} → {split_to})"
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
        logger.info("\nBackfill complete: Splits table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
