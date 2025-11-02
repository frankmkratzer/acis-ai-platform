"""
Technical Indicator Assets for Dagster
SMA, EMA, RSI, MACD - all depend on daily_bars
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from dagster import AssetExecutionContext, AssetIn, Output, asset

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils import get_logger, get_psycopg2_connection


@asset(
    name="sma",
    group_name="technical_indicators",
    description="Simple Moving Averages (20, 50, 200 day)",
    compute_kind="python",
    ins={"daily_bars": AssetIn()},  # Depends on daily_bars
)
def sma(context: AssetExecutionContext, daily_bars: dict) -> Output[dict]:
    """
    Calculate Simple Moving Averages

    Depends on: daily_bars
    Windows: 20, 50, 200 days
    """
    from scripts.update import update_sma

    target_date = date.today() - timedelta(days=1)
    context.log.info(f"Calculating SMA for {target_date}")

    result = update_sma.update_sma(target_date)

    context.log.info(f"Calculated SMA for {result['tickers_updated']} tickers")

    return Output(value=result, metadata={"tickers_updated": result["tickers_updated"]})


@asset(
    name="ema",
    group_name="technical_indicators",
    description="Exponential Moving Averages (12, 26, 50 day)",
    compute_kind="python",
    ins={"daily_bars": AssetIn()},
)
def ema(context: AssetExecutionContext, daily_bars: dict) -> Output[dict]:
    """
    Calculate Exponential Moving Averages

    Depends on: daily_bars
    Windows: 12, 26, 50 days
    """
    from scripts.update import update_ema

    target_date = date.today() - timedelta(days=1)
    context.log.info(f"Calculating EMA for {target_date}")

    result = update_ema.update_ema(target_date)

    context.log.info(f"Calculated EMA for {result['tickers_updated']} tickers")

    return Output(value=result, metadata={"tickers_updated": result["tickers_updated"]})


@asset(
    name="rsi",
    group_name="technical_indicators",
    description="Relative Strength Index (14 day)",
    compute_kind="python",
    ins={"daily_bars": AssetIn()},
)
def rsi(context: AssetExecutionContext, daily_bars: dict) -> Output[dict]:
    """
    Calculate Relative Strength Index

    Depends on: daily_bars
    Period: 14 days
    """
    from scripts.update import update_rsi

    target_date = date.today() - timedelta(days=1)
    context.log.info(f"Calculating RSI for {target_date}")

    result = update_rsi.update_rsi(target_date)

    context.log.info(f"Calculated RSI for {result['tickers_updated']} tickers")

    return Output(value=result, metadata={"tickers_updated": result["tickers_updated"]})


@asset(
    name="macd",
    group_name="technical_indicators",
    description="MACD indicator (12,26,9)",
    compute_kind="python",
    ins={"ema": AssetIn()},  # Depends on EMA
)
def macd(context: AssetExecutionContext, ema: dict) -> Output[dict]:
    """
    Calculate MACD indicators

    Depends on: ema (uses EMA-12 and EMA-26)
    Parameters: 12, 26, 9
    """
    from scripts.update import update_macd

    target_date = date.today() - timedelta(days=1)
    context.log.info(f"Calculating MACD for {target_date}")

    result = update_macd.update_macd(target_date)

    context.log.info(f"Calculated MACD for {result['tickers_updated']} tickers")

    return Output(value=result, metadata={"tickers_updated": result["tickers_updated"]})
