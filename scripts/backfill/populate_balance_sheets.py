#!/usr/bin/env python3
"""
Backfill balance_sheets table from Polygon.io API
Fetches historical balance sheet data from list_date to present
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
API_URL = "https://api.polygon.io/stocks/financials/v1/balance-sheets"


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


def fetch_balance_sheets(ticker):
    """Fetch balance sheets for a ticker (both quarterly and annual)"""
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
                logger.debug(f"No {timeframe} balance sheets for {ticker}")
            else:
                logger.error(f"HTTP error for {ticker} ({timeframe}): {e}")
        except Exception as e:
            logger.error(f"Error fetching {timeframe} balance sheets for {ticker}: {e}")

    return all_results


def populate_table(tickers_data):
    """Fetch and insert balance sheets for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO balance_sheets (
            cik, period_end, timeframe, filing_date, fiscal_quarter, fiscal_year, tickers,
            accounts_payable, accrued_and_other_current_liabilities, accumulated_other_comprehensive_income,
            additional_paid_in_capital, cash_and_equivalents, commitments_and_contingencies, common_stock,
            debt_current, deferred_revenue_current, goodwill, intangible_assets_net, inventories,
            long_term_debt_and_capital_lease_obligations, noncontrolling_interest, other_assets,
            other_current_assets, other_equity, other_noncurrent_liabilities, preferred_stock,
            property_plant_equipment_net, receivables, retained_earnings_deficit, short_term_investments,
            total_assets, total_current_assets, total_current_liabilities, total_equity,
            total_equity_attributable_to_parent, total_liabilities, total_liabilities_and_equity, treasury_stock
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (cik, period_end, timeframe) DO UPDATE SET
            filing_date = EXCLUDED.filing_date,
            fiscal_quarter = EXCLUDED.fiscal_quarter,
            fiscal_year = EXCLUDED.fiscal_year,
            tickers = EXCLUDED.tickers,
            accounts_payable = EXCLUDED.accounts_payable,
            accrued_and_other_current_liabilities = EXCLUDED.accrued_and_other_current_liabilities,
            accumulated_other_comprehensive_income = EXCLUDED.accumulated_other_comprehensive_income,
            additional_paid_in_capital = EXCLUDED.additional_paid_in_capital,
            cash_and_equivalents = EXCLUDED.cash_and_equivalents,
            commitments_and_contingencies = EXCLUDED.commitments_and_contingencies,
            common_stock = EXCLUDED.common_stock,
            debt_current = EXCLUDED.debt_current,
            deferred_revenue_current = EXCLUDED.deferred_revenue_current,
            goodwill = EXCLUDED.goodwill,
            intangible_assets_net = EXCLUDED.intangible_assets_net,
            inventories = EXCLUDED.inventories,
            long_term_debt_and_capital_lease_obligations = EXCLUDED.long_term_debt_and_capital_lease_obligations,
            noncontrolling_interest = EXCLUDED.noncontrolling_interest,
            other_assets = EXCLUDED.other_assets,
            other_current_assets = EXCLUDED.other_current_assets,
            other_equity = EXCLUDED.other_equity,
            other_noncurrent_liabilities = EXCLUDED.other_noncurrent_liabilities,
            preferred_stock = EXCLUDED.preferred_stock,
            property_plant_equipment_net = EXCLUDED.property_plant_equipment_net,
            receivables = EXCLUDED.receivables,
            retained_earnings_deficit = EXCLUDED.retained_earnings_deficit,
            short_term_investments = EXCLUDED.short_term_investments,
            total_assets = EXCLUDED.total_assets,
            total_current_assets = EXCLUDED.total_current_assets,
            total_current_liabilities = EXCLUDED.total_current_liabilities,
            total_equity = EXCLUDED.total_equity,
            total_equity_attributable_to_parent = EXCLUDED.total_equity_attributable_to_parent,
            total_liabilities = EXCLUDED.total_liabilities,
            total_liabilities_and_equity = EXCLUDED.total_liabilities_and_equity,
            treasury_stock = EXCLUDED.treasury_stock;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING balance_sheets table...")
            cur.execute("TRUNCATE TABLE balance_sheets RESTART IDENTITY CASCADE;")

            # Fetch and insert balance sheets
            logger.info(f"Fetching balance sheets for {len(tickers_data)} tickers...")
            processed = 0
            unique_sheets = {}  # Dictionary to deduplicate by (cik, period_end, timeframe)

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                # Use list_date or default to 20 years ago
                from_date = list_date if list_date else (today - timedelta(days=20 * 365))

                # Don't fetch data for future dates
                if from_date > today:
                    logger.warning(f"{ticker}: list_date {from_date} is in future, skipping")
                    processed += 1
                    continue

                balance_sheets = fetch_balance_sheets(ticker)

                if balance_sheets:
                    for bs in balance_sheets:
                        # Parse dates
                        period_end = None
                        filing_date = None

                        if bs.get("period_end"):
                            try:
                                period_end = datetime.strptime(bs["period_end"], "%Y-%m-%d").date()
                            except:
                                pass

                        if bs.get("filing_date"):
                            try:
                                filing_date = datetime.strptime(
                                    bs["filing_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if period_end and period_end < from_date:
                            continue

                        # Create unique key
                        cik = bs.get("cik")
                        timeframe = bs.get("timeframe")
                        if cik and period_end and timeframe:
                            key = (cik, period_end, timeframe)

                            # Store unique balance sheet (later entries overwrite earlier ones)
                            values = (
                                cik,
                                period_end,
                                timeframe,
                                filing_date,
                                bs.get("fiscal_quarter"),
                                bs.get("fiscal_year"),
                                bs.get("tickers"),
                                bs.get("accounts_payable"),
                                bs.get("accrued_and_other_current_liabilities"),
                                bs.get("accumulated_other_comprehensive_income"),
                                bs.get("additional_paid_in_capital"),
                                bs.get("cash_and_equivalents"),
                                bs.get("commitments_and_contingencies"),
                                bs.get("common_stock"),
                                bs.get("debt_current"),
                                bs.get("deferred_revenue_current"),
                                bs.get("goodwill"),
                                bs.get("intangible_assets_net"),
                                bs.get("inventories"),
                                bs.get("long_term_debt_and_capital_lease_obligations"),
                                bs.get("noncontrolling_interest"),
                                bs.get("other_assets"),
                                bs.get("other_current_assets"),
                                bs.get("other_equity"),
                                bs.get("other_noncurrent_liabilities"),
                                bs.get("preferred_stock"),
                                bs.get("property_plant_equipment_net"),
                                bs.get("receivables"),
                                bs.get("retained_earnings_deficit"),
                                bs.get("short_term_investments"),
                                bs.get("total_assets"),
                                bs.get("total_current_assets"),
                                bs.get("total_current_liabilities"),
                                bs.get("total_equity"),
                                bs.get("total_equity_attributable_to_parent"),
                                bs.get("total_liabilities"),
                                bs.get("total_liabilities_and_equity"),
                                bs.get("treasury_stock"),
                            )
                            unique_sheets[key] = values

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_sheets):,} unique balance sheets collected"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique balance sheets in batches
            logger.info(f"Inserting {len(unique_sheets):,} unique balance sheets...")
            batch = []
            batch_size = 1000
            total_sheets_inserted = 0

            for values in unique_sheets.values():
                batch.append(values)
                total_sheets_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(
                f"Final: {processed} tickers processed, {total_sheets_inserted:,} balance sheets inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_sheets,
                    COUNT(DISTINCT cik) as unique_ciks,
                    MIN(period_end) as earliest_date,
                    MAX(period_end) as latest_date
                FROM balance_sheets;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total balance sheets: {stats[0]:,}")
            logger.info(f"  Unique CIKs: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, total_assets
                FROM balance_sheets
                WHERE period_end = (SELECT MAX(period_end) FROM balance_sheets)
                ORDER BY total_assets DESC NULLS LAST
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by total assets on latest period:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, total_assets = row
                assets_b = total_assets / 1_000_000_000 if total_assets else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Assets: ${assets_b:,.1f}B"
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
        logger.info("\nBackfill complete: Balance sheets table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
