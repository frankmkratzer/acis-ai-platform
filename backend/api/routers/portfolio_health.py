"""
Portfolio Health & Rebalancing API

Provides endpoints for portfolio analysis, health monitoring,
and intelligent rebalancing recommendations.
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from portfolio_analyzer import PortfolioAnalyzer

from ..database.connection import get_db

router = APIRouter(prefix="/api/portfolio-health", tags=["Portfolio Health"])

# Database connection string from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "acis-ai")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_CONN_STRING = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST}"


async def sync_schwab_positions_to_paper(client_id: int, account_hash: str, db: Session):
    """
    Sync Schwab positions to paper_positions table for analysis

    Uses a separate psycopg2 connection to ensure data is immediately
    committed and visible to the Portfolio Analyzer.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor

    from ..services.schwab_api import SchwabAPIClient
    from ..services.schwab_oauth import SchwabOAuthService

    # Get valid token (same pattern as /api/schwab/portfolio endpoint)
    oauth_service = SchwabOAuthService(db)
    token = await oauth_service.get_valid_token(client_id)

    if not token:
        print(f"No valid Schwab token for client {client_id}")
        return False

    # Get positions and balances from Schwab API
    api_client = SchwabAPIClient(token)
    positions = await api_client.get_positions(account_hash)
    balances = await api_client.get_balances(account_hash)

    if not positions:
        print(f"No positions found for account {account_hash}")
        # Still update balances even with no positions

    # Extract balance values
    cash_balance = balances.get("cash", 0) or 0
    buying_power = balances.get("buying_power", 0) or 0
    account_value = balances.get("account_value", 0) or 0

    print(
        f"Schwab balances - Cash: ${cash_balance:,.2f}, Buying Power: ${buying_power:,.2f}, Account Value: ${account_value:,.2f}"
    )

    # Use separate connection to ensure immediate commit
    conn = psycopg2.connect(DB_CONN_STRING)
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Ensure account exists in paper_accounts with actual balances from Schwab
        cursor.execute(
            """
            INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (account_id) DO UPDATE SET
                cash_balance = EXCLUDED.cash_balance,
                buying_power = EXCLUDED.buying_power,
                total_value = EXCLUDED.total_value,
                updated_at = CURRENT_TIMESTAMP
        """,
            (account_hash, cash_balance, buying_power, account_value),
        )

        # Clear existing positions for this account in paper_positions
        cursor.execute(
            """
            DELETE FROM paper_positions
            WHERE account_id = %s
        """,
            (account_hash,),
        )

        # Insert current Schwab positions (if any)
        inserted_count = 0
        if positions:
            for position in positions:
                ticker = position.get("symbol", "")

                if not ticker:
                    continue

                # Calculate values from Schwab position data (already formatted by get_positions)
                quantity = float(position.get("quantity", 0))
                market_value = float(position.get("current_value", 0))
                avg_price = float(position.get("average_price", 0))
                current_price = market_value / quantity if quantity > 0 else 0
                unrealized_pnl = float(position.get("total_gain", 0))

                cursor.execute(
                    """
                    INSERT INTO paper_positions (account_id, ticker, quantity, avg_price, market_value, unrealized_pnl)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_id, ticker)
                    DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        avg_price = EXCLUDED.avg_price,
                        market_value = EXCLUDED.market_value,
                        unrealized_pnl = EXCLUDED.unrealized_pnl,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    (account_hash, ticker, quantity, avg_price, market_value, unrealized_pnl),
                )
                inserted_count += 1
                print(f"  Inserted {ticker}: qty={quantity}, value=${market_value}")

        # Commit immediately to make data visible to other connections
        conn.commit()

        if positions:
            print(
                f"Successfully synced {inserted_count}/{len(positions)} positions to paper_positions"
            )
        else:
            print(f"No positions to sync, but balances updated successfully")

        # Verify the data was actually inserted
        cursor.execute(
            "SELECT COUNT(*) FROM paper_positions WHERE account_id = %s", (account_hash,)
        )
        count = cursor.fetchone()["count"]
        print(f"  Verification: {count} positions in database for account {account_hash[:8]}...")

        return True
    except Exception as e:
        conn.rollback()
        print(f"Error syncing positions: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        conn.close()


@router.get("/{client_id}/analysis")
async def analyze_client_portfolio(
    client_id: int,
    account_id: Optional[str] = None,
    strategy: str = "growth_largecap",
    db: Session = Depends(get_db),
):
    """
    Comprehensive portfolio analysis for a client

    Returns:
        - Current positions with drift analysis
        - Underperforming positions
        - Intelligent swap recommendations
        - Tax-loss harvesting opportunities
        - Overall portfolio health score
        - Rebalancing needs assessment
    """
    try:
        # If no account_id specified, get the client's primary brokerage account
        if not account_id:
            result = db.execute(
                text(
                    """
                SELECT account_hash
                FROM client_brokerage_accounts
                WHERE client_id = :client_id
                  AND is_active = true
                ORDER BY created_at ASC
                LIMIT 1
            """
                ),
                {"client_id": client_id},
            )

            account_row = result.fetchone()
            if account_row:
                account_id = account_row.account_hash
            else:
                # Fallback to paper account
                account_id = f"PAPER_CLIENT_{client_id}"

        # Sync Schwab positions to paper_positions table for analysis
        await sync_schwab_positions_to_paper(client_id, account_id, db)

        analyzer = PortfolioAnalyzer(DB_CONN_STRING)
        analysis = analyzer.analyze_portfolio(client_id, account_id, strategy)

        return analysis

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing portfolio: {str(e)}")


@router.get("/{client_id}/rebalance-recommendations")
async def get_rebalance_recommendations(
    client_id: int,
    account_id: Optional[str] = None,
    min_priority: str = "low",
    db: Session = Depends(get_db),
):
    """
    Get prioritized rebalancing recommendations

    Args:
        client_id: Client ID
        account_id: Account ID (optional)
        min_priority: Minimum priority level ('low', 'medium', 'high')

    Returns:
        Filtered list of swap recommendations prioritized by net benefit
    """
    try:
        if not account_id:
            account_id = f"PAPER_CLIENT_{client_id}"

        analyzer = PortfolioAnalyzer(DB_CONN_STRING)
        analysis = analyzer.analyze_portfolio(client_id, account_id)

        # Filter by priority
        priority_map = {"low": 0, "medium": 1, "high": 2}
        min_level = priority_map.get(min_priority, 0)

        recommendations = [
            rec
            for rec in analysis["swap_recommendations"]
            if priority_map.get(rec["priority"], 0) >= min_level
        ]

        return {
            "client_id": client_id,
            "account_id": account_id,
            "total_recommendations": len(analysis["swap_recommendations"]),
            "filtered_recommendations": len(recommendations),
            "recommendations": recommendations,
            "estimated_total_improvement": sum(r["net_benefit"] for r in recommendations),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/{client_id}/health-score")
async def get_portfolio_health_score(
    client_id: int, account_id: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    Get quick portfolio health score (0-100)

    Returns simplified health metrics without full analysis
    """
    try:
        if not account_id:
            account_id = f"PAPER_CLIENT_{client_id}"

        analyzer = PortfolioAnalyzer(DB_CONN_STRING)
        analysis = analyzer.analyze_portfolio(client_id, account_id)

        return {
            "client_id": client_id,
            "health_score": analysis["health_score"],
            "needs_rebalance": analysis["needs_rebalance"],
            "max_drift": analysis["drift_analysis"]["max_drift"],
            "num_underperformers": len(analysis["underperformers"]),
            "num_recommendations": len(analysis["swap_recommendations"]),
            "portfolio_value": analysis["total_portfolio_value"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating health score: {str(e)}")


@router.post("/{client_id}/execute-rebalance")
async def execute_rebalance(
    client_id: int, recommendations: list, dry_run: bool = True, db: Session = Depends(get_db)
):
    """
    Execute selected rebalancing recommendations

    Args:
        client_id: Client ID
        recommendations: List of recommendation IDs to execute
        dry_run: If True, simulate without executing (default: True)

    Returns:
        Execution results and trade confirmations
    """
    try:
        # This would integrate with the trading execution system
        # For now, return a placeholder

        return {
            "status": "not_implemented",
            "message": "Rebalance execution not yet implemented",
            "dry_run": dry_run,
            "recommendations_count": len(recommendations),
            "note": "Would execute trades through Schwab API or paper trading system",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing rebalance: {str(e)}")


@router.post("/{client_id}/sync-positions")
async def sync_positions(client_id: int, account_hash: str, db: Session = Depends(get_db)):
    """
    Sync Schwab positions to paper_positions table

    This endpoint fetches current positions from Schwab API
    and syncs them to the paper_positions table for analysis.

    Args:
        client_id: Client ID
        account_hash: Schwab account hash

    Returns:
        Success status and sync details
    """
    try:
        success = await sync_schwab_positions_to_paper(client_id, account_hash, db)

        if success:
            # Get count of synced positions
            result = db.execute(
                text(
                    "SELECT COUNT(*) as count FROM paper_positions WHERE account_id = :account_hash"
                ),
                {"account_hash": account_hash},
            )
            count = result.fetchone().count

            return {
                "success": True,
                "message": f"Successfully synced {count} positions",
                "client_id": client_id,
                "account_hash": account_hash,
                "positions_count": count,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to sync positions - check server logs"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing positions: {str(e)}")
