#!/usr/bin/env python3
"""
Create ratios table
Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/ratios
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create ratios table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS ratios (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            cik VARCHAR(20),
            price NUMERIC(20,4),
            market_cap NUMERIC(20,4),
            enterprise_value NUMERIC(20,4),
            average_volume NUMERIC(20,4),
            price_to_earnings NUMERIC(20,4),
            price_to_book NUMERIC(20,4),
            price_to_sales NUMERIC(20,4),
            price_to_cash_flow NUMERIC(20,4),
            price_to_free_cash_flow NUMERIC(20,4),
            ev_to_sales NUMERIC(20,4),
            ev_to_ebitda NUMERIC(20,4),
            earnings_per_share NUMERIC(20,4),
            return_on_assets NUMERIC(20,4),
            return_on_equity NUMERIC(20,4),
            dividend_yield NUMERIC(20,4),
            current NUMERIC(20,4),
            quick NUMERIC(20,4),
            cash NUMERIC(20,4),
            debt_to_equity NUMERIC(20,4),
            free_cash_flow NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date)
        );

        CREATE INDEX IF NOT EXISTS idx_ratios_ticker ON ratios(ticker);
        CREATE INDEX IF NOT EXISTS idx_ratios_date ON ratios(date);
        CREATE INDEX IF NOT EXISTS idx_ratios_cik ON ratios(cik);

        COMMENT ON TABLE ratios IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/ratios';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Ratios table created successfully")


if __name__ == "__main__":
    create_table()
