#!/usr/bin/env python3
"""
Create news table for stock news articles with sentiment analysis
Source: https://polygon.io/docs/api/llms/rest/stocks/news
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


def create_table():
    """Create news table"""
    create_sql = """
        CREATE TABLE IF NOT EXISTS news (
            article_id VARCHAR(255) PRIMARY KEY,
            title TEXT,
            author VARCHAR(255),
            published_utc TIMESTAMP,
            article_url TEXT,
            image_url TEXT,
            description TEXT,
            tickers TEXT[],
            publisher_name VARCHAR(255),
            publisher_homepage_url TEXT,
            publisher_logo_url TEXT,
            keywords TEXT[],
            sentiment VARCHAR(20),
            sentiment_reasoning TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_utc DESC);
        CREATE INDEX IF NOT EXISTS idx_news_tickers ON news USING GIN(tickers);
        CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news(sentiment);
        CREATE INDEX IF NOT EXISTS idx_news_publisher ON news(publisher_name);

        COMMENT ON TABLE news IS 'Source: https://polygon.io/docs/api/llms/rest/stocks/news';
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            logger.info("News table created successfully")


if __name__ == "__main__":
    create_table()
