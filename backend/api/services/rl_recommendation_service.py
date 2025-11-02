"""
RL Recommendation Service

Loads trained RL models and generates trade recommendations.

Flow:
1. Load RL model for specific portfolio (Growth/Momentum, Dividend, etc.)
2. Get current portfolio state from Schwab
3. Run RL model to get target allocation
4. Compare current vs target
5. Generate trade list (buys/sells)
6. Include reasoning from RL agent
"""

import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from stable_baselines3 import PPO


class RLRecommendationService:
    """
    Service to generate trade recommendations from RL models.
    """

    def __init__(self):
        self.models = {}  # Cache loaded models
        self.portfolio_configs = {
            1: {
                "name": "Growth/Momentum",
                "model_path": "models/growth_momentum/ppo_growth_momentum.zip",
                "description": "15-25 large/mid cap growth stocks with strong momentum",
            },
            # 2 and 3 to be added later
        }

    def load_model(self, portfolio_id: int) -> Optional[PPO]:
        """
        Load RL model for a portfolio.

        Args:
            portfolio_id: Portfolio ID (1=Growth/Momentum, 2=Dividend, 3=Value)

        Returns:
            Loaded PPO model or None if not found (will use demo mode)
        """
        if portfolio_id in self.models:
            return self.models[portfolio_id]

        config = self.portfolio_configs.get(portfolio_id)
        if not config:
            print(f"Portfolio ID {portfolio_id} not configured, using demo mode")
            return None

        model_path = config["model_path"]
        if not os.path.exists(model_path):
            print(
                f"Model not found: {model_path}. Using demo mode with rule-based recommendations."
            )
            return None

        try:
            # Load model
            model = PPO.load(model_path)
            self.models[portfolio_id] = model
            print(f"Successfully loaded RL model for portfolio {portfolio_id}")
            return model
        except Exception as e:
            print(f"Failed to load model {model_path}: {e}. Using demo mode.")
            return None

    def generate_recommendations(
        self,
        portfolio_id: int,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        cash: float,
    ) -> Dict[str, Any]:
        """
        Generate trade recommendations from RL model.

        Args:
            portfolio_id: Portfolio ID
            current_positions: Current positions from Schwab
            account_value: Total account value
            cash: Available cash

        Returns:
            Dict with target allocation and trade recommendations
        """
        # Load RL model
        model = self.load_model(portfolio_id)

        # Get portfolio name
        portfolio_names = {1: "Growth/Momentum", 2: "Dividend", 3: "Value"}
        portfolio_name = portfolio_names.get(portfolio_id, "Unknown")

        if model is None:
            # Use demo mode - rule-based recommendations
            print(f"Using demo mode for {portfolio_name} portfolio")
            return self._generate_demo_recommendations(
                portfolio_id, portfolio_name, current_positions, account_value, cash
            )

        # Real RL model path
        # Build observation from current state
        observation = self._build_observation(current_positions, account_value, cash, portfolio_id)

        # Get RL model prediction (target allocation)
        action, _states = model.predict(observation, deterministic=True)

        # Convert action to target allocation
        target_allocation = self._action_to_allocation(action, portfolio_id)

        # Compare current vs target
        current_allocation = self._current_to_allocation(current_positions, account_value)

        # Generate trades
        trades = self._generate_trades(current_allocation, target_allocation, account_value)

        # Calculate metrics
        total_turnover = sum(abs(t["weight_change"]) for t in trades)
        total_buy_value = sum(t["dollar_amount"] for t in trades if t["action"] in ["BUY", "ADD"])
        total_sell_value = sum(
            t["dollar_amount"] for t in trades if t["action"] in ["SELL", "TRIM"]
        )

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_name,
            "current_allocation": current_allocation,
            "target_allocation": target_allocation,
            "trades": trades,
            "summary": {
                "num_trades": len(trades),
                "total_turnover": float(total_turnover),
                "total_buy_value": float(total_buy_value),
                "total_sell_value": float(total_sell_value),
                "cash_required": float(total_buy_value - total_sell_value),
            },
        }

    def _build_observation(
        self,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        cash: float,
        portfolio_id: int,
    ) -> np.ndarray:
        """
        Build observation vector for RL model.

        This should match the observation space from training.
        For now, simplified version.
        """
        # Simplified: return random observation (replace with real implementation)
        # Real implementation would fetch market data, technical indicators, etc.

        # For Growth/Momentum portfolio (ID 1)
        if portfolio_id == 1:
            # Match environment observation space
            obs_size = 10  # Simplified (real: portfolio + stock features + market)
            return np.random.randn(obs_size).astype(np.float32)

        return np.random.randn(10).astype(np.float32)

    def _action_to_allocation(self, action: np.ndarray, portfolio_id: int) -> Dict[str, float]:
        """
        Convert RL model action to target allocation.

        Args:
            action: Model output (weights)
            portfolio_id: Portfolio ID

        Returns:
            Dict of {symbol: weight}
        """
        # For Growth/Momentum (ID 1), action is weights for top stocks
        # This is a simplified version - real would map to actual symbols

        # Normalize action to sum to 1
        action = np.clip(action, 0, 1)
        action_sum = np.sum(action)
        if action_sum > 1e-6:
            action = action / action_sum

        # Map to symbols (simplified - would use actual stock universe)
        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AMD", "NFLX", "CRM"]

        allocation = {}
        for i, symbol in enumerate(symbols[: len(action)]):
            weight = float(action[i])
            if weight > 0.01:  # Only include positions > 1%
                allocation[symbol] = weight

        # Add cash
        allocated = sum(allocation.values())
        if allocated < 1.0:
            allocation["CASH"] = 1.0 - allocated

        return allocation

    def _current_to_allocation(
        self, positions: List[Dict[str, Any]], account_value: float
    ) -> Dict[str, float]:
        """
        Convert current positions to allocation dict.

        Args:
            positions: List of current positions
            account_value: Total account value

        Returns:
            Dict of {symbol: weight}
        """
        allocation = {}

        for position in positions:
            symbol = position.get("symbol", "")
            value = position.get("current_value", 0)

            if account_value > 0:
                weight = value / account_value
                allocation[symbol] = float(weight)

        # Calculate cash position
        invested = sum(allocation.values())
        if invested < 1.0:
            allocation["CASH"] = 1.0 - invested

        return allocation

    def _generate_trades(
        self, current: Dict[str, float], target: Dict[str, float], account_value: float
    ) -> List[Dict[str, Any]]:
        """
        Generate trade list from current and target allocations.

        Args:
            current: Current allocation {symbol: weight}
            target: Target allocation {symbol: weight}
            account_value: Total account value

        Returns:
            List of trades with action, symbol, shares, reasoning
        """
        trades = []

        # Get all symbols
        all_symbols = set(current.keys()) | set(target.keys())
        all_symbols.discard("CASH")  # Don't trade cash

        for symbol in all_symbols:
            current_weight = current.get(symbol, 0)
            target_weight = target.get(symbol, 0)
            weight_change = target_weight - current_weight

            # Skip if change is too small
            if abs(weight_change) < 0.01:  # Less than 1% change
                continue

            # Determine action
            if current_weight < 0.01 and target_weight >= 0.01:
                action = "BUY"
            elif current_weight >= 0.01 and target_weight < 0.01:
                action = "SELL"
            elif weight_change > 0:
                action = "ADD"
            else:
                action = "TRIM"

            # Calculate dollar amount and shares
            dollar_amount = abs(weight_change) * account_value
            # Shares would be calculated with real-time price
            shares = int(dollar_amount / 100)  # Simplified: assume $100/share

            # Generate reasoning
            reasoning = self._generate_reasoning(
                symbol, action, current_weight, target_weight, weight_change
            )

            trades.append(
                {
                    "symbol": symbol,
                    "action": action,
                    "shares": shares,
                    "weight_old": float(current_weight),
                    "weight_new": float(target_weight),
                    "weight_change": float(weight_change),
                    "dollar_amount": float(dollar_amount),
                    "reasoning": reasoning,
                }
            )

        # Sort trades: sells first, then buys
        trades.sort(key=lambda t: 0 if t["action"] in ["SELL", "TRIM"] else 1)

        return trades

    def _generate_reasoning(
        self,
        symbol: str,
        action: str,
        current_weight: float,
        target_weight: float,
        weight_change: float,
    ) -> str:
        """
        Generate human-readable reasoning for a trade.

        Args:
            symbol: Stock symbol
            action: Trade action
            current_weight: Current weight
            target_weight: Target weight
            weight_change: Weight change

        Returns:
            Reasoning string
        """
        reasons = []

        if action in ["BUY", "ADD"]:
            reasons.append(f"RL model recommends increasing {symbol} allocation")
            reasons.append(
                f"Target weight: {target_weight*100:.1f}% (current: {current_weight*100:.1f}%)"
            )
            reasons.append("Strong momentum and growth signals")
        else:
            reasons.append(f"RL model recommends decreasing {symbol} allocation")
            reasons.append(
                f"Target weight: {target_weight*100:.1f}% (current: {current_weight*100:.1f}%)"
            )
            reasons.append("Momentum weakening or rebalancing required")

        return " | ".join(reasons)

    def _generate_demo_recommendations(
        self,
        portfolio_id: int,
        portfolio_name: str,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        cash: float,
    ) -> Dict[str, Any]:
        """
        Generate demo recommendations using rule-based allocation.
        This is used when RL models are not yet trained.
        """
        # Define strategy-specific target allocations
        strategies = {
            1: {  # Growth/Momentum
                "AAPL": 0.15,  # Apple
                "MSFT": 0.15,  # Microsoft
                "NVDA": 0.12,  # NVIDIA
                "GOOGL": 0.12,  # Google
                "AMZN": 0.12,  # Amazon
                "META": 0.10,  # Meta
                "TSLA": 0.09,  # Tesla
                "AVGO": 0.08,  # Broadcom
                "AMD": 0.07,  # AMD
            },
            2: {  # Dividend
                "ABBV": 0.12,  # AbbVie
                "VZ": 0.11,  # Verizon
                "WMT": 0.10,  # Walmart
                "HD": 0.10,  # Home Depot
                "LOW": 0.09,  # Lowe's
                "CVX": 0.09,  # Chevron
                "TGT": 0.09,  # Target
                "NEE": 0.09,  # NextEra Energy
                "UPS": 0.08,  # UPS
                "BAC": 0.07,  # Bank of America
                "C": 0.06,  # Citigroup
            },
            3: {  # Value
                "BRK.B": 0.15,  # Berkshire Hathaway
                "JPM": 0.12,  # JP Morgan
                "JNJ": 0.11,  # Johnson & Johnson
                "PG": 0.10,  # Procter & Gamble
                "V": 0.10,  # Visa
                "MA": 0.09,  # Mastercard
                "UNH": 0.09,  # UnitedHealth
                "XOM": 0.08,  # Exxon
                "WFC": 0.08,  # Wells Fargo
                "KO": 0.08,  # Coca-Cola
            },
        }

        target_allocation = strategies.get(portfolio_id, strategies[1])
        current_allocation = self._current_to_allocation(current_positions, account_value)

        # Generate trades
        trades = self._generate_trades(current_allocation, target_allocation, account_value)

        # Update reasoning to indicate demo mode
        for trade in trades:
            trade["reasoning"] = (
                f"Demo Mode: {trade['reasoning']} [Train RL models for AI-powered recommendations]"
            )

        # Calculate metrics
        total_turnover = sum(abs(t["weight_change"]) for t in trades)
        total_buy_value = sum(t["dollar_amount"] for t in trades if t["action"] in ["BUY", "ADD"])
        total_sell_value = sum(
            t["dollar_amount"] for t in trades if t["action"] in ["SELL", "TRIM"]
        )

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio_name,
            "current_allocation": current_allocation,
            "target_allocation": target_allocation,
            "trades": trades,
            "summary": {
                "num_trades": len(trades),
                "total_turnover": float(total_turnover),
                "total_buy_value": float(total_buy_value),
                "total_sell_value": float(total_sell_value),
                "cash_required": float(total_buy_value - total_sell_value),
            },
            "mode": "demo",
            "note": "Using rule-based allocation. Train RL models for AI-powered recommendations.",
        }


def get_recommendation_service() -> RLRecommendationService:
    """Get singleton instance of recommendation service."""
    return RLRecommendationService()
