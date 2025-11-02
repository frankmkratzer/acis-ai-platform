"""
RL Live Trading Router

Endpoints for AI-driven portfolio rebalancing and live trading execution.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services.rl_trading_pipeline import get_rl_trading_pipeline

router = APIRouter(prefix="/api/rl/trading", tags=["rl-trading"])


class RebalanceRequest(BaseModel):
    """Request to generate rebalancing orders."""

    client_id: int
    account_hash: str
    portfolio_id: int  # 1=Growth, 2=Dividend, 3=Value
    max_positions: int = 10
    require_approval: bool = True


class ExecuteBatchRequest(BaseModel):
    """Request to execute an order batch."""

    batch_id: str
    dry_run: bool = True  # Safety: default to dry run


@router.post("/rebalance")
async def generate_rebalance_orders(request: RebalanceRequest) -> Dict[str, Any]:
    """
    Generate RL-based rebalancing orders for a portfolio.

    This endpoint:
    1. Fetches current Schwab portfolio
    2. Uses trained RL model to generate target allocation
    3. Calculates required trades (BUY/SELL)
    4. Saves order batch for approval
    5. Optionally executes immediately if require_approval=False

    Args:
        request: Rebalance request with client_id, portfolio strategy, etc.

    Returns:
        Order batch with trades and status
    """
    try:
        pipeline = get_rl_trading_pipeline()

        result = await pipeline.generate_rebalance_orders(
            client_id=request.client_id,
            account_hash=request.account_hash,
            portfolio_id=request.portfolio_id,
            max_positions=request.max_positions,
            require_approval=request.require_approval,
        )

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate rebalance orders: {str(e)}"
        )


@router.post("/execute-batch")
async def execute_order_batch(request: ExecuteBatchRequest) -> Dict[str, Any]:
    """
    Execute a batch of rebalancing orders.

    IMPORTANT: Set dry_run=False to execute real trades!
    By default, orders are validated but NOT executed (dry_run=True).

    Args:
        request: Execution request with batch_id and dry_run flag

    Returns:
        Execution results for all orders in batch
    """
    try:
        pipeline = get_rl_trading_pipeline()

        result = await pipeline.execute_order_batch(
            batch_id=request.batch_id, dry_run=request.dry_run
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute order batch: {str(e)}")


@router.get("/batches/{batch_id}")
async def get_order_batch(batch_id: str) -> Dict[str, Any]:
    """
    Get details of an order batch.

    Args:
        batch_id: Order batch ID

    Returns:
        Order batch details with trades and status
    """
    try:
        pipeline = get_rl_trading_pipeline()
        batch = await pipeline._get_order_batch(batch_id)

        if not batch:
            raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

        return batch

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order batch: {str(e)}")


@router.get("/batches")
async def list_order_batches(
    client_id: Optional[int] = None, status: Optional[str] = None, limit: int = 20
) -> Dict[str, Any]:
    """
    List order batches with optional filters.

    Args:
        client_id: Filter by client ID
        status: Filter by status (pending_approval, executed, etc.)
        limit: Max number of batches to return

    Returns:
        List of order batches
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        conn = psycopg2.connect(**db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM rl_order_batches WHERE 1=1"
        params = []

        if client_id is not None:
            query += " AND client_id = %s"
            params.append(client_id)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        batches = cur.fetchall()

        cur.close()
        conn.close()

        return {"batches": [dict(b) for b in batches], "count": len(batches)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list order batches: {str(e)}")


@router.post("/batches/{batch_id}/approve")
async def approve_order_batch(
    batch_id: str, execute_immediately: bool = True, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Approve an order batch for execution.

    Args:
        batch_id: Order batch ID
        execute_immediately: If True, execute after approval
        dry_run: If True, validate but don't execute

    Returns:
        Approval status and execution results
    """
    from datetime import datetime

    import psycopg2

    try:
        db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        # Update batch status to approved
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE rl_order_batches
            SET status = 'approved', updated_at = %s
            WHERE batch_id = %s AND status = 'pending_approval'
            RETURNING batch_id
        """,
            [datetime.now(), batch_id],
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not result:
            raise HTTPException(
                status_code=400, detail=f"Batch {batch_id} not found or not pending approval"
            )

        # Execute if requested
        execution_result = None
        if execute_immediately:
            pipeline = get_rl_trading_pipeline()
            execution_result = await pipeline.execute_order_batch(
                batch_id=batch_id, dry_run=dry_run
            )

        return {
            "success": True,
            "batch_id": batch_id,
            "status": "approved",
            "executed": execute_immediately,
            "execution_result": execution_result,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve batch: {str(e)}")


@router.post("/batches/{batch_id}/reject")
async def reject_order_batch(batch_id: str, reason: str = "") -> Dict[str, Any]:
    """
    Reject an order batch.

    Args:
        batch_id: Order batch ID
        reason: Rejection reason

    Returns:
        Rejection confirmation
    """
    from datetime import datetime

    import psycopg2

    try:
        db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE rl_order_batches
            SET status = 'rejected', updated_at = %s
            WHERE batch_id = %s AND status = 'pending_approval'
            RETURNING batch_id
        """,
            [datetime.now(), batch_id],
        )

        result = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not result:
            raise HTTPException(
                status_code=400, detail=f"Batch {batch_id} not found or not pending approval"
            )

        return {"success": True, "batch_id": batch_id, "status": "rejected", "reason": reason}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject batch: {str(e)}")


@router.get("/order-status/{symbol}")
async def get_order_status(symbol: str, client_id: int, account_hash: str) -> Dict[str, Any]:
    """
    Get status of orders for a specific symbol.

    Args:
        symbol: Stock symbol
        client_id: Client ID
        account_hash: Account hash

    Returns:
        Order status from Schwab
    """
    try:
        # Get Schwab API token
        from sqlalchemy import create_engine, text

        from ..services.schwab_api import SchwabAPIClient

        engine = create_engine(
            os.getenv("POSTGRES_URL", "postgresql://postgres@localhost:5432/acis-ai")
        )

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT access_token
                FROM brokerage_oauth_tokens
                WHERE client_id = :client_id AND brokerage_id = 1
                LIMIT 1
            """
                ),
                {"client_id": client_id},
            ).fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="No Schwab token found")

            token = result[0]

        # Get orders from Schwab
        api_client = SchwabAPIClient(token)
        orders = await api_client.get_orders(account_hash)

        # Filter for this symbol
        symbol_orders = [
            order
            for order in orders
            if order.get("orderLegCollection", [{}])[0].get("instrument", {}).get("symbol")
            == symbol
        ]

        return {"symbol": symbol, "orders": symbol_orders, "count": len(symbol_orders)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order status: {str(e)}")
