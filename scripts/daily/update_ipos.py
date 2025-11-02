#!/usr/bin/env python3
"""
Daily update for ipos table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent IPO data (last 180 days) to capture new IPOs and status changes
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
API_URL = "https://api.polygon.io/vX/reference/ipos"


def fetch_recent_ipos():
    """Fetch recent IPO data (last 180 days)"""
    # Fetch last 180 days to capture IPOs and status changes
    from_date = date.today() - timedelta(days=180)

    params = {
        "listing_date.gte": from_date.strftime("%Y-%m-%d"),
        "limit": 1000,
        "apiKey": POLYGON_API_KEY,
    }

    all_ipos = []
    page_count = 0

    try:
        logger.info(f"Fetching IPO data from {from_date} onwards...")
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_ipos.extend(data["results"])
            page_count += 1

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
                else:
                    break

        logger.info(f"Fetched {len(all_ipos):,} IPO records ({page_count} pages)")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Error fetching IPO data: {e}")

    return all_ipos


def upsert_ipos(ipos_data):
    """Upsert IPO data (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO ipos (
            ticker, issuer_name, isin, listing_date, ipo_status,
            final_issue_price, lowest_offer_price, highest_offer_price,
            min_shares_offered, max_shares_offered, total_offer_size,
            announced_date, last_updated, primary_exchange, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, listing_date) DO UPDATE SET
            issuer_name = EXCLUDED.issuer_name,
            isin = EXCLUDED.isin,
            ipo_status = EXCLUDED.ipo_status,
            final_issue_price = EXCLUDED.final_issue_price,
            lowest_offer_price = EXCLUDED.lowest_offer_price,
            highest_offer_price = EXCLUDED.highest_offer_price,
            min_shares_offered = EXCLUDED.min_shares_offered,
            max_shares_offered = EXCLUDED.max_shares_offered,
            total_offer_size = EXCLUDED.total_offer_size,
            announced_date = EXCLUDED.announced_date,
            last_updated = EXCLUDED.last_updated,
            primary_exchange = EXCLUDED.primary_exchange,
            updated_at = CURRENT_TIMESTAMP;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM ipos;")
            count_before = cur.fetchone()[0]

            # Process data
            logger.info(f"Processing {len(ipos_data):,} IPO records...")
            batch = []
            total_upserted = 0

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
                        last_updated = datetime.fromtimestamp(last_updated_ts / 1000)
                    except:
                        pass

                if ticker and listing_date:
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
                    batch.append(values_tuple)
                    total_upserted += 1

            # Upsert all records
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM ipos;")
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
                SELECT ticker, issuer_name, listing_date, ipo_status, final_issue_price, updated_at
                FROM ipos
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY listing_date DESC
                LIMIT 15;
            """
            )
            logger.info("\nRecently updated IPOs:")
            for row in cur.fetchall():
                ticker, issuer, list_date, status, price, updated = row
                price_str = f"${price:.2f}" if price else "N/A"
                logger.info(f"  {ticker:8} {list_date} {status:15} {price_str:>10} {issuer[:35]}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        ipos_data = fetch_recent_ipos()

        if not ipos_data:
            logger.info("No IPO data found for update period")
            return

        upsert_ipos(ipos_data)
        logger.info("\nDaily update complete: IPOs updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
