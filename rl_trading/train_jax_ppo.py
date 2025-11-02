#!/usr/bin/env python3
"""
JAX-based PPO Training for Hybrid ML+RL Portfolio

Uses JAX for GPU acceleration with the HybridPortfolioEnv.
Architecture:
1. ML Model (XGBoost) → Top N candidates
2. JAX PPO Agent → Optimal portfolio weights (GPU-accelerated)

Strategies: growth, value, dividend
Market Caps: small, mid, large
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pickle
from datetime import datetime
from typing import Any, Dict, Tuple

import flax.linen as nn
import jax
import jax.numpy as jnp
import numpy as np
import optax
from flax.training import train_state
from jax import jit, random, value_and_grad

from rl_trading.hybrid_portfolio_env import HybridPortfolioEnv
from utils import get_logger

logger = get_logger(__name__)


class ActorCriticNetwork(nn.Module):
    """Actor-Critic network for PPO"""

    action_dim: int
    hidden_dim: int = 256

    @nn.compact
    def __call__(self, x):
        # Shared feature extraction
        x = nn.Dense(self.hidden_dim)(x)
        x = nn.relu(x)
        x = nn.Dense(self.hidden_dim)(x)
        x = nn.relu(x)

        # Actor head (policy)
        actor = nn.Dense(self.hidden_dim // 2)(x)
        actor = nn.relu(actor)
        logits = nn.Dense(self.action_dim)(actor)
        # Use softmax to ensure weights sum to 1
        action_probs = nn.softmax(logits)

        # Critic head (value function)
        critic = nn.Dense(self.hidden_dim // 2)(x)
        critic = nn.relu(critic)
        value = nn.Dense(1)(critic).squeeze()

        return action_probs, value


class PPOTrainer:
    """JAX-based PPO trainer with GPU acceleration"""

    def __init__(
        self,
        env,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        n_epochs: int = 10,
        batch_size: int = 64,
        hidden_dim: int = 256,
    ):
        self.env = env
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.max_grad_norm = max_grad_norm
        self.n_epochs = n_epochs
        self.batch_size = batch_size

        # Initialize network
        self.rng = random.PRNGKey(0)
        self.network = ActorCriticNetwork(
            action_dim=env.action_space.shape[0], hidden_dim=hidden_dim
        )

        # Initialize network parameters
        dummy_obs = jnp.ones((1, env.observation_space.shape[0]))
        self.rng, init_rng = random.split(self.rng)
        params = self.network.init(init_rng, dummy_obs)

        # Create optimizer and training state
        tx = optax.chain(optax.clip_by_global_norm(max_grad_norm), optax.adam(learning_rate))
        self.train_state = train_state.TrainState.create(
            apply_fn=self.network.apply, params=params, tx=tx
        )

        logger.info(f"✅ JAX PPO initialized on device: {jax.devices()[0]}")
        logger.info(f"Network parameters: {sum(x.size for x in jax.tree_util.tree_leaves(params))}")

    @staticmethod
    @jit
    def compute_gae(
        rewards: jnp.ndarray,
        values: jnp.ndarray,
        dones: jnp.ndarray,
        gamma: float,
        gae_lambda: float,
    ) -> Tuple[jnp.ndarray, jnp.ndarray]:
        """Compute Generalized Advantage Estimation"""
        advantages = []
        gae = 0.0

        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0.0
            else:
                next_value = values[t + 1]

            delta = rewards[t] + gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + gamma * gae_lambda * (1 - dones[t]) * gae
            advantages.insert(0, gae)

        advantages = jnp.array(advantages)
        returns = advantages + values

        return advantages, returns

    @staticmethod
    def ppo_loss(
        params: Any,
        apply_fn: Any,
        obs_batch: jnp.ndarray,
        action_batch: jnp.ndarray,
        old_log_probs_batch: jnp.ndarray,
        advantages_batch: jnp.ndarray,
        returns_batch: jnp.ndarray,
        clip_epsilon: float,
        value_coef: float,
        entropy_coef: float,
    ) -> Tuple[jnp.ndarray, Dict]:
        """PPO loss function"""
        # Forward pass
        action_probs, values = apply_fn(params, obs_batch)

        # Compute log probabilities for taken actions
        log_probs = jnp.log(jnp.sum(action_probs * action_batch, axis=-1) + 1e-8)

        # Compute ratio for PPO
        ratio = jnp.exp(log_probs - old_log_probs_batch)

        # Clipped surrogate objective
        surr1 = ratio * advantages_batch
        surr2 = jnp.clip(ratio, 1 - clip_epsilon, 1 + clip_epsilon) * advantages_batch
        actor_loss = -jnp.mean(jnp.minimum(surr1, surr2))

        # Value loss
        value_loss = jnp.mean((returns_batch - values) ** 2)

        # Entropy bonus
        entropy = -jnp.mean(jnp.sum(action_probs * jnp.log(action_probs + 1e-8), axis=-1))

        # Total loss
        total_loss = actor_loss + value_coef * value_loss - entropy_coef * entropy

        info = {
            "total_loss": total_loss,
            "actor_loss": actor_loss,
            "value_loss": value_loss,
            "entropy": entropy,
            "ratio_mean": jnp.mean(ratio),
        }

        return total_loss, info

    def collect_trajectory(self, n_steps: int) -> Dict:
        """Collect trajectory data from environment"""
        observations = []
        actions = []
        rewards = []
        dones = []
        values = []
        log_probs = []

        obs, _ = self.env.reset()

        for step in range(n_steps):
            # Convert observation to JAX array
            obs_jax = jnp.array(obs).reshape(1, -1)

            # Get action from policy
            action_probs, value = self.network.apply(self.train_state.params, obs_jax)
            action_probs = np.array(action_probs[0])
            value = float(value)

            # Sample action (use probabilities directly as continuous weights)
            action = action_probs

            # Compute log prob
            log_prob = np.log(np.sum(action_probs * action) + 1e-8)

            # Take step in environment
            next_obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated

            # Store transition
            observations.append(obs)
            actions.append(action)
            rewards.append(reward)
            dones.append(float(done))
            values.append(value)
            log_probs.append(log_prob)

            obs = next_obs

            if done:
                obs, _ = self.env.reset()

        return {
            "observations": jnp.array(observations),
            "actions": jnp.array(actions),
            "rewards": jnp.array(rewards),
            "dones": jnp.array(dones),
            "values": jnp.array(values),
            "log_probs": jnp.array(log_probs),
        }

    def update(self, trajectory: Dict) -> Dict:
        """Update policy using PPO"""
        # Compute advantages and returns
        advantages, returns = self.compute_gae(
            trajectory["rewards"],
            trajectory["values"],
            trajectory["dones"],
            self.gamma,
            self.gae_lambda,
        )

        # Normalize advantages
        advantages = (advantages - jnp.mean(advantages)) / (jnp.std(advantages) + 1e-8)

        # Create batches
        n_samples = len(trajectory["observations"])
        indices = np.arange(n_samples)

        epoch_info = []

        for epoch in range(self.n_epochs):
            np.random.shuffle(indices)

            for start in range(0, n_samples, self.batch_size):
                end = min(start + self.batch_size, n_samples)
                batch_idx = indices[start:end]

                # Get batch
                obs_batch = trajectory["observations"][batch_idx]
                action_batch = trajectory["actions"][batch_idx]
                old_log_probs_batch = trajectory["log_probs"][batch_idx]
                advantages_batch = advantages[batch_idx]
                returns_batch = returns[batch_idx]

                # Compute loss and gradients
                grad_fn = value_and_grad(self.ppo_loss, has_aux=True)
                (loss, info), grads = grad_fn(
                    self.train_state.params,
                    self.train_state.apply_fn,
                    obs_batch,
                    action_batch,
                    old_log_probs_batch,
                    advantages_batch,
                    returns_batch,
                    self.clip_epsilon,
                    self.value_coef,
                    self.entropy_coef,
                )

                # Update parameters
                self.train_state = self.train_state.apply_gradients(grads=grads)
                epoch_info.append(info)

        # Average info over all updates
        avg_info = {
            key: float(jnp.mean(jnp.array([info[key] for info in epoch_info])))
            for key in epoch_info[0].keys()
        }

        return avg_info

    def train(
        self,
        total_timesteps: int,
        n_steps: int = 2048,
        eval_freq: int = 10000,
        save_freq: int = 50000,
        output_dir: Path = None,
    ):
        """Train the PPO agent"""
        logger.info("=" * 80)
        logger.info("Starting JAX PPO Training")
        logger.info(f"Total timesteps: {total_timesteps:,}")
        logger.info(f"Steps per update: {n_steps}")
        logger.info(f"Device: {jax.devices()[0]}")
        logger.info("=" * 80)

        timesteps = 0
        episode = 0
        best_mean_reward = -float("inf")

        while timesteps < total_timesteps:
            # Collect trajectory
            trajectory = self.collect_trajectory(n_steps)
            timesteps += n_steps

            # Update policy
            info = self.update(trajectory)

            # Logging
            mean_reward = float(jnp.mean(trajectory["rewards"]))
            episode += 1

            if episode % 10 == 0:
                logger.info(
                    f"Episode {episode} | Timesteps: {timesteps:,} | "
                    f"Mean Reward: {mean_reward:.4f} | "
                    f"Loss: {info['total_loss']:.4f} | "
                    f"Entropy: {info['entropy']:.4f}"
                )

            # Save checkpoint
            if output_dir and timesteps % save_freq < n_steps:
                checkpoint_path = output_dir / "checkpoints" / f"model_{timesteps}.pkl"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

                with open(checkpoint_path, "wb") as f:
                    pickle.dump(
                        {
                            "params": self.train_state.params,
                            "timesteps": timesteps,
                            "episode": episode,
                        },
                        f,
                    )

                logger.info(f"💾 Checkpoint saved: {checkpoint_path}")

            # Save best model
            if mean_reward > best_mean_reward:
                best_mean_reward = mean_reward
                if output_dir:
                    best_model_path = output_dir / "best_model" / "model.pkl"
                    best_model_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(best_model_path, "wb") as f:
                        pickle.dump(
                            {
                                "params": self.train_state.params,
                                "timesteps": timesteps,
                                "episode": episode,
                                "mean_reward": mean_reward,
                            },
                            f,
                        )

        logger.info("=" * 80)
        logger.info("✅ JAX PPO TRAINING COMPLETE!")
        logger.info(f"Best mean reward: {best_mean_reward:.4f}")
        logger.info("=" * 80)

        return self.train_state


def create_env(strategy: str, market_cap_segment: str, train_mode: bool = True):
    """Create environment instance"""
    if train_mode:
        start_date = "2015-01-01"
        end_date = "2023-12-31"
    else:
        start_date = "2024-01-01"
        end_date = "2025-10-27"

    env = HybridPortfolioEnv(
        strategy=strategy,
        market_cap_segment=market_cap_segment,
        start_date=start_date,
        end_date=end_date,
        ml_top_n=100,
        rl_max_positions=50,
        rebalance_frequency=20,
        transaction_cost=0.001,
        position_limits=(0.01, 0.10),
        min_ml_score=0.01,
    )

    return env


def train(
    strategy: str,
    market_cap_segment: str,
    total_timesteps: int = 1_000_000,
    eval_freq: int = 10_000,
    save_freq: int = 50_000,
):
    """Train JAX PPO agent"""

    logger.info("=" * 80)
    logger.info("JAX HYBRID ML+RL PORTFOLIO TRAINING")
    logger.info(f"Strategy: {strategy.upper()}")
    logger.info(f"Market Cap Segment: {market_cap_segment.upper()}")
    logger.info(f"JAX Backend: {jax.default_backend()}")
    logger.info(f"Devices: {jax.devices()}")
    logger.info("=" * 80)

    # Create model name
    model_name = f"jax_ppo_hybrid_{strategy}_{market_cap_segment}cap"
    output_dir = Path("models") / model_name
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Model will be saved to: {output_dir}")

    # Create environment
    logger.info("Creating training environment...")
    env = create_env(strategy, market_cap_segment, train_mode=True)

    # Get strategy-specific hyperparameters
    hyperparams = {
        "learning_rate": 3e-4,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_epsilon": 0.2,
        "value_coef": 0.5,
        "entropy_coef": 0.01,
        "max_grad_norm": 0.5,
        "n_epochs": 10,
        "batch_size": 64,
        "hidden_dim": 256,
    }

    # Strategy-specific adjustments
    if strategy == "dividend":
        hyperparams["entropy_coef"] = 0.005
        hyperparams["gamma"] = 0.98
    elif strategy == "growth":
        hyperparams["entropy_coef"] = 0.02
        hyperparams["gamma"] = 0.995

    # Create trainer
    logger.info("Initializing JAX PPO trainer...")
    logger.info(f"Hyperparameters: {hyperparams}")

    trainer = PPOTrainer(env, **hyperparams)

    # Train
    start_time = datetime.now()

    trainer.train(
        total_timesteps=total_timesteps,
        n_steps=2048,
        eval_freq=eval_freq,
        save_freq=save_freq,
        output_dir=output_dir,
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60

    # Save final model
    final_model_path = output_dir / "final_model.pkl"
    with open(final_model_path, "wb") as f:
        pickle.dump(
            {
                "params": trainer.train_state.params,
                "hyperparams": hyperparams,
                "strategy": strategy,
                "market_cap_segment": market_cap_segment,
            },
            f,
        )

    logger.info("=" * 80)
    logger.info("✅ TRAINING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Training duration: {duration:.2f} minutes")
    logger.info(f"Final model saved to: {final_model_path}")
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
        "train_date_range": "2015-01-01 to 2023-12-31",
        "eval_date_range": "2024-01-01 to 2025-10-27",
        "ml_top_n": 100,
        "rl_max_positions": 50,
        "trained_at": str(datetime.now()),
        "framework": "JAX",
        "device": str(jax.devices()[0]),
    }

    with open(output_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadata saved to: {output_dir / 'metadata.json'}")


def main():
    parser = argparse.ArgumentParser(description="Train JAX-based Hybrid ML+RL PPO Agent")
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
    )


if __name__ == "__main__":
    main()
