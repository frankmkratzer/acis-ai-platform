#!/usr/bin/env python3
"""
Auto-Training Orchestrator
Trains all ML models (XGBoost) for production use

Runs daily after market close to retrain models with latest data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import subprocess
from datetime import date, datetime
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from utils import get_logger

logger = get_logger(__name__)

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}

# Model configurations
ML_MODEL_CONFIGS = [
    # Growth models
    {"strategy": "growth", "market_cap": "small", "name": "growth_smallcap"},
    {"strategy": "growth", "market_cap": "mid", "name": "growth_midcap"},
    {"strategy": "growth", "market_cap": "large", "name": "growth_largecap"},
    # Value models
    {"strategy": "value", "market_cap": "small", "name": "value_smallcap"},
    {"strategy": "value", "market_cap": "mid", "name": "value_midcap"},
    {"strategy": "value", "market_cap": "large", "name": "value_largecap"},
    # Dividend model
    {"strategy": "dividend", "market_cap": "mid", "name": "dividend_strategy"},
]


def refresh_ml_features():
    """Refresh the ml_training_features materialized view"""
    logger.info("=" * 80)
    logger.info("REFRESHING ML TRAINING FEATURES")
    logger.info("=" * 80)

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        start_time = datetime.now()
        logger.info("Starting REFRESH MATERIALIZED VIEW...")

        cursor.execute("REFRESH MATERIALIZED VIEW ml_training_features")
        conn.commit()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Materialized view refreshed in {duration:.1f} seconds")

        # Get row count
        cursor.execute("SELECT COUNT(*) FROM ml_training_features")
        count = cursor.fetchone()[0]
        logger.info(f"Total feature rows: {count:,}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to refresh materialized view: {e}")
        return False

    finally:
        if conn:
            conn.close()


def train_ml_model(config: Dict, start_date: str, end_date: str, gpu: bool = True) -> Dict:
    """Train a single ML model"""
    strategy = config["strategy"]
    market_cap = config["market_cap"]
    model_name = config["name"]

    logger.info("=" * 80)
    logger.info(f"TRAINING ML MODEL: {model_name}")
    logger.info(f"Strategy: {strategy}, Market Cap: {market_cap}")
    logger.info(f"Date Range: {start_date} to {end_date}")
    logger.info("=" * 80)

    # Determine training script
    if strategy == "dividend":
        script = Path(__file__).parent.parent / "ml_models" / "train_dividend_strategy.py"
    elif strategy == "growth":
        script = Path(__file__).parent.parent / "ml_models" / "train_growth_strategy.py"
    elif strategy == "value":
        script = Path(__file__).parent.parent / "ml_models" / "train_value_strategy.py"
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Build command
    cmd = ["python", str(script), "--start-date", start_date, "--end-date", end_date]

    # Add market cap for growth/value
    if strategy in ["growth", "value"]:
        cmd.extend(["--market-cap", market_cap])

    # Add GPU if enabled
    if gpu:
        cmd.extend(["--gpu", "0"])

    # Run training
    start_time = datetime.now()

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        duration = (datetime.now() - start_time).total_seconds() / 60

        logger.info(f"✅ {model_name} trained successfully in {duration:.1f} minutes")

        return {
            "model_name": model_name,
            "strategy": strategy,
            "market_cap": market_cap,
            "status": "success",
            "duration_minutes": duration,
            "start_date": start_date,
            "end_date": end_date,
        }

    except subprocess.CalledProcessError as e:
        duration = (datetime.now() - start_time).total_seconds() / 60
        logger.error(f"❌ {model_name} training failed after {duration:.1f} minutes")
        logger.error(f"Error: {e.stderr}")

        return {
            "model_name": model_name,
            "strategy": strategy,
            "market_cap": market_cap,
            "status": "failed",
            "duration_minutes": duration,
            "error": str(e.stderr),
        }


def log_training_run(results: List[Dict]):
    """Log training run results to database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for result in results:
            cursor.execute(
                """
                INSERT INTO auto_training_log (
                    model_name, strategy, market_cap, status,
                    duration_minutes, trained_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    result["model_name"],
                    result["strategy"],
                    result["market_cap"],
                    result["status"],
                    result["duration_minutes"],
                    datetime.now(),
                ),
            )

        conn.commit()
        logger.info("Training results logged to database")

    except Exception as e:
        logger.warning(f"Could not log to database (table may not exist): {e}")

    finally:
        if conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="Auto-train all ML models")
    parser.add_argument("--start-date", type=str, default="2015-01-01", help="Training start date")
    parser.add_argument(
        "--end-date", type=str, default=None, help="Training end date (default: yesterday)"
    )
    parser.add_argument("--gpu", action="store_true", default=True, help="Use GPU for training")
    parser.add_argument(
        "--refresh-features",
        action="store_true",
        default=False,
        help="Refresh ml_training_features before training",
    )
    parser.add_argument(
        "--models", nargs="+", default=None, help="Specific models to train (default: all)"
    )

    args = parser.parse_args()

    # Default end date to yesterday (don't include today's incomplete data)
    if args.end_date is None:
        from datetime import timedelta

        args.end_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info("=" * 80)
    logger.info("AUTO-TRAINING ORCHESTRATOR")
    logger.info("=" * 80)
    logger.info(f"Start Date: {args.start_date}")
    logger.info(f"End Date: {args.end_date}")
    logger.info(f"GPU Enabled: {args.gpu}")
    logger.info("=" * 80)

    # Optionally refresh features
    if args.refresh_features:
        if not refresh_ml_features():
            logger.error("Failed to refresh features, aborting training")
            return 1

    # Filter models if specified
    models_to_train = ML_MODEL_CONFIGS
    if args.models:
        models_to_train = [m for m in ML_MODEL_CONFIGS if m["name"] in args.models]
        logger.info(f"Training {len(models_to_train)} specified models")
    else:
        logger.info(f"Training all {len(models_to_train)} models")

    # Train each model
    results = []
    for config in models_to_train:
        result = train_ml_model(
            config, start_date=args.start_date, end_date=args.end_date, gpu=args.gpu
        )
        results.append(result)

    # Summary
    logger.info("=" * 80)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 80)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]

    logger.info(f"✅ Successful: {len(successful)}/{len(results)}")
    logger.info(f"❌ Failed: {len(failed)}/{len(results)}")

    if successful:
        logger.info("\nSuccessful models:")
        for r in successful:
            logger.info(f"  - {r['model_name']} ({r['duration_minutes']:.1f} min)")

    if failed:
        logger.info("\nFailed models:")
        for r in failed:
            logger.info(f"  - {r['model_name']}")

    # Log results to database
    log_training_run(results)

    logger.info("=" * 80)
    logger.info("AUTO-TRAINING COMPLETE")
    logger.info("=" * 80)

    # Return exit code based on results
    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
