#!/usr/bin/env python3
"""
Daily update for ticker_overview table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
"""
import os
import sys
import time
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
API_URL = "https://api.polygon.io/v3/reference/tickers/{ticker}"


def get_all_tickers():
    """Get all active tickers from tickers table"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ticker FROM tickers WHERE active = true ORDER BY ticker;")
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(f"Found {len(tickers)} active tickers to process")
            return tickers


def fetch_ticker_overview(ticker):
    """Fetch overview for a single ticker"""
    url = API_URL.format(ticker=ticker)
    params = {"apiKey": POLYGON_API_KEY}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            return data["results"]
        else:
            logger.warning(f"No results for {ticker}: {data.get('status')}")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Ticker {ticker} not found (404)")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None


def upsert_ticker_overviews(tickers):
    """Fetch and upsert ticker overviews (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO ticker_overview (
            ticker, name, market, locale, type, active,
            currency_name, cik, composite_figi, share_class_figi, primary_exchange,
            description, homepage_url, phone_number, list_date, delisted_utc,
            market_cap, share_class_shares_outstanding, weighted_shares_outstanding,
            round_lot, total_employees, sic_code, sic_description,
            ticker_root, ticker_suffix,
            address_address1, address_city, address_postal_code, address_state,
            branding_icon_url, branding_logo_url, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
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
            description = EXCLUDED.description,
            homepage_url = EXCLUDED.homepage_url,
            phone_number = EXCLUDED.phone_number,
            list_date = EXCLUDED.list_date,
            delisted_utc = EXCLUDED.delisted_utc,
            market_cap = EXCLUDED.market_cap,
            share_class_shares_outstanding = EXCLUDED.share_class_shares_outstanding,
            weighted_shares_outstanding = EXCLUDED.weighted_shares_outstanding,
            round_lot = EXCLUDED.round_lot,
            total_employees = EXCLUDED.total_employees,
            sic_code = EXCLUDED.sic_code,
            sic_description = EXCLUDED.sic_description,
            ticker_root = EXCLUDED.ticker_root,
            ticker_suffix = EXCLUDED.ticker_suffix,
            address_address1 = EXCLUDED.address_address1,
            address_city = EXCLUDED.address_city,
            address_postal_code = EXCLUDED.address_postal_code,
            address_state = EXCLUDED.address_state,
            branding_icon_url = EXCLUDED.branding_icon_url,
            branding_logo_url = EXCLUDED.branding_logo_url,
            updated_at = CURRENT_TIMESTAMP;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM ticker_overview;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert ticker overviews
            logger.info(f"Upserting overview data for {len(tickers)} tickers...")
            processed = 0
            upserted = 0
            batch = []
            batch_size = 100

            for i, ticker in enumerate(tickers, 1):
                overview = fetch_ticker_overview(ticker)

                if overview:
                    # Parse dates
                    list_date = None
                    delisted_utc = None

                    if overview.get("list_date"):
                        try:
                            list_date = datetime.strptime(overview["list_date"], "%Y-%m-%d").date()
                        except:
                            pass

                    if overview.get("delisted_utc"):
                        try:
                            delisted_utc = datetime.fromisoformat(
                                overview["delisted_utc"].replace("Z", "+00:00")
                            )
                        except:
                            pass

                    # Extract nested address and branding
                    address = overview.get("address", {}) or {}
                    branding = overview.get("branding", {}) or {}

                    values = (
                        overview.get("ticker"),
                        overview.get("name"),
                        overview.get("market"),
                        overview.get("locale"),
                        overview.get("type"),
                        overview.get("active"),
                        overview.get("currency_name"),
                        overview.get("cik"),
                        overview.get("composite_figi"),
                        overview.get("share_class_figi"),
                        overview.get("primary_exchange"),
                        overview.get("description"),
                        overview.get("homepage_url"),
                        overview.get("phone_number"),
                        list_date,
                        delisted_utc,
                        overview.get("market_cap"),
                        overview.get("share_class_shares_outstanding"),
                        overview.get("weighted_shares_outstanding"),
                        overview.get("round_lot"),
                        overview.get("total_employees"),
                        overview.get("sic_code"),
                        overview.get("sic_description"),
                        overview.get("ticker_root"),
                        overview.get("ticker_suffix"),
                        address.get("address1"),
                        address.get("city"),
                        address.get("postal_code"),
                        address.get("state"),
                        branding.get("icon_url"),
                        branding.get("logo_url"),
                    )
                    batch.append(values)
                    upserted += 1

                processed += 1

                # Upsert batch
                if len(batch) >= batch_size:
                    cur.executemany(upsert_sql, batch)
                    logger.info(
                        f"  Progress: {processed}/{len(tickers)} processed, {upserted} upserted"
                    )
                    batch = []

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM ticker_overview;")
            count_after = cur.fetchone()[0]

            new_records = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Records before: {count_before}")
            logger.info(f"  Records after:  {count_after}")
            logger.info(f"  New records:    {new_records}")
            logger.info(f"  Updated:        {upserted - new_records}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, name, market_cap, updated_at
                FROM ticker_overview
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '2 minutes'
                ORDER BY updated_at DESC
                LIMIT 5;
            """
            )
            logger.info("\nRecently updated ticker overviews:")
            for row in cur.fetchall():
                market_cap_b = row[2] / 1_000_000_000 if row[2] else 0
                logger.info(f"  {row[0]:8} - {row[1]:40} Market Cap: ${market_cap_b:,.1f}B")

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(description) as with_description,
                    COUNT(market_cap) as with_market_cap
                FROM ticker_overview;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData completeness:")
            logger.info(f"  Total records: {stats[0]}")
            logger.info(
                f"  With description: {stats[1]} ({stats[1]*100//stats[0] if stats[0] else 0}%)"
            )
            logger.info(
                f"  With market cap: {stats[2]} ({stats[2]*100//stats[0] if stats[0] else 0}%)"
            )


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_all_tickers()

        if not tickers:
            logger.warning("No active tickers found in database")
            return

        upsert_ticker_overviews(tickers)
        logger.info("\nDaily update complete: Ticker overviews updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
