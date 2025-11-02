#!/usr/bin/env python3
"""
Create short_interest table
Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/short-interest
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create short_interest table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS short_interest (
            ticker VARCHAR(20) NOT NULL,
            settlement_date DATE NOT NULL,
            short_interest BIGINT,
            avg_daily_volume BIGINT,
            days_to_cover NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, settlement_date)
        );

        CREATE INDEX IF NOT EXISTS idx_short_interest_ticker ON short_interest(ticker);
        CREATE INDEX IF NOT EXISTS idx_short_interest_settlement_date ON short_interest(settlement_date);
        CREATE INDEX IF NOT EXISTS idx_short_interest_days_to_cover ON short_interest(days_to_cover);

        COMMENT ON TABLE short_interest IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/fundamentals/short-interest';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Short interest table created successfully")


if __name__ == "__main__":
    create_table()
