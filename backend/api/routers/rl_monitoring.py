"""
RL Model Monitoring API

Provides endpoints for monitoring RL training progress, model performance,
and generating recommendations.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/api/rl", tags=["rl"])

# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

DB_CONFIG = {
    "dbname": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
    "host": "localhost",
    "port": 5432,
}


@router.get("/training-status")
async def get_training_status() -> Dict[str, Any]:
    """
    Get current training status for all RL models.

    Returns training progress, timesteps completed, and estimated completion time.
    """

    portfolios = {
        1: {
            "name": "Growth/Momentum",
            "log_file": str(PROJECT_ROOT / "logs" / "growth_momentum_training.log"),
        },
        2: {
            "name": "Dividend",
            "log_file": str(PROJECT_ROOT / "logs" / "rl_training_dividend_stocks.log"),
        },
        3: {"name": "Value", "log_file": str(PROJECT_ROOT / "logs" / "value_training.log")},
    }

    status = {}

    for portfolio_id, info in portfolios.items():
        log_file = info["log_file"]

        if not os.path.exists(log_file):
            status[portfolio_id] = {
                "name": info["name"],
                "status": "not_started",
                "progress": 0.0,
                "timesteps_completed": 0,
                "total_timesteps": 1000000,
                "estimated_completion": None,
            }
            continue

        # Parse log file for progress
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()

            # Look for progress indicators in logs
            timesteps_completed = 0
            total_timesteps = 1000000

            for line in reversed(lines[-200:]):  # Check last 200 lines
                # Look for PPO training updates
                # Format: "|    total_timesteps      | 1001472     |"
                if "total_timesteps" in line.lower():
                    parts = line.split("|")
                    if len(parts) >= 3:
                        try:
                            timesteps_completed = int(parts[2].strip())
                            break
                        except:
                            pass

            progress_pct = (
                (timesteps_completed / total_timesteps) * 100 if total_timesteps > 0 else 0
            )

            # Estimate completion time (rough estimate: 1M timesteps ~= 2-3 hours)
            if timesteps_completed > 0:
                # Assume ~5000 timesteps/minute
                remaining_timesteps = total_timesteps - timesteps_completed
                estimated_minutes = remaining_timesteps / 5000
                estimated_completion = datetime.now() + timedelta(minutes=estimated_minutes)
            else:
                estimated_completion = None

            status[portfolio_id] = {
                "name": info["name"],
                "status": "training" if timesteps_completed < total_timesteps else "completed",
                "progress": round(progress_pct, 1),
                "timesteps_completed": timesteps_completed,
                "total_timesteps": total_timesteps,
                "estimated_completion": (
                    estimated_completion.isoformat() if estimated_completion else None
                ),
            }

        except Exception as e:
            status[portfolio_id] = {
                "name": info["name"],
                "status": "error",
                "error": str(e),
                "progress": 0.0,
            }

    return {"timestamp": datetime.now().isoformat(), "portfolios": status}


@router.get("/model-performance")
async def get_model_performance() -> Dict[str, Any]:
    """
    Get performance metrics for all trained models.

    Returns backtest results, Sharpe ratios, returns, etc.
    """

    # Check for saved evaluation results
    results_dir = PROJECT_ROOT / "results"

    if not os.path.exists(results_dir):
        return {
            "status": "no_results",
            "message": "No evaluation results found. Run model evaluation first.",
            "portfolios": [],
        }

    # Find most recent comparison results
    result_files = [f for f in os.listdir(results_dir) if f.startswith("model_comparison_")]

    if not result_files:
        return {"status": "no_results", "message": "No comparison results found.", "portfolios": []}

    # Get most recent file
    latest_file = sorted(result_files)[-1]

    with open(os.path.join(results_dir, latest_file), "r") as f:
        comparison_results = json.load(f)

    # Add comparison summary
    if comparison_results:
        best_return = max(comparison_results, key=lambda x: x.get("mean_return", 0))
        best_sharpe = max(comparison_results, key=lambda x: x.get("sharpe_ratio", 0))

        summary = {
            "best_return": {
                "portfolio": best_return["portfolio_name"],
                "value": best_return["mean_return"],
            },
            "best_sharpe": {
                "portfolio": best_sharpe["portfolio_name"],
                "value": best_sharpe["sharpe_ratio"],
            },
        }
    else:
        summary = {}

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "last_updated": latest_file.replace("model_comparison_", "").replace(".json", ""),
        "portfolios": comparison_results,
        "summary": summary,
    }


@router.get("/recommendations/{portfolio_id}")
async def get_rl_recommendations(
    portfolio_id: int, client_id: int = 1, max_recommendations: int = 10
) -> Dict[str, Any]:
    """
    Generate trade recommendations using trained RL model.

    Args:
        portfolio_id: Strategy (1=Growth, 2=Dividend, 3=Value)
        client_id: Client ID
        max_recommendations: Max number of recommendations
    """

    import httpx

    from backend.api.services.rl_recommender import get_rl_recommender_service

    # Get client's account hash
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT account_hash
        FROM brokerage_accounts
        WHERE client_id = %s
        LIMIT 1
    """,
        [client_id],
    )

    account_row = cur.fetchone()
    cur.close()
    conn.close()

    if not account_row:
        raise HTTPException(status_code=404, detail="No brokerage account found for client")

    account_hash = account_row["account_hash"]

    # Fetch current portfolio
    async with httpx.AsyncClient() as http_client:
        portfolio_response = await http_client.get(
            f"http://localhost:8000/api/schwab/portfolio/{client_id}/{account_hash}", timeout=30.0
        )

    if portfolio_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio data")

    portfolio_data = portfolio_response.json()

    # Generate recommendations
    rl_service = get_rl_recommender_service()

    recommendations = await rl_service.generate_recommendations(
        portfolio_id=portfolio_id,
        current_positions=portfolio_data["positions"],
        account_value=portfolio_data["summary"]["total_value"],
        max_recommendations=max_recommendations,
    )

    return recommendations


