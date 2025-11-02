#!/usr/bin/env python3
"""
Incremental PPO RL Agent Training

Supports both:
1. Full retraining (from scratch on entire historical period)
2. Incremental updates (fine-tuning existing agent on recent data)

Usage:
    # Full retraining (monthly)
    python incremental_train_ppo.py --strategy growth --market-cap mid --mode full --timesteps 1000000

    # Incremental update (daily/weekly)
    python incremental_train_ppo.py --strategy growth --market-cap mid --mode incremental --timesteps 50000
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import json
import shutil
from datetime import date, datetime

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_trading.hybrid_portfolio_env import HybridPortfolioEnv
from utils import get_logger

logger = get_logger(__name__)


class IncrementalPPOTrainer:
    """
    Incremental PPO Trainer with Warm-Start Capability

    Features:
    - Load existing agent checkpoints
    - Fine-tune on new data (incremental)
    - Full retraining option
    - Agent versioning and rollback
    """

    def __init__(
        self,
        strategy: str,
        market_cap_segment: str,
        device: str = "auto",
        models_dir: str = "models/rl",
    ):
        self.strategy = strategy
        self.market_cap_segment = market_cap_segment
        self.device = device
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Model naming
        self.model_name = f"ppo_hybrid_{strategy}_{market_cap_segment}cap"
        self.model_path = self.models_dir / f"{self.model_name}.zip"
        self.metadata_path = self.models_dir / f"{self.model_name}_metadata.json"

    def load_existing_agent(self):
        """Load existing PPO agent if available"""
        if not self.model_path.exists():
            logger.info("No existing agent found")
            return None, None

        try:
            # Load agent
            agent = PPO.load(str(self.model_path), device=self.device)

            # Load metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, "r") as f:
                    metadata = json.load(f)
            else:
                metadata = {}

            logger.info(f"✓ Loaded existing agent: {self.model_name}")
            logger.info(f"  Last trained: {metadata.get('last_trained_date', 'unknown')}")
            logger.info(f"  Total timesteps: {metadata.get('total_timesteps', 'unknown')}")

            return agent, metadata

        except Exception as e:
            logger.error(f"Failed to load existing agent: {e}")
            return None, None

    def backup_agent(self):
        """Backup current agent before updating"""
        if not self.model_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.models_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Backup agent
        backup_model_path = backup_dir / f"{self.model_name}_{timestamp}.zip"
        shutil.copy2(self.model_path, backup_model_path)

        # Backup metadata
        if self.metadata_path.exists():
            backup_meta_path = backup_dir / f"{self.model_name}_{timestamp}_metadata.json"
            shutil.copy2(self.metadata_path, backup_meta_path)

        logger.info(f"✓ Backed up agent to: {backup_model_path.name}")

        # Clean old backups (keep last 10)
        backups = sorted(backup_dir.glob(f"{self.model_name}_*.zip"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
                meta_backup = old_backup.with_name(old_backup.stem + "_metadata.json")
                if meta_backup.exists():
                    meta_backup.unlink()

    def create_env(self, train_mode: bool = True, start_date: str = None, end_date: str = None):
        """Create training or evaluation environment"""
        if train_mode:
            # Training defaults
            if start_date is None:
                start_date = "2015-01-01"
            if end_date is None:
                end_date = "2023-12-31"
        else:
            # Evaluation defaults
            if start_date is None:
                start_date = "2024-01-01"
            if end_date is None:
                end_date = "2025-10-27"

        env = HybridPortfolioEnv(
            strategy=self.strategy,
            market_cap_segment=self.market_cap_segment,
            start_date=start_date,
            end_date=end_date,
            ml_top_n=100,
            rl_max_positions=50,
            rebalance_frequency=20,
            transaction_cost=0.001,
            position_limits=(0.01, 0.10),
            min_ml_score=0.01,
        )

        return DummyVecEnv([lambda: env])

    def get_ppo_params(self):
        """Get strategy-specific PPO hyperparameters"""
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
            "device": self.device,
        }

        # Strategy-specific adjustments
        if self.strategy == "dividend":
            base_params["ent_coef"] = 0.005
            base_params["gamma"] = 0.98
        elif self.strategy == "growth":
            base_params["ent_coef"] = 0.02
            base_params["gamma"] = 0.995
        elif self.strategy == "value":
            base_params["ent_coef"] = 0.01
            base_params["gamma"] = 0.99

        return base_params

    def train_full(
        self, total_timesteps: int = 1_000_000, start_date: str = None, end_date: str = None
    ):
        """Full retraining from scratch"""
        logger.info("=" * 60)
        logger.info("FULL RL RETRAINING MODE")
        logger.info("=" * 60)

        # Backup existing agent
        self.backup_agent()

        # Create environment
        env = self.create_env(train_mode=True, start_date=start_date, end_date=end_date)

        # Train new agent
        logger.info("Training new PPO agent from scratch...")
        params = self.get_ppo_params()
        agent = PPO("MlpPolicy", env, **params)

        # Train
        agent.learn(total_timesteps=total_timesteps)

        # Save agent
        agent.save(str(self.model_path))

        # Save metadata
        metadata = {
            "strategy": self.strategy,
            "market_cap_segment": self.market_cap_segment,
            "last_trained_date": date.today().isoformat(),
            "training_start_date": start_date or "2015-01-01",
            "training_end_date": end_date or "2023-12-31",
            "total_timesteps": total_timesteps,
            "mode": "full",
            "timestamp": datetime.now().isoformat(),
        }

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("FULL RL RETRAINING COMPLETE")
        logger.info(f"✓ Agent saved: {self.model_path}")
        logger.info(f"✓ Total timesteps: {total_timesteps:,}")
        logger.info("=" * 60)

        return agent, metadata

    def train_incremental(
        self, timesteps: int = 50_000, start_date: str = None, end_date: str = None
    ):
        """Incremental training on recent data"""
        logger.info("=" * 60)
        logger.info("INCREMENTAL RL UPDATE MODE")
        logger.info("=" * 60)

        # Load existing agent
        agent, metadata = self.load_existing_agent()

        if agent is None:
            logger.warning("No existing agent found. Running full retraining instead.")
            return self.train_full(total_timesteps=timesteps)

        # Backup existing agent
        self.backup_agent()

        # Create environment with recent data
        if start_date is None:
            # Default: use last 2 years for incremental training
            start_date = "2022-01-01"
        if end_date is None:
            end_date = "2023-12-31"

        logger.info(f"Fine-tuning on period: {start_date} to {end_date}")

        env = self.create_env(train_mode=True, start_date=start_date, end_date=end_date)

        # Set environment for existing agent
        agent.set_env(env)

        # Continue training (warm-start)
        logger.info(f"Continuing training for {timesteps:,} additional timesteps...")
        agent.learn(total_timesteps=timesteps, reset_num_timesteps=False)

        # Save updated agent
        agent.save(str(self.model_path))

        # Update metadata
        prev_timesteps = metadata.get("total_timesteps", 0)
        metadata["last_trained_date"] = date.today().isoformat()
        metadata["last_incremental_start"] = start_date
        metadata["last_incremental_end"] = end_date
        metadata["incremental_timesteps"] = timesteps
        metadata["total_timesteps"] = prev_timesteps + timesteps
        metadata["mode"] = "incremental"
        metadata["timestamp"] = datetime.now().isoformat()

        with open(self.metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("=" * 60)
        logger.info("INCREMENTAL RL UPDATE COMPLETE")
        logger.info(f"✓ Agent updated: {self.model_path}")
        logger.info(f"✓ Additional timesteps: {timesteps:,}")
        logger.info(f"✓ Total timesteps: {prev_timesteps + timesteps:,}")
        logger.info("=" * 60)

        return agent, metadata


def main():
    parser = argparse.ArgumentParser(description="Incremental PPO Training")
    parser.add_argument(
        "--strategy", type=str, required=True, choices=["growth", "value", "dividend"]
    )
    parser.add_argument("--market-cap", type=str, required=True, choices=["small", "mid", "large"])
    parser.add_argument("--mode", type=str, default="full", choices=["full", "incremental"])
    parser.add_argument("--timesteps", type=int, default=1_000_000, help="Training timesteps")
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Create trainer
    trainer = IncrementalPPOTrainer(
        strategy=args.strategy, market_cap_segment=args.market_cap, device=args.device
    )

    # Train
    if args.mode == "full":
        agent, metadata = trainer.train_full(
            total_timesteps=args.timesteps, start_date=args.start_date, end_date=args.end_date
        )
    else:
        agent, metadata = trainer.train_incremental(
            timesteps=args.timesteps, start_date=args.start_date, end_date=args.end_date
        )

    logger.info("Training complete!")


if __name__ == "__main__":
    main()
