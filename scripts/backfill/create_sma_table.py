#!/usr/bin/env python3
"""
Create sma table for Simple Moving Average technical indicator
Source: https://polygon.io/docs/api/llms/rest/stocks/technical-indicators/simple-moving-average
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create sma table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS sma (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            window_size INTEGER NOT NULL,
            series_type VARCHAR(20) DEFAULT 'close',
            timespan VARCHAR(20) DEFAULT 'day',
            value NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date, window_size, series_type, timespan)
        );

        CREATE INDEX IF NOT EXISTS idx_sma_ticker ON sma(ticker);
        CREATE INDEX IF NOT EXISTS idx_sma_date ON sma(date);
        CREATE INDEX IF NOT EXISTS idx_sma_window_size ON sma(window_size);
        CREATE INDEX IF NOT EXISTS idx_sma_ticker_date ON sma(ticker, date);

        COMMENT ON TABLE sma IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/technical-indicators/simple-moving-average';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("SMA table created successfully")


if __name__ == "__main__":
    create_table()
