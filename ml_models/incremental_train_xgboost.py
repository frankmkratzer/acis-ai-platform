#!/usr/bin/env python3
"""
Incremental XGBoost Model Training

Supports both:
1. Full retraining (from scratch on entire dataset)
2. Incremental updates (fine-tuning existing model on new data)

Usage:
    # Full retraining (monthly)
    python incremental_train_xgboost.py --strategy growth --market-cap mid --mode full

    # Incremental update (daily)
    python incremental_train_xgboost.py --strategy growth --market-cap mid --mode incremental --days 7
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import pickle
import shutil
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class IncrementalXGBoostTrainer:
    """
    Incremental XGBoost Trainer with Warm-Start Capability

    Features:
    - Load existing model checkpoints
    - Train only on new data (incremental)
    - Full retraining option
    - Model versioning and rollback
    """

    def __init__(
        self,
        strategy: str,
        market_cap_segment: str,
        gpu_id: int = None,
        models_dir: str = "models/ml",
    ):
        self.strategy = strategy
        self.market_cap_segment = market_cap_segment
        self.gpu_id = gpu_id
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Model naming
        self.model_name = f"{strategy}_{market_cap_segment}cap"
        self.model_path = self.models_dir / f"{self.model_name}.json"
        self.metadata_path = self.models_dir / f"{self.model_name}_metadata.json"

        # Set filters based on segment
        if market_cap_segment == "small":
            self.min_market_cap = 300_000_000
            self.max_market_cap = 2_000_000_000
            self.min_price = 5.0
        elif market_cap_segment == "mid":
            self.min_market_cap = 2_000_000_000
            self.max_market_cap = 10_000_000_000
            self.min_price = 0.50
        elif market_cap_segment == "large":
            self.min_market_cap = 10_000_000_000
            self.max_market_cap = None
            self.min_price = 0.50
        else:
            self.min_market_cap = 300_000_000
            self.max_market_cap = None
            self.min_price = 5.0

    def load_existing_model(self):
        """Load existing model if available"""
        if not self.model_path.exists():
            logger.info("No existing model found")
            return None, None

        try:
            # Load model
            model = xgb.XGBRegressor()
            model.load_model(str(self.model_path))

            # Load metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, "r") as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            logger.info(f"✓ Loaded existing model: {self.model_name}")
            logger.info(f"  Last trained: {metadata.get('last_trained_date', 'unknown')}")
            logger.info(f"  Training samples: {metadata.get('n_samples', 'unknown')}")

            return model, metadata

        except Exception as e:
            logger.error(f"Failed to load existing model: {e}")
            return None, None

    def backup_model(self):
        """Backup current model before updating"""
        if not self.model_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.models_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Backup model
        backup_model_path = backup_dir / f"{self.model_name}_{timestamp}.json"
        shutil.copy2(self.model_path, backup_model_path)

        # Backup metadata
        if self.metadata_path.exists():
            backup_meta_path = backup_dir / f"{self.model_name}_{timestamp}_metadata.json"
            shutil.copy2(self.metadata_path, backup_meta_path)

        logger.info(f"✓ Backed up model to: {backup_model_path.name}")

        # Clean old backups (keep last 10)
        backups = sorted(backup_dir.glob(f"{self.model_name}_*.json"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
                meta_backup = old_backup.with_name(old_backup.stem + "_metadata.json")
                if meta_backup.exists():
                    meta_backup.unlink()

    def load_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Load training features for date range"""
        logger.info(f"Loading features for {self.strategy} ({self.market_cap_segment} cap)")
        logger.info(f"Date range: {start_date} to {end_date}")

        query = """
        SELECT * FROM ml_training_features
        WHERE date >= %(start_date)s
          AND date <= %(end_date)s
          AND target_return IS NOT NULL
          AND close >= %(min_price)s
        ORDER BY date, ticker
        """

        params = {"start_date": start_date, "end_date": end_date, "min_price": self.min_price}

        df = pd.read_sql(query, engine, params=params)

        logger.info(f"Loaded {len(df):,} rows, {df['ticker'].nunique()} unique tickers")
        return df

    def prepare_features(self, df: pd.DataFrame):
        """Prepare features for training"""
        exclude_cols = ["ticker", "date", "target_return"]
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].fillna(0)
        y = df["target_return"]

        return X, y, feature_cols

    def get_xgboost_params(self):
        """Get strategy-specific XGBoost parameters"""
        params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "max_depth": 7,
            "learning_rate": 0.01,
            "n_estimators": 1000,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
        }

        if self.gpu_id is not None:
            params["device"] = f"cuda:{self.gpu_id}"

        return params

    def train_full(self, start_date: date = None, end_date: date = None):
        """Full retraining from scratch"""
        logger.info("=" * 60)
        logger.info("FULL RETRAINING MODE")
        logger.info("=" * 60)

        # Default to full historical range
        if start_date is None:
            start_date = date(2015, 1, 1)
        if end_date is None:
            end_date = date.today()

        # Backup existing model
        self.backup_model()

        # Load data
        df = self.load_features(start_date, end_date)
        X, y, feature_cols = self.prepare_features(df)

        # Train new model
        logger.info("Training new model from scratch...")
        params = self.get_xgboost_params()
        model = xgb.XGBRegressor(**params)
        model.fit(X, y, verbose=100)

        # Evaluate
        train_preds = model.predict(X)
        train_corr, _ = spearmanr(y, train_preds)

        # Save model
        model.save_model(str(self.model_path))

        # Save metadata
        metadata = {
            "strategy": self.strategy,
            "market_cap_segment": self.market_cap_segment,
            "last_trained_date": end_date.isoformat(),
            "training_start_date": start_date.isoformat(),
            "training_end_date": end_date.isoformat(),
            "n_samples": len(X),
            "n_features": len(feature_cols),
            "train_correlation": float(train_corr),
            "mode": "full",
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("FULL RETRAINING COMPLETE")
        logger.info(f"✓ Model saved: {self.model_path}")
        logger.info(f"✓ Training samples: {len(X):,}")
        logger.info(f"✓ Train correlation: {train_corr:.4f}")
        logger.info("=" * 60)

        return model, metadata

    def train_incremental(self, days: int = 7, n_iterations: int = 100):
        """Incremental training on recent data"""
        logger.info("=" * 60)
        logger.info("INCREMENTAL UPDATE MODE")
        logger.info("=" * 60)

        # Load existing model
        model, metadata = self.load_existing_model()

        if model is None:
            logger.warning("No existing model found. Running full retraining instead.")
            return self.train_full()

        # Backup existing model
        self.backup_model()

        # Load recent data
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Training on last {days} days of data: {start_date} to {end_date}")

        df = self.load_features(start_date, end_date)

        if len(df) == 0:
            logger.warning(f"No new data found for the last {days} days")
            return model, metadata

        X, y, feature_cols = self.prepare_features(df)

        # Incremental training: Continue from existing model
        logger.info(f"Fine-tuning existing model with {len(X):,} new samples...")
        logger.info(f"Using {n_iterations} additional iterations")

        # XGBoost doesn't natively support warm-start, but we can:
        # 1. Use xgb_model parameter to continue training
        # 2. Reduce n_estimators for incremental updates
        params = self.get_xgboost_params()
        params["n_estimators"] = n_iterations  # Fewer trees for incremental

        # Create new model that continues from existing
        model_incremental = xgb.XGBRegressor(**params)
        model_incremental.fit(X, y, verbose=100, xgb_model=model.get_booster())

        # Evaluate
        preds = model_incremental.predict(X)
        corr, _ = spearmanr(y, preds)

        # Save updated model
        model_incremental.save_model(str(self.model_path))

        # Update metadata
        metadata["last_trained_date"] = end_date.isoformat()
        metadata["last_incremental_start"] = start_date.isoformat()
        metadata["last_incremental_end"] = end_date.isoformat()
        metadata["incremental_samples"] = len(X)
        metadata["incremental_correlation"] = float(corr)
        metadata["incremental_iterations"] = n_iterations
        metadata["mode"] = "incremental"
        metadata["timestamp"] = datetime.now().isoformat()

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("INCREMENTAL UPDATE COMPLETE")
        logger.info(f"✓ Model updated: {self.model_path}")
        logger.info(f"✓ New samples: {len(X):,}")
        logger.info(f"✓ Correlation on new data: {corr:.4f}")
        logger.info("=" * 60)

        return model_incremental, metadata


def main():
    parser = argparse.ArgumentParser(description="Incremental XGBoost Training")
    parser.add_argument(
        "--strategy", type=str, required=True, choices=["growth", "value", "dividend"]
    )
    parser.add_argument("--market-cap", type=str, required=True, choices=["small", "mid", "large"])
    parser.add_argument("--mode", type=str, default="full", choices=["full", "incremental"])
    parser.add_argument("--days", type=int, default=7, help="Days of data for incremental training")
    parser.add_argument(
        "--iterations", type=int, default=100, help="Iterations for incremental training"
    )
    parser.add_argument("--gpu", type=int, default=None, help="GPU ID")
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date (YYYY-MM-DD) for full training"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date (YYYY-MM-DD) for full training"
    )

    args = parser.parse_args()

    # Parse dates
    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None

    # Create trainer
    trainer = IncrementalXGBoostTrainer(
        strategy=args.strategy, market_cap_segment=args.market_cap, gpu_id=args.gpu
    )

    # Train
    if args.mode == "full":
        model, metadata = trainer.train_full(start_date, end_date)
    else:
        model, metadata = trainer.train_incremental(days=args.days, n_iterations=args.iterations)

    logger.info("Training complete!")


if __name__ == "__main__":
    main()
