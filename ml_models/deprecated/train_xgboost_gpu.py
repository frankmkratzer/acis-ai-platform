#!/usr/bin/env python3
"""
GPU-Accelerated XGBoost Training for Stock Ranking
Trains models to predict forward returns for portfolio stock selection

Features:
- Multi-GPU training via XGBoost GPU hist
- Walk-forward validation (prevents overfitting)
- Feature importance tracking
- MLflow experiment tracking
- Outputs predictions for portfolio builder

Expected speedup: 10-20x faster than CPU
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class XGBoostGPUTrainer:
    """Train XGBoost models on GPU for stock ranking"""

    def __init__(
        self,
        target_horizon_days: int = 20,
        n_estimators: int = 1000,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        gpu_id: int = 0,
    ):
        """
        Args:
            target_horizon_days: Days ahead to predict (20 = monthly)
            n_estimators: Number of boosting rounds
            learning_rate: Learning rate (eta)
            max_depth: Maximum tree depth
            gpu_id: GPU device ID to use
        """
        self.target_horizon_days = target_horizon_days
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.gpu_id = gpu_id

        # XGBoost GPU parameters (API changed in 3.1+)
        self.params = {
            "tree_method": "hist",  # Use 'hist' with device parameter
            "device": f"cuda:{gpu_id}",  # New API: use 'device' instead of 'gpu_id'
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "seed": 42,
        }

        self.model = None
        self.feature_names = None

    def load_features(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Load features from database for training

        Features include:
        - Fundamental ratios (P/E, P/B, ROE, etc.)
        - Technical indicators (RSI, MACD, SMA, EMA)
        - Price momentum (5/20/60 day returns)
        - Volume metrics
        """
        logger.info(f"Loading features from {start_date} to {end_date}...")

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
                LEAD(close, %(horizon)s) OVER (PARTITION BY ticker ORDER BY date) as close_future,
                AVG(volume) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as avg_volume_20d
            FROM daily_bars
            WHERE date >= %(start_date)s AND date <= %(end_date)s
        ),
        features AS (
            SELECT
                lp.ticker,
                lp.date,

                -- Price momentum features
                (lp.close / NULLIF(lp.close_5d_ago, 0) - 1) as ret_5d,
                (lp.close / NULLIF(lp.close_20d_ago, 0) - 1) as ret_20d,
                (lp.close / NULLIF(lp.close_60d_ago, 0) - 1) as ret_60d,

                -- Volume features
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

                -- Fundamental ratios (latest available)
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

                -- Market cap (log scale)
                LOG(tov.market_cap) as log_market_cap,

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
        return df

    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Prepare features and target for training"""

        # Drop non-feature columns
        meta_cols = ["ticker", "date", "target_return"]
        feature_cols = [col for col in df.columns if col not in meta_cols]

        X = df[feature_cols].copy()
        y = df["target_return"].copy()

        # Remove rows where target is NaN first
        valid_mask = ~y.isna()
        X = X[valid_mask]
        y = y[valid_mask]

        # Handle missing values in features (fill with median, then 0 if column is all NaN)
        X = X.fillna(X.median()).fillna(0)

        logger.info(f"Features: {len(feature_cols)}, Samples: {len(X):,}")

        return X, y, feature_cols

    def train_walk_forward(self, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> Dict:
        """
        Walk-forward validation: train on past, test on future
        Prevents overfitting and mimics real trading conditions
        """
        logger.info(f"Starting walk-forward validation with {n_splits} splits...")

        tscv = TimeSeriesSplit(n_splits=n_splits)
        results = {"fold_metrics": [], "feature_importance": None}

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            logger.info(f"\nFold {fold}/{n_splits}")
            logger.info(f"  Train: {len(train_idx):,} samples")
            logger.info(f"  Val:   {len(val_idx):,} samples")

            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Create DMatrix for GPU training
            dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)
            dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)

            # Train model
            evals = [(dtrain, "train"), (dval, "val")]
            evals_result = {}

            model = xgb.train(
                self.params,
                dtrain,
                num_boost_round=self.n_estimators,
                evals=evals,
                evals_result=evals_result,
                early_stopping_rounds=50,
                verbose_eval=100,
            )

            # Evaluate
            y_pred = model.predict(dval)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            mae = mean_absolute_error(y_val, y_pred)

            # Calculate Information Coefficient (IC)
            ic = np.corrcoef(y_val, y_pred)[0, 1]

            logger.info(f"  RMSE: {rmse:.4f}")
            logger.info(f"  MAE:  {mae:.4f}")
            logger.info(f"  IC:   {ic:.4f}")

            results["fold_metrics"].append(
                {
                    "fold": fold,
                    "rmse": rmse,
                    "mae": mae,
                    "ic": ic,
                    "train_size": len(train_idx),
                    "val_size": len(val_idx),
                }
            )

            # Store last model
            if fold == n_splits:
                self.model = model
                results["feature_importance"] = model.get_score(importance_type="gain")

        # Calculate average metrics
        avg_rmse = np.mean([m["rmse"] for m in results["fold_metrics"]])
        avg_mae = np.mean([m["mae"] for m in results["fold_metrics"]])
        avg_ic = np.mean([m["ic"] for m in results["fold_metrics"]])

        logger.info(f"\n{'='*60}")
        logger.info(f"Walk-Forward Validation Results ({n_splits} folds)")
        logger.info(f"{'='*60}")
        logger.info(f"Average RMSE: {avg_rmse:.4f}")
        logger.info(f"Average MAE:  {avg_mae:.4f}")
        logger.info(f"Average IC:   {avg_ic:.4f}")

        results["avg_rmse"] = avg_rmse
        results["avg_mae"] = avg_mae
        results["avg_ic"] = avg_ic

        return results

    def save_model(self, output_path: str):
        """Save trained model"""
        if self.model is None:
            raise ValueError("No model to save. Train first.")

        self.model.save_model(output_path)
        logger.info(f"Model saved to: {output_path}")

        # Also save feature names
        feature_file = output_path.replace(".json", "_features.json")
        with open(feature_file, "w") as f:
            json.dump(self.feature_names, f)
        logger.info(f"Feature names saved to: {feature_file}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions"""
        if self.model is None:
            raise ValueError("No model loaded. Train or load first.")

        dtest = xgb.DMatrix(X, feature_names=self.feature_names)
        return self.model.predict(dtest)


def main():
    """Main training pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="Train XGBoost model on GPU")
    parser.add_argument(
        "--start-date", type=str, default="2015-01-01", help="Start date for training data"
    )
    parser.add_argument(
        "--end-date", type=str, default=str(date.today()), help="End date for training data"
    )
    parser.add_argument("--horizon", type=int, default=20, help="Prediction horizon in days")
    parser.add_argument("--gpu", type=int, default=0, help="GPU device ID")
    parser.add_argument("--n-splits", type=int, default=5, help="Number of walk-forward splits")
    parser.add_argument(
        "--output", type=str, default="models/xgboost_gpu.json", help="Output model path"
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("XGBoost GPU Training Pipeline")
    logger.info("=" * 60)
    logger.info(f"Start date: {args.start_date}")
    logger.info(f"End date: {args.end_date}")
    logger.info(f"Horizon: {args.horizon} days")
    logger.info(f"GPU: {args.gpu}")

    # Initialize MLflow
    mlflow.set_experiment("xgboost_stock_ranking")

    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("start_date", args.start_date)
        mlflow.log_param("end_date", args.end_date)
        mlflow.log_param("horizon_days", args.horizon)
        mlflow.log_param("gpu_id", args.gpu)

        # Initialize trainer
        trainer = XGBoostGPUTrainer(target_horizon_days=args.horizon, gpu_id=args.gpu)

        # Load data
        df = trainer.load_features(args.start_date, args.end_date)
        X, y, feature_names = trainer.prepare_data(df)
        trainer.feature_names = feature_names

        # Train with walk-forward validation
        results = trainer.train_walk_forward(X, y, n_splits=args.n_splits)

        # Log metrics to MLflow
        mlflow.log_metric("avg_rmse", results["avg_rmse"])
        mlflow.log_metric("avg_mae", results["avg_mae"])
        mlflow.log_metric("avg_ic", results["avg_ic"])

        # Log feature importance
        if results["feature_importance"]:
            importance_df = pd.DataFrame(
                [
                    {"feature": k, "importance": v}
                    for k, v in sorted(
                        results["feature_importance"].items(), key=lambda x: x[1], reverse=True
                    )
                ]
            )
            importance_df.to_csv("feature_importance.csv", index=False)
            mlflow.log_artifact("feature_importance.csv")

            logger.info(f"\nTop 10 Features:")
            for _, row in importance_df.head(10).iterrows():
                logger.info(f"  {row['feature']:30} {row['importance']:.0f}")

        # Save model
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(output_path))
        mlflow.log_artifact(str(output_path))

        logger.info(f"\n{'='*60}")
        logger.info("Training Complete!")
        logger.info(f"{'='*60}")
        logger.info(f"Model: {output_path}")
        logger.info(f"Information Coefficient: {results['avg_ic']:.4f}")
        logger.info(f"RMSE: {results['avg_rmse']:.4f}")


if __name__ == "__main__":
    main()
