#!/usr/bin/env python3
"""
Hybrid Portfolio Generator for Autonomous Fund

Integrates ML (XGBoost) + RL (PPO) models to generate optimal portfolios.

Architecture:
1. ML Model (XGBoost) → Select top N stocks by predicted return
2. RL Agent (PPO) → Optimize portfolio weights among selected stocks

This replaces the mock portfolio generator in autonomous_rebalancer.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import date, datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# ML imports
import xgboost as xgb

# RL imports
from stable_baselines3 import PPO

from portfolio.ml_portfolio_manager import MLPortfolioManager
from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class HybridPortfolioGenerator:
    """
    Generates portfolios using trained ML+RL models

    Usage:
        generator = HybridPortfolioGenerator()
        portfolio = generator.generate_portfolio(
            strategy='growth_largecap',
            total_value=100000,
            as_of_date=date.today()
        )
        # Returns: {'AAPL': 0.08, 'MSFT': 0.07, ...}  # Normalized weights summing to 1.0
    """

    def __init__(self):
        """Initialize hybrid portfolio generator"""
        self.models_dir = Path(__file__).parent.parent / "models"
        logger.info("Hybrid Portfolio Generator initialized")

    def generate_portfolio(
        self,
        strategy: str,
        total_value: float,
        as_of_date: Optional[date] = None,
        use_rl: bool = True,  # Enable RL by default for weight optimization
        top_n: int = 50,
        max_position: float = 0.10,
    ) -> Dict[str, float]:
        """
        Generate portfolio using ML+RL models

        Args:
            strategy: Strategy name ('growth_largecap', 'value_midcap', 'dividend_strategy', etc.)
            total_value: Total portfolio value in dollars
            as_of_date: Date to generate portfolio for (None = latest data)
            use_rl: Use RL agent for weight optimization (False = use ML only with equal weights)
            top_n: Number of positions to hold
            max_position: Maximum weight per position

        Returns:
            Dict of {ticker: weight} where weights sum to 1.0
        """
        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Generating portfolio for strategy: {strategy}")
        logger.info(f"  Portfolio value: ${total_value:,.2f}")
        logger.info(f"  As of date: {as_of_date}")
        logger.info(f"  Use RL: {use_rl}")

        try:
            # Step 1: Parse strategy into components
            strategy_type, market_cap = self._parse_strategy(strategy)

            # Step 2: Load ML model and generate predictions
            ml_predictions = self._run_ml_model(strategy_type, market_cap, as_of_date, top_n)

            if ml_predictions is None or len(ml_predictions) == 0:
                logger.error("ML model returned no predictions")
                return {}

            # Step 3: Apply RL for weight optimization (if available and enabled)
            if use_rl:
                portfolio_weights = self._run_rl_model(
                    strategy_type, market_cap, ml_predictions, as_of_date, max_position
                )
            else:
                # Fallback: Equal weight top N stocks
                portfolio_weights = self._equal_weight_portfolio(
                    ml_predictions, top_n, max_position
                )

            # Step 4: Validate and normalize weights
            portfolio_weights = self._normalize_weights(portfolio_weights, max_position)

            logger.info(f"✅ Portfolio generated: {len(portfolio_weights)} positions")
            logger.info(f"   Top 5: {list(portfolio_weights.items())[:5]}")

            return portfolio_weights

        except Exception as e:
            logger.error(f"Error generating portfolio: {e}")
            import traceback

            traceback.print_exc()
            return {}

    def _parse_strategy(self, strategy: str) -> tuple:
        """
        Parse strategy string into (type, market_cap)

        Examples:
            'growth_largecap' -> ('growth', 'large')
            'value_midcap' -> ('value', 'mid')
            'dividend_strategy' -> ('dividend', None)
        """
        if strategy == "dividend_strategy":
            return ("dividend", None)

        parts = strategy.split("_")
        if len(parts) >= 2:
            strategy_type = parts[0]  # 'growth' or 'value'
            market_cap = parts[1].replace("cap", "")  # 'large', 'mid', 'small'
            return (strategy_type, market_cap)

        logger.warning(f"Unknown strategy format: {strategy}, defaulting to growth/mid")
        return ("growth", "mid")

    def _run_ml_model(
        self, strategy_type: str, market_cap: Optional[str], as_of_date: date, top_n: int
    ) -> Optional[pd.DataFrame]:
        """
        Run ML model to get stock predictions

        Returns:
            DataFrame with columns: ticker, predicted_return, rank
        """
        logger.info(f"  [ML] Running XGBoost model: {strategy_type}_{market_cap or ''}")

        try:
            # Initialize ML Portfolio Manager
            ml_manager = MLPortfolioManager(strategy=strategy_type, market_cap_segment=market_cap)

            # Get latest features from database
            features_df = ml_manager.get_latest_features(as_of_date=as_of_date)

            if len(features_df) == 0:
                logger.warning("No features available from database")
                return None

            # Generate predictions
            predictions = ml_manager.generate_predictions(features_df)

            # Filter to top N with positive predictions
            predictions = predictions[predictions["predicted_return"] > 0].head(top_n * 2)

            logger.info(f"  [ML] Generated {len(predictions)} predictions")
            logger.info(
                f"  [ML] Top 5: {predictions[['ticker', 'predicted_return']].head().to_dict('records')}"
            )

            return predictions

        except Exception as e:
            logger.error(f"ML model error: {e}")
            return None

    def _run_rl_model(
        self,
        strategy_type: str,
        market_cap: Optional[str],
        ml_predictions: pd.DataFrame,
        as_of_date: date,
        max_position: float,
    ) -> Dict[str, float]:
        """
        Run RL model to optimize portfolio weights

        Returns:
            Dict of {ticker: weight}
        """
        logger.info(f"  [RL] Running PPO agent for weight optimization")

        try:
            # Construct model path
            if strategy_type == "dividend":
                model_name = "dividend_strategy"
            else:
                model_name = f"{strategy_type}_{market_cap}cap"

            # Try hybrid model first (PPO trained with ML environment)
            rl_model_path = self.models_dir / f"ppo_hybrid_{model_name}" / "best_model.zip"

            if not rl_model_path.exists():
                # Fallback to standard PPO model
                rl_model_path = self.models_dir / model_name / "ppo_best.zip"

            if not rl_model_path.exists():
                logger.warning(f"RL model not found at {rl_model_path}, using equal weights")
                return self._equal_weight_portfolio(
                    ml_predictions, len(ml_predictions), max_position
                )

            # Load RL agent
            logger.info(f"  [RL] Loading model from: {rl_model_path}")
            rl_agent = PPO.load(str(rl_model_path))

            # Prepare observation (state) for RL agent
            # State includes: ML predictions, market indicators, portfolio metrics
            state = self._prepare_rl_state(ml_predictions, as_of_date)

            # Get action (portfolio weights) from RL agent
            action, _ = rl_agent.predict(state, deterministic=True)

            # Convert action to portfolio weights
            # Action is array of weights that need to be normalized
            weights = np.maximum(action, 0)  # Ensure non-negative
            weights = weights / (weights.sum() + 1e-8)  # Normalize to sum to 1

            # Map weights to tickers
            tickers = ml_predictions["ticker"].tolist()[: len(weights)]
            portfolio_weights = {
                ticker: float(weight) for ticker, weight in zip(tickers, weights) if weight > 0.01
            }

            logger.info(f"  [RL] Generated {len(portfolio_weights)} positions with RL optimization")

            return portfolio_weights

        except Exception as e:
            logger.error(f"RL model error: {e}, falling back to equal weights")
            import traceback

            traceback.print_exc()
            return self._equal_weight_portfolio(ml_predictions, len(ml_predictions), max_position)

    def _prepare_rl_state(self, ml_predictions: pd.DataFrame, as_of_date: date) -> np.ndarray:
        """
        Prepare state observation for RL agent

        State includes:
        - ML prediction scores (normalized)
        - Market regime indicators
        - Portfolio metrics (if available)

        Returns:
            numpy array of state features
        """
        # Extract ML predictions (top 50)
        top_predictions = ml_predictions["predicted_return"].head(50).values

        # Pad if fewer than 50
        if len(top_predictions) < 50:
            top_predictions = np.pad(
                top_predictions, (0, 50 - len(top_predictions)), constant_values=0
            )

        # Normalize predictions to [0, 1]
        if top_predictions.max() > 0:
            top_predictions = top_predictions / top_predictions.max()

        # Add market regime features (placeholder - would query from database)
        market_features = np.array(
            [
                0.5,  # volatility regime (normalized)
                0.6,  # trend strength
                1.0,  # market breadth
            ]
        )

        # Combine into state vector
        state = np.concatenate([top_predictions, market_features])

        return state.astype(np.float32)

    def _equal_weight_portfolio(
        self, ml_predictions: pd.DataFrame, top_n: int, max_position: float
    ) -> Dict[str, float]:
        """
        Fallback: Create equal-weight portfolio from ML predictions
        """
        logger.info(f"  Creating equal-weight portfolio with top {top_n} stocks")

        top_stocks = ml_predictions.head(top_n)
        equal_weight = min(1.0 / top_n, max_position)

        portfolio = {row["ticker"]: equal_weight for _, row in top_stocks.iterrows()}

        # Normalize to sum to 1.0
        total_weight = sum(portfolio.values())
        portfolio = {k: v / total_weight for k, v in portfolio.items()}

        return portfolio

    def _normalize_weights(
        self, portfolio: Dict[str, float], max_position: float
    ) -> Dict[str, float]:
        """
        Ensure weights are valid:
        - All weights >= 0
        - No weight > max_position
        - Sum to 1.0
        """
        if not portfolio:
            return {}

        # Remove negative weights
        portfolio = {k: v for k, v in portfolio.items() if v > 0}

        # Cap at max position
        portfolio = {k: min(v, max_position) for k, v in portfolio.items()}

        # Normalize to sum to 1.0
        total_weight = sum(portfolio.values())
        if total_weight > 0:
            portfolio = {k: v / total_weight for k, v in portfolio.items()}

        # Remove tiny positions (< 0.5%)
        portfolio = {k: v for k, v in portfolio.items() if v >= 0.005}

        # Renormalize after filtering
        total_weight = sum(portfolio.values())
        if total_weight > 0:
            portfolio = {k: v / total_weight for k, v in portfolio.items()}

        return portfolio


def main():
    """Test the hybrid portfolio generator"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Hybrid Portfolio Generator")
    parser.add_argument(
        "--strategy",
        type=str,
        default="growth_largecap",
        choices=[
            "growth_largecap",
            "growth_midcap",
            "growth_smallcap",
            "value_largecap",
            "value_midcap",
            "value_smallcap",
            "dividend_strategy",
        ],
    )
    parser.add_argument("--value", type=float, default=100000, help="Portfolio value")
    parser.add_argument("--use-rl", action="store_true", help="Use RL for weight optimization")

    args = parser.parse_args()

    generator = HybridPortfolioGenerator()

    portfolio = generator.generate_portfolio(
        strategy=args.strategy, total_value=args.value, use_rl=args.use_rl
    )

    logger.info("=" * 60)
    logger.info("GENERATED PORTFOLIO")
    logger.info("=" * 60)

    if portfolio:
        df = pd.DataFrame(
            [
                {
                    "Ticker": ticker,
                    "Weight": f"{weight:.2%}",
                    "Value": f"${weight * args.value:,.2f}",
                }
                for ticker, weight in sorted(portfolio.items(), key=lambda x: x[1], reverse=True)
            ]
        )

        print(df.to_string(index=False))
        print(f"\nTotal positions: {len(portfolio)}")
        print(f"Total weight: {sum(portfolio.values()):.4f}")
    else:
        logger.error("Failed to generate portfolio")


if __name__ == "__main__":
    main()
