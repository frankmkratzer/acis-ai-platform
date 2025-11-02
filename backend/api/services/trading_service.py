"""
Trading Service

Handles trade execution via Schwab API.

Features:
- Execute single trades
- Execute batch trades (rebalancing)
- Track trade status
- Log all trades to database
- Calculate transaction costs
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .balance_manager import get_balance_manager
from .schwab_api import SchwabAPIClient, create_limit_order, create_market_order


class TradingService:
    """
    Service for executing trades via Schwab API.
    """

    def __init__(self, db_session: Session, schwab_client: SchwabAPIClient):
        self.db = db_session
        self.schwab = schwab_client
        self.balance_manager = get_balance_manager()

    async def execute_trade(
        self,
        client_id: int,
        account_id: int,
        account_hash: str,
        symbol: str,
        action: str,
        shares: int,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        recommendation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single trade.

        Args:
            client_id: Internal client ID
            account_id: Client brokerage account ID
            account_hash: Schwab account hash
            symbol: Stock symbol
            action: "BUY" or "SELL"
            shares: Number of shares
            order_type: "market" or "limit"
            limit_price: Limit price (if limit order)
            recommendation_id: Link to trade recommendation

        Returns:
            Trade execution result
        """
        try:
            # Create order object
            if order_type == "market":
                order = create_market_order(symbol, shares, action)
            else:
                if not limit_price:
                    raise ValueError("Limit price required for limit orders")
                order = create_limit_order(symbol, shares, limit_price, action)

            # Place order via Schwab API
            result = await self.schwab.place_order(account_hash, order)

            # Get current price (for market orders, estimate)
            quote = await self.schwab.get_quote(symbol)
            price = quote.get("lastPrice", 0) if quote else 0

            # Determine if this is paper or live trading by checking client's trading_mode
            trading_mode_query = text(
                """
                SELECT trading_mode FROM clients WHERE client_id = :client_id
            """
            )
            mode_result = self.db.execute(trading_mode_query, {"client_id": client_id}).fetchone()
            trading_mode = mode_result[0] if mode_result else "paper"

            # Update balance based on trading mode
            commission = 0.0  # Schwab has $0 commission for stocks
            balance_result = None

            if trading_mode == "paper":
                # PAPER TRADING: Update cash in database directly
                if action.upper() == "BUY":
                    balance_result = self.balance_manager.update_balance_after_buy(
                        account_id=account_hash,
                        shares=shares,
                        price=price,
                        commission=commission,
                        validate=True,
                    )
                    if not balance_result["success"]:
                        raise ValueError(f"Balance update failed: {balance_result.get('error')}")
                elif action.upper() == "SELL":
                    balance_result = self.balance_manager.update_balance_after_sell(
                        account_id=account_hash, shares=shares, price=price, commission=commission
                    )
                    if not balance_result["success"]:
                        raise ValueError(f"Balance update failed: {balance_result.get('error')}")
            else:
                # LIVE TRADING: Sync balances FROM Schwab (Schwab is source of truth)
                try:
                    # Fetch current balances from Schwab API
                    schwab_balances = await self.schwab.get_balances(account_hash)
                    # Sync those balances to our database
                    balance_result = self.balance_manager.sync_from_schwab(
                        account_id=account_hash, schwab_balances=schwab_balances
                    )
                except Exception as e:
                    # Log error but don't fail the trade
                    print(f"Warning: Failed to sync balances from Schwab: {e}")
                    balance_result = {"success": False, "error": str(e)}

            # Log trade to database
            trade_id = self._log_trade_execution(
                client_id=client_id,
                account_id=account_id,
                recommendation_id=recommendation_id,
                symbol=symbol,
                action=action,
                shares=shares,
                price=price,
                limit_price=limit_price,
                order_type=order_type,
                status="submitted",
                order_id=result.get("order_id"),
            )

            return {
                "success": True,
                "trade_id": trade_id,
                "order_id": result.get("order_id"),
                "symbol": symbol,
                "action": action,
                "shares": shares,
                "estimated_price": price,
                "status": "submitted",
                "balance_update": balance_result,
            }

        except Exception as e:
            # Log failed trade
            trade_id = self._log_trade_execution(
                client_id=client_id,
                account_id=account_id,
                recommendation_id=recommendation_id,
                symbol=symbol,
                action=action,
                shares=shares,
                order_type=order_type,
                status="failed",
                error_message=str(e),
            )

            return {
                "success": False,
                "trade_id": trade_id,
                "symbol": symbol,
                "action": action,
                "shares": shares,
                "status": "failed",
                "error": str(e),
            }

    async def execute_recommendation(
        self, recommendation_id: int, account_hash: str
    ) -> Dict[str, Any]:
        """
        Execute all trades from a recommendation.

        Args:
            recommendation_id: Trade recommendation ID
            account_hash: Schwab account hash

        Returns:
            Execution results for all trades
        """
        # Get recommendation from database
        recommendation = self._get_recommendation(recommendation_id)

        if not recommendation:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        client_id = recommendation["client_id"]
        account_id = recommendation["account_id"]
        trades = recommendation["trades"]

        # Execute all trades
        results = []
        successful = 0
        failed = 0

        for trade in trades:
            result = await self.execute_trade(
                client_id=client_id,
                account_id=account_id,
                account_hash=account_hash,
                symbol=trade["symbol"],
                action=trade["action"],
                shares=trade["shares"],
                order_type="market",  # Default to market orders
                recommendation_id=recommendation_id,
            )

            results.append(result)

            if result["success"]:
                successful += 1
            else:
                failed += 1

        # Update recommendation status
        if failed == 0:
            self._update_recommendation_status(recommendation_id, "executed")
        elif successful == 0:
            self._update_recommendation_status(recommendation_id, "failed")
        else:
            self._update_recommendation_status(recommendation_id, "partially_executed")

        return {
            "recommendation_id": recommendation_id,
            "total_trades": len(trades),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    def _log_trade_execution(
        self,
        client_id: int,
        account_id: int,
        symbol: str,
        action: str,
        shares: int,
        order_type: str,
        status: str,
        recommendation_id: Optional[int] = None,
        price: Optional[float] = None,
        limit_price: Optional[float] = None,
        commission: float = 0.0,
        order_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """
        Log trade execution to database.

        Returns:
            Trade execution ID
        """
        query = text(
            """
            INSERT INTO trade_executions (
                recommendation_id, client_id, account_id, symbol, action,
                shares, price, limit_price, order_type, commission, status,
                order_id, error_message, executed_at, created_at
            )
            VALUES (
                :recommendation_id, :client_id, :account_id, :symbol, :action,
                :shares, :price, :limit_price, :order_type, :commission, :status,
                :order_id, :error_message,
                CASE WHEN :status = 'submitted' THEN NOW() ELSE NULL END,
                NOW()
            )
            RETURNING id
        """
        )

        result = self.db.execute(
            query,
            {
                "recommendation_id": recommendation_id,
                "client_id": client_id,
                "account_id": account_id,
                "symbol": symbol,
                "action": action,
                "shares": shares,
                "price": price,
                "limit_price": limit_price,
                "order_type": order_type,
                "commission": commission,
                "status": status,
                "order_id": order_id,
                "error_message": error_message,
            },
        ).fetchone()

        self.db.commit()

        return result[0]

    def _get_recommendation(self, recommendation_id: int) -> Optional[Dict[str, Any]]:
        """Get recommendation from database."""
        query = text(
            """
            SELECT
                id, client_id, account_id, rl_portfolio_id, rl_portfolio_name,
                trades, status
            FROM trade_recommendations
            WHERE id = :recommendation_id
        """
        )

        result = self.db.execute(query, {"recommendation_id": recommendation_id}).fetchone()

        if not result:
            return None

        return {
            "id": result[0],
            "client_id": result[1],
            "account_id": result[2],
            "rl_portfolio_id": result[3],
            "rl_portfolio_name": result[4],
            "trades": result[5],  # JSONB
            "status": result[6],
        }

    def _update_recommendation_status(self, recommendation_id: int, status: str):
        """Update recommendation status."""
        query = text(
            """
            UPDATE trade_recommendations
            SET status = :status,
                executed_at = CASE WHEN :status = 'executed' THEN NOW() ELSE executed_at END
            WHERE id = :recommendation_id
        """
        )

        self.db.execute(query, {"recommendation_id": recommendation_id, "status": status})

        self.db.commit()

    async def get_trade_status(self, trade_id: int) -> Dict[str, Any]:
        """
        Get status of a trade execution.

        Args:
            trade_id: Trade execution ID

        Returns:
            Trade status and details
        """
        query = text(
            """
            SELECT
                id, recommendation_id, client_id, account_id, symbol, action,
                shares, price, order_type, status, order_id, error_message,
                executed_at, created_at
            FROM trade_executions
            WHERE id = :trade_id
        """
        )

        result = self.db.execute(query, {"trade_id": trade_id}).fetchone()

        if not result:
            raise ValueError(f"Trade {trade_id} not found")

        return {
            "id": result[0],
            "recommendation_id": result[1],
            "client_id": result[2],
            "account_id": result[3],
            "symbol": result[4],
            "action": result[5],
            "shares": result[6],
            "price": result[7],
            "order_type": result[8],
            "status": result[9],
            "order_id": result[10],
            "error_message": result[11],
            "executed_at": result[12],
            "created_at": result[13],
        }

    async def cancel_trade(self, trade_id: int, account_hash: str) -> Dict[str, Any]:
        """
        Cancel a pending trade.

        Args:
            trade_id: Trade execution ID
            account_hash: Schwab account hash

        Returns:
            Cancellation result
        """
        # Get trade
        trade = await self.get_trade_status(trade_id)

        if trade["status"] not in ["pending", "submitted"]:
            raise ValueError(f"Cannot cancel trade with status: {trade['status']}")

        order_id = trade.get("order_id")
        if not order_id:
            raise ValueError("No order ID found for trade")

        try:
            # Cancel order via Schwab API
            result = await self.schwab.cancel_order(account_hash, order_id)

            # Update trade status
            query = text(
                """
                UPDATE trade_executions
                SET status = 'cancelled'
                WHERE id = :trade_id
            """
            )

            self.db.execute(query, {"trade_id": trade_id})
            self.db.commit()

            return {
                "success": True,
                "trade_id": trade_id,
                "order_id": order_id,
                "status": "cancelled",
            }

        except Exception as e:
            return {"success": False, "trade_id": trade_id, "order_id": order_id, "error": str(e)}
