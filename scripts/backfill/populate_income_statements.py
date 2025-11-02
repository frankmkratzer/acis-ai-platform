#!/usr/bin/env python3
"""
Backfill income_statements table from Polygon.io API
Fetches historical income statement data from list_date to present
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
API_URL = "https://api.polygon.io/stocks/financials/v1/income-statements"


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


def fetch_income_statements(ticker):
    """Fetch income statements for a ticker (both quarterly and annual)"""
    all_results = []

    for timeframe in ["quarterly", "annual"]:
        params = {
            "tickers": ticker,
            "timeframe": timeframe,
            "limit": 1000,
            "apiKey": POLYGON_API_KEY,
        }

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
                logger.debug(f"No {timeframe} income statements for {ticker}")
            else:
                logger.error(f"HTTP error for {ticker} ({timeframe}): {e}")
        except Exception as e:
            logger.error(f"Error fetching {timeframe} income statements for {ticker}: {e}")

    return all_results


def populate_table(tickers_data):
    """Fetch and insert income statements for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO income_statements (
            cik, period_end, timeframe, filing_date, fiscal_quarter, fiscal_year, tickers,
            revenue, cost_of_revenue, gross_profit, research_development, selling_general_administrative,
            other_operating_expenses, total_operating_expenses, operating_income, interest_income,
            interest_expense, other_income_expense, total_other_income_expense, income_before_income_taxes,
            income_taxes, consolidated_net_income_loss, net_income_loss_attributable_common_shareholders,
            noncontrolling_interest, discontinued_operations, extraordinary_items, preferred_stock_dividends_declared,
            equity_in_affiliates, basic_earnings_per_share, basic_shares_outstanding, diluted_earnings_per_share,
            diluted_shares_outstanding, ebitda, depreciation_depletion_amortization
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING income_statements table...")
            cur.execute("TRUNCATE TABLE income_statements RESTART IDENTITY CASCADE;")

            # Fetch and insert income statements
            logger.info(f"Fetching income statements for {len(tickers_data)} tickers...")
            processed = 0
            unique_statements = {}  # Dictionary to deduplicate by (cik, period_end, timeframe)

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                income_statements = fetch_income_statements(ticker)

                if income_statements:
                    for inc in income_statements:
                        # Parse dates
                        period_end = None
                        filing_date = None

                        if inc.get("period_end"):
                            try:
                                period_end = datetime.strptime(inc["period_end"], "%Y-%m-%d").date()
                            except:
                                pass

                        if inc.get("filing_date"):
                            try:
                                filing_date = datetime.strptime(
                                    inc["filing_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if period_end and period_end < from_date:
                            continue

                        # Create unique key
                        cik = inc.get("cik")
                        timeframe = inc.get("timeframe")
                        if cik and period_end and timeframe:
                            key = (cik, period_end, timeframe)

                            # Store unique income statement (later entries overwrite earlier ones)
                            values = (
                                cik,
                                period_end,
                                timeframe,
                                filing_date,
                                inc.get("fiscal_quarter"),
                                inc.get("fiscal_year"),
                                inc.get("tickers"),
                                inc.get("revenue"),
                                inc.get("cost_of_revenue"),
                                inc.get("gross_profit"),
                                inc.get("research_development"),
                                inc.get("selling_general_administrative"),
                                inc.get("other_operating_expenses"),
                                inc.get("total_operating_expenses"),
                                inc.get("operating_income"),
                                inc.get("interest_income"),
                                inc.get("interest_expense"),
                                inc.get("other_income_expense"),
                                inc.get("total_other_income_expense"),
                                inc.get("income_before_income_taxes"),
                                inc.get("income_taxes"),
                                inc.get("consolidated_net_income_loss"),
                                inc.get("net_income_loss_attributable_common_shareholders"),
                                inc.get("noncontrolling_interest"),
                                inc.get("discontinued_operations"),
                                inc.get("extraordinary_items"),
                                inc.get("preferred_stock_dividends_declared"),
                                inc.get("equity_in_affiliates"),
                                inc.get("basic_earnings_per_share"),
                                inc.get("basic_shares_outstanding"),
                                inc.get("diluted_earnings_per_share"),
                                inc.get("diluted_shares_outstanding"),
                                inc.get("ebitda"),
                                inc.get("depreciation_depletion_amortization"),
                            )
                            unique_statements[key] = values

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_statements):,} unique income statements collected"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique income statements in batches
            logger.info(f"Inserting {len(unique_statements):,} unique income statements...")
            batch = []
            batch_size = 1000
            total_statements_inserted = 0

            for values in unique_statements.values():
                batch.append(values)
                total_statements_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_statements_inserted:,} income statements inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_statements,
                    COUNT(DISTINCT cik) as unique_ciks,
                    MIN(period_end) as earliest_date,
                    MAX(period_end) as latest_date
                FROM income_statements;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total income statements: {stats[0]:,}")
            logger.info(f"  Unique CIKs: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, revenue
                FROM income_statements
                WHERE period_end = (SELECT MAX(period_end) FROM income_statements)
                ORDER BY revenue DESC NULLS LAST
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by revenue on latest period:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, revenue = row
                rev_b = revenue / 1_000_000_000 if revenue else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Revenue: ${rev_b:,.1f}B"
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
        logger.info("\nBackfill complete: Income statements table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
