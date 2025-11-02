#!/usr/bin/env python3
"""
Backfill cash_flow_statements table from Polygon.io API
Fetches historical cash flow statement data from list_date to present
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
API_URL = "https://api.polygon.io/stocks/financials/v1/cash-flow-statements"


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


def fetch_cash_flow_statements(ticker):
    """Fetch cash flow statements for a ticker (both quarterly and annual)"""
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
                logger.debug(f"No {timeframe} cash flow statements for {ticker}")
            else:
                logger.error(f"HTTP error for {ticker} ({timeframe}): {e}")
        except Exception as e:
            logger.error(f"Error fetching {timeframe} cash flow statements for {ticker}: {e}")

    return all_results


def populate_table(tickers_data):
    """Fetch and insert cash flow statements for all tickers (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO cash_flow_statements (
            cik, period_end, timeframe, filing_date, fiscal_quarter, fiscal_year, tickers,
            cash_from_operating_activities_continuing_operations, net_cash_from_operating_activities,
            net_cash_from_operating_activities_discontinued_operations, change_in_other_operating_assets_and_liabilities_net,
            other_operating_activities, net_cash_from_investing_activities, net_cash_from_investing_activities_continuing_operations,
            net_cash_from_investing_activities_discontinued_operations, purchase_of_property_plant_and_equipment,
            sale_of_property_plant_and_equipment, other_investing_activities, net_cash_from_financing_activities,
            net_cash_from_financing_activities_continuing_operations, net_cash_from_financing_activities_discontinued_operations,
            dividends, long_term_debt_issuances_repayments, short_term_debt_issuances_repayments,
            other_financing_activities, net_income, depreciation_depletion_and_amortization,
            change_in_cash_and_equivalents, effect_of_currency_exchange_rate, income_loss_from_discontinued_operations,
            noncontrolling_interests, other_cash_adjustments
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (cik, period_end, timeframe) DO UPDATE SET
            filing_date = EXCLUDED.filing_date,
            fiscal_quarter = EXCLUDED.fiscal_quarter,
            fiscal_year = EXCLUDED.fiscal_year,
            tickers = EXCLUDED.tickers,
            cash_from_operating_activities_continuing_operations = EXCLUDED.cash_from_operating_activities_continuing_operations,
            net_cash_from_operating_activities = EXCLUDED.net_cash_from_operating_activities,
            net_cash_from_operating_activities_discontinued_operations = EXCLUDED.net_cash_from_operating_activities_discontinued_operations,
            change_in_other_operating_assets_and_liabilities_net = EXCLUDED.change_in_other_operating_assets_and_liabilities_net,
            other_operating_activities = EXCLUDED.other_operating_activities,
            net_cash_from_investing_activities = EXCLUDED.net_cash_from_investing_activities,
            net_cash_from_investing_activities_continuing_operations = EXCLUDED.net_cash_from_investing_activities_continuing_operations,
            net_cash_from_investing_activities_discontinued_operations = EXCLUDED.net_cash_from_investing_activities_discontinued_operations,
            purchase_of_property_plant_and_equipment = EXCLUDED.purchase_of_property_plant_and_equipment,
            sale_of_property_plant_and_equipment = EXCLUDED.sale_of_property_plant_and_equipment,
            other_investing_activities = EXCLUDED.other_investing_activities,
            net_cash_from_financing_activities = EXCLUDED.net_cash_from_financing_activities,
            net_cash_from_financing_activities_continuing_operations = EXCLUDED.net_cash_from_financing_activities_continuing_operations,
            net_cash_from_financing_activities_discontinued_operations = EXCLUDED.net_cash_from_financing_activities_discontinued_operations,
            dividends = EXCLUDED.dividends,
            long_term_debt_issuances_repayments = EXCLUDED.long_term_debt_issuances_repayments,
            short_term_debt_issuances_repayments = EXCLUDED.short_term_debt_issuances_repayments,
            other_financing_activities = EXCLUDED.other_financing_activities,
            net_income = EXCLUDED.net_income,
            depreciation_depletion_and_amortization = EXCLUDED.depreciation_depletion_and_amortization,
            change_in_cash_and_equivalents = EXCLUDED.change_in_cash_and_equivalents,
            effect_of_currency_exchange_rate = EXCLUDED.effect_of_currency_exchange_rate,
            income_loss_from_discontinued_operations = EXCLUDED.income_loss_from_discontinued_operations,
            noncontrolling_interests = EXCLUDED.noncontrolling_interests,
            other_cash_adjustments = EXCLUDED.other_cash_adjustments;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING cash_flow_statements table...")
            cur.execute("TRUNCATE TABLE cash_flow_statements RESTART IDENTITY CASCADE;")

            # Fetch and insert cash flow statements
            logger.info(f"Fetching cash flow statements for {len(tickers_data)} tickers...")
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

                cash_flow_statements = fetch_cash_flow_statements(ticker)

                if cash_flow_statements:
                    for cfs in cash_flow_statements:
                        # Parse dates
                        period_end = None
                        filing_date = None

                        if cfs.get("period_end"):
                            try:
                                period_end = datetime.strptime(cfs["period_end"], "%Y-%m-%d").date()
                            except:
                                pass

                        if cfs.get("filing_date"):
                            try:
                                filing_date = datetime.strptime(
                                    cfs["filing_date"], "%Y-%m-%d"
                                ).date()
                            except:
                                pass

                        # Filter by list_date
                        if period_end and period_end < from_date:
                            continue

                        # Create unique key
                        cik = cfs.get("cik")
                        timeframe = cfs.get("timeframe")
                        if cik and period_end and timeframe:
                            key = (cik, period_end, timeframe)

                            # Store unique cash flow statement (later entries overwrite earlier ones)
                            values = (
                                cik,
                                period_end,
                                timeframe,
                                filing_date,
                                cfs.get("fiscal_quarter"),
                                cfs.get("fiscal_year"),
                                cfs.get("tickers"),
                                cfs.get("cash_from_operating_activities_continuing_operations"),
                                cfs.get("net_cash_from_operating_activities"),
                                cfs.get(
                                    "net_cash_from_operating_activities_discontinued_operations"
                                ),
                                cfs.get("change_in_other_operating_assets_and_liabilities_net"),
                                cfs.get("other_operating_activities"),
                                cfs.get("net_cash_from_investing_activities"),
                                cfs.get("net_cash_from_investing_activities_continuing_operations"),
                                cfs.get(
                                    "net_cash_from_investing_activities_discontinued_operations"
                                ),
                                cfs.get("purchase_of_property_plant_and_equipment"),
                                cfs.get("sale_of_property_plant_and_equipment"),
                                cfs.get("other_investing_activities"),
                                cfs.get("net_cash_from_financing_activities"),
                                cfs.get("net_cash_from_financing_activities_continuing_operations"),
                                cfs.get(
                                    "net_cash_from_financing_activities_discontinued_operations"
                                ),
                                cfs.get("dividends"),
                                cfs.get("long_term_debt_issuances_repayments"),
                                cfs.get("short_term_debt_issuances_repayments"),
                                cfs.get("other_financing_activities"),
                                cfs.get("net_income"),
                                cfs.get("depreciation_depletion_and_amortization"),
                                cfs.get("change_in_cash_and_equivalents"),
                                cfs.get("effect_of_currency_exchange_rate"),
                                cfs.get("income_loss_from_discontinued_operations"),
                                cfs.get("noncontrolling_interests"),
                                cfs.get("other_cash_adjustments"),
                            )
                            unique_statements[key] = values

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {len(unique_statements):,} unique cash flow statements collected"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Insert all unique cash flow statements in batches
            logger.info(f"Inserting {len(unique_statements):,} unique cash flow statements...")
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
                f"Final: {processed} tickers processed, {total_statements_inserted:,} cash flow statements inserted"
            )

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_statements,
                    COUNT(DISTINCT cik) as unique_ciks,
                    MIN(period_end) as earliest_date,
                    MAX(period_end) as latest_date
                FROM cash_flow_statements;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total cash flow statements: {stats[0]:,}")
            logger.info(f"  Unique CIKs: {stats[1]}")
            logger.info(f"  Date range: {stats[2]} to {stats[3]}")

            # Sample recent data
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, net_cash_from_operating_activities
                FROM cash_flow_statements
                WHERE period_end = (SELECT MAX(period_end) FROM cash_flow_statements)
                ORDER BY net_cash_from_operating_activities DESC NULLS LAST
                LIMIT 5;
            """
            )
            logger.info(f"\nTop 5 by operating cash flow on latest period:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, operating_cf = row
                cf_b = operating_cf / 1_000_000_000 if operating_cf else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Op Cash Flow: ${cf_b:,.1f}B"
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
        logger.info("\nBackfill complete: Cash flow statements table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
