#!/usr/bin/env python3
"""
Daily update for news table from Polygon.io API
Incremental update: UPSERT only (safe to rerun)
Fetches recent news (last 7 days) to capture new articles
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


def fetch_recent_news(days=7):
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
                else:
                    break

        logger.info(f"Fetched {len(all_articles):,} news articles ({page_count} pages)")

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Error fetching news: {e}")

    return all_articles


def upsert_news(articles_data):
    """Upsert news articles (INSERT ... ON CONFLICT DO UPDATE)"""
    upsert_sql = """
        INSERT INTO news (
            article_id, title, author, published_utc, article_url,
            image_url, description, tickers, publisher_name,
            publisher_homepage_url, publisher_logo_url, keywords,
            sentiment, sentiment_reasoning, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
        )
        ON CONFLICT (article_id) DO UPDATE SET
            title = EXCLUDED.title,
            author = EXCLUDED.author,
            published_utc = EXCLUDED.published_utc,
            article_url = EXCLUDED.article_url,
            image_url = EXCLUDED.image_url,
            description = EXCLUDED.description,
            tickers = EXCLUDED.tickers,
            publisher_name = EXCLUDED.publisher_name,
            publisher_homepage_url = EXCLUDED.publisher_homepage_url,
            publisher_logo_url = EXCLUDED.publisher_logo_url,
            keywords = EXCLUDED.keywords,
            sentiment = EXCLUDED.sentiment,
            sentiment_reasoning = EXCLUDED.sentiment_reasoning,
            updated_at = CURRENT_TIMESTAMP;
    """

    with get_psycopg2_connection() as conn:
        with conn.cursor() as cur:
            # Get counts before update
            cur.execute("SELECT COUNT(*) FROM news;")
            count_before = cur.fetchone()[0]

            # Process data
            logger.info(f"Processing {len(articles_data):,} news articles...")
            batch = []
            total_upserted = 0

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
                batch.append(values_tuple)
                total_upserted += 1

            # Upsert all records
            if batch:
                cur.executemany(upsert_sql, batch)

            # Get counts after update
            cur.execute("SELECT COUNT(*) FROM news;")
            count_after = cur.fetchone()[0]

            new_records = count_after - count_before
            logger.info(f"\nUpsert summary:")
            logger.info(f"  Records before: {count_before:,}")
            logger.info(f"  Records after:  {count_after:,}")
            logger.info(f"  New records:    {new_records:,}")
            logger.info(f"  Updated:        {total_upserted - new_records:,}")

            # Show recently updated
            cur.execute(
                """
                SELECT title, published_utc, tickers, sentiment, updated_at
                FROM news
                WHERE updated_at > CURRENT_TIMESTAMP - INTERVAL '5 minutes'
                ORDER BY published_utc DESC
                LIMIT 15;
            """
            )
            if cur.rowcount > 0:
                logger.info("\nRecently updated news articles:")
                for row in cur.fetchall():
                    title, pub_date, tickers_arr, sentiment_val, updated = row
                    tickers_str = ",".join(tickers_arr[:3]) if tickers_arr else "N/A"
                    sentiment_str = sentiment_val or "N/A"
                    logger.info(f"  [{tickers_str:15}] {sentiment_str:8} {title[:60]}")


def main():
    """Main execution"""
    try:
        if not POLYGON_API_KEY:
            raise ValueError("POLYGON_API_KEY not found in environment variables")

        # Fetch last 7 days of news
        articles_data = fetch_recent_news(days=7)

        if not articles_data:
            logger.info("No news articles found for update period")
            return

        upsert_news(articles_data)
        logger.info("\nDaily update complete: News updated via UPSERT")

    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
