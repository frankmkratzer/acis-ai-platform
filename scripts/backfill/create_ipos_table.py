#!/usr/bin/env python3
"""
Create ipos table for IPO events
Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/ipos
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create ipos table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS ipos (
            ticker VARCHAR(20) NOT NULL,
            issuer_name VARCHAR(255),
            isin VARCHAR(20),
            listing_date DATE,
            ipo_status VARCHAR(50),
            final_issue_price NUMERIC(20,4),
            lowest_offer_price NUMERIC(20,4),
            highest_offer_price NUMERIC(20,4),
            min_shares_offered BIGINT,
            max_shares_offered BIGINT,
            total_offer_size NUMERIC(20,2),
            announced_date DATE,
            last_updated TIMESTAMP,
            primary_exchange VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, listing_date)
        );

        CREATE INDEX IF NOT EXISTS idx_ipos_ticker ON ipos(ticker);
        CREATE INDEX IF NOT EXISTS idx_ipos_listing_date ON ipos(listing_date);
        CREATE INDEX IF NOT EXISTS idx_ipos_status ON ipos(ipo_status);

        COMMENT ON TABLE ipos IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/ipos';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("IPOs table created successfully")


if __name__ == "__main__":
    create_table()
