#!/usr/bin/env python3
"""
Create dividends table
Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/dividends
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create dividends table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS dividends (
            id VARCHAR(100) PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            cash_amount NUMERIC(20,4),
            currency VARCHAR(10),
            declaration_date DATE,
            dividend_type VARCHAR(10),
            ex_dividend_date DATE,
            frequency INTEGER,
            pay_date DATE,
            record_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_dividends_ticker ON dividends(ticker);
        CREATE INDEX IF NOT EXISTS idx_dividends_ex_dividend_date ON dividends(ex_dividend_date);
        CREATE INDEX IF NOT EXISTS idx_dividends_pay_date ON dividends(pay_date);

        COMMENT ON TABLE dividends IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/dividends';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Dividends table created successfully")


if __name__ == "__main__":
    create_table()
