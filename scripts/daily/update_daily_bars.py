#!/usr/bin/env python3
"""
Daily update for daily_bars table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches last 30 days of data for all active tickers
"""
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from utils import get_logger, get_psycopg2_connection

load_dotenv()

logger = get_logger(__name__)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
API_URL = "https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"


def get_active_tickers():
    """Get all active tickers"""
    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker
                FROM tickers
                WHERE active = true
                ORDER BY ticker;
            """
            )
            tickers = [row[0] for row in cur.fetchall()]
            logger.info(f"Found {len(tickers)} active tickers")
            return tickers


def fetch_daily_bars(ticker, from_date, to_date):
    """Fetch daily bars for a ticker between dates"""
    url = API_URL.format(
        ticker=ticker,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
    )
    params = {"apiKey": POLYGON_API_KEY, "adjusted": "true", "sort": "asc", "limit": 50000}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            return data["results"]
        else:
            return []

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.debug(f"No data for {ticker}")
        else:
            logger.error(f"HTTP error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return []


def upsert_daily_bars(tickers):
    """Fetch and upsert daily bars (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO daily_bars (
            ticker, date, open, high, low, close, volume, vwap, transactions, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (ticker, date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            vwap = EXCLUDED.vwap,
            transactions = EXCLUDED.transactions,
            updated_at = CURRENT_TIMESTAMP;
    """

    # Fetch last 30 days of data
    today = date.today()
    from_date = today - timedelta(days=30)

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM daily_bars;")
            count_before = cur.fetchone()[0]

            # Fetch and upsert daily bars
            logger.info(f"Upserting daily bars for {len(tickers)} tickers (last 30 days)...")
            processed = 0
            total_bars_upserted = 0
            batch = []
            batch_size = 1000

            for i, ticker in enumerate(tickers, 1):
                bars = fetch_daily_bars(ticker, from_date, today)

                if bars:
                    for bar in bars:
                        # Convert timestamp to date
                        bar_date = datetime.fromtimestamp(bar["t"] / 1000).date()

                        values = (
                            ticker,
                            bar_date,
                            bar.get("o"),  # open
                            bar.get("h"),  # high
                            bar.get("l"),  # low
                            bar.get("c"),  # close
                            bar.get("v"),  # volume
                            bar.get("vw"),  # vwap
                            bar.get("n"),  # transactions
                        )
                        batch.append(values)
                        total_bars_upserted += 1

                    # Upsert batch
                    if len(batch) >= batch_size:
                        cur.executemany(upsert_sql, batch)
                        batch = []

                processed += 1

                # Log progress every 100 tickers
                if processed % 100 == 0:
                    logger.info(
                        f"  Progress: {processed}/{len(tickers)} tickers, {total_bars_upserted:,} bars upserted"
                    )

                # Rate limiting: 100 requests per second
                if i % 100 == 0:
                    time.sleep(1)

            # Upsert remaining batch
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM daily_bars;")
            count_after = cur.fetchone()[0]

            new_bars = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Bars before: {count_before:,}")
            logger.info(f"  Bars after:  {count_after:,}")
            logger.info(f"  New bars:    {new_bars:,}")
            logger.info(f"  Updated:     {total_bars_upserted - new_bars:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT ticker, date, close, volume, updated_at
                FROM daily_bars
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '2 minutes'
                ORDER BY date DESC, volume DESC
                LIMIT 10;
            """
            )
            logger.info("\nRecently updated bars (top by volume):")
            for row in cur.fetchall():
                ticker, bar_date, close, vol, updated = row
                logger.info(f"  {ticker:8} {bar_date} Close: ${close:>8.2f} Volume: {vol:>15,.0f}")

            # Show latest date coverage
            cur.execute(
                """
                SELECT date, COUNT(DISTINCT ticker) as ticker_count
                FROM daily_bars
                WHERE date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY date
                ORDER BY date DESC;
            """
            )
            logger.info("\nLast 7 days coverage:")
            for row in cur.fetchall():
                bar_date, count = row
                logger.info(f"  {bar_date}: {count:,} tickers")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        tickers = get_active_tickers()

        if not tickers:
            logger.warning("No active tickers found")
            return

        upsert_daily_bars(tickers)
        logger.info("\nDaily update complete: Daily bars updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
