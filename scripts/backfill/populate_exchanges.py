#!/usr/bin/env python3
"""
Populate exchanges table from Polygon.io API
"""
import os
import sys
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v3/reference/exchanges"


def fetch_exchanges():
    """Fetch exchanges from Polygon API"""
    params = {
        "apiKey": POLYGON_API_KEY,
        "asset_class": "stocks",  # Focus on stock exchanges
    }

    logger.info(f"Fetching exchanges from {API_URL}")
    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    logger.info(f"API Status: {data.get('status')}")
    logger.info(f"Total exchanges: {data.get('count', 0)}")

    return data.get("results", [])


def populate_table(exchanges):
    """Insert exchanges into database"""
    insert_sql = """
        INSERT INTO exchanges (
            exchange_id, acronym, asset_class, locale, mic,
            name, operating_mic, participant_id, type, url
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT DO NOTHING;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Clear existing data
            logger.info("Clearing existing exchanges data...")
            cur.execute("TRUNCATE TABLE exchanges RESTART IDENTITY CASCADE;")

            # Insert new data
            logger.info(f"Inserting {len(exchanges)} exchanges...")
            for exchange in exchanges:
                values = (
                    exchange.get("id"),
                    exchange.get("acronym"),
                    exchange.get("asset_class"),
                    exchange.get("locale"),
                    exchange.get("mic"),
                    exchange.get("name"),
                    exchange.get("operating_mic"),
                    exchange.get("participant_id"),
                    exchange.get("type"),
                    exchange.get("url"),
                )
                cur.execute(insert_sql, values)

            # Get final count
            cur.execute("SELECT COUNT(*) FROM exchanges;")
            count = cur.fetchone()[0]
            logger.info(f"✓ Successfully inserted {count} exchanges")

            # Show sample data
            cur.execute(
                """
                SELECT exchange_id, acronym, name, mic, type
                FROM exchanges
                ORDER BY name
                LIMIT 5;
            """
            )
            logger.info("\nSample exchanges:")
            for row in cur.fetchall():
                logger.info(f"  {row[1]} - {row[2]} (MIC: {row[3]}, Type: {row[4]})")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        exchanges = fetch_exchanges()
        populate_table(exchanges)

        logger.info("\n✓ Exchanges table populated successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
