#!/usr/bin/env python3
"""
Daily update for tickers table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
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


def upsert_tickers(tickers):
    """Upsert tickers into database (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO tickers (
            ticker, name, market, locale, type, active,
            currency_name, cik, composite_figi, share_class_figi,
            primary_exchange, delisted_utc, last_updated_utc, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker) DO UPDATE SET
            name = EXCLUDED.name,
            market = EXCLUDED.market,
            locale = EXCLUDED.locale,
            type = EXCLUDED.type,
            active = EXCLUDED.active,
            currency_name = EXCLUDED.currency_name,
            cik = EXCLUDED.cik,
            composite_figi = EXCLUDED.composite_figi,
            share_class_figi = EXCLUDED.share_class_figi,
            primary_exchange = EXCLUDED.primary_exchange,
            delisted_utc = EXCLUDED.delisted_utc,
            last_updated_utc = EXCLUDED.last_updated_utc,
            updated_at = CURRENT_TIMESTAMP;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM tickers;")
            count_before = cur.fetchone()[0]

            # UPSERT: Insert new or update existing
            logger.info(f"Upserting {len(tickers)} tickers...")
            batch_size = 1000
            total_processed = 0

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

                cur.executemany(upsert_sql, values_list)
                total_processed += len(values_list)
                logger.info(f"  Batch {i//batch_size + 1}: {len(values_list)} tickers upserted")

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM tickers;")
            count_after = cur.fetchone()[0]

            new_tickers = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Tickers before: {count_before}")
            logger.info(f"  Tickers after:  {count_after}")
            logger.info(f"  New tickers:    {new_tickers}")
            logger.info(f"  Updated:        {total_processed - new_tickers}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, name, type, active, updated_at
                FROM tickers
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '1 minute'
                ORDER BY updated_at DESC
                LIMIT 5;
            """
            )
            logger.info("\nRecently updated tickers:")
            for row in cur.fetchall():
                status = "ACTIVE" if row[3] else "INACTIVE"
                logger.info(f"  {row[0]:8} - {row[1]:40} ({row[2]}) {status}")

            # Show statistics
            cur.execute(
                """
                SELECT active, COUNT(*)
                FROM tickers
                GROUP BY active
                ORDER BY active DESC;
            """
            )
            logger.info("\nCurrent ticker counts:")
            for row in cur.fetchall():
                status = "ACTIVE" if row[0] else "INACTIVE"
                logger.info(f"  {status}: {row[1]} tickers")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = fetch_all_tickers()
        upsert_tickers(tickers)

        logger.info("\nDaily update complete: Tickers updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
