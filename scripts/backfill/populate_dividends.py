#!/usr/bin/env python3
"""
Backfill dividends table from Polygon.io API
Fetches historical dividend data from list_date to present
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
API_URL = "https://api.polygon.io/v3/reference/dividends"


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


def fetch_dividends(ticker, from_date, to_date):
    """Fetch dividends for a ticker between dates"""
    params = {
        "ticker": ticker,
        "ex_dividend_date.gte": from_date.strftime("%Y-%m-%d"),
        "ex_dividend_date.lte": to_date.strftime("%Y-%m-%d"),
        "apiKey": POLYGON_API_KEY,
        "limit": 1000,
        "sort": "ex_dividend_date",
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
            logger.debug(f"No dividends for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching dividends for {ticker}: {e}")
        return []


def populate_table(tickers_data):
    """Fetch and insert dividends for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO dividends (
            id, ticker, cash_amount, currency, declaration_date,
            dividend_type, ex_dividend_date, frequency, pay_date, record_date
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING dividends table...")
            cur.execute("TRUNCATE TABLE dividends RESTART IDENTITY CASCADE;")

            # Fetch and insert dividends
            logger.info(f"Fetching dividends for {len(tickers_data)} tickers...")
            processed = 0
            total_dividends_inserted = 0
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

                dividends = fetch_dividends(ticker, from_date, today)

                if dividends:
                    for div in dividends:
                        # Parse dates
                        declaration_date = None
                        ex_dividend_date = None
                        pay_date = None
                        record_date = None

                        if div.get("declaration_date"):
                            try:
                                declaration_date = datetime.strptime(
                                    div["declaration_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        if div.get("ex_dividend_date"):
                            try:
                                ex_dividend_date = datetime.strptime(
                                    div["ex_dividend_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        if div.get("pay_date"):
                            try:
                                pay_date = datetime.strptime(div["pay_date"], "%Y-%m-%d").date()
                            except:
                                pass

                        if div.get("record_date"):
                            try:
                                record_date = datetime.strptime(
                                    div["record_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        values = (
                            div.get("id"),
                            div.get("ticker"),
                            div.get("cash_amount"),
                            div.get("currency"),
                            declaration_date,
                            div.get("dividend_type"),
                            ex_dividend_date,
                            div.get("frequency"),
                            pay_date,
                            record_date,
                        )
                        batch.append(values)
                        total_dividends_inserted += 1

                    # Insert batch
                    if len(batch) >= batch_size:
                        cur.executemany(insert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_dividends_inserted:,} dividends inserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_dividends_inserted:,} dividends inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_dividends,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(ex_dividend_date) as earliest_date,
                    MAX(ex_dividend_date) as latest_date
                FROM dividends;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total dividends: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, ex_dividend_date, cash_amount, currency, dividend_type, pay_date
                FROM dividends
                WHERE ex_dividend_date = (SELECT MAX(ex_dividend_date) FROM dividends)
                ORDER BY cash_amount DESC
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by cash amount on latest ex-dividend date:")
            for row in cur.fetchall():
                ticker, ex_div_date, cash_amt, currency, div_type, pay_date = row
                logger.info(
                    f"  {ticker:8} Ex-Date: {ex_div_date} Amount: {cash_amt:>8.4f} {currency} Type: {div_type} Pay: {pay_date}"
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
        logger.info("\nBackfill complete: Dividends table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
