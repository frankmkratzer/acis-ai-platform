"""
Trade Execution Service

Handles automated order placement and execution via Schwab API.
Supports market orders, limit orders, and order validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor


class OrderType(str, Enum):
    """Order types supported."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderAction(str, Enum):
    """Order actions."""

    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"


class OrderDuration(str, Enum):
    """Order duration."""

    DAY = "DAY"
    GOOD_TILL_CANCEL = "GOOD_TILL_CANCEL"
    FILL_OR_KILL = "FILL_OR_KILL"


class TradeExecutionService:
    """Service for executing trades via Schwab API."""

    def __init__(self):
        self.db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

        # Max order value limits (aligned with autonomous rebalancer)
        self.max_order_value_usd = 100000  # $100k per order
        self.max_position_pct = (
            0.10  # 10% of portfolio in single position (matches autonomous rebalancer)
        )

    async def execute_trade(
        self,
        client_id: int,
        account_hash: str,
        symbol: str,
        action: OrderAction,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float = None,
        stop_price: float = None,
        duration: OrderDuration = OrderDuration.DAY,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a trade order.

        Args:
            client_id: Client ID
            account_hash: Account hash
            symbol: Stock symbol
            action: BUY, SELL, etc.
            quantity: Number of shares
            order_type: MARKET, LIMIT, etc.
            limit_price: Limit price (for LIMIT orders)
            stop_price: Stop price (for STOP orders)
            duration: DAY, GOOD_TILL_CANCEL, etc.
            dry_run: If True, validate but don't execute

        Returns:
            Order execution result
        """

        # Validate order
        validation = await self._validate_order(
            client_id, account_hash, symbol, action, quantity, order_type, limit_price
        )

        if not validation["valid"]:
            return {"success": False, "error": validation["error"], "validation": validation}

        # Build order payload
        order_payload = self._build_order_payload(
            symbol, action, quantity, order_type, limit_price, stop_price, duration
        )

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": "Order validated successfully (not executed - dry run mode)",
                "order": order_payload,
                "validation": validation,
            }

        # Execute order via Schwab API
        result = await self._execute_schwab_order(client_id, account_hash, order_payload)

        # Log order to database
        await self._log_order(
            client_id, account_hash, symbol, action, quantity, order_type, limit_price, result
        )

        return result

    async def _validate_order(
        self,
        client_id: int,
        account_hash: str,
        symbol: str,
        action: OrderAction,
        quantity: int,
        order_type: OrderType,
        limit_price: float = None,
    ) -> Dict[str, Any]:
        """Validate order before execution."""

        errors = []

        # Check quantity
        if quantity <= 0:
            errors.append("Quantity must be positive")

        # Check limit price for limit orders
        if order_type == OrderType.LIMIT and not limit_price:
            errors.append("Limit price required for LIMIT orders")

        if order_type == OrderType.LIMIT and limit_price <= 0:
            errors.append("Limit price must be positive")

        # Get current portfolio value
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"http://localhost:8000/api/schwab/portfolio/{client_id}/{account_hash}",
                    timeout=30.0,
                )

                if response.status_code == 200:
                    portfolio = response.json()
                    total_value = portfolio["summary"]["total_value"]
                    cash = portfolio["summary"]["cash"]

                    # Estimate order value
                    if order_type == OrderType.MARKET:
                        # Use conservative estimate (need to fetch current price)
                        estimated_price = limit_price if limit_price else 100  # Placeholder
                    else:
                        estimated_price = limit_price

                    order_value = quantity * estimated_price

                    # Check order value limits
                    if order_value > self.max_order_value_usd:
                        errors.append(
                            f"Order value ${order_value:,.0f} exceeds max ${self.max_order_value_usd:,.0f}"
                        )

                    # Check position size limits
                    position_pct = order_value / total_value if total_value > 0 else 0
                    if position_pct > self.max_position_pct:
                        errors.append(
                            f"Position size {position_pct*100:.1f}% exceeds max {self.max_position_pct*100:.0f}%"
                        )

                    # Check buying power for buy orders
                    if action in [OrderAction.BUY, OrderAction.BUY_TO_COVER]:
                        if order_value > cash:
                            errors.append(
                                f"Insufficient cash: need ${order_value:,.0f}, have ${cash:,.0f}"
                            )

                else:
                    errors.append("Failed to fetch portfolio data for validation")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return {
            "valid": len(errors) == 0,
            "error": "; ".join(errors) if errors else None,
            "checks": {
                "quantity_positive": quantity > 0,
                "limit_price_valid": order_type != OrderType.LIMIT
                or (limit_price and limit_price > 0),
                "within_limits": len(errors) == 0,
            },
        }

    def _build_order_payload(
        self,
        symbol: str,
        action: OrderAction,
        quantity: int,
        order_type: OrderType,
        limit_price: float = None,
        stop_price: float = None,
        duration: OrderDuration = OrderDuration.DAY,
    ) -> Dict[str, Any]:
        """Build Schwab API order payload."""

        payload = {
            "orderType": order_type.value,
            "session": "NORMAL",
            "duration": duration.value,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": action.value,
                    "quantity": quantity,
                    "instrument": {"symbol": symbol, "assetType": "EQUITY"},
                }
            ],
        }

        if order_type == OrderType.LIMIT and limit_price:
            payload["price"] = limit_price

        if order_type == OrderType.STOP and stop_price:
            payload["stopPrice"] = stop_price

        if order_type == OrderType.STOP_LIMIT and limit_price and stop_price:
            payload["price"] = limit_price
            payload["stopPrice"] = stop_price

        return payload

    async def _execute_schwab_order(
        self, client_id: int, account_hash: str, order_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute order via Schwab API."""

        try:
            # Get OAuth token for this client
            conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
            cur = conn.cursor()

            sql = """
                SELECT access_token
                FROM brokerage_oauth_tokens
                WHERE client_id = %s AND brokerage_id = 1
                LIMIT 1
            """
            cur.execute(sql, [client_id])
            token_row = cur.fetchone()
            cur.close()
            conn.close()

            if not token_row:
                return {"success": False, "error": "No OAuth token found for client"}

            access_token = token_row["access_token"]

            # Execute order
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"https://api.schwabapi.com/trader/v1/accounts/{account_hash}/orders",
                    json=order_payload,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

                if response.status_code == 201:
                    # Order accepted
                    order_id = response.headers.get("Location", "").split("/")[-1]
                    return {
                        "success": True,
                        "order_id": order_id,
                        "status": "WORKING",
                        "message": "Order submitted successfully",
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Schwab API error: {response.status_code} - {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": f"Order execution failed: {str(e)}"}

    async def _log_order(
        self,
        client_id: int,
        account_hash: str,
        symbol: str,
        action: OrderAction,
        quantity: int,
        order_type: OrderType,
        limit_price: float,
        result: Dict[str, Any],
    ):
        """Log order to database for audit trail."""

        try:
            conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
            cur = conn.cursor()

            # Create orders table if it doesn't exist
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_orders (
                    id SERIAL PRIMARY KEY,
                    client_id INTEGER NOT NULL,
                    account_hash VARCHAR(255) NOT NULL,
                    symbol VARCHAR(10) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    quantity INTEGER NOT NULL,
                    order_type VARCHAR(20) NOT NULL,
                    limit_price DECIMAL(10, 2),
                    order_id VARCHAR(255),
                    status VARCHAR(50),
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """
            )

            # Insert order log
            cur.execute(
                """
                INSERT INTO trade_orders (
                    client_id, account_hash, symbol, action, quantity,
                    order_type, limit_price, order_id, status, success, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                [
                    client_id,
                    account_hash,
                    symbol,
                    action.value,
                    quantity,
                    order_type.value,
                    limit_price,
                    result.get("order_id"),
                    result.get("status"),
                    result.get("success"),
                    result.get("error"),
                ],
            )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            print(f"Failed to log order: {e}")


# Singleton instance
_trade_execution_service = None


def get_trade_execution_service() -> TradeExecutionService:
    """Get singleton instance of trade execution service."""
    global _trade_execution_service
    if _trade_execution_service is None:
        _trade_execution_service = TradeExecutionService()
    return _trade_execution_service
