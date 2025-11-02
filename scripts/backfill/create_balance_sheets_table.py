#!/usr/bin/env python3
"""
Create balance_sheets table
Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/balance-sheets
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create balance_sheets table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS balance_sheets (
            cik VARCHAR(20) NOT NULL,
            period_end DATE NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            filing_date DATE,
            fiscal_quarter INTEGER,
            fiscal_year INTEGER,
            tickers TEXT[],
            accounts_payable NUMERIC(20,4),
            accrued_and_other_current_liabilities NUMERIC(20,4),
            accumulated_other_comprehensive_income NUMERIC(20,4),
            additional_paid_in_capital NUMERIC(20,4),
            cash_and_equivalents NUMERIC(20,4),
            commitments_and_contingencies NUMERIC(20,4),
            common_stock NUMERIC(20,4),
            debt_current NUMERIC(20,4),
            deferred_revenue_current NUMERIC(20,4),
            goodwill NUMERIC(20,4),
            intangible_assets_net NUMERIC(20,4),
            inventories NUMERIC(20,4),
            long_term_debt_and_capital_lease_obligations NUMERIC(20,4),
            noncontrolling_interest NUMERIC(20,4),
            other_assets NUMERIC(20,4),
            other_current_assets NUMERIC(20,4),
            other_equity NUMERIC(20,4),
            other_noncurrent_liabilities NUMERIC(20,4),
            preferred_stock NUMERIC(20,4),
            property_plant_equipment_net NUMERIC(20,4),
            receivables NUMERIC(20,4),
            retained_earnings_deficit NUMERIC(20,4),
            short_term_investments NUMERIC(20,4),
            total_assets NUMERIC(20,4),
            total_current_assets NUMERIC(20,4),
            total_current_liabilities NUMERIC(20,4),
            total_equity NUMERIC(20,4),
            total_equity_attributable_to_parent NUMERIC(20,4),
            total_liabilities NUMERIC(20,4),
            total_liabilities_and_equity NUMERIC(20,4),
            treasury_stock NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cik, period_end, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_balance_sheets_cik ON balance_sheets(cik);
        CREATE INDEX IF NOT EXISTS idx_balance_sheets_period_end ON balance_sheets(period_end);
        CREATE INDEX IF NOT EXISTS idx_balance_sheets_fiscal_year ON balance_sheets(fiscal_year);
        CREATE INDEX IF NOT EXISTS idx_balance_sheets_filing_date ON balance_sheets(filing_date);

        COMMENT ON TABLE balance_sheets IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/balance-sheets';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Balance sheets table created successfully")


if __name__ == "__main__":
    create_table()
