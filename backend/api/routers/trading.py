"""
Trading Router - Trade Recommendations and Execution

Endpoints:
- Generate trade recommendations from RL models
- Create trade recommendations
- Execute trades
- Track trade status
- Approve/reject recommendations
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models import schemas
from ..services.rl_recommendation_service import get_recommendation_service
from ..services.schwab_api import SchwabAPIClient
from ..services.schwab_oauth import SchwabOAuthService
from ..services.trading_service import TradingService

router = APIRouter(prefix="/api/trading", tags=["Trading"])


@router.post("/recommendations/generate")
async def generate_recommendations(
    client_id: int,
    account_hash: str,
    portfolio_id: int = 1,  # Default: Growth/Momentum
    db: Session = Depends(get_db),
):
    """
    Generate trade recommendations from RL model.

    Steps:
    1. Fetch current portfolio from Schwab
    2. Load RL model for portfolio
    3. Generate target allocation
    4. Calculate required trades
    5. Store recommendations in database

    Args:
        client_id: Internal client ID
        account_hash: Schwab account hash
        portfolio_id: RL portfolio ID (1=Growth/Momentum, 2=Dividend, 3=Value)

    Returns:
        Trade recommendations with reasoning
    """
    try:
        # Get valid Schwab token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404,
                detail="No Schwab connection. Authorize at /api/schwab/authorize/{client_id}",
            )

        # Get current portfolio from Schwab
        schwab_client = SchwabAPIClient(token)
        positions = await schwab_client.get_positions(account_hash)
        balances = await schwab_client.get_balances(account_hash)

        account_value = balances.get("account_value", 0)
        cash = balances.get("cash", 0)

        # Generate recommendations from RL model
        rec_service = get_recommendation_service()
        recommendations = rec_service.generate_recommendations(
            portfolio_id=portfolio_id,
            current_positions=positions,
            account_value=account_value,
            cash=cash,
        )

        # Store in database
        recommendation_id = _store_recommendation(db, client_id, account_hash, recommendations)

        return {"recommendation_id": recommendation_id, **recommendations}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}")


@router.get("/recommendations/")
async def get_recommendations(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get trade recommendations.

    Args:
        client_id: Filter by client ID
        status: Filter by status (pending, approved, rejected, executed)
        limit: Maximum results

    Returns:
        List of trade recommendations
    """
    query = """
        SELECT
            id, client_id, account_id, rl_portfolio_id, rl_portfolio_name,
            recommendation_type, trades, status, total_trades,
            total_buy_value, total_sell_value, expected_turnover,
            notes, created_at, approved_at, executed_at
        FROM trade_recommendations
        WHERE 1=1
    """

    params = {"limit": limit}

    if client_id:
        query += " AND client_id = :client_id"
        params["client_id"] = client_id

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY created_at DESC LIMIT :limit"

    result = db.execute(text(query), params)

    recommendations = []
    for row in result:
        recommendations.append(
            {
                "id": row[0],
                "client_id": row[1],
                "account_id": row[2],
                "rl_portfolio_id": row[3],
                "rl_portfolio_name": row[4],
                "recommendation_type": row[5],
                "trades": row[6],
                "status": row[7],
                "total_trades": row[8],
                "total_buy_value": float(row[9]) if row[9] else 0,
                "total_sell_value": float(row[10]) if row[10] else 0,
                "expected_turnover": float(row[11]) if row[11] else 0,
                "notes": row[12],
                "created_at": row[13],
                "approved_at": row[14],
                "executed_at": row[15],
            }
        )

    return {"recommendations": recommendations, "count": len(recommendations)}


