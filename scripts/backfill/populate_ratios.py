#!/usr/bin/env python3
"""
Backfill ratios table from Polygon.io API
Fetches historical ratio data from list_date to present
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
# Note: Polygon.io does not have a dedicated ratios endpoint
# Ratios must be calculated from financial statements (balance_sheets, income_statements, cash_flow_statements)
# This script is disabled until proper calculation logic is implemented
API_URL = None  # 'https://api.polygon.io/vX/reference/financials'  # Wrong endpoint


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


def fetch_all_ratios():
    """Fetch ALL ratios from Polygon (endpoint doesn't support per-ticker filtering)"""
    params = {"limit": 1000, "sort": "ticker.asc", "apiKey": POLYGON_API_KEY}

    all_results = []

    try:
        logger.info("Fetching all ratios from Polygon API...")
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_results.extend(data["results"])
            logger.info(f"  Fetched {len(data['results'])} ratios")

            # Handle pagination
            while data.get("next_url"):
                next_url = data["next_url"]
                if "apiKey" not in next_url:
                    next_url += f"&apiKey={POLYGON_API_KEY}"

                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK" and "results" in data:
                    all_results.extend(data["results"])
                    logger.info(f"  Fetched {len(all_results):,} ratios total...")
                else:
                    break

                # Rate limiting
                time.sleep(0.1)

        logger.info(f"Total ratios fetched: {len(all_results):,}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching ratios: {e}")
    except Exception as e:
        logger.error(f"Error fetching ratios: {e}")

    return all_results


def populate_table(tickers_data):
    """Fetch and insert ratios for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO ratios (
            ticker, date, cik, price, market_cap, enterprise_value, average_volume,
            price_to_earnings, price_to_book, price_to_sales, price_to_cash_flow,
            price_to_free_cash_flow, ev_to_sales, ev_to_ebitda, earnings_per_share,
            return_on_assets, return_on_equity, dividend_yield, current, quick,
            cash, debt_to_equity, free_cash_flow
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING ratios table...")
            cur.execute("TRUNCATE TABLE ratios RESTART IDENTITY CASCADE;")

            # Fetch ALL ratios from API (endpoint doesn't support per-ticker filtering)
            all_ratios = fetch_all_ratios()

            if not all_ratios:
                logger.warning("No ratios fetched from API")
                return

            # Build ticker list_date lookup
            ticker_dates = {ticker: list_date for ticker, list_date in tickers_data}

            # Process and filter ratios
            logger.info(
                f"Processing {len(all_ratios):,} ratios for {len(tickers_data)} active tickers..."
            )
            unique_ratios = {}  # Dictionary to deduplicate by (ticker, date)

            # Debug: Log first few API tickers and DB tickers
            api_tickers_sample = sorted(
                set(r.get("ticker") for r in all_ratios[:100] if r.get("ticker"))
            )[:10]
            db_tickers_sample = sorted(list(ticker_dates.keys()))[:10]
            logger.info(f"Sample API tickers: {api_tickers_sample}")
            logger.info(f"Sample DB tickers: {db_tickers_sample}")

            skipped_not_in_db = 0
            skipped_no_date = 0
            skipped_before_list_date = 0

            for result in all_ratios:
                ticker = result.get("ticker")

                # Skip if ticker not in our active list
                if ticker not in ticker_dates:
                    skipped_not_in_db += 1
                    continue

                # Parse date field (API uses 'date', not 'period_end')
                ratio_date = None
                if result.get("date"):
                    try:
                        ratio_date = datetime.strptime(result["date"], "%Y-%m-%d").date()
                    except:
                        skipped_no_date += 1
                        continue

                if not ratio_date:
                    skipped_no_date += 1
                    continue

                # Filter by list_date
                list_date = ticker_dates[ticker]
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                if ratio_date < from_date:
                    skipped_before_list_date += 1
                    continue

                # Get CIK
                cik = result.get("cik")

                key = (ticker, ratio_date)

                # Store unique ratio (later entries overwrite earlier ones)
                values = (
                    ticker,
                    ratio_date,
                    cik,
                    result.get("price"),
                    result.get("market_cap"),
                    result.get("enterprise_value"),
                    result.get("average_volume"),
                    result.get("price_to_earnings"),
                    result.get("price_to_book"),
                    result.get("price_to_sales"),
                    result.get("price_to_cash_flow"),
                    result.get("price_to_free_cash_flow"),
                    result.get("ev_to_sales"),
                    result.get("ev_to_ebitda"),
                    result.get("earnings_per_share"),
                    result.get("return_on_assets"),
                    result.get("return_on_equity"),
                    result.get("dividend_yield"),
                    result.get("current"),
                    result.get("quick"),
                    result.get("cash"),
                    result.get("debt_to_equity"),
                    result.get("free_cash_flow"),
                )
                unique_ratios[key] = values

            # Log filtering statistics
            logger.info(f"Filtering statistics:")
            logger.info(f"  Skipped (not in DB): {skipped_not_in_db:,}")
            logger.info(f"  Skipped (no date): {skipped_no_date:,}")
            logger.info(f"  Skipped (before list_date): {skipped_before_list_date:,}")
            logger.info(f"  Kept (unique ratios): {len(unique_ratios):,}")

            # Insert all unique ratios in batches
            logger.info(f"Inserting {len(unique_ratios):,} unique ratios...")
            batch = []
            batch_size = 1000
            total_ratios_inserted = 0

            for values in unique_ratios.values():
                batch.append(values)
                total_ratios_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {total_ratios_inserted:,} ratios inserted from {len(tickers_data)} active tickers"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_ratios,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM ratios;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total ratios: {stats[0]:,}")
            logger.info(f"  Unique tickers: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT ticker, date, price_to_earnings, price_to_book, return_on_equity
                FROM ratios
                WHERE date = (SELECT MAX(date) FROM ratios)
                ORDER BY market_cap DESC NULLS LAST
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by market cap on latest period:")
            for row in cur.fetchall():
                ticker, ratio_date, pe, pb, roe = row
                pe_str = f"{pe:.2f}" if pe else "N/A"
                pb_str = f"{pb:.2f}" if pb else "N/A"
                roe_str = f"{roe:.2%}" if roe else "N/A"
                logger.info(
                    f"  {ticker:8} {ratio_date} P/E: {pe_str:>8} P/B: {pb_str:>8} ROE: {roe_str:>8}"
                )


def main():
    """Main execution"""
    logger.error("=" * 80)
    logger.error("SCRIPT DISABLED: Polygon.io does not provide a ratios endpoint")
    logger.error("=" * 80)
    logger.error("")
    logger.error("Financial ratios must be calculated from financial statements.")
    logger.error("The ratios table should be populated by calculating metrics from:")
    logger.error("  - balance_sheets")
    logger.error("  - income_statements")
    logger.error("  - cash_flow_statements")
    logger.error("")
    logger.error("To enable this table, create a new script that:")
    logger.error("  1. Reads data from the three financial statement tables")
    logger.error("  2. Calculates ratios (P/E, P/B, ROE, ROA, debt/equity, etc.)")
    logger.error("  3. Inserts calculated ratios into the ratios table")
    logger.error("")
    logger.error("Exiting without making any changes to the database.")
    logger.error("=" * 80)
    return


if __name__ == "__main__":
    main()
