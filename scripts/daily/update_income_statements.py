#!/usr/bin/env python3
"""
Daily update for income_statements table from Polygon.io API
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
API_URL = "https://api.polygon.io/stocks/financials/v1/income-statements"


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


def fetch_income_statements(ticker, limit=4):
    """Fetch recent income statements for a ticker (both quarterly and annual)"""
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
                logger.debug(f"No {timeframe} income statements for {ticker}")
            else:
                logger.error(f"HTTP error for {ticker} ({timeframe}): {e}")
        except Exception as e:
            logger.error(f"Error fetching {timeframe} income statements for {ticker}: {e}")

    return all_results


def upsert_income_statements(tickers_data):
    """Fetch and upsert income statements (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO income_statements (
            cik, period_end, timeframe, filing_date, fiscal_quarter, fiscal_year, tickers,
            revenue, cost_of_revenue, gross_profit, research_development, selling_general_administrative,
            other_operating_expenses, total_operating_expenses, operating_income, interest_income,
            interest_expense, other_income_expense, total_other_income_expense, income_before_income_taxes,
            income_taxes, consolidated_net_income_loss, net_income_loss_attributable_common_shareholders,
            noncontrolling_interest, discontinued_operations, extraordinary_items, preferred_stock_dividends_declared,
            equity_in_affiliates, basic_earnings_per_share, basic_shares_outstanding, diluted_earnings_per_share,
            diluted_shares_outstanding, ebitda, depreciation_depletion_amortization, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (cik, period_end, timeframe) DO UPDATE SET
            filing_date = EXCLUDED.filing_date,
            fiscal_quarter = EXCLUDED.fiscal_quarter,
            fiscal_year = EXCLUDED.fiscal_year,
            tickers = EXCLUDED.tickers,
            revenue = EXCLUDED.revenue,
            cost_of_revenue = EXCLUDED.cost_of_revenue,
            gross_profit = EXCLUDED.gross_profit,
            research_development = EXCLUDED.research_development,
            selling_general_administrative = EXCLUDED.selling_general_administrative,
            other_operating_expenses = EXCLUDED.other_operating_expenses,
            total_operating_expenses = EXCLUDED.total_operating_expenses,
            operating_income = EXCLUDED.operating_income,
            interest_income = EXCLUDED.interest_income,
            interest_expense = EXCLUDED.interest_expense,
            other_income_expense = EXCLUDED.other_income_expense,
            total_other_income_expense = EXCLUDED.total_other_income_expense,
            income_before_income_taxes = EXCLUDED.income_before_income_taxes,
            income_taxes = EXCLUDED.income_taxes,
            consolidated_net_income_loss = EXCLUDED.consolidated_net_income_loss,
            net_income_loss_attributable_common_shareholders = EXCLUDED.net_income_loss_attributable_common_shareholders,
            noncontrolling_interest = EXCLUDED.noncontrolling_interest,
            discontinued_operations = EXCLUDED.discontinued_operations,
            extraordinary_items = EXCLUDED.extraordinary_items,
            preferred_stock_dividends_declared = EXCLUDED.preferred_stock_dividends_declared,
            equity_in_affiliates = EXCLUDED.equity_in_affiliates,
            basic_earnings_per_share = EXCLUDED.basic_earnings_per_share,
            basic_shares_outstanding = EXCLUDED.basic_shares_outstanding,
            diluted_earnings_per_share = EXCLUDED.diluted_earnings_per_share,
            diluted_shares_outstanding = EXCLUDED.diluted_shares_outstanding,
            ebitda = EXCLUDED.ebitda,
            depreciation_depletion_amortization = EXCLUDED.depreciation_depletion_amortization,
            updated_at = CURRENT_TIMESTAMP;
    """

    today = date.today()

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM income_statements;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert income statements
            logger.info(
                f"Upserting income statements for {len(tickers_data)} tickers (last 4 quarters)..."
            )
            processed = 0
            total_statements_upserted = 0
            batch = []
            batch_size = 1000

            for i, (ticker, list_date) in enumerate(tickers_data, 1):
                income_statements = fetch_income_statements(ticker, limit=4)

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
                        if list_date and period_end and period_end < list_date:
                            continue

                        values = (
                            inc.get("cik"),
                            period_end,
                            inc.get("timeframe"),
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
                        f"  Progress: {processed}/{len(tickers_data)} tickers, {total_statements_upserted:,} income statements upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM income_statements;")
            count_after = cur.fetchone()[0]

            new_statements = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Income statements before: {count_before:,}")
            logger.info(f"  Income statements after:  {count_after:,}")
            logger.info(f"  New statements:            {new_statements:,}")
            logger.info(
                f"  Updated:                   {total_statements_upserted - new_statements:,}"
            )

            # Show recently updated
            cur.execute(
                """
                SELECT cik, tickers[1], period_end, timeframe, revenue, updated_at
                FROM income_statements
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY period_end DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated income statements:")
            for row in cur.fetchall():
                cik, ticker, period_end, timeframe, revenue, updated = row
                rev_b = revenue / 1_000_000_000 if revenue else 0
                logger.info(
                    f"  {ticker:8} ({cik}) {period_end} {timeframe:10} Revenue: ${rev_b:,.1f}B"
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

        upsert_income_statements(tickers)
        logger.info("\nDaily update complete: Income statements updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