@router.get("/recommendations/{recommendation_id}")
async def get_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    """Get a specific trade recommendation by ID."""
    query = text(
        """
        SELECT
            id, client_id, account_id, rl_portfolio_id, rl_portfolio_name,
            recommendation_type, trades, status, total_trades,
            total_buy_value, total_sell_value, expected_turnover,
            notes, created_at, approved_at, executed_at
        FROM trade_recommendations
        WHERE id = :recommendation_id
    """
    )

    result = db.execute(query, {"recommendation_id": recommendation_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return {
        "id": result[0],
        "client_id": result[1],
        "account_id": result[2],
        "rl_portfolio_id": result[3],
        "rl_portfolio_name": result[4],
        "recommendation_type": result[5],
        "trades": result[6],
        "status": result[7],
        "total_trades": result[8],
        "total_buy_value": float(result[9]) if result[9] else 0,
        "total_sell_value": float(result[10]) if result[10] else 0,
        "expected_turnover": float(result[11]) if result[11] else 0,
        "notes": result[12],
        "created_at": result[13],
        "approved_at": result[14],
        "executed_at": result[15],
    }


@router.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    """
    Approve a trade recommendation.

    This changes status from 'pending' to 'approved'.
    Trades can then be executed.
    """
    query = text(
        """
        UPDATE trade_recommendations
        SET status = 'approved', approved_at = NOW()
        WHERE id = :recommendation_id AND status = 'pending'
        RETURNING id
    """
    )

    result = db.execute(query, {"recommendation_id": recommendation_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")

    db.commit()

    return {"success": True, "recommendation_id": recommendation_id, "status": "approved"}


@router.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: int, reason: Optional[str] = None, db: Session = Depends(get_db)
):
    """Reject a trade recommendation."""
    query = text(
        """
        UPDATE trade_recommendations
        SET status = 'rejected', notes = :reason
        WHERE id = :recommendation_id AND status = 'pending'
        RETURNING id
    """
    )

    result = db.execute(
        query, {"recommendation_id": recommendation_id, "reason": reason or "Rejected by user"}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found or already processed")

    db.commit()

    return {"success": True, "recommendation_id": recommendation_id, "status": "rejected"}


@router.post("/recommendations/{recommendation_id}/execute")
async def execute_recommendation(
    recommendation_id: int, account_hash: str, db: Session = Depends(get_db)
):
    """
    Execute all trades from an approved recommendation.

    Requires recommendation to be in 'approved' status.

    Args:
        recommendation_id: Recommendation ID
        account_hash: Schwab account hash

    Returns:
        Execution results for all trades
    """
    # Get recommendation
    rec = await get_recommendation(recommendation_id, db)

    if rec["status"] != "approved":
        raise HTTPException(
            status_code=400, detail=f"Cannot execute recommendation with status: {rec['status']}"
        )

    client_id = rec["client_id"]

    try:
        # Get Schwab token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(status_code=404, detail="No Schwab connection")

        # Create trading service
        schwab_client = SchwabAPIClient(token)
        trading_service = TradingService(db, schwab_client)

        # Execute all trades
        result = await trading_service.execute_recommendation(recommendation_id, account_hash)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute trades: {str(e)}")


@router.get("/executions/")
async def get_trade_executions(
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get trade execution history.

    Args:
        client_id: Filter by client
        status: Filter by status
        limit: Maximum results

    Returns:
        List of trade executions
    """
    query = """
        SELECT
            id, rebalance_id, account_id, ticker, side,
            quantity, execution_price, order_type, execution_status,
            brokerage_order_id, executed_at, created_at,
            slippage, commission, sec_fee, total_cost
        FROM trade_executions
        WHERE 1=1
    """

    params = {"limit": limit}

    if client_id:
        query += " AND account_id = :client_id"
        params["client_id"] = client_id

    if status:
        query += " AND execution_status = :status"
        params["status"] = status

    query += " ORDER BY created_at DESC LIMIT :limit"

    result = db.execute(text(query), params)

    executions = []
    for row in result:
        executions.append(
            {
                "id": row.id,
                "rebalance_id": row.rebalance_id,
                "account_id": row.account_id,
                "symbol": row.ticker,
                "action": row.side,
                "shares": float(row.quantity) if row.quantity else None,
                "price": float(row.execution_price) if row.execution_price else None,
                "order_type": row.order_type,
                "status": row.execution_status,
                "order_id": row.brokerage_order_id,
                "executed_at": row.executed_at,
                "created_at": row.created_at,
                "slippage": float(row.slippage) if row.slippage else None,
                "commission": float(row.commission) if row.commission else None,
                "sec_fee": float(row.sec_fee) if row.sec_fee else None,
                "total_cost": float(row.total_cost) if row.total_cost else None,
            }
        )

    return {"executions": executions, "count": len(executions)}


def _store_recommendation(
    db: Session, client_id: int, account_hash: str, recommendations: dict
) -> int:
    """Store recommendation in database."""
    # Get account_id from account_hash (simplified - would need proper lookup)
    # For now, assume account_id = 1
    account_id = 1

    query = text(
        """
        INSERT INTO trade_recommendations (
            client_id, account_id, rl_portfolio_id, rl_portfolio_name,
            recommendation_type, trades, status, total_trades,
            total_buy_value, total_sell_value, expected_turnover,
            created_at
        )
        VALUES (
            :client_id, :account_id, :rl_portfolio_id, :rl_portfolio_name,
            'rebalance', :trades, 'pending', :total_trades,
            :total_buy_value, :total_sell_value, :expected_turnover,
            NOW()
        )
        RETURNING id
    """
    )

    summary = recommendations["summary"]

    result = db.execute(
        query,
        {
            "client_id": client_id,
            "account_id": account_id,
            "rl_portfolio_id": recommendations["portfolio_id"],
            "rl_portfolio_name": recommendations["portfolio_name"],
            "trades": recommendations["trades"],
            "total_trades": summary["num_trades"],
            "total_buy_value": summary["total_buy_value"],
            "total_sell_value": summary["total_sell_value"],
            "expected_turnover": summary["total_turnover"],
        },
    ).fetchone()

    db.commit()

    return result[0]
