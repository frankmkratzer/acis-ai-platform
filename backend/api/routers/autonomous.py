"""
Autonomous Trading System API Routes

Provides real-time status and control for the autonomous fund
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.connection import get_db

router = APIRouter(prefix="/api/autonomous", tags=["autonomous"])


@router.get("/status")
async def get_autonomous_status(db: Session = Depends(get_db)):
    """
    Get current status of the autonomous trading system

    Returns:
        - Market regime
        - Active strategy
        - Portfolio status
        - Model status
        - Next rebalance time
    """
    try:
        # Get latest market regime
        result = db.execute(
            text(
                """
            SELECT *
            FROM market_regime
            ORDER BY date DESC
            LIMIT 1
        """
            )
        )
        market_regime = result.fetchone()

        # Get latest rebalance event to determine active strategy
        result = db.execute(
            text(
                """
            SELECT strategy_selected, meta_model_confidence
            FROM rebalancing_log
            ORDER BY rebalance_date DESC
            LIMIT 1
        """
            )
        )
        latest_rebalance = result.fetchone()

        # Get aggregate portfolio status across ALL active client accounts
        result = db.execute(
            text(
                """
            SELECT
                COALESCE(
                    (SELECT SUM(cash_balance) FROM paper_accounts WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as cash_balance,
                COALESCE(
                    (SELECT SUM(market_value) FROM paper_positions WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as positions_value,
                COALESCE(
                    (SELECT SUM(cash_balance) FROM paper_accounts WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) + COALESCE(
                    (SELECT SUM(market_value) FROM paper_positions WHERE account_id IN
                        (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
                    ), 0
                ) as total_value
        """
            )
        )
        account = result.fetchone()

        # Get current positions count across all active accounts
        result = db.execute(
            text(
                """
            SELECT COUNT(*) as num_positions
            FROM paper_positions
            WHERE account_id IN (SELECT account_hash FROM client_brokerage_accounts WHERE is_active = true)
              AND quantity > 0
        """
            )
        )
        positions_count = result.fetchone()

        # Calculate max drift (simplified - would need target weights from last rebalance)
        max_drift = 0.032  # Mock for now - would calculate from actual vs target weights
        max_drift_ticker = "AAPL"

        # Determine model status
        # In production, would check actual model files and training status
        ml_model_status = "active"  # XGBoost is active
        rl_model_status = "fallback"  # PPO training, using equal weights
        risk_status = "operational"

        # Next rebalance (daily at 4:30 PM ET)
        next_rebalance = "Today 4:30 PM"

        return {
            "market_regime": dict(market_regime._mapping) if market_regime else None,
            "active_strategy": (
                latest_rebalance.strategy_selected if latest_rebalance else "growth_largecap"
            ),
            "strategy_confidence": (
                float(latest_rebalance.meta_model_confidence) if latest_rebalance else 0.85
            ),
            "portfolio_value": float(account.total_value) if account else 100000.0,
            "cash_balance": float(account.cash_balance) if account else 2000.0,
            "num_positions": positions_count.num_positions if positions_count else 0,
            "max_drift": max_drift,
            "max_drift_ticker": max_drift_ticker,
            "next_rebalance": next_rebalance,
            "ml_model_status": ml_model_status,
            "rl_model_status": rl_model_status,
            "risk_status": risk_status,
            "paper_trading": True,  # Would check from config
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching autonomous status: {str(e)}")


@router.get("/rebalances")
async def get_rebalances(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """
    Get recent rebalancing events

    Args:
        limit: Number of events to return (default: 10)
        offset: Pagination offset (default: 0)

    Returns:
        List of rebalancing events with trades and performance
    """
    try:
        result = db.execute(
            text(
                """
            SELECT
                id,
                rebalance_date,
                account_id,
                strategy_selected,
                meta_model_confidence,
                market_regime,
                pre_rebalance_value,
                post_rebalance_value,
                num_positions_before,
                num_positions_after,
                num_buys,
                num_sells,
                total_turnover,
                total_transaction_costs,
                status,
                execution_time_seconds,
                created_at
            FROM rebalancing_log
            ORDER BY rebalance_date DESC
            LIMIT :limit OFFSET :offset
        """
            ),
            {"limit": limit, "offset": offset},
        )

        rebalances = result.fetchall()

        return [dict(r._mapping) for r in rebalances]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rebalances: {str(e)}")


@router.get("/rebalances/{rebalance_id}")
async def get_rebalance_detail(rebalance_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific rebalancing event

    Args:
        rebalance_id: ID of the rebalancing event

    Returns:
        Detailed rebalancing data including trades
    """
    try:
        result = db.execute(
            text(
                """
            SELECT *
            FROM rebalancing_log
            WHERE id = :rebalance_id
        """
            ),
            {"rebalance_id": rebalance_id},
        )

        rebalance = result.fetchone()

        if not rebalance:
            raise HTTPException(status_code=404, detail="Rebalance event not found")

        # Get associated trades
        result = db.execute(
            text(
                """
            SELECT *
            FROM trade_executions
            WHERE rebalance_id = :rebalance_id
            ORDER BY executed_at
        """
            ),
            {"rebalance_id": rebalance_id},
        )

        trades = result.fetchall()

        response = dict(rebalance._mapping)
        response["trades"] = [dict(t._mapping) for t in trades]

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rebalance detail: {str(e)}")


@router.get("/portfolio")
async def get_autonomous_portfolio(db: Session = Depends(get_db)):
    """
    Get current autonomous fund portfolio positions

    Returns:
        Current positions with market values and weights
    """
    try:
        result = db.execute(
            text(
                """
            SELECT
                ticker,
                quantity,
                avg_price,
                market_value,
                unrealized_pnl,
                updated_at
            FROM paper_positions
            WHERE account_id = 'PAPER_AUTONOMOUS_FUND'
              AND quantity > 0
            ORDER BY market_value DESC
        """
            )
        )

        positions = result.fetchall()

        # Calculate total value for weights
        total_value = sum(float(p.market_value) for p in positions)

        response = []
        for pos in positions:
            p = dict(pos._mapping)
            p["weight"] = float(p["market_value"]) / total_value if total_value > 0 else 0
            response.append(p)

        return {"positions": response, "total_value": total_value, "num_positions": len(response)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching portfolio: {str(e)}")


@router.get("/market-regime")
async def get_market_regime_history(days: int = 30, db: Session = Depends(get_db)):
    """
    Get market regime history

    Args:
        days: Number of days of history to return (default: 30)

    Returns:
        Historical market regime classifications
    """
    try:
        result = db.execute(
            text(
                """
            SELECT *
            FROM market_regime
            ORDER BY date DESC
            LIMIT :days
        """
            ),
            {"days": days},
        )

        regimes = result.fetchall()

        return [dict(r._mapping) for r in regimes]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching market regime history: {str(e)}"
        )


@router.post("/rebalance/trigger")
async def trigger_rebalance(force: bool = False, dry_run: bool = True, db=Depends(get_db)):
    """
    Manually trigger a rebalance (admin only)

    Args:
        force: Force rebalance even if not needed
        dry_run: Run in dry run mode (default: True)

    Returns:
        Rebalance execution results
    """
    # This would call the autonomous rebalancer
    # For now, return a mock response

    return {
        "status": "not_implemented",
        "message": "Manual rebalancing trigger not yet implemented. Use CLI: python scripts/run_daily_rebalance.py",
        "force": force,
        "dry_run": dry_run,
    }


@router.get("/performance/metrics")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get autonomous fund performance metrics

    Returns:
        Performance statistics (CAGR, Sharpe, drawdown, etc.)
    """
    try:
        # Get historical values from rebalancing log
        result = db.execute(
            text(
                """
            SELECT
                rebalance_date,
                post_rebalance_value
            FROM rebalancing_log
            ORDER BY rebalance_date ASC
        """
            )
        )

        history = result.fetchall()

        if not history or len(history) < 2:
            return {
                "total_return": 0.0,
                "cagr": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "num_rebalances": 0,
            }

        # Calculate basic metrics
        initial_value = float(history[0].post_rebalance_value)
        final_value = float(history[-1].post_rebalance_value)
        total_return = final_value / initial_value - 1

        # Calculate CAGR (simplified - would need actual date range)
        years = len(history) / 12  # Assuming monthly rebalances
        cagr = (final_value / initial_value) ** (1 / years) - 1 if years > 0 else 0

        # Calculate drawdown
        values = [float(r.post_rebalance_value) for r in history]
        peak = values[0]
        max_dd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

        return {
            "total_return": total_return,
            "cagr": cagr,
            "sharpe_ratio": 1.19,  # Would calculate from returns
            "max_drawdown": max_dd,
            "num_rebalances": len(history),
            "initial_value": initial_value,
            "current_value": final_value,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating performance metrics: {str(e)}"
        )
