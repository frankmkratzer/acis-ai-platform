#!/usr/bin/env python3
"""
Enhanced GPU-Accelerated XGBoost Training with Financial Statement Features
Integrates all 88 features: 31 base + 57 financial statement features
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
from datetime import date, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from ml_models.financial_statement_features_sql import (
    get_calculated_features,
    get_financial_features_sql,
)
from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class EnhancedXGBoostTrainer:
    """Enhanced XGBoost trainer with full financial statement features"""

    def __init__(self, gpu_id: int = 0, target_horizon_days: int = 20):
        self.gpu_id = gpu_id
        self.target_horizon_days = target_horizon_days
        self.feature_names = []

    def load_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Load ALL features including financial statements (88 total features)

        Features include:
        - 31 Base features: ratios, technical indicators, momentum, volume
        - 57 Financial statement features: growth, profitability, cash flow, health, F-score
        """
        logger.info(f"Loading ENHANCED features from {start_date} to {end_date}...")
        logger.info("Including 57 financial statement features...")

        # Get financial statement SQL fragments
        financial_joins = get_financial_features_sql()
        financial_features = get_calculated_features()

        query = f"""
        WITH latest_prices AS (
            SELECT
                ticker,
                date,
                close,
                volume,
                LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date) as close_5d_ago,
                LAG(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_20d_ago,
                LAG(close, 60) OVER (PARTITION BY ticker ORDER BY date) as close_60d_ago,
                LEAD(close, %(horizon)s) OVER (PARTITION BY ticker ORDER BY date) as close_future,
                AVG(volume) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as avg_volume_20d
            FROM daily_bars
            WHERE date >= %(start_date)s AND date <= %(end_date)s
        ),
        features AS (
            SELECT
                lp.ticker,
                lp.date,

                -- ===== BASE FEATURES (31) =====

                -- Price momentum features (3)
                (lp.close / NULLIF(lp.close_5d_ago, 0) - 1) as ret_5d,
                (lp.close / NULLIF(lp.close_20d_ago, 0) - 1) as ret_20d,
                (lp.close / NULLIF(lp.close_60d_ago, 0) - 1) as ret_60d,

                -- Volume features (1)
                (lp.volume / NULLIF(lp.avg_volume_20d, 0)) as volume_ratio,

                -- Technical indicators (14)
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

                -- Fundamental ratios (12)
                r.price_to_earnings as pe_ratio,
                r.price_to_book as pb_ratio,
                r.price_to_sales as ps_ratio,
                r.price_to_cash_flow as pcf_ratio,
                r.price_to_free_cash_flow as pfcf_ratio,
                r.ev_to_sales,
                r.ev_to_ebitda,
                r.return_on_equity as roe,
                r.return_on_assets as roa,
                r.debt_to_equity as debt_to_equity_ratio,
                r.current as current_ratio_base,
                r.quick as quick_ratio_base,

                -- Market cap (1)
                LOG(NULLIF(tov.market_cap, 0)) as log_market_cap,

                -- ===== FINANCIAL STATEMENT FEATURES (57) =====
                {financial_features},

                -- Target: Forward return
                (lp.close_future / NULLIF(lp.close, 0) - 1) as target_return

            FROM latest_prices lp

            -- Join technical indicators
            LEFT JOIN rsi ON lp.ticker = rsi.ticker AND lp.date = rsi.date AND rsi.window_size = 14
            LEFT JOIN macd ON lp.ticker = macd.ticker AND lp.date = macd.date
            LEFT JOIN sma sma20 ON lp.ticker = sma20.ticker AND lp.date = sma20.date AND sma20.window_size = 20
            LEFT JOIN sma sma50 ON lp.ticker = sma50.ticker AND lp.date = sma50.date AND sma50.window_size = 50
            LEFT JOIN sma sma200 ON lp.ticker = sma200.ticker AND lp.date = sma200.date AND sma200.window_size = 200
            LEFT JOIN ema ema12 ON lp.ticker = ema12.ticker AND lp.date = ema12.date AND ema12.window_size = 12
            LEFT JOIN ema ema26 ON lp.ticker = ema26.ticker AND lp.date = ema26.date AND ema26.window_size = 26

            -- Join fundamentals (latest available as of date)
            LEFT JOIN LATERAL (
                SELECT *
                FROM ratios r2
                WHERE r2.ticker = lp.ticker
                  AND r2.date <= lp.date
                ORDER BY r2.date DESC
                LIMIT 1
            ) r ON true

            -- Join ticker overview for market cap
            LEFT JOIN ticker_overview tov ON lp.ticker = tov.ticker

            -- Join financial statements
            {financial_joins}

            WHERE lp.close_future IS NOT NULL  -- Must have future price
        )
        SELECT * FROM features
        WHERE target_return IS NOT NULL
        ORDER BY ticker, date;
        """

        df = pd.read_sql(
            query,
            engine,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "horizon": self.target_horizon_days,
            },
        )

        logger.info(f"Loaded {len(df):,} samples for {df['ticker'].nunique()} tickers")
        logger.info(f"Total columns: {len(df.columns)}")

        return df

    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Prepare features and target for training"""

        # Drop non-feature columns
        feature_cols = [c for c in df.columns if c not in ["ticker", "date", "target_return"]]
        X = df[feature_cols].copy()
        y = df["target_return"].copy()

        # Remove rows where target is NaN
        valid_mask = ~y.isna()
        X = X[valid_mask]
        y = y[valid_mask]

        # Convert all object dtypes to numeric (handles SQL NULL values)
        X = X.apply(pd.to_numeric, errors="coerce")

        # Fill NaN values in features (median for numeric, then 0 for remaining)
        X = X.fillna(X.median()).fillna(0)

        logger.info(f"Features: {len(feature_cols)}, Samples: {len(X):,}")

        return X, y, feature_cols

    def train_walk_forward(
        self, X: pd.DataFrame, y: pd.Series, feature_names: List[str]
    ) -> Tuple[xgb.Booster, Dict]:
        """
        Walk-forward validation: Train on expanding window, test on next period
        """
        n_splits = 5
        samples_per_fold = len(X) // (n_splits + 1)

        metrics = {"rmse": [], "mae": [], "ic": []}
        feature_importance = np.zeros(len(feature_names))
        final_model = None

        logger.info(f"Starting walk-forward validation with {n_splits} splits...")

        for fold in range(1, n_splits + 1):
            # Train on data from start to fold, test on next fold
            train_end = samples_per_fold * fold
            val_start = train_end
            val_end = train_end + samples_per_fold

            X_train = X.iloc[:train_end]
            y_train = y.iloc[:train_end]
            X_val = X.iloc[val_start:val_end]
            y_val = y.iloc[val_start:val_end]

            logger.info(f"\nFold {fold}/{n_splits}")
            logger.info(f"  Train: {len(X_train):,} samples")
            logger.info(f"  Val:   {len(X_val):,} samples")

            # Create DMatrix
            dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_names)
            dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_names)

            # XGBoost parameters
            params = {
                "objective": "reg:squarederror",
                "tree_method": "hist",
                "device": f"cuda:{self.gpu_id}",
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "min_child_weight": 5,
                "gamma": 0.1,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "seed": 42,
            }

            # Train model
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=100,
                evals=[(dtrain, "train"), (dval, "val")],
                verbose_eval=50,
            )

            # Predictions
            y_pred = model.predict(dval)

            # Metrics
            rmse = np.sqrt(np.mean((y_val - y_pred) ** 2))
            mae = np.mean(np.abs(y_val - y_pred))
            ic, _ = spearmanr(y_val, y_pred)

            metrics["rmse"].append(rmse)
            metrics["mae"].append(mae)
            metrics["ic"].append(ic)

            logger.info(f"  RMSE: {rmse:.4f}")
            logger.info(f"  MAE:  {mae:.4f}")
            logger.info(f"  IC:   {ic:.4f}")

            # Accumulate feature importance
            importance = model.get_score(importance_type="weight")
            for i, fname in enumerate(feature_names):
                if fname in importance:
                    feature_importance[i] += importance[fname]

            # Save last model as final
            final_model = model

        # Average metrics
        avg_metrics = {k: np.mean(v) for k, v in metrics.items()}

        logger.info(f"\n{'='*60}")
        logger.info(f"Walk-Forward Validation Results ({n_splits} folds)")
        logger.info(f"{'='*60}")
        logger.info(f"Average RMSE: {avg_metrics['rmse']:.4f}")
        logger.info(f"Average MAE:  {avg_metrics['mae']:.4f}")
        logger.info(f"Average IC:   {avg_metrics['ic']:.4f}")

        return final_model, {"avg_metrics": avg_metrics, "feature_importance": feature_importance}

    def save_model(self, model: xgb.Booster, feature_names: List[str], output_path: str):
        """Save trained model and feature names"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save model
        model.save_model(str(output_path))
        logger.info(f"Model saved to: {output_path}")

        # Save feature names
        feature_path = output_path.with_suffix(".json").with_name(
            output_path.stem + "_features.json"
        )
        with open(feature_path, "w") as f:
            json.dump(feature_names, f)
        logger.info(f"Feature names saved to: {feature_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced XGBoost training with financial statements"
    )
    parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--gpu", type=int, default=0, help="GPU ID to use")
    parser.add_argument("--horizon", type=int, default=20, help="Prediction horizon in days")
    parser.add_argument(
        "--output", type=str, default="models/xgboost_enhanced.json", help="Output model path"
    )

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)

    logger.info("=" * 60)
    logger.info("Enhanced XGBoost GPU Training Pipeline")
    logger.info("88 Features: 31 Base + 57 Financial Statements")
    logger.info("=" * 60)
    logger.info(f"Start date: {start_date}")
    logger.info(f"End date: {end_date}")
    logger.info(f"Horizon: {args.horizon} days")
    logger.info(f"GPU: {args.gpu}")

    try:
        # Initialize trainer
        trainer = EnhancedXGBoostTrainer(gpu_id=args.gpu, target_horizon_days=args.horizon)

        # Load features
        df = trainer.load_features(start_date, end_date)

        # Prepare data
        X, y, feature_names = trainer.prepare_data(df)
        trainer.feature_names = feature_names

        # Train with walk-forward validation
        model, results = trainer.train_walk_forward(X, y, feature_names)

        # Save model
        trainer.save_model(model, feature_names, args.output)

        # Display top features
        importance_dict = dict(zip(feature_names, results["feature_importance"]))
        top_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)[:15]

        logger.info(f"\nTop 15 Features:")
        for feat, score in top_features:
            logger.info(f"  {feat:40} {score:>10.0f}")

        logger.info(f"\n{'='*60}")
        logger.info("Training Complete!")
        logger.info("=" * 60)
        logger.info(f"Model: {args.output}")
        logger.info(f"Information Coefficient: {results['avg_metrics']['ic']:.4f}")
        logger.info(f"RMSE: {results['avg_metrics']['rmse']:.4f}")

    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise


if __name__ == "__main__":
    main()
