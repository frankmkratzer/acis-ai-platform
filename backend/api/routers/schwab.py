"""
Schwab Router - OAuth and Account Management

Endpoints:
- Start OAuth flow
- Handle OAuth callback
- Refresh tokens
- Get account info
- Get positions
- Get balances
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..models import schemas
from ..services.schwab_api import SchwabAPIClient
from ..services.schwab_oauth import SchwabOAuthService

router = APIRouter(prefix="/api/schwab", tags=["Schwab"])


@router.post("/ngrok/start")
async def start_ngrok():
    """
    Start ngrok tunnel for OAuth callbacks.

    Returns:
        Status of ngrok tunnel
    """
    import subprocess
    import time

    try:
        # Check if ngrok is installed
        ngrok_check = subprocess.run(["which", "ngrok"], capture_output=True, text=True)

        if ngrok_check.returncode != 0:
            raise HTTPException(
                status_code=400,
                detail="Ngrok is not installed. Please install ngrok from https://ngrok.com/download",
            )

        # Check if ngrok is already running
        check_result = subprocess.run(["pgrep", "-f", "ngrok"], capture_output=True, text=True)

        if check_result.returncode == 0:
            return {"success": True, "message": "Ngrok is already running", "already_running": True}

        # Get ngrok config from environment
        ngrok_domain = os.getenv("NGROK_DOMAIN", "acis.ngrok.app")
        ngrok_port = os.getenv("NGROK_LOCAL_PORT", "8000")
        ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")

        if not ngrok_auth_token:
            raise HTTPException(
                status_code=400, detail="NGROK_AUTH_TOKEN environment variable is not set"
            )

        # Start ngrok in background
        subprocess.Popen(
            ["ngrok", "http", f"--domain={ngrok_domain}", ngrok_port],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait a bit for ngrok to start
        time.sleep(2)

        return {
            "success": True,
            "message": f"Ngrok started on domain {ngrok_domain}",
            "domain": ngrok_domain,
            "port": ngrok_port,
            "already_running": False,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start ngrok: {str(e)}")


@router.get("/ngrok/status")
async def check_ngrok_status():
    """
    Check if ngrok is running.

    Returns:
        Status of ngrok tunnel
    """
    import subprocess

    try:
        # Check if ngrok process is running
        check_result = subprocess.run(["pgrep", "-f", "ngrok"], capture_output=True, text=True)

        is_running = check_result.returncode == 0

        ngrok_domain = os.getenv("NGROK_DOMAIN", "acis.ngrok.app")

        return {
            "running": is_running,
            "domain": ngrok_domain if is_running else None,
            "message": "Ngrok is running" if is_running else "Ngrok is not running",
        }

    except Exception as e:
        return {"running": False, "error": str(e)}


@router.get("/authorize/{client_id}")
async def start_oauth_flow(client_id: int, db: Session = Depends(get_db)):
    """
    Start Schwab OAuth flow for a client.

    This will redirect to Schwab's authorization page.
    User must approve access, then Schwab redirects back to /callback.

    Args:
        client_id: Internal client ID

    Returns:
        Redirect to Schwab authorization page
    """
    # Verify client exists
    from sqlalchemy import text

    query = text("SELECT client_id FROM clients WHERE client_id = :client_id")
    result = db.execute(query, {"client_id": client_id}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    # Generate authorization URL
    oauth_service = SchwabOAuthService(db)
    auth_data = oauth_service.generate_authorization_url(client_id)

    # Redirect to Schwab
    return RedirectResponse(url=auth_data["authorization_url"])


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Schwab"),
    state: str = Query(..., description="State parameter"),
    db: Session = Depends(get_db),
):
    """
    Handle OAuth callback from Schwab.

    Schwab redirects here after user approves access.
    Exchanges authorization code for access token.

    Args:
        code: Authorization code from Schwab
        state: State parameter (contains client_id)

    Returns:
        Success message with client_id
    """
    try:
        oauth_service = SchwabOAuthService(db)
        result = await oauth_service.handle_callback(code, state)

        return {
            "success": True,
            "message": "Schwab account connected successfully",
            "client_id": result["client_id"],
            "brokerage_id": result["brokerage_id"],
            "expires_in": result["expires_in"],
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@router.post("/callback/manual")
async def manual_oauth_callback(request_body: dict, db: Session = Depends(get_db)):
    """
    Manually process OAuth callback URL from Schwab.

    Use this if automatic redirect doesn't work - paste the full URL
    that Schwab redirected to.

    Args:
        request_body: JSON body with callback_url field

    Returns:
        Success message with client_id
    """
    try:
        from urllib.parse import parse_qs, urlparse

        callback_url = request_body.get("callback_url")
        if not callback_url:
            raise HTTPException(status_code=400, detail="callback_url is required in request body")

        # Parse URL to extract code and state
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if not code or not state:
            raise HTTPException(
                status_code=400,
                detail="Invalid callback URL. Must contain 'code' and 'state' parameters.",
            )

        # Process the callback
        oauth_service = SchwabOAuthService(db)
        result = await oauth_service.handle_callback(code, state)

        return {
            "success": True,
            "message": "Schwab account connected successfully",
            "client_id": result["client_id"],
            "brokerage_id": result["brokerage_id"],
            "expires_in": result["expires_in"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback processing failed: {str(e)}")


@router.post("/refresh/{client_id}")
async def refresh_token(client_id: int, db: Session = Depends(get_db)):
    """
    Manually refresh Schwab OAuth token for a client.

    (Tokens are automatically refreshed when needed, but this allows manual refresh)

    Args:
        client_id: Internal client ID

    Returns:
        Success message
    """
    try:
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404, detail="No Schwab token found for client. Please authorize first."
            )

        return {"success": True, "message": "Token refreshed successfully", "client_id": client_id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token refresh failed: {str(e)}")


@router.delete("/revoke/{client_id}")
async def revoke_token(client_id: int, db: Session = Depends(get_db)):
    """
    Revoke (delete) Schwab OAuth token for a client.

    This disconnects the Schwab account.

    Args:
        client_id: Internal client ID

    Returns:
        Success message
    """
    oauth_service = SchwabOAuthService(db)
    oauth_service.revoke_token(client_id)

    return {"success": True, "message": "Schwab account disconnected", "client_id": client_id}


@router.get("/accounts/{client_id}")
async def get_accounts(client_id: int, db: Session = Depends(get_db)):
    """
    Get all Schwab accounts for a client.

    Args:
        client_id: Internal client ID

    Returns:
        List of Schwab accounts with account numbers
    """
    try:
        # Get valid token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404,
                detail="No Schwab token found. Please authorize first at /api/schwab/authorize/{client_id}",
            )

        # Get accounts from Schwab API
        api_client = SchwabAPIClient(token)
        accounts = await api_client.get_account_numbers()

        return {"client_id": client_id, "accounts": accounts}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get accounts: {str(e)}")


@router.get("/positions/{client_id}/{account_hash}")
async def get_positions(client_id: int, account_hash: str, db: Session = Depends(get_db)):
    """
    Get positions for a specific Schwab account.

    Args:
        client_id: Internal client ID
        account_hash: Schwab account hash ID

    Returns:
        List of positions with symbol, quantity, value, etc.
    """
    try:
        # Get valid token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404, detail="No Schwab token found. Please authorize first."
            )

        # Get positions from Schwab API
        api_client = SchwabAPIClient(token)
        positions = await api_client.get_positions(account_hash)

        return {
            "client_id": client_id,
            "account_hash": account_hash,
            "positions": positions,
            "count": len(positions),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/balances/{client_id}/{account_hash}")
async def get_balances(client_id: int, account_hash: str, db: Session = Depends(get_db)):
    """
    Get account balances for a specific Schwab account.

    Args:
        client_id: Internal client ID
        account_hash: Schwab account hash ID

    Returns:
        Account balances (cash, buying power, account value, etc.)
    """
    try:
        # Get valid token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404, detail="No Schwab token found. Please authorize first."
            )

        # Get balances from Schwab API
        api_client = SchwabAPIClient(token)
        balances = await api_client.get_balances(account_hash)

        return {"client_id": client_id, "account_hash": account_hash, "balances": balances}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")


@router.get("/portfolio/{client_id}")
async def get_portfolio_auto(client_id: int, db: Session = Depends(get_db)):
    """
    Get complete portfolio view - automatically discovers account hash.

    This endpoint:
    1. Gets the linked brokerage account
    2. Discovers account_hash if not stored
    3. Returns portfolio data

    Args:
        client_id: Internal client ID

    Returns:
        Complete portfolio with positions and balances
    """
    from sqlalchemy import text

    try:
        # Get valid token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404, detail="No Schwab token found. Please authorize first."
            )

        # Get linked account info
        query = text(
            """
            SELECT cba.id, cba.account_number, cba.account_hash
            FROM brokerage_oauth_tokens bot
            JOIN client_brokerage_accounts cba ON cba.id = bot.account_id
            WHERE bot.client_id = :client_id AND bot.brokerage_id = 1
        """
        )

        result = db.execute(query, {"client_id": client_id}).fetchone()

        if not result:
            raise HTTPException(
                status_code=404,
                detail="No linked brokerage account found. Please complete OAuth flow.",
            )

        account_id, account_number, account_hash = result

        # If account_hash is missing, discover it from Schwab API
        if not account_hash:
            api_client = SchwabAPIClient(token)
            accounts = await api_client.get_account_numbers()

            # Find matching account by number
            for acc in accounts:
                if acc.get("accountNumber") == account_number:
                    account_hash = acc.get("hashValue")
                    break

            if not account_hash:
                raise HTTPException(
                    status_code=404,
                    detail=f"Account {account_number} not found in Schwab API response",
                )

            # Store account_hash for future use
            update_query = text(
                """
                UPDATE client_brokerage_accounts
                SET account_hash = :account_hash, updated_at = NOW()
                WHERE id = :account_id
            """
            )
            db.execute(update_query, {"account_hash": account_hash, "account_id": account_id})
            db.commit()

        # Get data from Schwab API
        api_client = SchwabAPIClient(token)
        positions = await api_client.get_positions(account_hash)
        balances = await api_client.get_balances(account_hash)

        # Calculate portfolio metrics
        total_value = balances.get("account_value", 0)
        cash = balances.get("cash", 0)
        invested = sum(p["current_value"] for p in positions)

        return {
            "client_id": client_id,
            "account_number": account_number,
            "account_hash": account_hash,
            "summary": {
                "total_value": total_value,
                "cash": cash,
                "invested": invested,
                "cash_percent": (cash / total_value * 100) if total_value > 0 else 0,
                "invested_percent": (invested / total_value * 100) if total_value > 0 else 0,
                "num_positions": len(positions),
            },
            "positions": positions,
            "balances": balances,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio: {str(e)}")


@router.get("/portfolio/{client_id}/{account_hash}")
async def get_portfolio(client_id: int, account_hash: str, db: Session = Depends(get_db)):
    """
    Get complete portfolio view (positions + balances) for a Schwab account.

    Args:
        client_id: Internal client ID
        account_hash: Schwab account hash ID

    Returns:
        Complete portfolio with positions and balances
    """
    try:
        # Get valid token
        oauth_service = SchwabOAuthService(db)
        token = await oauth_service.get_valid_token(client_id)

        if not token:
            raise HTTPException(
                status_code=404, detail="No Schwab token found. Please authorize first."
            )

        # Get data from Schwab API
        api_client = SchwabAPIClient(token)
        positions = await api_client.get_positions(account_hash)
        balances = await api_client.get_balances(account_hash)

        # Calculate portfolio metrics
        total_value = balances.get("account_value", 0)
        cash = balances.get("cash", 0)
        invested = sum(p["current_value"] for p in positions)

        return {
            "client_id": client_id,
            "account_hash": account_hash,
            "summary": {
                "total_value": total_value,
                "cash": cash,
                "invested": invested,
                "cash_percent": (cash / total_value * 100) if total_value > 0 else 0,
                "invested_percent": (invested / total_value * 100) if total_value > 0 else 0,
                "num_positions": len(positions),
            },
            "positions": positions,
            "balances": balances,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get portfolio: {str(e)}")


@router.get("/status/{client_id}")
async def get_connection_status(client_id: int, db: Session = Depends(get_db)):
    """
    Check if client has active Schwab connection.

    Args:
        client_id: Internal client ID

    Returns:
        Connection status and token expiration
    """
    from sqlalchemy import text

    query = text(
        """
        SELECT expires_at, created_at, updated_at
        FROM brokerage_oauth_tokens
        WHERE client_id = :client_id
          AND brokerage_id = 1
    """
    )

    result = db.execute(query, {"client_id": client_id}).fetchone()

    if not result:
        return {"client_id": client_id, "connected": False, "message": "No Schwab connection found"}

    from datetime import datetime

    expires_at, created_at, updated_at = result

    is_expired = expires_at <= datetime.utcnow()

    return {
        "client_id": client_id,
        "connected": True,
        "expired": is_expired,
        "expires_at": expires_at.isoformat(),
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
    }


@router.post("/orders/{account_hash}")
async def place_order(account_hash: str, order: dict, db: Session = Depends(get_db)):
    """
    Place an order with Schwab.

    Args:
        account_hash: Account hash ID
        order: Order details matching Schwab order schema

    Returns:
        Order confirmation with order ID
    """
    try:
        # Find the brokerage account by hash
        query = text(
            """
            SELECT cba.client_id, bot.access_token
            FROM client_brokerage_accounts cba
            JOIN brokerage_oauth_tokens bot ON bot.client_id = cba.client_id AND bot.brokerage_id = cba.brokerage_id
            WHERE cba.account_hash = :account_hash
              AND cba.brokerage_id = 1
            LIMIT 1
        """
        )

        result = db.execute(query, {"account_hash": account_hash}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Account not found or no OAuth connection")

        client_id, access_token = result

        # Get valid token (refreshes if needed)
        oauth_service = SchwabOAuthService(db)
        valid_token = await oauth_service.get_valid_token(client_id, brokerage_id=1)

        if not valid_token:
            raise HTTPException(
                status_code=401, detail="No valid Schwab authentication. Please authorize first."
            )

        # Place order using Schwab API
        api_client = SchwabAPIClient(valid_token)
        order_result = await api_client.place_order(account_hash, order)

        return {
            "success": True,
            "order_id": order_result.get("order_id"),
            "status": order_result.get("status"),
            "message": order_result.get("message", "Order placed successfully"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")


@router.get("/portfolio/{client_id}/{account_hash}/risk")
async def get_portfolio_risk_metrics(
    client_id: int, account_hash: str, lookback_days: int = 252, db: Session = Depends(get_db)
):
    """
    Get comprehensive risk analytics for a portfolio.

    Calculates:
    - Sharpe Ratio: Risk-adjusted return
    - Sortino Ratio: Downside risk-adjusted return
    - Max Drawdown: Largest peak-to-trough decline
    - Volatility: Annual standard deviation
    - Beta: Market sensitivity
    - VaR (95%, 99%): Value at Risk
    - CVaR: Conditional Value at Risk
    - Correlation Matrix: Holdings correlations
    - Diversification Score: 0-100 scale

    Args:
        client_id: Internal client ID
        account_hash: Schwab account hash
        lookback_days: Days of history to analyze (default 252 = 1 year)

    Returns:
        Comprehensive risk metrics
    """
    try:
        # Get portfolio positions
        portfolio_data = await get_portfolio(client_id, account_hash, db)

        if not portfolio_data or not portfolio_data.get("positions"):
            raise HTTPException(status_code=404, detail="No portfolio positions found")

        # Calculate risk metrics
        from backend.api.services.risk_analytics import get_risk_analytics

        risk_service = get_risk_analytics()

        # Convert all Decimal values to float before passing to risk analytics
        positions_for_risk = []
        for pos in portfolio_data["positions"]:
            pos_copy = {}
            for key, value in pos.items():
                # Convert Decimal to float
                if hasattr(value, "__float__"):
                    pos_copy[key] = float(value)
                else:
                    pos_copy[key] = value
            positions_for_risk.append(pos_copy)

        risk_metrics = risk_service.calculate_portfolio_risk(
            positions=positions_for_risk, lookback_days=lookback_days
        )

        # Add portfolio context
        return {
            "client_id": client_id,
            "account_hash": account_hash,
            "account_value": portfolio_data["summary"]["total_value"],
            "num_positions": portfolio_data["summary"]["num_positions"],
            "risk_metrics": risk_metrics,
            "interpretation": _interpret_risk_metrics(risk_metrics),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate risk metrics: {str(e)}")


def _interpret_risk_metrics(metrics: dict) -> dict:
    """Provide plain English interpretation of risk metrics."""

    sharpe = metrics.get("sharpe_ratio", 0)
    volatility = metrics.get("volatility", 0)
    max_dd = metrics.get("max_drawdown", 0)
    div_score = metrics.get("diversification_score", 0)

    return {
        "risk_adjusted_return": (
            "Excellent"
            if sharpe > 2.0
            else "Good" if sharpe > 1.0 else "Fair" if sharpe > 0.5 else "Poor"
        ),
        "volatility_level": (
            "Low"
            if volatility < 0.15
            else "Moderate" if volatility < 0.25 else "High" if volatility < 0.40 else "Very High"
        ),
        "drawdown_risk": (
            "Low"
            if max_dd > -0.10
            else "Moderate" if max_dd > -0.20 else "High" if max_dd > -0.30 else "Severe"
        ),
        "diversification": (
            "Excellent"
            if div_score > 75
            else "Good" if div_score > 60 else "Fair" if div_score > 40 else "Poor"
        ),
        "overall_risk": (
            "Conservative"
            if volatility < 0.15 and max_dd > -0.15
            else "Moderate" if volatility < 0.25 and max_dd > -0.25 else "Aggressive"
        ),
    }
