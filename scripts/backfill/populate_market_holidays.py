#!/usr/bin/env python3
"""
Populate market_holidays table from Polygon.io API
Fetches market holidays for multiple years
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v1/marketstatus/upcoming"


def fetch_market_holidays():
    """Fetch market holidays from Polygon API"""
    params = {
        "apiKey": POLYGON_API_KEY,
    }

    logger.info(f"Fetching market holidays from {API_URL}")
    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()

    # The response is an array of holiday objects
    holidays = data if isinstance(data, list) else []

    logger.info(f"Total holidays fetched: {len(holidays)}")

    return holidays


def populate_table(holidays):
    """Insert market holidays into database"""
    insert_sql = """
        INSERT INTO market_holidays (
            date, exchange, name, status, open, close
        ) VALUES (
            %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (date, exchange) DO UPDATE SET
            name = EXCLUDED.name,
            status = EXCLUDED.status,
            open = EXCLUDED.open,
            close = EXCLUDED.close;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Clear existing data
            logger.info("Clearing existing market holidays data...")
            cur.execute("TRUNCATE TABLE market_holidays RESTART IDENTITY CASCADE;")

            # Insert new data
            logger.info(f"Inserting {len(holidays)} market holidays...")
            for holiday in holidays:
                # Parse timestamps if present
                open_time = None
                close_time = None

                if "open" in holiday and holiday["open"]:
                    try:
                        open_time = datetime.fromisoformat(holiday["open"].replace("Z", "+00:00"))
                    except:
                        pass

                if "close" in holiday and holiday["close"]:
                    try:
                        close_time = datetime.fromisoformat(holiday["close"].replace("Z", "+00:00"))
                    except:
                        pass

                values = (
                    holiday.get("date"),
                    holiday.get("exchange"),
                    holiday.get("name"),
                    holiday.get("status"),
                    open_time,
                    close_time,
                )
                cur.execute(insert_sql, values)

            # Get final count
            cur.execute("SELECT COUNT(*) FROM market_holidays;")
            count = cur.fetchone()[0]
            logger.info(f"Successfully inserted {count} market holidays")

            # Show sample data
            cur.execute(
                """
                SELECT date, exchange, name, status, open, close
                FROM market_holidays
                ORDER BY date
                LIMIT 10;
            """
            )
            logger.info("\nUpcoming market holidays:")
            for row in cur.fetchall():
                date_str = row[0].strftime("%Y-%m-%d") if row[0] else "N/A"
                status_info = f"Status: {row[3]}"
                if row[4] and row[5]:  # If open and close times exist
                    open_str = row[4].strftime("%H:%M") if row[4] else ""
                    close_str = row[5].strftime("%H:%M") if row[5] else ""
                    status_info += f" ({open_str}-{close_str})"
                logger.info(f"  {date_str} - {row[2]:30} ({row[1]}) {status_info}")

            # Show statistics
            cur.execute(
                """
                SELECT status, COUNT(*)
                FROM market_holidays
                GROUP BY status
                ORDER BY status;
            """
            )
            logger.info("\nHoliday statistics by status:")
            for row in cur.fetchall():
                logger.info(f"  {row[0]}: {row[1]} days")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        holidays = fetch_market_holidays()
        populate_table(holidays)

        logger.info("\nMarket holidays table populated successfully")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
