#!/usr/bin/env python3
"""
Daily update for splits table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches last 90 days of split data for all active tickers
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


def upsert_splits(tickers_data):
    """Fetch and upsert splits (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO splits (
            id, ticker, execution_date, split_from, split_to, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (id) DO UPDATE SET
            ticker = EXCLUDED.ticker,
            execution_date = EXCLUDED.execution_date,
            split_from = EXCLUDED.split_from,
            split_to = EXCLUDED.split_to,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 90 days of data
    today = date.today()
    from_date = today - timedelta(days=90)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM splits;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert splits
            logger.info(f"Upserting splits for {len(tickers_data)} tickers (last 90 days)...")
            processed = 0
            total_splits_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Don't fetch data before list_date
                effective_from_date = from_date
                if list_date and list_date > from_date:
                    effective_from_date = list_date

                # Don't fetch data for future dates
                if effective_from_date > today:
                    processed += 1
                    continue

                splits = fetch_splits(ticker, effective_from_date, today)

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
                        total_splits_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_splits_upserted:,} splits upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM splits;")
            count_after = cur.fetchone()[0]

            new_splits = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Splits before: {count_before:,}")
            logger.info(f"  Splits after:  {count_after:,}")
            logger.info(f"  New splits:    {new_splits:,}")
            logger.info(f"  Updated:       {total_splits_upserted - new_splits:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, execution_date, split_from, split_to, updated_at
                FROM splits
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '2 minutes'
                ORDER BY execution_date DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated splits:")
            for row in cur.fetchall():
                ticker, exec_date, split_from, split_to, updated = row
                split_ratio = (
                    f"{int(split_to)}:{int(split_from)}" if split_from and split_to else "N/A"
                )
                logger.info(
                    f"  {ticker:8} Date: {exec_date} Split: {split_ratio} ({split_from} → {split_to})"
                )

            # Show upcoming splits
            cur.execute(
                """
                SELECT ticker, execution_date, split_from, split_to
                FROM splits
                WHERE execution_date >= CURRENT_DATE
                ORDER BY execution_date ASC
                LIMIT 10;
            """
            )
            logger.info("\nUpcoming splits (next 10):")
            for row in cur.fetchall():
                ticker, exec_date, split_from, split_to = row
                split_ratio = (
                    f"{int(split_to)}:{int(split_from)}" if split_from and split_to else "N/A"
                )
                logger.info(f"  {ticker:8} Date: {exec_date} Split: {split_ratio}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_active_tickers()

        if not tickers:
            logger.warning("No active tickers found")
            return

        upsert_splits(tickers)
        logger.info("\nDaily update complete: Splits updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
