"""
ML Portfolio Management API Endpoints
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio.ml_portfolio_manager import MLPortfolioManager

router = APIRouter(prefix="/api/ml-portfolio", tags=["ml-portfolio"])


class PortfolioConfig(BaseModel):
    """Portfolio configuration"""

    top_n: int = 50
    weighting: str = "signal"  # 'equal', 'rank', 'signal'
    max_position: float = 0.10
    cash_available: float = 100000.0
    tickers: Optional[List[str]] = None
    as_of_date: Optional[str] = None
    min_market_cap: Optional[float] = None  # Minimum market cap in dollars (e.g., 10e9 for $10B)
    strategy: Optional[str] = None  # 'dividend', 'growth', 'value', None for default
    market_cap_segment: Optional[str] = None  # 'small', 'mid', 'large', 'all'


class PortfolioResponse(BaseModel):
    """Portfolio generation response"""

    target_portfolio: List[dict]
    predictions: List[dict]
    stats: dict
    config: PortfolioConfig


@router.post("/generate", response_model=PortfolioResponse)
async def generate_portfolio(config: PortfolioConfig):
    """
    Generate ML-based portfolio recommendations

    Args:
        config: Portfolio configuration

    Returns:
        Portfolio with predictions and statistics
    """
    try:
        # Initialize manager with strategy-specific model
        manager = MLPortfolioManager(
            strategy=config.strategy, market_cap_segment=config.market_cap_segment
        )

        # Convert date string to date object
        as_of_date = None
        if config.as_of_date:
            as_of_date = date.fromisoformat(config.as_of_date)

        # Execute rebalancing workflow
        result = manager.execute_rebalance(
            tickers=config.tickers,
            current_portfolio={},
            cash_available=config.cash_available,
            top_n=config.top_n,
            weighting=config.weighting,
            max_position=config.max_position,
            as_of_date=as_of_date,
            min_market_cap=config.min_market_cap,
        )

        if result is None:
            raise HTTPException(status_code=500, detail="Failed to generate portfolio")

        # Format response
        target_portfolio = result["target_portfolio"].to_dict("records")
        predictions = result["predictions"].head(100).to_dict("records")  # Top 100 only

        # Calculate stats
        stats = {
            "total_universe": result["universe_size"],
            "top_predicted_return": (
                float(predictions[0]["predicted_return"]) if len(predictions) > 0 else 0.0
            ),
            "median_predicted_return": float(result["predictions"]["predicted_return"].median()),
            "model_ic": 0.0876,  # From training
            "last_updated": str(result["rebalance_date"]),
        }

        return PortfolioResponse(
            target_portfolio=target_portfolio, predictions=predictions, stats=stats, config=config
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating portfolio: {str(e)}")


@router.get("/model-info")
async def get_model_info():
    """Get trained model information"""
    try:
        manager = MLPortfolioManager()

        return {
            "model_path": str(manager.model_path),
            "num_features": len(manager.feature_names),
            "feature_names": manager.feature_names,
            "spearman_ic": 0.0876,
            "training_period": "2015-2025 (10.8 years)",
            "training_samples": 5965707,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading model info: {str(e)}")


@router.get("/feature-importance")
async def get_feature_importance():
    """Get feature importance from trained model"""
    try:
        import pandas as pd

        # Load feature importance
        importance_df = pd.read_csv("ml_models/feature_importance/feature_importance.csv")

        return {"features": importance_df.head(20).to_dict("records")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading feature importance: {str(e)}")


@router.get("/predictions")
async def get_latest_predictions(limit: int = 100):
    """Get latest stock predictions"""
    try:
        manager = MLPortfolioManager()

        # Load latest features
        features_df = manager.get_latest_features()

        # Generate predictions
        predictions = manager.generate_predictions(features_df)

        return {
            "predictions": predictions.head(limit).to_dict("records"),
            "total_count": len(predictions),
            "date": str(features_df["date"].iloc[0]) if len(features_df) > 0 else None,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting predictions: {str(e)}")
