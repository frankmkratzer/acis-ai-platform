#!/usr/bin/env python3
"""
Daily update for dividends table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches last 90 days of dividend data for all active tickers
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
            logger.debug(f"No dividends for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching dividends for {ticker}: {e}")
        return []


def upsert_dividends(tickers_data):
    """Fetch and upsert dividends (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO dividends (
            id, ticker, cash_amount, currency, declaration_date,
            dividend_type, ex_dividend_date, frequency, pay_date, record_date, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (id) DO UPDATE SET
            ticker = EXCLUDED.ticker,
            cash_amount = EXCLUDED.cash_amount,
            currency = EXCLUDED.currency,
            declaration_date = EXCLUDED.declaration_date,
            dividend_type = EXCLUDED.dividend_type,
            ex_dividend_date = EXCLUDED.ex_dividend_date,
            frequency = EXCLUDED.frequency,
            pay_date = EXCLUDED.pay_date,
            record_date = EXCLUDED.record_date,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 90 days of data
    today = date.today()
    from_date = today - timedelta(days=90)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM dividends;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert dividends
            logger.info(f"Upserting dividends for {len(tickers_data)} tickers (last 90 days)...")
            processed = 0
            total_dividends_upserted = 0
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

                dividends = fetch_dividends(ticker, effective_from_date, today)

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
                        total_dividends_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_dividends_upserted:,} dividends upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM dividends;")
            count_after = cur.fetchone()[0]

            new_dividends = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Dividends before: {count_before:,}")
            logger.info(f"  Dividends after:  {count_after:,}")
            logger.info(f"  New dividends:    {new_dividends:,}")
            logger.info(f"  Updated:          {total_dividends_upserted - new_dividends:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, ex_dividend_date, cash_amount, currency, dividend_type, updated_at
                FROM dividends
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '2 minutes'
                ORDER BY ex_dividend_date DESC, cash_amount DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated dividends:")
            for row in cur.fetchall():
                ticker, ex_div_date, cash_amt, currency, div_type, updated = row
                logger.info(
                    f"  {ticker:8} Ex-Date: {ex_div_date} Amount: {cash_amt:>8.4f} {currency} Type: {div_type}"
                )

            # Show upcoming dividends
            cur.execute(
                """
                SELECT ticker, ex_dividend_date, cash_amount, currency, pay_date
                FROM dividends
                WHERE ex_dividend_date >= CURRENT_DATE
                ORDER BY ex_dividend_date ASC
                LIMIT 10;
            """
            )
            logger.info("\nUpcoming dividends (next 10):")
            for row in cur.fetchall():
                ticker, ex_div_date, cash_amt, currency, pay_date = row
                logger.info(
                    f"  {ticker:8} Ex-Date: {ex_div_date} Amount: {cash_amt:>8.4f} {currency} Pay: {pay_date}"
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

        upsert_dividends(tickers)
        logger.info("\nDaily update complete: Dividends updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
