#!/usr/bin/env python3
"""
Auto-train all RL (PPO) models for portfolio optimization

This script trains RL agents for all strategy/market-cap combinations:
- Growth: small, mid, large cap
- Value: small, mid, large cap
- Dividend: mid/large cap combined

Each RL agent learns optimal portfolio allocation from the candidates
selected by the corresponding ML model.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import subprocess
from datetime import datetime
from typing import Dict, List

import psycopg2

from utils import get_logger

logger = get_logger(__name__)

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}

# RL Model Configurations
# Note: These should match the ML models that have been trained
RL_MODEL_CONFIGS = [
    {"strategy": "growth", "market_cap": "small", "name": "ppo_hybrid_growth_smallcap"},
    {"strategy": "growth", "market_cap": "mid", "name": "ppo_hybrid_growth_midcap"},
    {"strategy": "growth", "market_cap": "large", "name": "ppo_hybrid_growth_largecap"},
    {"strategy": "value", "market_cap": "small", "name": "ppo_hybrid_value_smallcap"},
    {"strategy": "value", "market_cap": "mid", "name": "ppo_hybrid_value_midcap"},
    {"strategy": "value", "market_cap": "large", "name": "ppo_hybrid_value_largecap"},
    {"strategy": "dividend", "market_cap": "mid", "name": "ppo_hybrid_dividend_strategy"},
]


def log_training_result(result: Dict):
    """Log training result to database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO auto_training_log
            (model_name, strategy, market_cap, status, duration_minutes, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (
                result["model_name"],
                result["strategy"],
                result.get("market_cap"),
                result["status"],
                result.get("duration_minutes"),
                result.get("error_message"),
            ),
        )

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Failed to log training result: {e}")


def train_rl_model(
    config: Dict,
    timesteps: int = 1_000_000,
    eval_freq: int = 10_000,
    save_freq: int = 50_000,
    device: str = "cpu",
) -> Dict:
    """Train a single RL model"""

    strategy = config["strategy"]
    market_cap = config["market_cap"]
    model_name = config["name"]

    logger.info("=" * 80)
    logger.info(f"TRAINING RL MODEL: {model_name}")
    logger.info(f"Strategy: {strategy}, Market Cap: {market_cap}")
    logger.info("=" * 80)

    # Build command
    script = Path(__file__).parent.parent / "rl_trading" / "train_hybrid_ppo.py"

    cmd = [
        "python",
        str(script),
        "--strategy",
        strategy,
        "--market-cap",
        market_cap,
        "--timesteps",
        str(timesteps),
        "--eval-freq",
        str(eval_freq),
        "--save-freq",
        str(save_freq),
        "--device",
        device,
    ]

    logger.info(f"Command: {' '.join(cmd)}")

    start_time = datetime.now()

    try:
        # Run training
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        logger.info(f"✅ Successfully trained {model_name} in {duration:.2f} minutes")

        return {
            "model_name": model_name,
            "strategy": strategy,
            "market_cap": market_cap,
            "status": "success",
            "duration_minutes": duration,
        }

    except subprocess.CalledProcessError as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60

        error_msg = f"Exit code {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        logger.error(f"❌ Failed to train {model_name}: {error_msg}")

        return {
            "model_name": model_name,
            "strategy": strategy,
            "market_cap": market_cap,
            "status": "failed",
            "duration_minutes": duration,
            "error_message": error_msg[:1000],  # Truncate long errors
        }


def main():
    parser = argparse.ArgumentParser(description="Auto-train all RL models")
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        help="Specific models to train (e.g., ppo_hybrid_growth_midcap)",
    )
    parser.add_argument(
        "--timesteps", type=int, default=1_000_000, help="Total training timesteps (default: 1M)"
    )
    parser.add_argument("--eval-freq", type=int, default=10_000, help="Evaluation frequency")
    parser.add_argument("--save-freq", type=int, default=50_000, help="Checkpoint save frequency")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cuda", "cpu"],
        help="Training device (default: cpu)",
    )

    args = parser.parse_args()

    # Filter models if specific ones requested
    models_to_train = RL_MODEL_CONFIGS
    if args.models:
        models_to_train = [m for m in RL_MODEL_CONFIGS if m["name"] in args.models]
        if not models_to_train:
            logger.error(f"No matching models found for: {args.models}")
            logger.info(f"Available models: {[m['name'] for m in RL_MODEL_CONFIGS]}")
            return 1

    logger.info("=" * 80)
    logger.info("ACIS AI - RL MODEL AUTO-TRAINING")
    logger.info("=" * 80)
    logger.info(f"Training {len(models_to_train)} RL models")
    logger.info(f"Timesteps: {args.timesteps:,}")
    logger.info(f"Device: {args.device}")
    logger.info("=" * 80)
    logger.info("")

    results = []
    start_time = datetime.now()

    for i, config in enumerate(models_to_train, 1):
        logger.info(f"[{i}/{len(models_to_train)}] Training {config['name']}...")

        result = train_rl_model(
            config,
            timesteps=args.timesteps,
            eval_freq=args.eval_freq,
            save_freq=args.save_freq,
            device=args.device,
        )

        results.append(result)
        log_training_result(result)

        logger.info("")

    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds() / 60

    # Print summary
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info("=" * 80)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total models: {len(results)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total duration: {total_duration:.2f} minutes")
    logger.info("")

    for result in results:
        status_symbol = "✅" if result["status"] == "success" else "❌"
        logger.info(
            f"{status_symbol} {result['model_name']}: {result['status']} "
            f"({result.get('duration_minutes', 0):.2f} min)"
        )

    logger.info("=" * 80)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
