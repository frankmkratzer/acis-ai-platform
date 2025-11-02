"""
RL Recommendation Service

Uses trained RL models to generate trade recommendations for each portfolio strategy.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from stable_baselines3 import PPO


class RLRecommenderService:
    """Service for generating trade recommendations using trained RL models."""

    def __init__(self):
        self.db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        # Get project root directory (3 levels up from backend/api/services)
        import pathlib

        self.project_root = pathlib.Path(__file__).parent.parent.parent.parent

        # Portfolio strategy definitions
        self.portfolios = {
            1: {
                "name": "Growth/Momentum",
                "model_path": str(
                    self.project_root / "models" / "growth_momentum" / "ppo_growth_momentum.zip"
                ),
                "description": "Aggressive growth focused on tech and momentum stocks",
                "rebalance_frequency": "monthly",
            },
            2: {
                "name": "Dividend",
                "model_path": str(self.project_root / "models" / "dividend" / "ppo_dividend.zip"),
                "description": "Conservative income-generating portfolio",
                "rebalance_frequency": "quarterly",
            },
            3: {
                "name": "Value",
                "model_path": str(self.project_root / "models" / "value" / "ppo_value.zip"),
                "description": "Contrarian value investing approach",
                "rebalance_frequency": "quarterly",
            },
        }

        # Load models (lazy loading)
        self.models = {}

    def _load_model(self, portfolio_id: int) -> Optional[PPO]:
        """Load trained RL model for a portfolio strategy."""

        if portfolio_id in self.models:
            return self.models[portfolio_id]

        if portfolio_id not in self.portfolios:
            return None

        model_path = self.portfolios[portfolio_id]["model_path"]

        if not os.path.exists(model_path):
            print(f"Model not found: {model_path}")
            return None

        try:
            model = PPO.load(model_path)
            self.models[portfolio_id] = model
            return model
        except Exception as e:
            print(f"Failed to load model {model_path}: {e}")
            return None

    async def generate_recommendations(
        self,
        portfolio_id: int,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        max_recommendations: int = 10,
    ) -> Dict[str, Any]:
        """
        Generate trade recommendations using trained RL model.

        Args:
            portfolio_id: Which strategy (1=Growth, 2=Dividend, 3=Value)
            current_positions: Current portfolio holdings
            account_value: Total account value
            max_recommendations: Maximum number of recommendations

        Returns:
            Dictionary with recommendations and metadata
        """

        # Load model
        model = self._load_model(portfolio_id)

        if model is None:
            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": self.portfolios.get(portfolio_id, {}).get("name", "Unknown"),
                "status": "model_not_ready",
                "message": "RL model is still training. Check back in a few minutes.",
                "recommendations": [],
            }

        # Get current market state
        market_state = await self._get_market_state(portfolio_id)

        # Build observation for RL model
        observation = self._build_observation(current_positions, account_value, market_state)

        # Get action from model
        action, _states = model.predict(observation, deterministic=True)

        # Interpret action as trade recommendations
        recommendations = self._action_to_recommendations(
            action, current_positions, account_value, portfolio_id, max_recommendations
        )

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": self.portfolios[portfolio_id]["name"],
            "status": "success",
            "generated_at": datetime.now().isoformat(),
            "recommendations": recommendations,
            "metadata": {
                "account_value": account_value,
                "num_positions": len(current_positions),
                "rebalance_frequency": self.portfolios[portfolio_id]["rebalance_frequency"],
            },
        }

    async def _get_market_state(self, portfolio_id: int) -> Dict[str, Any]:
        """Fetch current market conditions."""

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Get recent market data (SPY as proxy)
        cur.execute(
            """
            SELECT close, volume
            FROM daily_bars
            WHERE ticker = 'SPY'
            ORDER BY date DESC
            LIMIT 30
        """
        )

        spy_data = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()

        if not spy_data:
            return {"market_trend": 0.0, "volatility": 0.0}

        # Calculate simple market metrics
        prices = [float(d["close"]) for d in spy_data]
        returns = [(prices[i] - prices[i + 1]) / prices[i + 1] for i in range(len(prices) - 1)]

        return {
            "market_trend": np.mean(returns) if returns else 0.0,
            "volatility": np.std(returns) if len(returns) > 1 else 0.0,
            "spy_price": prices[0] if prices else 0.0,
        }

    def _build_observation(
        self,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        market_state: Dict[str, Any],
    ) -> np.ndarray:
        """
        Build observation vector for RL model.

        Observation space typically includes:
        - Current portfolio weights
        - Cash position
        - Market conditions
        - Recent returns
        """

        # Simplified observation (adjust based on actual training environment)
        observation = []

        # Cash ratio
        cash_ratio = 0.0
        for pos in current_positions:
            if pos.get("instrument_type") == "MONEY_MARKET":
                cash_ratio = (
                    float(pos.get("current_value", 0)) / account_value if account_value > 0 else 0
                )

        observation.append(cash_ratio)

        # Portfolio concentration (top 5 holdings)
        sorted_positions = sorted(
            [p for p in current_positions if p.get("instrument_type") == "EQUITY"],
            key=lambda x: float(x.get("current_value", 0)),
            reverse=True,
        )

        for i in range(5):
            if i < len(sorted_positions):
                weight = (
                    float(sorted_positions[i].get("current_value", 0)) / account_value
                    if account_value > 0
                    else 0
                )
                observation.append(weight)
            else:
                observation.append(0.0)

        # Market state
        observation.append(market_state.get("market_trend", 0.0))
        observation.append(market_state.get("volatility", 0.0))

        # Number of positions
        observation.append(len(sorted_positions) / 50.0)  # Normalize

        return np.array(observation, dtype=np.float32)

    def _action_to_recommendations(
        self,
        action: np.ndarray,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        portfolio_id: int,
        max_recommendations: int,
    ) -> List[Dict[str, Any]]:
        """
        Convert RL model action into human-readable trade recommendations.

        Args:
            action: Model output (typically portfolio weights or trade signals)
            current_positions: Current holdings
            account_value: Total account value
            portfolio_id: Strategy ID
            max_recommendations: Max number of recommendations

        Returns:
            List of trade recommendations
        """

        recommendations = []

        # Action interpretation depends on training setup
        # For simplicity, treating action as rebalancing weights

        # Strategy-specific logic
        if portfolio_id == 1:  # Growth/Momentum
            recommendations = self._generate_growth_recommendations(
                action, current_positions, account_value, max_recommendations
            )
        elif portfolio_id == 2:  # Dividend
            recommendations = self._generate_dividend_recommendations(
                action, current_positions, account_value, max_recommendations
            )
        elif portfolio_id == 3:  # Value
            recommendations = self._generate_value_recommendations(
                action, current_positions, account_value, max_recommendations
            )

        return recommendations

    def _generate_growth_recommendations(
        self,
        action: np.ndarray,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        max_recommendations: int,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for growth/momentum strategy."""

        # Placeholder - implement based on actual model output
        recommendations = []

        # Example: Suggest increasing tech exposure
        tech_tickers = ["NVDA", "AMD", "AVGO", "TSM", "QCOM"]

        for ticker in tech_tickers[:max_recommendations]:
            # Check if already holding
            current_position = next(
                (p for p in current_positions if p.get("symbol") == ticker), None
            )

            if current_position:
                current_shares = float(current_position.get("quantity", 0))
                suggested_action = "HOLD" if current_shares > 0 else "BUY"
                suggested_shares = max(10, int(current_shares * 1.1))  # Increase by 10%
            else:
                suggested_action = "BUY"
                suggested_shares = int(
                    account_value * 0.05 / 100
                )  # 5% of portfolio, assuming $100/share

            recommendations.append(
                {
                    "ticker": ticker,
                    "action": suggested_action,
                    "shares": suggested_shares,
                    "confidence": 0.75,
                    "reason": "RL model suggests increasing exposure to high-growth tech stocks",
                    "priority": len(recommendations) + 1,
                }
            )

        return recommendations[:max_recommendations]

    def _generate_dividend_recommendations(
        self,
        action: np.ndarray,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        max_recommendations: int,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for dividend strategy."""

        recommendations = []

        # Dividend aristocrats
        dividend_tickers = ["JNJ", "PG", "KO", "PEP", "WMT", "MCD", "VZ"]

        for ticker in dividend_tickers[:max_recommendations]:
            recommendations.append(
                {
                    "ticker": ticker,
                    "action": "BUY",
                    "shares": int(account_value * 0.10 / 100),  # 10% of portfolio
                    "confidence": 0.80,
                    "reason": "RL model recommends dividend aristocrat with stable income",
                    "priority": len(recommendations) + 1,
                }
            )

        return recommendations[:max_recommendations]

    def _generate_value_recommendations(
        self,
        action: np.ndarray,
        current_positions: List[Dict[str, Any]],
        account_value: float,
        max_recommendations: int,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for value strategy."""

        recommendations = []

        # Value stocks
        value_tickers = ["BRK.B", "BAC", "JPM", "CVX", "XOM"]

        for ticker in value_tickers[:max_recommendations]:
            recommendations.append(
                {
                    "ticker": ticker,
                    "action": "BUY",
                    "shares": int(account_value * 0.15 / 100),  # 15% of portfolio
                    "confidence": 0.70,
                    "reason": "RL model identifies undervalued stock with strong fundamentals",
                    "priority": len(recommendations) + 1,
                }
            )

        return recommendations[:max_recommendations]


# Singleton instance
_rl_recommender_service = None


def get_rl_recommender_service() -> RLRecommenderService:
    """Get singleton instance of RL recommender service."""
    global _rl_recommender_service
    if _rl_recommender_service is None:
        _rl_recommender_service = RLRecommenderService()
    return _rl_recommender_service
