#!/usr/bin/env python3
"""
Create ticker_events table for ticker symbol changes and corporate events
Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/ticker-events
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create ticker_events table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS ticker_events (
            ticker VARCHAR(20) NOT NULL,
            event_date DATE NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            new_ticker VARCHAR(20),
            company_name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, event_date, event_type)
        );

        CREATE INDEX IF NOT EXISTS idx_ticker_events_ticker ON ticker_events(ticker);
        CREATE INDEX IF NOT EXISTS idx_ticker_events_date ON ticker_events(event_date);
        CREATE INDEX IF NOT EXISTS idx_ticker_events_type ON ticker_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_ticker_events_new_ticker ON ticker_events(new_ticker);

        COMMENT ON TABLE ticker_events IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/corporate-actions/ticker-events';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("Ticker events table created successfully")


if __name__ == "__main__":
    create_table()
