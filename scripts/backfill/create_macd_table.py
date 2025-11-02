#!/usr/bin/env python3
"""
Create macd table for MACD (Moving Average Convergence Divergence) technical indicator
Source: https://polygon.io/docs/rest/stocks/technical-indicators/moving-average-convergence-divergence
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create macd table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS macd (
            ticker VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            short_window INTEGER NOT NULL,
            long_window INTEGER NOT NULL,
            signal_window INTEGER NOT NULL,
            series_type VARCHAR(20) DEFAULT 'close',
            timespan VARCHAR(20) DEFAULT 'day',
            macd_value NUMERIC(20,4),
            signal_value NUMERIC(20,4),
            histogram_value NUMERIC(20,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, date, short_window, long_window, signal_window, series_type, timespan)
        );

        CREATE INDEX IF NOT EXISTS idx_macd_ticker ON macd(ticker);
        CREATE INDEX IF NOT EXISTS idx_macd_date ON macd(date);
        CREATE INDEX IF NOT EXISTS idx_macd_ticker_date ON macd(ticker, date);

        COMMENT ON TABLE macd IS 'Source: https://polygon.io/docs/rest/stocks/technical-indicators/moving-average-convergence-divergence';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("MACD table created successfully")


if __name__ == "__main__":
    create_table()
