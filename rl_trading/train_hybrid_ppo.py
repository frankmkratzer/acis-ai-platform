#!/usr/bin/env python3
"""
Train PPO agent with Hybrid ML+RL Environment

Architecture:
1. ML Model (XGBoost) → Top N candidates
2. RL Agent (PPO) → Optimal portfolio weights

Strategies: growth, value, dividend
Market Caps: small, mid, large
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_trading.hybrid_portfolio_env import HybridPortfolioEnv
from utils import get_logger

logger = get_logger(__name__)


def create_env(strategy: str, market_cap_segment: str, train_mode: bool = True):
    """Create environment instance"""
    # Now with historical market cap backfilled, use proper train/val split
    if train_mode:
        # Training: 2015-2023 (about 8 years of data, matching ML training)
        start_date = "2015-01-01"
        end_date = "2023-12-31"
    else:
        # Evaluation: 2024-2025 (out-of-sample)
        start_date = "2024-01-01"
        end_date = "2025-10-27"

    env = HybridPortfolioEnv(
        strategy=strategy,
        market_cap_segment=market_cap_segment,
        start_date=start_date,
        end_date=end_date,
        ml_top_n=100,  # ML selects top 100
        rl_max_positions=50,  # RL allocates to 50
        rebalance_frequency=20,  # Rebalance every 20 trading days (monthly)
        transaction_cost=0.001,
        position_limits=(0.01, 0.10),
        min_ml_score=0.01,
    )

    return env


def get_strategy_hyperparams(strategy: str):
    """Get strategy-specific hyperparameters"""

    base_params = {
        "learning_rate": 3e-4,
        "n_steps": 2048,
        "batch_size": 64,
        "n_epochs": 10,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_range": 0.2,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        "max_grad_norm": 0.5,
        "verbose": 1,
    }

    # Strategy-specific adjustments
    if strategy == "dividend":
        # Dividend: Lower volatility, stable allocation
        base_params["ent_coef"] = 0.005  # Less exploration
        base_params["gamma"] = 0.98  # Less long-term focused
        logger.info("Using DIVIDEND strategy hyperparameters (stable, low volatility)")

    elif strategy == "growth":
        # Growth: More exploration, momentum-focused
        base_params["ent_coef"] = 0.02  # More exploration
        base_params["gamma"] = 0.995  # More long-term focused
        logger.info("Using GROWTH strategy hyperparameters (momentum, exploration)")

    elif strategy == "value":
        # Value: Moderate exploration, mean reversion
        base_params["ent_coef"] = 0.01  # Moderate exploration
        base_params["gamma"] = 0.99  # Standard discounting
        logger.info("Using VALUE strategy hyperparameters (mean reversion)")

    return base_params


def train(
    strategy: str,
    market_cap_segment: str,
    total_timesteps: int = 1_000_000,
    eval_freq: int = 10_000,
    save_freq: int = 50_000,
    device: str = "cuda",
):
    """Train PPO agent"""

    logger.info("=" * 80)
    logger.info("HYBRID ML+RL PORTFOLIO TRAINING")
    logger.info(f"Strategy: {strategy.upper()}")
    logger.info(f"Market Cap Segment: {market_cap_segment.upper()}")
    logger.info("=" * 80)

    # Create model name
    model_name = f"ppo_hybrid_{strategy}_{market_cap_segment}cap"
    output_dir = Path("models") / model_name
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Model will be saved to: {output_dir}")

    # Create environments
    logger.info("Creating training environment...")
    train_env = DummyVecEnv([lambda: create_env(strategy, market_cap_segment, train_mode=True)])

    logger.info("Creating evaluation environment...")
    eval_env = DummyVecEnv([lambda: create_env(strategy, market_cap_segment, train_mode=False)])

    # Get strategy-specific hyperparameters
    hyperparams = get_strategy_hyperparams(strategy)

    # Create PPO model
    logger.info("Initializing PPO model...")
    logger.info(f"Hyperparameters: {hyperparams}")

    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        **hyperparams,
        device=device,
        tensorboard_log=str(output_dir / "tensorboard"),
    )

    # Setup callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq,
        save_path=str(output_dir / "checkpoints"),
        name_prefix=model_name,
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(output_dir / "best_model"),
        log_path=str(output_dir / "eval_logs"),
        eval_freq=eval_freq,
        deterministic=True,
        render=False,
        n_eval_episodes=5,
    )

    # Train
    logger.info("=" * 80)
    logger.info("Starting training...")
    logger.info(f"Total timesteps: {total_timesteps:,}")
    logger.info(f"Evaluation frequency: {eval_freq:,}")
    logger.info(f"Checkpoint frequency: {save_freq:,}")
    logger.info("=" * 80)

    start_time = datetime.now()

    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback],
        log_interval=10,
        progress_bar=True,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60

    # Save final model
    final_model_path = output_dir / "final_model.zip"
    model.save(str(final_model_path))

    logger.info("=" * 80)
    logger.info("✅ TRAINING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Training duration: {duration:.2f} minutes")
    logger.info(f"Final model saved to: {final_model_path}")
    logger.info(f"Best model saved to: {output_dir / 'best_model'}")
    logger.info(f"Tensorboard logs: {output_dir / 'tensorboard'}")
    logger.info("=" * 80)

    # Save metadata
    import json

    metadata = {
        "strategy": strategy,
        "market_cap_segment": market_cap_segment,
        "model_name": model_name,
        "total_timesteps": total_timesteps,
        "training_duration_minutes": duration,
        "hyperparameters": hyperparams,
        "train_date_range": "2020-01-01 to 2023-12-31",
        "eval_date_range": "2024-01-01 to 2025-10-27",
        "ml_top_n": 100,
        "rl_max_positions": 50,
        "trained_at": str(datetime.now()),
        "device": device,
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to: {output_dir / 'metadata.json'}")

    return model


def main():
    parser = argparse.ArgumentParser(description="Train Hybrid ML+RL PPO Agent")
    parser.add_argument(
        "--strategy",
        type=str,
        default="growth",
        choices=["dividend", "growth", "value"],
        help="Investment strategy",
    )
    parser.add_argument(
        "--market-cap",
        type=str,
        default="mid",
        choices=["small", "mid", "large"],
        help="Market cap segment",
    )
    parser.add_argument("--timesteps", type=int, default=1_000_000, help="Total training timesteps")
    parser.add_argument("--eval-freq", type=int, default=10_000, help="Evaluation frequency")
    parser.add_argument("--save-freq", type=int, default=50_000, help="Checkpoint save frequency")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cuda", "cpu"],
        help="Training device (default: cpu, recommended for PPO+MLP)",
    )

    args = parser.parse_args()

    # Adjust market cap for dividend strategy
    if args.strategy == "dividend":
        if args.market_cap == "small":
            logger.warning("⚠️  Dividend strategy requires mid/large cap. Overriding to 'mid'")
            args.market_cap = "mid"

    train(
        strategy=args.strategy,
        market_cap_segment=args.market_cap,
        total_timesteps=args.timesteps,
        eval_freq=args.eval_freq,
        save_freq=args.save_freq,
        device=args.device,
    )


if __name__ == "__main__":
    main()
