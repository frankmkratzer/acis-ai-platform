"""
Backtesting API Endpoints
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio.backtest_engine import BacktestEngine

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestConfig(BaseModel):
    """Backtest configuration"""

    start_date: str  # ISO format date
    end_date: str  # ISO format date
    initial_capital: float = 100000.0
    top_n: int = 50
    weighting: str = "signal"
    max_position: float = 0.10
    rebalance_frequency: int = 20  # days
    transaction_cost: float = 0.001  # 10 bps
    min_market_cap: Optional[float] = None


class BacktestResponse(BaseModel):
    """Backtest results"""

    performance_metrics: dict
    rebalance_history: List[dict]
    config: dict


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(config: BacktestConfig):
    """
    Run a backtest simulation

    Args:
        config: Backtest configuration

    Returns:
        Backtest results with performance metrics
    """
    try:
        # Parse dates
        start_date = date.fromisoformat(config.start_date)
        end_date = date.fromisoformat(config.end_date)

        # Validate dates
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        # Initialize backtest engine
        engine = BacktestEngine(
            rebalance_frequency=config.rebalance_frequency, transaction_cost=config.transaction_cost
        )

        # Run backtest
        results = engine.run_backtest(
            start_date=start_date,
            end_date=end_date,
            initial_capital=config.initial_capital,
            top_n=config.top_n,
            weighting=config.weighting,
            max_position=config.max_position,
            min_market_cap=config.min_market_cap,
        )

        return BacktestResponse(
            performance_metrics=results["performance_metrics"],
            rebalance_history=results["rebalance_history"],
            config=results["config"],
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/quick-metrics")
async def get_quick_metrics(start_date: str, end_date: str, min_market_cap: Optional[float] = None):
    """
    Get quick performance metrics for a time period

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        min_market_cap: Optional market cap filter

    Returns:
        Quick performance summary
    """
    try:
        # Parse dates
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        # Run quick backtest
        engine = BacktestEngine()
        results = engine.run_backtest(
            start_date=start,
            end_date=end,
            initial_capital=100000.0,
            top_n=50,
            min_market_cap=min_market_cap,
        )

        return {
            "metrics": results["performance_metrics"],
            "num_rebalances": len(results["rebalance_history"]),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
