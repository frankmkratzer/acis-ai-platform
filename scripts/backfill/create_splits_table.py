#!/usr/bin/env python3
"""
Create splits table
Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/splits
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create splits table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS splits (
            id VARCHAR(100) PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            execution_date DATE,
            split_from NUMERIC(20,4),
            split_to NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_splits_ticker ON splits(ticker);
        CREATE INDEX IF NOT EXISTS idx_splits_execution_date ON splits(execution_date);

        COMMENT ON TABLE splits IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/splits';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Splits table created successfully")


if __name__ == "__main__":
    create_table()
