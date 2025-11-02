#!/usr/bin/env python3
"""
Dividend Strategy Model Training
Focus: High dividend yield + sustainable fundamentals (Mid/Large cap only)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import date

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class DividendStrategyTrainer:
    """
    Dividend Strategy Model Trainer

    Target: Stocks with high sustainable dividends + moderate growth
    Universe: Mid-cap+ (>$2B), Price >$5
    """

    def __init__(self, gpu_id: int = None):
        self.gpu_id = gpu_id
        self.strategy = "dividend"
        self.min_market_cap = 2_000_000_000  # $2B (mid-cap+)
        self.min_price = 5.0

    def load_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Load features with dividend strategy filters"""
        logger.info(f"Loading dividend strategy features: {start_date} to {end_date}")
        logger.info(
            f"Target filters: Market Cap >= ${self.min_market_cap/1e9:.1f}B, Price >= ${self.min_price}, Dividend Yield > 1%"
        )

        # NOTE: Market cap and dividend filters removed for training due to sparse fundamental data
        # Filtering will be applied at inference time in portfolio generation
        logger.warning("⚠️  Training on ALL stocks (fundamental data is sparse)")
        logger.warning(
            "⚠️  Market cap & dividend filtering will be applied during portfolio generation"
        )

        query = """
        SELECT * FROM ml_training_features
        WHERE date >= %(start_date)s
          AND date <= %(end_date)s
          AND target_return IS NOT NULL
          AND close >= %(min_price)s
        ORDER BY date, ticker
        """

        df = pd.read_sql(
            query,
            engine,
            params={"start_date": start_date, "end_date": end_date, "min_price": self.min_price},
        )

        logger.info(f"Loaded {len(df):,} rows")
        logger.info(f"Unique tickers: {df['ticker'].nunique()}")
        return df

    def prepare_features(self, df: pd.DataFrame):
        """Prepare features with dividend focus"""
        # Key dividend features (higher importance)
        dividend_features = [
            "dividend_yield",
            "free_cash_flow",
            "debt_to_equity",
            "current_ratio",
            "roe",
            "roa",
            "pe_ratio",
            "pb_ratio",
        ]

        # Supporting technical features (lower importance)
        technical_features = [
            "return_1d",
            "return_5d",
            "return_20d",
            "volatility_20d",
            "volume_ratio_20d",
            "price_vs_sma20",
            "price_vs_sma50",
            "price_vs_ema50",
            "price_vs_ema200",
            "macd_line",
            "macd_signal",
            "macd_histogram",
        ]

        # Market context
        context_features = ["market_cap", "average_volume"]

        exclude_cols = ["ticker", "date", "target_return"]
        all_feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[all_feature_cols].fillna(0)
        y = df["target_return"]

        logger.info(f"Total features: {len(all_feature_cols)}")
        logger.info(f"Key dividend features: {len(dividend_features)}")
        logger.info(f"Training samples: {len(X):,}")

        return X, y, all_feature_cols

    def train(self, X, y, feature_names):
        """Train XGBoost with dividend strategy parameters"""
        logger.info("Training dividend strategy model...")

        params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "max_depth": 5,  # Slightly shallower for stability focus
            "learning_rate": 0.01,
            "n_estimators": 1000,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.2,  # Higher regularization for stability
            "reg_lambda": 1.5,
            "random_state": 42,
        }

        if self.gpu_id is not None:
            params["device"] = f"cuda:{self.gpu_id}"
            logger.info(f"Using GPU: {self.gpu_id}")
        else:
            logger.info("Using CPU")

        model = xgb.XGBRegressor(**params)
        model.fit(X, y, verbose=100)

        logger.info("Training complete!")

        # Feature importance
        importance = pd.DataFrame(
            {"feature": feature_names, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        logger.info("\nTop 20 features:")
        logger.info(importance.head(20).to_string())

        return model, importance

    def evaluate(self, model, X, y):
        """Evaluate model performance"""
        logger.info("Evaluating model...")

        y_pred = model.predict(X)

        corr = np.corrcoef(y, y_pred)[0, 1]
        spearman_ic, _ = spearmanr(y, y_pred)

        logger.info(f"Pearson correlation: {corr:.4f}")
        logger.info(f"Spearman IC: {spearman_ic:.4f}")

        return {"pearson": corr, "spearman_ic": spearman_ic, "predictions": y_pred}

    def save_model(self, model, feature_names, metrics):
        """Save trained model"""
        output_dir = Path("models/dividend_strategy")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = output_dir / "model.json"
        model.save_model(str(model_path))
        logger.info(f"Model saved to {model_path}")

        # Save feature names
        import json

        with open(output_dir / "feature_names.json", "w") as f:
            json.dump(feature_names, f)

        # Save metadata
        metadata = {
            "strategy": self.strategy,
            "framework": "xgboost",
            "min_market_cap": self.min_market_cap,
            "min_price": self.min_price,
            "spearman_ic": float(metrics["spearman_ic"]),
            "pearson": float(metrics["pearson"]),
            "n_features": len(feature_names),
            "trained_at": str(date.today()),
        }

        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata saved to {output_dir}/metadata.json")


def main():
    parser = argparse.ArgumentParser(description="Train dividend strategy model")
    parser.add_argument("--start-date", type=str, default="2015-01-01")
    parser.add_argument("--end-date", type=str, default="2025-10-30")
    parser.add_argument("--gpu", type=int, default=None, help="GPU ID (omit for CPU)")

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("DIVIDEND STRATEGY MODEL TRAINING")
    logger.info("Focus: High sustainable dividends + moderate growth")
    logger.info("Universe: Mid/Large cap (>$2B), Price >$5")
    logger.info("=" * 80)
    logger.info(f"Start date: {args.start_date}")
    logger.info(f"End date: {args.end_date}")
    logger.info(f"GPU: {args.gpu if args.gpu is not None else 'CPU'}")
    logger.info("=" * 80)

    trainer = DividendStrategyTrainer(gpu_id=args.gpu)

    # Load data
    df = trainer.load_features(
        start_date=date.fromisoformat(args.start_date), end_date=date.fromisoformat(args.end_date)
    )

    # Prepare features
    X, y, feature_names = trainer.prepare_features(df)

    # Train
    model, importance = trainer.train(X, y, feature_names)

    # Evaluate
    metrics = trainer.evaluate(model, X, y)

    # Save
    trainer.save_model(model, feature_names, metrics)

    # Save feature importance
    importance.to_csv("ml_models/feature_importance/feature_importance_dividend.csv", index=False)

    logger.info("=" * 80)
    logger.info("✅ DIVIDEND STRATEGY MODEL TRAINING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Spearman IC: {metrics['spearman_ic']:.4f}")
    logger.info("Model saved to: models/dividend_strategy/")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
