#!/usr/bin/env python3
"""
Daily update for ticker_events table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Checks all active tickers for new events
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
API_URL_TEMPLATE = "https://api.polygon.io/vX/reference/tickers/{ticker}/events"


def get_active_tickers():
    """Get all active tickers"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker
                FROM ticker_overview
                WHERE active = true
                ORDER BY ticker;
            """
            )
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(f"Found {len(tickers)} active tickers")
            return tickers


def fetch_ticker_events(ticker):
    """Fetch events for a specific ticker"""
    url = API_URL_TEMPLATE.format(ticker=ticker)
    params = {
        "types": "ticker_change",  # Currently only ticker_change is supported
        "apiKey": POLYGON_API_KEY,
    }

    events = []

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            results = data["results"]
            company_name = results.get("name")

            if "events" in results and isinstance(results["events"], list):
                for event in results["events"]:
                    event_date_str = event.get("date")
                    event_type = event.get("type")

                    # Parse date
                    event_date = None
                    if event_date_str:
                        try:
                            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                        except:
                            pass

                    # Extract new ticker for ticker_change events
                    new_ticker = None
                    if event_type == "ticker_change" and "ticker_change" in event:
                        new_ticker = event["ticker_change"].get("ticker")

                    if event_date and event_type:
                        events.append(
                            {
                                "ticker": ticker,
                                "event_date": event_date,
                                "event_type": event_type,
                                "new_ticker": new_ticker,
                                "company_name": company_name,
                            }
                        )

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No events for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching events for {ticker}: {e}")

    return events


def upsert_ticker_events(tickers_list):
    """Fetch and upsert ticker events (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO ticker_events (
            ticker, event_date, event_type, new_ticker, company_name, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, event_date, event_type) DO UPDATE SET
            new_ticker = EXCLUDED.new_ticker,
            company_name = EXCLUDED.company_name,
            updated_at = CURRENT_TIMESTAMP;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM ticker_events;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert ticker events
            logger.info(f"Upserting ticker events for {len(tickers_list)} active tickers...")
            processed = 0
            total_upserted = 0
            batch = []
            batch_size = 1000

            for i, ticker in enumerate(tickers_list, 1):
                events = fetch_ticker_events(ticker)

                for event in events:
                    values_tuple = (
                        event["ticker"],
                        event["event_date"],
                        event["event_type"],
                        event["new_ticker"],
                        event["company_name"],
                    )
                    batch.append(values_tuple)
                    total_upserted += 1

                # Upsert batch
                if len(batch) >= batch_size:
                    cur.executemany(upsert_sql, batch)
                    batch = []

                processed += 1

                # Log progress every 1000 tickers
                if processed % 1000 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_list)} tickers, {total_upserted:,} events upserted"
                    )

                # Rate limiting: ~100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM ticker_events;")
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
                SELECT ticker, event_date, event_type, new_ticker, company_name, updated_at
                FROM ticker_events
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY event_date DESC
                LIMIT 15;
            """
            )
            if cur.rowcount > 0:
                logger.info("\nRecently updated ticker events:")
                for row in cur.fetchall():
                    ticker, evt_date, evt_type, new_ticker, company, updated = row
                    if evt_type == "ticker_change":
                        logger.info(
                            f"  {ticker:8} -> {new_ticker:8} {evt_date} {company[:35] if company else ''}"
                        )
                    else:
                        logger.info(
                            f"  {ticker:8} {evt_type:15} {evt_date} {company[:35] if company else ''}"
                        )


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers_list = get_active_tickers()

        if not tickers_list:
            logger.warning("No active tickers found")
            return

        upsert_ticker_events(tickers_list)
        logger.info("\nDaily update complete: Ticker events updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
