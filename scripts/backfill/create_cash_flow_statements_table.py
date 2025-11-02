#!/usr/bin/env python3
"""
Create cash_flow_statements table
Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/cash-flow-statements
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create cash_flow_statements table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS cash_flow_statements (
            cik VARCHAR(20) NOT NULL,
            period_end DATE NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            filing_date DATE,
            fiscal_quarter INTEGER,
            fiscal_year INTEGER,
            tickers TEXT[],
            cash_from_operating_activities_continuing_operations NUMERIC(20,4),
            net_cash_from_operating_activities NUMERIC(20,4),
            net_cash_from_operating_activities_discontinued_operations NUMERIC(20,4),
            change_in_other_operating_assets_and_liabilities_net NUMERIC(20,4),
            other_operating_activities NUMERIC(20,4),
            net_cash_from_investing_activities NUMERIC(20,4),
            net_cash_from_investing_activities_continuing_operations NUMERIC(20,4),
            net_cash_from_investing_activities_discontinued_operations NUMERIC(20,4),
            purchase_of_property_plant_and_equipment NUMERIC(20,4),
            sale_of_property_plant_and_equipment NUMERIC(20,4),
            other_investing_activities NUMERIC(20,4),
            net_cash_from_financing_activities NUMERIC(20,4),
            net_cash_from_financing_activities_continuing_operations NUMERIC(20,4),
            net_cash_from_financing_activities_discontinued_operations NUMERIC(20,4),
            dividends NUMERIC(20,4),
            long_term_debt_issuances_repayments NUMERIC(20,4),
            short_term_debt_issuances_repayments NUMERIC(20,4),
            other_financing_activities NUMERIC(20,4),
            net_income NUMERIC(20,4),
            depreciation_depletion_and_amortization NUMERIC(20,4),
            change_in_cash_and_equivalents NUMERIC(20,4),
            effect_of_currency_exchange_rate NUMERIC(20,4),
            income_loss_from_discontinued_operations NUMERIC(20,4),
            noncontrolling_interests NUMERIC(20,4),
            other_cash_adjustments NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (cik, period_end, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_cik ON cash_flow_statements(cik);
        CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_period_end ON cash_flow_statements(period_end);
        CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_fiscal_year ON cash_flow_statements(fiscal_year);
        CREATE INDEX IF NOT EXISTS idx_cash_flow_statements_filing_date ON cash_flow_statements(filing_date);

        COMMENT ON TABLE cash_flow_statements IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/cash-flow-statements';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Cash flow statements table created successfully")


if __name__ == "__main__":
    create_table()
