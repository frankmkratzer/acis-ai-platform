#!/usr/bin/env python3
"""
Daily update for ratios table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent quarters (last 4 quarters) for all active tickers
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
API_URL = "https://api.polygon.io/stocks/financials/v1/ratios"


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


def fetch_ratios(ticker, limit=4):
    """Fetch recent ratios for a ticker"""
    params = {
        "ticker": ticker,
        "include_sources": "false",
        "limit": limit,
        "apiKey": POLYGON_API_KEY,
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

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No ratios for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Error fetching ratios for {ticker}: {e}")

    return all_results


def upsert_ratios(tickers_data):
    """Fetch and upsert ratios (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO ratios (
            ticker, date, cik, price, market_cap, enterprise_value, average_volume,
            price_to_earnings, price_to_book, price_to_sales, price_to_cash_flow,
            price_to_free_cash_flow, ev_to_sales, ev_to_ebitda, earnings_per_share,
            return_on_assets, return_on_equity, dividend_yield, current, quick,
            cash, debt_to_equity, free_cash_flow, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, date) DO UPDATE SET
            cik = EXCLUDED.cik,
            price = EXCLUDED.price,
            market_cap = EXCLUDED.market_cap,
            enterprise_value = EXCLUDED.enterprise_value,
            average_volume = EXCLUDED.average_volume,
            price_to_earnings = EXCLUDED.price_to_earnings,
            price_to_book = EXCLUDED.price_to_book,
            price_to_sales = EXCLUDED.price_to_sales,
            price_to_cash_flow = EXCLUDED.price_to_cash_flow,
            price_to_free_cash_flow = EXCLUDED.price_to_free_cash_flow,
            ev_to_sales = EXCLUDED.ev_to_sales,
            ev_to_ebitda = EXCLUDED.ev_to_ebitda,
            earnings_per_share = EXCLUDED.earnings_per_share,
            return_on_assets = EXCLUDED.return_on_assets,
            return_on_equity = EXCLUDED.return_on_equity,
            dividend_yield = EXCLUDED.dividend_yield,
            current = EXCLUDED.current,
            quick = EXCLUDED.quick,
            cash = EXCLUDED.cash,
            debt_to_equity = EXCLUDED.debt_to_equity,
            free_cash_flow = EXCLUDED.free_cash_flow,
            updated_at = CURRENT_TIMESTAMP;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM ratios;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert ratios
            logger.info(f"Upserting ratios for {len(tickers_data)} tickers (last 4 quarters)...")
            processed = 0
            total_ratios_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                results = fetch_ratios(ticker, limit=4)

                if results:
                    for result in results:
                        # Parse period_end date
                        ratio_date = None
                        if result.get("period_end"):
                            try:
                                ratio_date = datetime.strptime(
                                    result["period_end"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if list_date and ratio_date and ratio_date < list_date:
                            continue

                        # Get CIK
                        cik = result.get("cik")

                        # Extract ratio fields directly from result
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
                        batch.append(values)
                        total_ratios_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_ratios_upserted:,} ratios upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM ratios;")
            count_after = cur.fetchone()[0]

            new_ratios = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Ratios before: {count_before:,}")
            logger.info(f"  Ratios after:  {count_after:,}")
            logger.info(f"  New ratios:    {new_ratios:,}")
            logger.info(f"  Updated:       {total_ratios_upserted - new_ratios:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, date, price_to_earnings, return_on_equity, updated_at
                FROM ratios
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY date DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated ratios:")
            for row in cur.fetchall():
                ticker, ratio_date, pe, roe, updated = row
                logger.info(
                    f"  {ticker:8} {ratio_date} P/E: {pe:.2f if pe else 'N/A':>8} ROE: {roe:.2%if roe else 'N/A':>8}"
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

        upsert_ratios(tickers)
        logger.info("\nDaily update complete: Ratios updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
