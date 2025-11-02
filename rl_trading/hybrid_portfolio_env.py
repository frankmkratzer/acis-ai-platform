#!/usr/bin/env python3
"""
Hybrid Portfolio Environment: ML + RL

Architecture:
1. ML Model (XGBoost) → Selects top N candidate stocks by predicted return
2. RL Agent (PPO) → Decides optimal portfolio weights among candidates

State Space:
- ML predictions for top N stocks
- Current portfolio positions
- Portfolio metrics (Sharpe, drawdown, etc.)
- Market regime indicators

Action Space:
- Continuous portfolio weights for top N stocks (normalized to sum to 1)

Reward:
- Risk-adjusted returns (Sharpe ratio) - transaction costs
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from portfolio.ml_portfolio_manager import MLPortfolioManager
from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class HybridPortfolioEnv(gym.Env):
    """
    Hybrid RL Environment using ML predictions for stock selection

    The environment combines:
    - ML Model: Generates top N candidates
    - RL Agent: Learns optimal allocation among candidates
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        strategy: str = "growth",
        market_cap_segment: str = "mid",
        ml_top_n: int = 100,  # ML selects top 100 candidates
        rl_max_positions: int = 50,  # RL can allocate to max 50
        start_date: str = "2020-01-01",
        end_date: str = "2024-12-31",
        initial_capital: float = 100000.0,
        rebalance_frequency: int = 20,  # Days between rebalances
        transaction_cost: float = 0.001,  # 10 bps
        position_limits: Tuple[float, float] = (0.01, 0.10),  # 1-10% per position
        min_ml_score: float = 0.01,  # Minimum 1% predicted return
    ):
        super().__init__()

        self.strategy = strategy
        self.market_cap_segment = market_cap_segment
        self.ml_top_n = ml_top_n
        self.rl_max_positions = rl_max_positions
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.initial_capital = initial_capital
        self.rebalance_frequency = rebalance_frequency
        self.transaction_cost = transaction_cost
        self.position_limits = position_limits
        self.min_ml_score = min_ml_score

        # Load ML model
        logger.info(f"Loading ML model: {strategy}_{market_cap_segment}cap")
        self.ml_manager = MLPortfolioManager(
            strategy=strategy, market_cap_segment=market_cap_segment
        )

        # State tracking
        self.current_date = None
        self.current_capital = initial_capital
        self.current_positions = {}  # {ticker: shares}
        self.current_candidates = None  # ML-selected candidates
        self.portfolio_history = []

        # Load historical data for backtesting
        self._load_historical_data()

        # Define action and observation spaces
        # Action: Portfolio weights for top N stocks (continuous, sum to 1)
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.rl_max_positions,), dtype=np.float32
        )

        # Observation: [ML predictions, current positions, portfolio metrics, market features]
        obs_dim = (
            self.ml_top_n
            + self.rl_max_positions  # ML predicted returns
            + 5  # Current position weights
            + 3  # Portfolio metrics (value, cash_pct, sharpe, drawdown, num_positions)  # Market features (VIX proxy, market return, volatility)
        )

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        logger.info(f"Hybrid Environment initialized:")
        logger.info(f"  Strategy: {strategy}")
        logger.info(f"  ML Top N: {ml_top_n}")
        logger.info(f"  RL Max Positions: {rl_max_positions}")
        logger.info(f"  Action dim: {self.action_space.shape[0]}")
        logger.info(f"  Observation dim: {self.observation_space.shape[0]}")

    def _load_historical_data(self):
        """Load historical price data for backtesting"""
        logger.info("Loading historical price data...")

        query = """
        SELECT ticker, date, close, volume
        FROM daily_bars
        WHERE date >= %(start_date)s
          AND date <= %(end_date)s
          AND close > 0
          AND volume > 0
        ORDER BY date, ticker
        """

        self.price_data = pd.read_sql(
            query, engine, params={"start_date": self.start_date, "end_date": self.end_date}
        )

        self.price_data["date"] = pd.to_datetime(self.price_data["date"])

        # Create trading dates
        self.trading_dates = sorted(self.price_data["date"].unique())
        self.current_step = 0

        logger.info(f"Loaded {len(self.price_data)} price records")
        logger.info(f"Date range: {self.trading_dates[0]} to {self.trading_dates[-1]}")
        logger.info(f"Trading days: {len(self.trading_dates)}")

    def _get_ml_candidates(self, as_of_date: date) -> pd.DataFrame:
        """Get top N candidates from ML model"""
        try:
            # Get ML predictions for this date
            features = self.ml_manager.get_latest_features(as_of_date=as_of_date)

            if len(features) == 0:
                logger.warning(f"No features available for {as_of_date}")
                return pd.DataFrame()

            predictions = self.ml_manager.generate_predictions(features)

            # Filter by minimum score and select top N
            candidates = predictions[predictions["predicted_return"] >= self.min_ml_score].head(
                self.ml_top_n
            )

            logger.info(
                f"ML selected {len(candidates)} candidates (top pred: {candidates['predicted_return'].iloc[0]:.4f})"
            )

            return candidates

        except Exception as e:
            logger.error(f"Error getting ML candidates: {e}")
            return pd.DataFrame()

    def _build_observation(self) -> np.ndarray:
        """Build observation state"""
        obs = []

        # 1. ML predicted returns for top N stocks (padded to ml_top_n)
        ml_preds = np.zeros(self.ml_top_n)
        if self.current_candidates is not None and len(self.current_candidates) > 0:
            n = min(len(self.current_candidates), self.ml_top_n)
            ml_preds[:n] = self.current_candidates["predicted_return"].values[:n]
        obs.extend(ml_preds)

        # 2. Current position weights (padded to rl_max_positions)
        position_weights = np.zeros(self.rl_max_positions)
        if self.current_candidates is not None and len(self.current_positions) > 0:
            total_value = self.current_capital
            for i, ticker in enumerate(
                self.current_candidates["ticker"].values[: self.rl_max_positions]
            ):
                if ticker in self.current_positions:
                    # Get current price
                    price = self._get_price(ticker, self.current_date)
                    if price > 0:
                        position_value = self.current_positions[ticker] * price
                        position_weights[i] = position_value / total_value
        obs.extend(position_weights)

        # 3. Portfolio metrics
        cash_pct = self._get_cash_percentage()
        sharpe = self._calculate_sharpe_ratio()
        drawdown = self._calculate_drawdown()
        num_positions = len([v for v in self.current_positions.values() if v > 0])

        obs.extend(
            [
                self.current_capital / self.initial_capital,  # Portfolio value ratio
                cash_pct,
                sharpe,
                drawdown,
                num_positions / self.rl_max_positions,
            ]
        )

        # 4. Market features (simplified - using SPY as proxy)
        market_return, market_vol, vix_proxy = self._get_market_features()
        obs.extend([vix_proxy, market_return, market_vol])

        return np.array(obs, dtype=np.float32)

    def _get_price(self, ticker: str, date: pd.Timestamp) -> float:
        """Get price for ticker on date"""
        price_row = self.price_data[
            (self.price_data["ticker"] == ticker) & (self.price_data["date"] == date)
        ]
        return price_row["close"].values[0] if len(price_row) > 0 else 0.0

    def _get_cash_percentage(self) -> float:
        """Calculate percentage of portfolio in cash"""
        total_equity_value = 0
        for ticker, shares in self.current_positions.items():
            if shares > 0:
                price = self._get_price(ticker, self.current_date)
                total_equity_value += shares * price

        cash = self.current_capital - total_equity_value
        return cash / self.current_capital if self.current_capital > 0 else 0.0

    def _calculate_sharpe_ratio(self, window: int = 60) -> float:
        """Calculate Sharpe ratio over recent window"""
        if len(self.portfolio_history) < 2:
            return 0.0

        recent = self.portfolio_history[-min(window, len(self.portfolio_history)) :]
        returns = np.diff([p["value"] for p in recent]) / np.array(
            [p["value"] for p in recent[:-1]]
        )

        if len(returns) < 2:
            return 0.0

        return np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)

    def _calculate_drawdown(self) -> float:
        """Calculate current drawdown"""
        if len(self.portfolio_history) == 0:
            return 0.0

        values = [p["value"] for p in self.portfolio_history]
        peak = np.maximum.accumulate(values)
        drawdown = (values[-1] - peak[-1]) / peak[-1] if peak[-1] > 0 else 0.0

        return drawdown

    def _get_market_features(self) -> Tuple[float, float, float]:
        """Get market regime indicators (simplified)"""
        # This is a simplified version - you can enhance with actual market data
        # For now, use aggregate market stats

        try:
            # Get recent market returns (using average of universe)
            recent_dates = [d for d in self.trading_dates if d <= self.current_date][-20:]

            if len(recent_dates) < 2:
                return 0.0, 0.0, 0.0

            # Sample 100 random tickers for market proxy
            sample_tickers = self.price_data["ticker"].unique()[:100]
            market_data = self.price_data[
                (self.price_data["ticker"].isin(sample_tickers))
                & (self.price_data["date"].isin(recent_dates))
            ]

            if len(market_data) == 0:
                return 0.0, 0.0, 0.0

            # Calculate market metrics
            daily_avg = market_data.groupby("date")["close"].mean()
            market_return = (daily_avg.iloc[-1] - daily_avg.iloc[0]) / daily_avg.iloc[0]
            market_vol = daily_avg.pct_change().std()
            vix_proxy = market_vol * np.sqrt(252)  # Annualized vol as VIX proxy

            return market_return, market_vol, vix_proxy

        except Exception as e:
            logger.warning(f"Error calculating market features: {e}")
            return 0.0, 0.0, 0.0

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[np.ndarray, dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)

        self.current_step = 0
        self.current_date = self.trading_dates[self.current_step]
        self.current_capital = self.initial_capital
        self.current_positions = {}
        self.portfolio_history = []

        # Get initial ML candidates
        self.current_candidates = self._get_ml_candidates(self.current_date.date())

        observation = self._build_observation()
        info = {
            "date": str(self.current_date),
            "capital": self.current_capital,
            "num_candidates": (
                len(self.current_candidates) if self.current_candidates is not None else 0
            ),
        }

        logger.info(f"Environment reset to {self.current_date}")

        return observation, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one step"""
        # Normalize action to sum to 1 (portfolio weights)
        action = np.abs(action)  # Ensure non-negative
        action_sum = np.sum(action)
        if action_sum > 0:
            action = action / action_sum

        # Apply position limits
        action = np.clip(action, self.position_limits[0], self.position_limits[1])

        # Re-normalize after clipping
        action_sum = np.sum(action)
        if action_sum > 0:
            action = action / action_sum

        # Execute rebalance
        transaction_costs = self._execute_rebalance(action)

        # Advance to next rebalance date
        self.current_step += self.rebalance_frequency

        # Check if episode is done
        done = self.current_step >= len(self.trading_dates)

        if not done:
            self.current_date = self.trading_dates[self.current_step]

            # Calculate portfolio value with new prices
            self._update_portfolio_value()

            # Get new ML candidates
            self.current_candidates = self._get_ml_candidates(self.current_date.date())

        # Calculate reward
        reward = self._calculate_reward(transaction_costs)

        # Build next observation
        observation = self._build_observation()

        info = {
            "date": str(self.current_date) if not done else "terminal",
            "capital": self.current_capital,
            "reward": reward,
            "transaction_costs": transaction_costs,
            "num_positions": len([v for v in self.current_positions.values() if v > 0]),
        }

        return observation, reward, done, False, info

    def _execute_rebalance(self, action: np.ndarray) -> float:
        """Execute portfolio rebalance based on action"""
        if self.current_candidates is None or len(self.current_candidates) == 0:
            return 0.0

        # Get target portfolio
        target_tickers = self.current_candidates["ticker"].values[: self.rl_max_positions]
        target_weights = action[: len(target_tickers)]

        # Calculate target shares
        target_positions = {}
        total_costs = 0.0

        for ticker, weight in zip(target_tickers, target_weights):
            if weight < self.position_limits[0]:  # Skip tiny positions
                continue

            price = self._get_price(ticker, self.current_date)
            if price <= 0:
                continue

            target_value = self.current_capital * weight
            target_shares = int(target_value / price)

            if target_shares > 0:
                target_positions[ticker] = target_shares

                # Calculate transaction costs
                current_shares = self.current_positions.get(ticker, 0)
                shares_traded = abs(target_shares - current_shares)
                total_costs += shares_traded * price * self.transaction_cost

        # Liquidate positions not in target
        for ticker in list(self.current_positions.keys()):
            if ticker not in target_positions:
                shares = self.current_positions[ticker]
                price = self._get_price(ticker, self.current_date)
                total_costs += shares * price * self.transaction_cost

        # Update positions
        self.current_positions = target_positions
        self.current_capital -= total_costs

        return total_costs

    def _update_portfolio_value(self):
        """Update portfolio value based on current prices"""
        equity_value = 0.0

        for ticker, shares in self.current_positions.items():
            price = self._get_price(ticker, self.current_date)
            equity_value += shares * price

        # Track history
        self.portfolio_history.append(
            {"date": self.current_date, "value": equity_value, "capital": self.current_capital}
        )

    def _calculate_reward(self, transaction_costs: float) -> float:
        """Calculate reward for current step"""
        if len(self.portfolio_history) < 2:
            return 0.0

        # Calculate return
        prev_value = self.portfolio_history[-2]["value"]
        curr_value = self.portfolio_history[-1]["value"]

        if prev_value <= 0:
            return 0.0

        period_return = (curr_value - prev_value) / prev_value

        # Penalize transaction costs
        cost_penalty = transaction_costs / self.current_capital

        # Calculate Sharpe-based reward
        sharpe = self._calculate_sharpe_ratio()

        # Combined reward: return - costs + sharpe_bonus
        reward = period_return - cost_penalty + 0.1 * sharpe

        return reward

    def render(self, mode="human"):
        """Render environment state"""
        if mode == "human":
            print(f"\n{'='*60}")
            print(f"Date: {self.current_date}")
            print(f"Capital: ${self.current_capital:,.2f}")
            print(f"Positions: {len([v for v in self.current_positions.values() if v > 0])}")
            print(f"Sharpe: {self._calculate_sharpe_ratio():.2f}")
            print(f"Drawdown: {self._calculate_drawdown():.2%}")
            if self.current_candidates is not None:
                print(f"ML Candidates: {len(self.current_candidates)}")
            print(f"{'='*60}\n")
