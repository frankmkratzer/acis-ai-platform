"""
Market Data Assets for Dagster
Daily price data, dividends, splits, news, and fundamentals
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from dagster import AssetExecutionContext, DailyPartitionsDefinition, Output, asset

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection

# Define daily partitions for incremental processing
daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")


@asset(
    name="daily_bars",
    group_name="market_data",
    description="Daily OHLCV price data from Polygon",
    compute_kind="python",
)
def daily_bars(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch daily price bars for all tickers

    Updates: Daily after market close (4pm ET)
    Source: Polygon.io /v2/aggs/grouped/locale/us/market/stocks
    """
    from scripts.update import update_daily_bars

    target_date = date.today() - timedelta(days=1)  # Previous trading day
    context.log.info(f"Fetching daily bars for {target_date}")

    result = update_daily_bars.update_daily_bars(target_date)

    context.log.info(f"Inserted {result['rows_inserted']} daily bars")

    return Output(
        value=result,
        metadata={
            "rows_inserted": result["rows_inserted"],
            "tickers_updated": result.get("tickers_updated", 0),
            "date": str(target_date),
        },
    )


@asset(
    name="dividends",
    group_name="market_data",
    description="Dividend announcements and payments",
    compute_kind="python",
)
def dividends(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch recent dividend data

    Updates: Daily
    Source: Polygon.io /v3/reference/dividends
    """
    from scripts.update import update_dividends

    context.log.info("Fetching recent dividends")
    result = update_dividends.update_dividends()

    context.log.info(f"Inserted {result['rows_inserted']} new dividends")

    return Output(value=result, metadata={"rows_inserted": result["rows_inserted"]})


@asset(
    name="splits",
    group_name="market_data",
    description="Stock split announcements",
    compute_kind="python",
)
def splits(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch recent stock splits

    Updates: Daily
    Source: Polygon.io /v3/reference/splits
    """
    from scripts.update import update_splits

    context.log.info("Fetching recent splits")
    result = update_splits.update_splits()

    context.log.info(f"Inserted {result['rows_inserted']} new splits")

    return Output(value=result, metadata={"rows_inserted": result["rows_inserted"]})


@asset(
    name="news",
    group_name="market_data",
    description="News articles and sentiment",
    compute_kind="python",
)
def news(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch recent news articles

    Updates: Daily
    Source: Polygon.io /v2/reference/news
    """
    from scripts.update import update_news

    context.log.info("Fetching recent news")
    result = update_news.update_news()

    context.log.info(f"Inserted {result['rows_inserted']} new articles")

    return Output(value=result, metadata={"rows_inserted": result["rows_inserted"]})


@asset(
    name="short_interest",
    group_name="market_data",
    description="Short interest data",
    compute_kind="python",
)
def short_interest(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch short interest data

    Updates: Weekly (published bi-weekly by exchanges)
    Source: Polygon.io short interest endpoint
    """
    from scripts.update import update_short_interest

    context.log.info("Fetching short interest data")
    result = update_short_interest.update_short_interest()

    context.log.info(f"Inserted {result['rows_inserted']} short interest records")

    return Output(value=result, metadata={"rows_inserted": result["rows_inserted"]})


@asset(
    name="fundamentals",
    group_name="market_data",
    description="Quarterly/annual financial statements",
    compute_kind="python",
)
def fundamentals(context: AssetExecutionContext) -> Output[dict]:
    """
    Fetch latest fundamental data (balance sheets, income statements, cash flow, ratios)

    Updates: Daily (checks for new quarterly/annual reports)
    Source: Polygon.io financials endpoints
    """
    from scripts.update import update_fundamentals

    context.log.info("Fetching fundamental data")
    result = update_fundamentals.update_fundamentals()

    context.log.info(f"Updated fundamentals for {result['tickers_updated']} tickers")

    return Output(value=result, metadata={"tickers_updated": result["tickers_updated"]})
