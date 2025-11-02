#!/usr/bin/env python3
"""
Backfill ticker_events table from Polygon.io API
Fetches historical ticker events (symbol changes, etc.) for all tickers
Full reload: TRUNCATE then INSERT all data
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


def get_all_tickers():
    """Get all tickers from ticker_overview"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker
                FROM ticker_overview
                ORDER BY ticker;
            """
            )
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(f"Found {len(tickers)} tickers")
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


def populate_table(tickers_list):
    """Fetch and insert ticker events (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO ticker_events (
            ticker, event_date, event_type, new_ticker, company_name
        ) VALUES (
            %s, %s, %s, %s, %s
        );
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING ticker_events table...")
            cur.execute("TRUNCATE TABLE ticker_events RESTART IDENTITY CASCADE;")

            # Fetch and insert ticker events
            logger.info(f"Fetching ticker events for {len(tickers_list)} tickers...")
            processed = 0
            unique_records = {}  # Dictionary to deduplicate by (ticker, date, type)

            for i, ticker in enumerate(tickers_list, 1):
                events = fetch_ticker_events(ticker)

                for event in events:
                    key = (event["ticker"], event["event_date"], event["event_type"])
                    values_tuple = (
                        event["ticker"],
                        event["event_date"],
                        event["event_type"],
                        event["new_ticker"],
                        event["company_name"],
                    )
                    unique_records[key] = values_tuple

                processed += 1

                # Log progress every 1000 tickers
                if processed % 1000 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_list)} tickers, {len(unique_records):,} events collected"
                    )

                # Rate limiting: ~100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique ticker events...")
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

            logger.info(f"Final: {processed} tickers processed, {total_inserted:,} events inserted")

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    COUNT(DISTINCT event_type) as unique_types,
                    MIN(event_date) as earliest_date,
                    MAX(event_date) as latest_date
                FROM ticker_events;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total events: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Event types: {stats[2]}")
            logger.info(f"  Date range: {stats[3]} to {stats[4]}")

            # Show event type breakdown
            cur.execute(
                """
                SELECT event_type, COUNT(*) as count
                FROM ticker_events
                GROUP BY event_type
                ORDER BY count DESC;
            """
            )
            logger.info(f"\nEvent type breakdown:")
            for row in cur.fetchall():
                event_type, count = row
                logger.info(f"  {event_type:25} {count:>6,}")

            # Sample recent ticker changes
            cur.execute(
                """
                SELECT ticker, event_date, new_ticker, company_name
                FROM ticker_events
                WHERE event_type = 'ticker_change'
                ORDER BY event_date DESC
                LIMIT 15;
            """
            )
            logger.info(f"\nRecent ticker changes:")
            for row in cur.fetchall():
                ticker, evt_date, new_ticker, company = row
                logger.info(
                    f"  {ticker:8} -> {new_ticker:8} {evt_date} {company[:40] if company else ''}"
                )


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers_list = get_all_tickers()

        if not tickers_list:
            logger.warning("No tickers found")
            return

        populate_table(tickers_list)
        logger.info("\nBackfill complete: Ticker events table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
