#!/usr/bin/env python3
"""
Create income_statements table
Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/income-statements
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create income_statements table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS income_statements (
            cik VARCHAR(20) NOT NULL,
            period_end DATE NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            filing_date DATE,
            fiscal_quarter INTEGER,
            fiscal_year INTEGER,
            tickers TEXT[],
            revenue NUMERIC(20,4),
            cost_of_revenue NUMERIC(20,4),
            gross_profit NUMERIC(20,4),
            research_development NUMERIC(20,4),
            selling_general_administrative NUMERIC(20,4),
            other_operating_expenses NUMERIC(20,4),
            total_operating_expenses NUMERIC(20,4),
            operating_income NUMERIC(20,4),
            interest_income NUMERIC(20,4),
            interest_expense NUMERIC(20,4),
            other_income_expense NUMERIC(20,4),
            total_other_income_expense NUMERIC(20,4),
            income_before_income_taxes NUMERIC(20,4),
            income_taxes NUMERIC(20,4),
            consolidated_net_income_loss NUMERIC(20,4),
            net_income_loss_attributable_common_shareholders NUMERIC(20,4),
            noncontrolling_interest NUMERIC(20,4),
            discontinued_operations NUMERIC(20,4),
            extraordinary_items NUMERIC(20,4),
            preferred_stock_dividends_declared NUMERIC(20,4),
            equity_in_affiliates NUMERIC(20,4),
            basic_earnings_per_share NUMERIC(20,4),
            basic_shares_outstanding NUMERIC(20,4),
            diluted_earnings_per_share NUMERIC(20,4),
            diluted_shares_outstanding NUMERIC(20,4),
            ebitda NUMERIC(20,4),
            depreciation_depletion_amortization NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cik, period_end, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_income_statements_cik ON income_statements(cik);
        CREATE INDEX IF NOT EXISTS idx_income_statements_period_end ON income_statements(period_end);
        CREATE INDEX IF NOT EXISTS idx_income_statements_fiscal_year ON income_statements(fiscal_year);
        CREATE INDEX IF NOT EXISTS idx_income_statements_filing_date ON income_statements(filing_date);

        COMMENT ON TABLE income_statements IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/income-statements';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Income statements table created successfully")


if __name__ == "__main__":
    create_table()