@router.get("/training-logs/{portfolio_id}")
async def get_training_logs(portfolio_id: int, tail_lines: int = 100) -> Dict[str, Any]:
    """
    Get recent training logs for a specific portfolio.

    Args:
        portfolio_id: Strategy (1=Growth, 2=Dividend, 3=Value)
        tail_lines: Number of recent lines to return
    """

    log_files = {
        1: str(PROJECT_ROOT / "logs" / "growth_momentum_training.log"),
        2: str(PROJECT_ROOT / "logs" / "rl_training_dividend_stocks.log"),
        3: str(PROJECT_ROOT / "logs" / "value_training.log"),
    }

    if portfolio_id not in log_files:
        raise HTTPException(status_code=404, detail="Invalid portfolio_id")

    log_file = log_files[portfolio_id]

    if not os.path.exists(log_file):
        return {"portfolio_id": portfolio_id, "status": "not_started", "logs": []}

    # Read last N lines
    try:
        with open(log_file, "r") as f:
            lines = f.readlines()

        recent_lines = lines[-tail_lines:] if len(lines) > tail_lines else lines

        return {
            "portfolio_id": portfolio_id,
            "status": "success",
            "total_lines": len(lines),
            "returned_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")


@router.get("/model-info")
async def get_model_info() -> Dict[str, Any]:
    """
    Get information about all RL models (paths, strategies, status).
    """

    portfolios = {
        1: {
            "name": "Growth/Momentum",
            "description": "Aggressive growth focused on tech and momentum stocks",
            "model_paths": [
                str(
                    PROJECT_ROOT / "models" / "growth_momentum" / "ppo_growth_momentum.zip"
                ),  # Old location
                str(PROJECT_ROOT / "models" / "growth" / "ppo_growth.zip"),  # New unified location
            ],
            "rebalance_frequency": "monthly",
            "target_volatility": 0.20,
            "expected_return": 0.12,
        },
        2: {
            "name": "Dividend",
            "description": "Conservative income-generating portfolio",
            "model_paths": [
                str(PROJECT_ROOT / "models" / "dividend" / "ppo_dividend.zip"),
            ],
            "rebalance_frequency": "quarterly",
            "target_volatility": 0.12,
            "expected_return": 0.08,
        },
        3: {
            "name": "Value",
            "description": "Contrarian value investing approach",
            "model_paths": [
                str(PROJECT_ROOT / "models" / "value" / "ppo_value.zip"),
            ],
            "rebalance_frequency": "quarterly",
            "target_volatility": 0.15,
            "expected_return": 0.10,
        },
    }

    # Check which models exist (try all possible paths)
    for portfolio_id, info in portfolios.items():
        model_exists = False
        model_path = None
        model_size_mb = 0
        last_modified = None

        for path in info["model_paths"]:
            if os.path.exists(path):
                model_exists = True
                model_path = path
                stat = os.stat(path)
                model_size_mb = round(stat.st_size / (1024 * 1024), 2)
                last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                break  # Use first found model

        info["model_exists"] = model_exists
        info["model_path"] = model_path
        info["model_size_mb"] = model_size_mb
        info["last_modified"] = last_modified

    return {"timestamp": datetime.now().isoformat(), "portfolios": portfolios}
