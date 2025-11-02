#!/usr/bin/env python3
"""
Test ML Model Predictions on Recent Data
Validates model performance on out-of-sample 2024-2025 data
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
from datetime import date

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


def load_model(model_path: str):
    """Load trained XGBoost model"""
    model = xgb.Booster()
    model.load_model(model_path)

    # Load feature names
    features_path = (
        Path(model_path).with_suffix(".json").with_name(Path(model_path).stem + "_features.json")
    )
    with open(features_path, "r") as f:
        feature_names = json.load(f)

    logger.info(f"Loaded model from: {model_path}")
    logger.info(f"Features: {len(feature_names)}")

    return model, feature_names


def load_recent_data(start_date: date, end_date: date):
    """Load recent data for testing (simplified query)"""
    logger.info(f"Loading test data from {start_date} to {end_date}...")

    query = """
    WITH latest_prices AS (
        SELECT
            ticker,
            date,
            close,
            volume,
            LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date) as close_5d_ago,
            LAG(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_20d_ago,
            LAG(close, 60) OVER (PARTITION BY ticker ORDER BY date) as close_60d_ago,
            LEAD(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_future,
            AVG(volume) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as avg_volume_20d
        FROM daily_bars
        WHERE date >= %(start_date)s AND date <= %(end_date)s
    )
    SELECT
        lp.ticker,
        lp.date,

        -- Price momentum
        (lp.close / NULLIF(lp.close_5d_ago, 0) - 1) as ret_5d,
        (lp.close / NULLIF(lp.close_20d_ago, 0) - 1) as ret_20d,
        (lp.close / NULLIF(lp.close_60d_ago, 0) - 1) as ret_60d,

        -- Volume
        (lp.volume / NULLIF(lp.avg_volume_20d, 0)) as volume_ratio,

        -- Technical indicators
        rsi.value as rsi_14,
        macd.macd_value,
        macd.signal_value,
        (macd.macd_value - macd.signal_value) as macd_histogram,
        sma20.value as sma_20,
        sma50.value as sma_50,
        sma200.value as sma_200,
        (lp.close / NULLIF(sma20.value, 0) - 1) as price_to_sma20,
        (lp.close / NULLIF(sma50.value, 0) - 1) as price_to_sma50,
        (lp.close / NULLIF(sma200.value, 0) - 1) as price_to_sma200,
        ema12.value as ema_12,
        ema26.value as ema_26,
        (ema12.value / NULLIF(ema26.value, 0) - 1) as ema_12_26_ratio,

        -- Fundamental ratios
        r.price_to_earnings as pe_ratio,
        r.price_to_book as pb_ratio,
        r.price_to_sales as ps_ratio,
        r.price_to_cash_flow as pcf_ratio,
        r.price_to_free_cash_flow as pfcf_ratio,
        r.ev_to_sales,
        r.ev_to_ebitda,
        r.return_on_equity as roe,
        r.return_on_assets as roa,
        r.debt_to_equity,
        r.current as current_ratio,
        r.quick as quick_ratio,
        r.dividend_yield,

        -- Market cap
        LOG(NULLIF(tov.market_cap, 0)) as log_market_cap,

        -- Target
        (lp.close_future / NULLIF(lp.close, 0) - 1) as target_return

    FROM latest_prices lp
    LEFT JOIN rsi ON lp.ticker = rsi.ticker AND lp.date = rsi.date AND rsi.window_size = 14
    LEFT JOIN macd ON lp.ticker = macd.ticker AND lp.date = macd.date
    LEFT JOIN sma sma20 ON lp.ticker = sma20.ticker AND lp.date = sma20.date AND sma20.window_size = 20
    LEFT JOIN sma sma50 ON lp.ticker = sma50.ticker AND lp.date = sma50.date AND sma50.window_size = 50
    LEFT JOIN sma sma200 ON lp.ticker = sma200.ticker AND lp.date = sma200.date AND sma200.window_size = 200
    LEFT JOIN ema ema12 ON lp.ticker = ema12.ticker AND lp.date = ema12.date AND ema12.window_size = 12
    LEFT JOIN ema ema26 ON lp.ticker = ema26.ticker AND lp.date = ema26.date AND ema26.window_size = 26
    LEFT JOIN LATERAL (
        SELECT *
        FROM ratios r2
        WHERE r2.ticker = lp.ticker
          AND r2.date <= lp.date
        ORDER BY r2.date DESC
        LIMIT 1
    ) r ON true
    LEFT JOIN ticker_overview tov ON lp.ticker = tov.ticker
    WHERE lp.close_future IS NOT NULL
    ORDER BY lp.ticker, lp.date;
    """

    df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
    logger.info(f"Loaded {len(df):,} samples for {df['ticker'].nunique()} tickers")

    return df


def test_model(model, feature_names: list, df: pd.DataFrame):
    """Test model on recent data"""

    # Prepare data
    feature_cols = [c for c in df.columns if c in feature_names]
    X = df[feature_cols].copy()
    y = df["target_return"].copy()
    tickers = df["ticker"].copy()
    dates = df["date"].copy()

    # Remove NaN targets
    valid_mask = ~y.isna()
    X = X[valid_mask]
    y = y[valid_mask]
    tickers = tickers[valid_mask]
    dates = dates[valid_mask]

    # Fill NaN features
    X = X.fillna(X.median()).fillna(0)

    logger.info(f"Testing on {len(X):,} samples with {len(feature_cols)} features")

    # Make predictions
    dtest = xgb.DMatrix(X, feature_names=feature_names)
    predictions = model.predict(dtest)

    # Calculate metrics
    rmse = np.sqrt(np.mean((y - predictions) ** 2))
    mae = np.mean(np.abs(y - predictions))
    ic, ic_pvalue = spearmanr(y, predictions)

    # Results by month
    results_df = pd.DataFrame(
        {"ticker": tickers, "date": dates, "actual": y, "predicted": predictions}
    )
    results_df["month"] = pd.to_datetime(results_df["date"]).dt.to_period("M")

    monthly_ic = results_df.groupby("month").apply(
        lambda x: spearmanr(x["actual"], x["predicted"])[0]
    )

    logger.info(f"\n{'='*60}")
    logger.info("TEST RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"RMSE: {rmse:.4f}")
    logger.info(f"MAE:  {mae:.4f}")
    logger.info(f"IC:   {ic:.4f} (p-value: {ic_pvalue:.4e})")
    logger.info(f"\nMonthly IC Statistics:")
    logger.info(f"  Mean:   {monthly_ic.mean():.4f}")
    logger.info(f"  Median: {monthly_ic.median():.4f}")
    logger.info(f"  Std:    {monthly_ic.std():.4f}")
    logger.info(f"  Min:    {monthly_ic.min():.4f}")
    logger.info(f"  Max:    {monthly_ic.max():.4f}")

    # Top predictions analysis
    top_decile = results_df.nlargest(int(len(results_df) * 0.1), "predicted")
    logger.info(f"\nTop Decile Performance (Top 10% predictions):")
    logger.info(f"  Mean actual return: {top_decile['actual'].mean()*100:.2f}%")
    logger.info(f"  Mean predicted return: {top_decile['predicted'].mean()*100:.2f}%")
    logger.info(f"  Hit rate (>0): {(top_decile['actual'] > 0).mean()*100:.1f}%")

    return {
        "rmse": rmse,
        "mae": mae,
        "ic": ic,
        "ic_pvalue": ic_pvalue,
        "monthly_ic": monthly_ic.to_dict(),
        "results_df": results_df,
    }


def main():
    parser = argparse.ArgumentParser(description="Test ML model predictions")
    parser.add_argument("--model", type=str, required=True, help="Path to model file")
    parser.add_argument("--start-date", type=str, default="2024-01-01", help="Test start date")
    parser.add_argument("--end-date", type=str, default="2025-01-01", help="Test end date")
    parser.add_argument("--output", type=str, help="Output CSV path for predictions")

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)

    logger.info("=" * 60)
    logger.info("ML Model Prediction Testing")
    logger.info("=" * 60)
    logger.info(f"Model: {args.model}")
    logger.info(f"Test period: {start_date} to {end_date}")

    # Load model
    model, feature_names = load_model(args.model)

    # Load recent data
    df = load_recent_data(start_date, end_date)

    # Test model
    results = test_model(model, feature_names, df)

    # Save predictions if requested
    if args.output:
        results["results_df"].to_csv(args.output, index=False)
        logger.info(f"\nPredictions saved to: {args.output}")

    logger.info("\n" + "=" * 60)
    logger.info("Testing Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
