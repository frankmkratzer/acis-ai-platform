#!/usr/bin/env python3
"""
Daily update for short_interest table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent data (last 90 days) for all active tickers
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


def fetch_short_interest(ticker, from_date):
    """Fetch recent short interest for a ticker"""
    params = {
        "ticker": ticker,
        "settlement_date.gte": from_date.strftime("%Y-%m-%d"),
        "limit": 1000,
        "apiKey": POLYGON_API_KEY,
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

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No short interest for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching short interest for {ticker}: {e}")

    return all_results


def upsert_short_interest(tickers_data):
    """Fetch and upsert short interest (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO short_interest (
            ticker, settlement_date, short_interest, avg_daily_volume, days_to_cover, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, settlement_date) DO UPDATE SET
            short_interest = EXCLUDED.short_interest,
            avg_daily_volume = EXCLUDED.avg_daily_volume,
            days_to_cover = EXCLUDED.days_to_cover,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 90 days to catch any updates
    from_date = date.today() - timedelta(days=90)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM short_interest;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert short interest
            logger.info(
                f"Upserting short interest for {len(tickers_data)} tickers (last 90 days)..."
            )
            processed = 0
            total_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Don't fetch data before list_date
                fetch_from = max(from_date, list_date) if list_date else from_date

                results = fetch_short_interest(ticker, fetch_from)

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
                        if list_date and settlement_date and settlement_date < list_date:
                            continue

                        values = (
                            ticker,
                            settlement_date,
                            result.get("short_interest"),
                            result.get("avg_daily_volume"),
                            result.get("days_to_cover"),
                        )
                        batch.append(values)
                        total_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_upserted:,} records upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM short_interest;")
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
                SELECT ticker, settlement_date, short_interest, avg_daily_volume, days_to_cover, updated_at
                FROM short_interest
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                  AND days_to_cover IS NOT NULL
                ORDER BY days_to_cover DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated (top 10 by days to cover):")
            for row in cur.fetchall():
                ticker, settle_date, short_int, avg_vol, days, updated = row
                logger.info(
                    f"  {ticker:8} {settle_date} Short: {short_int:>12,} Days: {days:>6.2f}"
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

        upsert_short_interest(tickers)
        logger.info("\nDaily update complete: Short interest updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
