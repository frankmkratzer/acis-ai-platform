#!/usr/bin/env python3
"""
Daily update for balance_sheets table from Polygon.io API
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
API_URL = "https://api.polygon.io/stocks/financials/v1/balance-sheets"


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


def fetch_balance_sheets(ticker, limit=4):
    """Fetch recent balance sheets for a ticker (both quarterly and annual)"""
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
                logger.debug(f"No {timeframe} balance sheets for {ticker}")
            else:
                logger.error(f"HTTP error for {ticker} ({timeframe}): {e}")
        except Exception as e:
            logger.error(f"Error fetching {timeframe} balance sheets for {ticker}: {e}")

    return all_results


def upsert_balance_sheets(tickers_data):
    """Fetch and upsert balance sheets (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO balance_sheets (
            cik, period_end, timeframe, filing_date, fiscal_quarter, fiscal_year, tickers,
            accounts_payable, accrued_and_other_current_liabilities, accumulated_other_comprehensive_income,
            additional_paid_in_capital, cash_and_equivalents, commitments_and_contingencies, common_stock,
            debt_current, deferred_revenue_current, goodwill, intangible_assets_net, inventories,
            long_term_debt_and_capital_lease_obligations, noncontrolling_interest, other_assets,
            other_current_assets, other_equity, other_noncurrent_liabilities, preferred_stock,
            property_plant_equipment_net, receivables, retained_earnings_deficit, short_term_investments,
            total_assets, total_current_assets, total_current_liabilities, total_equity,
            total_equity_attributable_to_parent, total_liabilities, total_liabilities_and_equity, treasury_stock,
            updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            CURRENT_TIMESTAMP
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
            treasury_stock = EXCLUDED.treasury_stock,
            updated_at = CURRENT_TIMESTAMP;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM balance_sheets;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert balance sheets
            logger.info(
                f"Upserting balance sheets for {len(tickers_data)} tickers (last 4 quarters)..."
            )
            processed = 0
            total_sheets_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                balance_sheets = fetch_balance_sheets(ticker, limit=4)

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
                        if list_date and period_end and period_end < list_date:
                            continue

                        values = (
                            bs.get("cik"),
                            period_end,
                            bs.get("timeframe"),
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
                        batch.append(values)
                        total_sheets_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_sheets_upserted:,} balance sheets upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM balance_sheets;")
            count_after = cur.fetchone()[0]

            new_sheets = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Balance sheets before: {count_before:,}")
            logger.info(f"  Balance sheets after:  {count_after:,}")
            logger.info(f"  New balance sheets:    {new_sheets:,}")
            logger.info(f"  Updated:               {total_sheets_upserted - new_sheets:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, total_assets, updated_at
                FROM balance_sheets
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY period_end DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated balance sheets:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, total_assets, updated = row
                assets_b = total_assets / 1_000_000_000 if total_assets else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Assets: ${assets_b:,.1f}B"
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

        upsert_balance_sheets(tickers)
        logger.info("\nDaily update complete: Balance sheets updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
