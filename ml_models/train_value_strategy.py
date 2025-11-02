#!/usr/bin/env python3
"""
Value Strategy Model Training
Focus: Undervalued quality stocks with mean reversion potential
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


class ValueStrategyTrainer:
    """
    Value Strategy Model Trainer

    Target: Undervalued quality stocks with mean reversion potential
    Universe: Small-cap+ (>$300M), Price >$5 for small-caps
    """

    def __init__(self, gpu_id: int = None, market_cap_segment: str = "all"):
        self.gpu_id = gpu_id
        self.strategy = "value"
        self.market_cap_segment = market_cap_segment

        # Set filters based on segment
        if market_cap_segment == "small":
            self.min_market_cap = 300_000_000  # $300M
            self.max_market_cap = 2_000_000_000  # $2B
            self.min_price = 5.0  # Higher price filter for small-caps
        elif market_cap_segment == "mid":
            self.min_market_cap = 2_000_000_000  # $2B
            self.max_market_cap = 10_000_000_000  # $10B
            self.min_price = 0.50
        elif market_cap_segment == "large":
            self.min_market_cap = 10_000_000_000  # $10B
            self.max_market_cap = None
            self.min_price = 0.50
        else:  # all
            self.min_market_cap = 300_000_000  # $300M+
            self.max_market_cap = None
            self.min_price = 5.0  # Conservative minimum

    def load_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Load features with value strategy filters"""
        logger.info(
            f"Loading value strategy features ({self.market_cap_segment} cap): {start_date} to {end_date}"
        )
        logger.info(
            f"Target filters: Market Cap >= ${self.min_market_cap/1e9:.1f}B"
            f"{f', <= ${self.max_market_cap/1e9:.1f}B' if self.max_market_cap else ''}, "
            f"Price >= ${self.min_price}"
        )

        # NOTE: Market cap and valuation filters removed for training due to sparse fundamental data
        # Filtering will be applied at inference time in portfolio generation
        logger.warning("⚠️  Training on ALL stocks (fundamental data is sparse)")
        logger.warning(
            "⚠️  Market cap & valuation filtering will be applied during portfolio generation"
        )

        query = f"""
        SELECT * FROM ml_training_features
        WHERE date >= %(start_date)s
          AND date <= %(end_date)s
          AND target_return IS NOT NULL
          AND close >= %(min_price)s
        ORDER BY date, ticker
        """

        params = {"start_date": start_date, "end_date": end_date, "min_price": self.min_price}

        df = pd.read_sql(query, engine, params=params)

        logger.info(f"Loaded {len(df):,} rows")
        logger.info(f"Unique tickers: {df['ticker'].nunique()}")
        return df

    def prepare_features(self, df: pd.DataFrame):
        """Prepare features with value focus"""
        # Key value features (higher importance)
        value_features = [
            "pe_ratio",
            "pb_ratio",
            "ps_ratio",  # Valuation multiples (lower = better)
            "pcf_ratio",
            "p_fcf_ratio",
            "ev_to_ebitda",
            "ev_to_sales",
            "free_cash_flow",  # Cash generation
            "current_ratio",
            "quick_ratio",
            "cash_ratio",  # Balance sheet strength
            "debt_to_equity",  # Leverage
            "roe",
            "roa",  # Profitability
        ]

        # Mean reversion indicators
        reversion_features = [
            "return_20d",  # Recent underperformance
            "price_vs_sma20",
            "price_vs_sma50",
            "price_vs_ema50",
            "price_vs_ema200",
            "daily_range",
            "range_20d",
        ]

        # Quality metrics
        quality_features = [
            "eps",
            "dividend_yield",
            "market_cap",
            "average_volume",
        ]

        # Technical context (lower weight)
        technical_features = [
            "return_1d",
            "return_5d",
            "volatility_20d",
            "volume_ratio_20d",
            "macd_histogram",
        ]

        exclude_cols = ["ticker", "date", "target_return"]
        all_feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[all_feature_cols].fillna(0)
        y = df["target_return"]

        logger.info(f"Total features: {len(all_feature_cols)}")
        logger.info(f"Training samples: {len(X):,}")

        return X, y, all_feature_cols

    def train(self, X, y, feature_names):
        """Train XGBoost with value strategy parameters"""
        logger.info("Training value strategy model...")

        params = {
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "max_depth": 6,
            "learning_rate": 0.01,
            "n_estimators": 1000,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.15,  # Moderate regularization
            "reg_lambda": 1.2,
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
        model_name = f"value_{self.market_cap_segment}cap"
        output_dir = Path(f"models/{model_name}")
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
            "market_cap_segment": self.market_cap_segment,
            "framework": "xgboost",
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap,
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
    parser = argparse.ArgumentParser(description="Train value strategy model")
    parser.add_argument("--start-date", type=str, default="2015-01-01")
    parser.add_argument("--end-date", type=str, default="2025-10-30")
    parser.add_argument(
        "--market-cap",
        type=str,
        default="all",
        choices=["small", "mid", "large", "all"],
        help="Market cap segment to train on",
    )
    parser.add_argument("--gpu", type=int, default=None, help="GPU ID (omit for CPU)")

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("VALUE STRATEGY MODEL TRAINING")
    logger.info(f"Market Cap Segment: {args.market_cap.upper()}")
    logger.info("Focus: Undervalued quality stocks + mean reversion")
    logger.info("=" * 80)
    logger.info(f"Start date: {args.start_date}")
    logger.info(f"End date: {args.end_date}")
    logger.info(f"GPU: {args.gpu if args.gpu is not None else 'CPU'}")
    logger.info("=" * 80)

    trainer = ValueStrategyTrainer(gpu_id=args.gpu, market_cap_segment=args.market_cap)

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
    importance.to_csv(
        f"ml_models/feature_importance/feature_importance_value_{args.market_cap}cap.csv",
        index=False,
    )

    logger.info("=" * 80)
    logger.info(f"✅ VALUE STRATEGY MODEL TRAINING COMPLETE ({args.market_cap.upper()} CAP)!")
    logger.info("=" * 80)
    logger.info(f"Spearman IC: {metrics['spearman_ic']:.4f}")
    logger.info(f"Model saved to: models/value_{args.market_cap}cap/")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
