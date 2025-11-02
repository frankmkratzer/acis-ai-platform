#!/usr/bin/env python3
"""
Daily update for cash_flow_statements table from Polygon.io API
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
API_URL = "https://api.polygon.io/stocks/financials/v1/cash-flow-statements"


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


def fetch_cash_flow_statements(ticker, limit=4):
    """Fetch recent cash flow statements for a ticker (both quarterly and annual)"""
    all_results = []

    for timeframe in ["quarterly", "annual"]:
        params = {
            "tickers": ticker,
            "timeframe": timeframe,
            "limit": limit,
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


def upsert_cash_flow_statements(tickers_data):
    """Fetch and upsert cash flow statements (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
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
            noncontrolling_interests, other_cash_adjustments, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
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
            other_cash_adjustments = EXCLUDED.other_cash_adjustments,
            updated_at = CURRENT_TIMESTAMP;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM cash_flow_statements;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert cash flow statements
            logger.info(
                f"Upserting cash flow statements for {len(tickers_data)} tickers (last 4 quarters)..."
            )
            processed = 0
            total_statements_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                cash_flow_statements = fetch_cash_flow_statements(ticker, limit=4)

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
                        if list_date and period_end and period_end < list_date:
                            continue

                        values = (
                            cfs.get("cik"),
                            period_end,
                            cfs.get("timeframe"),
                            filing_date,
                            cfs.get("fiscal_quarter"),
                            cfs.get("fiscal_year"),
                            cfs.get("tickers"),
                            cfs.get("cash_from_operating_activities_continuing_operations"),
                            cfs.get("net_cash_from_operating_activities"),
                            cfs.get("net_cash_from_operating_activities_discontinued_operations"),
                            cfs.get("change_in_other_operating_assets_and_liabilities_net"),
                            cfs.get("other_operating_activities"),
                            cfs.get("net_cash_from_investing_activities"),
                            cfs.get("net_cash_from_investing_activities_continuing_operations"),
                            cfs.get("net_cash_from_investing_activities_discontinued_operations"),
                            cfs.get("purchase_of_property_plant_and_equipment"),
                            cfs.get("sale_of_property_plant_and_equipment"),
                            cfs.get("other_investing_activities"),
                            cfs.get("net_cash_from_financing_activities"),
                            cfs.get("net_cash_from_financing_activities_continuing_operations"),
                            cfs.get("net_cash_from_financing_activities_discontinued_operations"),
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
                        batch.append(values)
                        total_statements_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_statements_upserted:,} cash flow statements upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM cash_flow_statements;")
            count_after = cur.fetchone()[0]

            new_statements = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Cash flow statements before: {count_before:,}")
            logger.info(f"  Cash flow statements after:  {count_after:,}")
            logger.info(f"  New statements:                {new_statements:,}")
            logger.info(
                f"  Updated:                       {total_statements_upserted - new_statements:,}"
            )

            # Show recently updated
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, net_cash_from_operating_activities, updated_at
                FROM cash_flow_statements
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY period_end DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated cash flow statements:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, operating_cf, updated = row
                cf_b = operating_cf / 1_000_000_000 if operating_cf else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Op CF: ${cf_b:,.1f}B"
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

        upsert_cash_flow_statements(tickers)
        logger.info("\nDaily update complete: Cash flow statements updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
