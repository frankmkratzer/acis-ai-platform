#!/usr/bin/env python3
"""
Backfill news table from Polygon.io API
Fetches recent stock news articles (last 90 days)
Full reload: TRUNCATE then INSERT all data
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
API_URL = "https://api.polygon.io/v2/reference/news"


def fetch_recent_news(days=90):
    """Fetch recent news articles"""
    from_date = date.today() - timedelta(days=days)

    params = {
        "published_utc.gte": from_date.isoformat(),
        "limit": 1000,
        "order": "desc",
        "sort": "published_utc",
        "apiKey": POLYGON_API_KEY,
    }

    all_articles = []
    page_count = 0

    try:
        logger.info(f"Fetching news articles from {from_date} onwards...")
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and "results" in data:
            all_articles.extend(data["results"])
            page_count += 1
            logger.info(
                f"  Page {page_count}: {len(data['results'])} articles (total: {len(all_articles):,})"
            )

            # Handle pagination
            while data.get("next_url"):
                time.sleep(0.1)  # Rate limiting
                next_url = data["next_url"] + f"&apiKey={POLYGON_API_KEY}"
                response = requests.get(next_url)
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "OK" and "results" in data:
                    all_articles.extend(data["results"])
                    page_count += 1
                    if page_count % 10 == 0:
                        logger.info(
                            f"  Page {page_count}: {len(data['results'])} articles (total: {len(all_articles):,})"
                        )
                else:
                    break

        logger.info(f"Fetched {len(all_articles):,} total news articles")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Error fetching news: {e}")

    return all_articles


def populate_table(articles_data):
    """Insert news articles into table (TRUNCATE + INSERT)"""
    insert_sql = """
        INSERT INTO news (
            article_id, title, author, published_utc, article_url,
            image_url, description, tickers, publisher_name,
            publisher_homepage_url, publisher_logo_url, keywords,
            sentiment, sentiment_reasoning
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        );
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # FULL RELOAD: Clear existing data
            logger.info("TRUNCATING news table...")
            cur.execute("TRUNCATE TABLE news RESTART IDENTITY CASCADE;")

            # Prepare data for insertion
            logger.info(f"Processing {len(articles_data):,} news articles...")
            unique_records = {}  # Dictionary to deduplicate by article_id

            for article in articles_data:
                article_id = article.get("id")

                if not article_id:
                    continue

                # Parse published timestamp
                published_utc = None
                published_str = article.get("published_utc")
                if published_str:
                    try:
                        published_utc = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    except:
                        pass

                # Extract tickers array
                tickers = article.get("tickers", [])

                # Extract publisher info
                publisher = article.get("publisher", {})
                publisher_name = publisher.get("name")
                publisher_homepage = publisher.get("homepage_url")
                publisher_logo = publisher.get("logo_url")

                # Extract keywords
                keywords = article.get("keywords", [])

                # Extract sentiment from insights
                sentiment = None
                sentiment_reasoning = None
                insights = article.get("insights", [])
                if insights and isinstance(insights, list) and len(insights) > 0:
                    first_insight = insights[0]
                    sentiment = first_insight.get("sentiment")
                    sentiment_reasoning = first_insight.get("sentiment_reasoning")

                values_tuple = (
                    article_id,
                    article.get("title"),
                    article.get("author"),
                    published_utc,
                    article.get("article_url"),
                    article.get("image_url"),
                    article.get("description"),
                    tickers,  # PostgreSQL array
                    publisher_name,
                    publisher_homepage,
                    publisher_logo,
                    keywords,  # PostgreSQL array
                    sentiment,
                    sentiment_reasoning,
                )
                unique_records[article_id] = values_tuple

            # Insert all unique records in batches
            logger.info(f"Inserting {len(unique_records):,} unique news articles...")
            batch = []
            batch_size = 1000
            total_inserted = 0

            for values_tuple in unique_records.values():
                batch.append(values_tuple)
                total_inserted += 1

                if len(batch) >= batch_size:
                    cur.executemany(insert_sql, batch)
                    batch = []

            # Insert remaining batch
            if batch:
                cur.executemany(insert_sql, batch)

            logger.info(f"Final: {total_inserted:,} news articles inserted")

            # Show statistics
            cur.execute(
                """
                SELECT
                    COUNT(*) as total_articles,
                    MIN(published_utc) as earliest_date,
                    MAX(published_utc) as latest_date,
                    COUNT(DISTINCT publisher_name) as unique_publishers
                FROM news;
            """
            )
            stats = cur.fetchone()
            logger.info(f"\nData statistics:")
            logger.info(f"  Total articles: {stats[0]:,}")
            logger.info(f"  Date range: {stats[1]} to {stats[2]}")
            logger.info(f"  Unique publishers: {stats[3]}")

            # Show sentiment breakdown
            cur.execute(
                """
                SELECT sentiment, COUNT(*) as count
                FROM news
                WHERE sentiment IS NOT NULL
                GROUP BY sentiment
                ORDER BY count DESC;
            """
            )
            logger.info(f"\nSentiment breakdown:")
            for row in cur.fetchall():
                sentiment_val, count = row
                logger.info(f"  {sentiment_val:15} {count:>6,}")

            # Show top publishers
            cur.execute(
                """
                SELECT publisher_name, COUNT(*) as count
                FROM news
                WHERE publisher_name IS NOT NULL
                GROUP BY publisher_name
                ORDER BY count DESC
                LIMIT 10;
            """
            )
            logger.info(f"\nTop 10 publishers:")
            for row in cur.fetchall():
                pub_name, count = row
                logger.info(f"  {pub_name[:40]:40} {count:>6,}")

            # Sample recent articles
            cur.execute(
                """
                SELECT title, published_utc, tickers, sentiment
                FROM news
                ORDER BY published_utc DESC
                LIMIT 10;
            """
            )
            logger.info(f"\nRecent news articles:")
            for row in cur.fetchall():
                title, pub_date, tickers_arr, sentiment_val = row
                tickers_str = ",".join(tickers_arr[:3]) if tickers_arr else "N/A"
                sentiment_str = sentiment_val or "N/A"
                logger.info(f"  [{tickers_str:15}] {sentiment_str:8} {title[:60]}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        # Fetch last 90 days of news
        articles_data = fetch_recent_news(days=90)

        if not articles_data:
            logger.warning("No news articles found")
            return

        populate_table(articles_data)
        logger.info("\nBackfill complete: News table fully loaded")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
