#!/usr/bin/env python3
"""
Meta-Strategy Selection System

AI model that automatically selects the best strategy based on:
- Market regime (volatility, trend, breadth)
- Recent strategy performance (Sharpe, returns, drawdown)
- Historical regime-strategy mappings

Outputs:
- Probability distribution over 7 strategies
- Selected strategy (highest expected Sharpe)
- Confidence score
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from utils import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}

STRATEGIES = [
    "growth_smallcap",
    "growth_midcap",
    "growth_largecap",
    "value_smallcap",
    "value_midcap",
    "value_largecap",
    "dividend_strategy",
]


class MetaStrategySelector:
    """
    AI model that selects optimal strategy based on market regime
    """

    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.model = None
        self.scaler = None
        self.model_path = Path(__file__).parent.parent / "models" / "meta_strategy_selector.joblib"
        self.scaler_path = Path(__file__).parent.parent / "models" / "meta_strategy_scaler.joblib"

    def get_latest_regime(self):
        """Get most recent market regime data"""
        query = """
        SELECT
            date,
            volatility_regime,
            realized_volatility_20d,
            trend_regime,
            spy_sma_50,
            spy_sma_200,
            advance_decline_ratio,
            new_highs_lows_ratio,
            regime_label,
            regime_confidence
        FROM market_regime
        ORDER BY date DESC
        LIMIT 1
        """
        df = pd.read_sql(query, self.conn)

        if df.empty:
            logger.warning("No market regime data found - run market_regime_detector.py first")
            return None

        return df.iloc[0]

    def get_strategy_performance(self, lookback_days=30):
        """
        Get recent performance for all strategies

        Returns DataFrame with columns:
        - strategy
        - sharpe_ratio_30d
        - max_drawdown_30d
        - win_rate_30d
        - outperformance_vs_spy
        """
        query = """
        SELECT
            strategy,
            AVG(sharpe_ratio_30d) as avg_sharpe,
            AVG(max_drawdown_30d) as avg_drawdown,
            AVG(win_rate_30d) as avg_win_rate,
            AVG(outperformance_vs_spy) as avg_alpha,
            AVG(volatility_30d) as avg_volatility
        FROM strategy_performance
        WHERE date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY strategy
        ORDER BY strategy
        """
        df = pd.read_sql(query, self.conn, params=(lookback_days,))

        if df.empty:
            logger.warning(
                "No strategy performance data found - need to populate strategy_performance table"
            )
            return None

        return df

    def create_features(self, regime_data, strategy_perf):
        """
        Create feature vector for meta-model

        Features:
        - Volatility regime (encoded: low=0, medium=1, high=2, extreme=3)
        - Realized volatility (numeric)
        - Trend regime (encoded: bear=-1, sideways=0, bull=1)
        - SMA ratio (SMA50 / SMA200)
        - Advance/Decline ratio
        - New Highs/Lows ratio
        - Recent strategy Sharpe ratios (7 features)
        - Recent strategy drawdowns (7 features)
        """
        features = {}

        # Market regime features
        vol_regime_map = {"low": 0, "medium": 1, "high": 2, "extreme": 3}
        features["vol_regime_encoded"] = vol_regime_map.get(regime_data["volatility_regime"], 1)
        features["realized_vol"] = regime_data["realized_volatility_20d"]

        trend_regime_map = {"bear": -1, "sideways": 0, "bull": 1}
        features["trend_regime_encoded"] = trend_regime_map.get(regime_data["trend_regime"], 0)

        features["sma_ratio"] = (
            regime_data["spy_sma_50"] / regime_data["spy_sma_200"]
            if regime_data["spy_sma_200"] > 0
            else 1.0
        )
        features["ad_ratio"] = regime_data["advance_decline_ratio"]
        features["hl_ratio"] = regime_data["new_highs_lows_ratio"]

        # Strategy performance features
        if strategy_perf is not None:
            for strategy in STRATEGIES:
                strategy_row = strategy_perf[strategy_perf["strategy"] == strategy]

                if not strategy_row.empty:
                    features[f"{strategy}_sharpe"] = strategy_row["avg_sharpe"].iloc[0]
                    features[f"{strategy}_drawdown"] = strategy_row["avg_drawdown"].iloc[0]
                else:
                    # Default values if strategy not tracked yet
                    features[f"{strategy}_sharpe"] = 0.0
                    features[f"{strategy}_drawdown"] = 0.0
        else:
            # No performance data yet - use neutral defaults
            for strategy in STRATEGIES:
                features[f"{strategy}_sharpe"] = 0.0
                features[f"{strategy}_drawdown"] = 0.0

        return features

    def select_strategy_rule_based(self, regime_data, strategy_perf):
        """
        Rule-based strategy selection (fallback when no trained model)

        Rules:
        - Bull + Low Vol → Growth Large Cap
        - Bull + High Vol → Value Large Cap (defensive)
        - Bear + Low Vol → Dividend Strategy
        - Bear + High Vol → Value Large Cap (defensive)
        - Sideways + Low Vol → Growth Mid Cap
        - Sideways + High Vol → Dividend Strategy
        """
        vol = regime_data["volatility_regime"]
        trend = regime_data["trend_regime"]

        logger.info(f"Rule-based selection: {trend} + {vol} volatility")

        # Bull market rules
        if trend == "bull":
            if vol in ["low", "medium"]:
                selected = "growth_largecap"
                confidence = 0.75
            else:  # high or extreme vol
                selected = "value_largecap"
                confidence = 0.65

        # Bear market rules
        elif trend == "bear":
            if vol in ["low", "medium"]:
                selected = "dividend_strategy"
                confidence = 0.70
            else:  # high or extreme vol
                selected = "value_largecap"
                confidence = 0.70

        # Sideways market rules
        else:
            if vol in ["low", "medium"]:
                selected = "growth_midcap"
                confidence = 0.60
            else:
                selected = "dividend_strategy"
                confidence = 0.65

        # If we have performance data, boost confidence for top performers
        if strategy_perf is not None:
            selected_perf = strategy_perf[strategy_perf["strategy"] == selected]
            if not selected_perf.empty:
                sharpe = selected_perf["avg_sharpe"].iloc[0]
                if sharpe > 1.5:
                    confidence += 0.1
                elif sharpe < 0.5:
                    confidence -= 0.15

        confidence = min(max(confidence, 0.0), 1.0)

        logger.info(f"Rule-based selected: {selected} (confidence: {confidence:.2%})")

        # Create probability distribution (one-hot with noise)
        probabilities = {s: 0.05 for s in STRATEGIES}  # Small prob for all
        probabilities[selected] = 0.65 + (confidence - 0.65)  # Boost selected

        # Normalize to sum to 1.0
        total = sum(probabilities.values())
        probabilities = {k: v / total for k, v in probabilities.items()}

        return selected, confidence, probabilities

    def select_strategy_ml(self, regime_data, strategy_perf):
        """
        ML-based strategy selection using trained model

        Returns: (selected_strategy, confidence, probabilities)
        """
        # Create feature vector
        features_dict = self.create_features(regime_data, strategy_perf)
        feature_names = sorted(features_dict.keys())
        X = np.array([features_dict[f] for f in feature_names]).reshape(1, -1)

        # Scale features
        X_scaled = self.scaler.transform(X)

        # Predict probabilities
        probs = self.model.predict_proba(X_scaled)[0]

        # Map to strategy names
        probabilities = {STRATEGIES[i]: float(probs[i]) for i in range(len(STRATEGIES))}

        # Select strategy with highest probability
        selected = max(probabilities, key=probabilities.get)
        confidence = probabilities[selected]

        logger.info(f"ML-based selected: {selected} (confidence: {confidence:.2%})")
        logger.info(
            f"Top 3 strategies: {sorted(probabilities.items(), key=lambda x: x[1], reverse=True)[:3]}"
        )

        return selected, confidence, probabilities

    def select_strategy(self, use_ml=False):
        """
        Main method: Select best strategy for current market regime

        Args:
            use_ml: If True and model exists, use ML. Otherwise use rule-based.

        Returns: dict with selection results
        """
        logger.info("=" * 60)
        logger.info("META-STRATEGY SELECTION")
        logger.info("=" * 60)

        # Get market regime
        regime_data = self.get_latest_regime()
        if regime_data is None:
            raise ValueError(
                "No market regime data available - run market_regime_detector.py first"
            )

        logger.info(f"Market Regime: {regime_data['regime_label']}")
        logger.info(
            f"  Volatility: {regime_data['volatility_regime']} ({regime_data['realized_volatility_20d']:.2%})"
        )
        logger.info(f"  Trend: {regime_data['trend_regime']}")

        # Get recent strategy performance
        strategy_perf = self.get_strategy_performance(lookback_days=30)
        if strategy_perf is not None:
            logger.info(f"Strategy performance data: {len(strategy_perf)} strategies tracked")

        # Select strategy
        if use_ml and self.model is not None:
            selected, confidence, probabilities = self.select_strategy_ml(
                regime_data, strategy_perf
            )
        else:
            if use_ml:
                logger.warning("ML model not trained yet - using rule-based selection")
            selected, confidence, probabilities = self.select_strategy_rule_based(
                regime_data, strategy_perf
            )

        result = {
            "date": datetime.now().date(),
            "selected_strategy": selected,
            "selection_confidence": confidence,
            "strategy_probabilities": probabilities,
            "market_regime": regime_data["regime_label"],
            "volatility_regime": regime_data["volatility_regime"],
            "trend_regime": regime_data["trend_regime"],
            "model_version": "rule_based_v1" if not use_ml else "ml_v1",
        }

        return result

    def save_selection(self, selection_data):
        """Save strategy selection to database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            INSERT INTO meta_strategy_selection (
                date, strategy_probabilities, selected_strategy,
                selection_confidence, market_regime, model_version
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                strategy_probabilities = EXCLUDED.strategy_probabilities,
                selected_strategy = EXCLUDED.selected_strategy,
                selection_confidence = EXCLUDED.selection_confidence,
                market_regime = EXCLUDED.market_regime,
                model_version = EXCLUDED.model_version
        """,
            (
                selection_data["date"],
                psycopg2.extras.Json(selection_data["strategy_probabilities"]),
                selection_data["selected_strategy"],
                selection_data["selection_confidence"],
                selection_data["market_regime"],
                selection_data["model_version"],
            ),
        )

        self.conn.commit()
        logger.info(f"✅ Selection saved to database: {selection_data['selected_strategy']}")

    def train_meta_model(self, start_date="2015-01-01", end_date=None):
        """
        Train meta-strategy selection model on historical data

        This requires:
        1. Historical market regime data
        2. Historical strategy performance data
        3. Labels (which strategy performed best in each regime)

        For now, this is a placeholder - we need to run the system
        for a while to collect training data.
        """
        logger.info("=" * 60)
        logger.info("TRAINING META-STRATEGY SELECTION MODEL")
        logger.info("=" * 60)

        # Check if we have enough data
        query = """
        SELECT COUNT(*) as regime_days
        FROM market_regime
        WHERE date >= %s
        """
        cur = self.conn.cursor()
        cur.execute(query, (start_date,))
        regime_days = cur.fetchone()[0]

        logger.info(f"Market regime data available: {regime_days} days")

        if regime_days < 100:
            logger.warning(
                "Not enough training data yet - need at least 100 days of regime tracking"
            )
            logger.warning("Run market_regime_detector.py daily to build up training data")
            return False

        # TODO: Implement actual model training
        # For now, we'll use rule-based selection
        logger.info("Meta-model training not yet implemented - using rule-based selection")

        return False

    def load_model(self):
        """Load trained meta-model from disk"""
        if self.model_path.exists() and self.scaler_path.exists():
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            logger.info(f"Loaded meta-model from {self.model_path}")
            return True
        return False

    def close(self):
        self.conn.close()


def main():
    """Run meta-strategy selection"""
    selector = MetaStrategySelector()

    try:
        # Try to load trained model
        has_model = selector.load_model()

        # Select strategy
        selection = selector.select_strategy(use_ml=has_model)

        # Save to database
        selector.save_selection(selection)

        # Print summary
        logger.info("=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Date: {selection['date']}")
        logger.info(f"Market Regime: {selection['market_regime']}")
        logger.info(f"Selected Strategy: {selection['selected_strategy']}")
        logger.info(f"Confidence: {selection['selection_confidence']:.2%}")
        logger.info(f"Model: {selection['model_version']}")
        logger.info("")
        logger.info("Strategy Probabilities:")
        for strategy, prob in sorted(
            selection["strategy_probabilities"].items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  {strategy:25s}: {prob:.2%}")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Error selecting strategy: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        selector.close()


if __name__ == "__main__":
    sys.exit(main())
