#!/usr/bin/env python3
"""
Backfill tickers table from Polygon.io API
Full reload: TRUNCATE then INSERT all tickers
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v3/reference/tickers"


def fetch_all_tickers():
    """Fetch all tickers from Polygon API with pagination"""
    all_tickers = []
    next_url = None
    page = 1

    params = {
        "apiKey": POLYGON_API_KEY,
        "market": "stocks",
        "active": "true",  # Get both active and inactive
        "limit": 1000,  # Max per page
    }

    while True:
        if next_url:
            logger.info(f"Fetching page {page}...")
            response = requests.get(next_url)
        else:
            logger.info(f"Fetching page {page} from {API_URL}")
            response = requests.get(API_URL, params=params)

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        all_tickers.extend(results)

        logger.info(f"  Page {page}: {len(results)} tickers (Total: {len(all_tickers)})")

        next_url = data.get("next_url")
        if next_url:
            # Add API key to next_url
            next_url = f"{next_url}&apiKey={POLYGON_API_KEY}"
            page += 1
        else:
            break

    logger.info(f"Total tickers fetched: {len(all_tickers)}")
    return all_tickers


def populate_table(tickers):
    """Insert all tickers into database (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO tickers (
            ticker, name, market, locale, type, active,
            currency_name, cik, composite_figi, share_class_figi,
            primary_exchange, delisted_utc, last_updated_utc
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING tickers table...")
            cur.execute("TRUNCATE TABLE tickers RESTART IDENTITY CASCADE;")

            # Insert new data in batches
            logger.info(f"Inserting {len(tickers)} tickers...")
            batch_size = 1000
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i : i + batch_size]
                values_list = []

                for ticker in batch:
                    # Parse timestamps
                    delisted_utc = None
                    last_updated_utc = None

                    if ticker.get("delisted_utc"):
                        try:
                            delisted_utc = datetime.fromisoformat(
                                ticker["delisted_utc"].replace("Z", "+00:00")
                            )
                        except:
                            pass

                    if ticker.get("last_updated_utc"):
                        try:
                            last_updated_utc = datetime.fromisoformat(
                                ticker["last_updated_utc"].replace("Z", "+00:00")
                            )
                        except:
                            pass

                    values = (
                        ticker.get("ticker"),
                        ticker.get("name"),
                        ticker.get("market"),
                        ticker.get("locale"),
                        ticker.get("type"),
                        ticker.get("active"),
                        ticker.get("currency_name"),
                        ticker.get("cik"),
                        ticker.get("composite_figi"),
                        ticker.get("share_class_figi"),
                        ticker.get("primary_exchange"),
                        delisted_utc,
                        last_updated_utc,
                    )
                    values_list.append(values)

                cur.executemany(insert_sql, values_list)
                logger.info(f"  Inserted batch {i//batch_size + 1}: {len(values_list)} tickers")

            # Get final count
            cur.execute("SELECT COUNT(*) FROM tickers;")
            count = cur.fetchone()[0]
            logger.info(f"Total tickers in database: {count}")

            # Show statistics
            cur.execute(
                """
                SELECT market, active, COUNT(*)
                FROM tickers
                GROUP BY market, active
                ORDER BY market, active DESC;
            """
            )
            logger.info("\nTicker statistics:")
            for row in cur.fetchall():
                status = "ACTIVE" if row[1] else "INACTIVE"
                logger.info(f"  {row[0]:15} {status:10} {row[2]:6} tickers")

            # Show sample
            cur.execute(
                """
                SELECT ticker, name, type, active
                FROM tickers
                WHERE active = true
                ORDER BY ticker
                LIMIT 5;
            """
            )
            logger.info("\nSample active tickers:")
            for row in cur.fetchall():
                status = "ACTIVE" if row[3] else "INACTIVE"
                logger.info(f"  {row[0]:8} - {row[1]:40} ({row[2]}) {status}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = fetch_all_tickers()
        populate_table(tickers)

        logger.info("\nBackfill complete: Tickers table fully reloaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
