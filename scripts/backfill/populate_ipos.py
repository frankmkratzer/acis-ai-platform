#!/usr/bin/env python3
"""
Backfill ipos table from Polygon.io API
Fetches historical IPO data from 2008 to present
Full reload: TRUNCATE then INSERT all data
"""
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/vX/reference/ipos"


def fetch_all_ipos():
    """Fetch all IPO data from Polygon.io API with pagination"""
    params = {
        "listing_date.gte": "2008-01-01",  # Polygon has IPO data from 2008
        "limit": 1000,
        "apiKey": POLYGON_API_KEY,
    }

    all_ipos = []
    page_count = 0

    try:
        logger.info("Fetching IPO data from Polygon.io API...")
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_ipos.extend(data["results"])
            page_count += 1
            logger.info(
                f"  Page {page_count}: {len(data['results'])} IPOs (total: {len(all_ipos):,})"
            )

            # Handle pagination
            while data.get("next_url"):
                time.sleep(0.1)  # Rate limiting
                next_url = data["next_url"] + f"&apiKey={POLYGON_API_KEY}"
                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK" and "results" in data:
                    all_ipos.extend(data["results"])
                    page_count += 1
                    logger.info(
                        f"  Page {page_count}: {len(data['results'])} IPOs (total: {len(all_ipos):,})"
                    )
                else:
                    break

        logger.info(f"Fetched {len(all_ipos):,} total IPO records")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Error fetching IPO data: {e}")

    return all_ipos


def populate_table(ipos_data):
    """Insert IPO data into table (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO ipos (
            ticker, issuer_name, isin, listing_date, ipo_status,
            final_issue_price, lowest_offer_price, highest_offer_price,
            min_shares_offered, max_shares_offered, total_offer_size,
            announced_date, last_updated, primary_exchange
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING ipos table...")
            cur.execute("TRUNCATE TABLE ipos RESTART IDENTITY CASCADE;")

            # Prepare data for insertion
            logger.info(f"Processing {len(ipos_data):,} IPO records...")
            unique_records = {}  # Dictionary to deduplicate by (ticker, listing_date)

            for ipo in ipos_data:
                ticker = ipo.get("ticker")
                listing_date_str = ipo.get("listing_date")

                # Parse listing_date
                listing_date = None
                if listing_date_str:
                    try:
                        listing_date = datetime.strptime(listing_date_str, "%Y-%m-%d").date()
                    except:
                        pass

                # Parse announced_date
                announced_date = None
                announced_date_str = ipo.get("announced_date")
                if announced_date_str:
                    try:
                        announced_date = datetime.strptime(announced_date_str, "%Y-%m-%d").date()
                    except:
                        pass

                # Parse last_updated timestamp
                last_updated = None
                last_updated_ts = ipo.get("last_updated")
                if last_updated_ts:
                    try:
                        # Assuming timestamp in milliseconds
                        last_updated = datetime.fromtimestamp(last_updated_ts / 1000)
                    except:
                        pass

                if ticker and listing_date:
                    key = (ticker, listing_date)

                    values_tuple = (
                        ticker,
                        ipo.get("issuer_name"),
                        ipo.get("isin"),
                        listing_date,
                        ipo.get("ipo_status"),
                        ipo.get("final_issue_price"),
                        ipo.get("lowest_offer_price"),
                        ipo.get("highest_offer_price"),
                        ipo.get("min_shares_offered"),
                        ipo.get("max_shares_offered"),
                        ipo.get("total_offer_size"),
                        announced_date,
                        last_updated,
                        ipo.get("primary_exchange"),
                    )
                    unique_records[key] = values_tuple

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique IPO records...")
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

            logger.info(f"Final: {total_inserted:,} IPO records inserted")

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_ipos,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(listing_date) as earliest_date,
                    MAX(listing_date) as latest_date,
                    COUNT(DISTINCT ipo_status) as unique_statuses
                FROM ipos;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total IPOs: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")
            logger.info(f"  Unique statuses: {stats[4]}")

            # Show IPO status breakdown
            cur.execute(
                """
                SELECT ipo_status, COUNT(*) as count
                FROM ipos
                GROUP BY ipo_status
                ORDER BY count DESC;
            """
            )
            logger.info(f"\nIPO status breakdown:")
            for row in cur.fetchall():
                status, count = row
                logger.info(f"  {status or 'NULL':25} {count:>6,}")

            # Sample recent IPOs
            cur.execute(
                """
                SELECT ticker, issuer_name, listing_date, ipo_status, final_issue_price
                FROM ipos
                WHERE listing_date >= CURRENT_DATE - INTERVAL '90 days'
                ORDER BY listing_date DESC
                LIMIT 15;
            """
            )
            logger.info(f"\nRecent IPOs (last 90 days):")
            for row in cur.fetchall():
                ticker, issuer, list_date, status, price = row
                price_str = f"${price:.2f}" if price else "N/A"
                logger.info(f"  {ticker:8} {list_date} {status:15} {price_str:>10} {issuer[:40]}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        ipos_data = fetch_all_ipos()

        if not ipos_data:
            logger.warning("No IPO data found")
            return

        populate_table(ipos_data)
        logger.info("\nBackfill complete: IPOs table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
