"""
RL Trading Pipeline

Connects RL model recommendations to live Schwab trading execution.
Handles the complete flow from RL prediction to order placement.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from .rl_recommender import get_rl_recommender_service
from .trade_execution import OrderAction, OrderDuration, OrderType, TradeExecutionService


class RLTradingPipeline:
    """
    Complete pipeline from RL recommendations to live trading.
    """

    def __init__(self):
        self.db_config = {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }
        self.rl_service = get_rl_recommender_service()
        self.trade_service = TradeExecutionService()

    async def generate_rebalance_orders(
        self,
        client_id: int,
        account_hash: str,
        portfolio_id: int,
        max_positions: int = 10,
        require_approval: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate rebalancing orders based on RL model recommendations.

        Args:
            client_id: Client ID
            account_hash: Schwab account hash
            portfolio_id: Strategy (1=Growth, 2=Dividend, 3=Value)
            max_positions: Max positions in portfolio
            require_approval: If True, save for approval; if False, execute immediately

        Returns:
            Dict with recommendations and order details
        """

        # 1. Fetch current portfolio from Schwab
        current_portfolio = await self._fetch_schwab_portfolio(client_id, account_hash)

        # 2. Generate RL recommendations
        recommendations = await self.rl_service.generate_recommendations(
            portfolio_id=portfolio_id,
            current_positions=current_portfolio["positions"],
            account_value=current_portfolio["summary"]["total_value"],
            max_recommendations=max_positions,
        )

        # 3. Calculate required trades to reach target allocation
        trades = await self._calculate_rebalance_trades(
            current_positions=current_portfolio["positions"],
            target_recommendations=recommendations["recommendations"],
            account_value=current_portfolio["summary"]["total_value"],
            cash_available=current_portfolio["summary"].get(
                "cash_available", current_portfolio["summary"].get("cash", 0)
            ),
        )

        # 4. Create order batch
        order_batch = {
            "batch_id": self._generate_batch_id(),
            "client_id": client_id,
            "account_hash": account_hash,
            "portfolio_id": portfolio_id,
            "strategy_name": recommendations.get(
                "strategy", recommendations.get("portfolio_name", "Unknown")
            ),
            "created_at": datetime.now().isoformat(),
            "status": "pending_approval" if require_approval else "ready",
            "current_portfolio": current_portfolio["summary"],
            "target_allocation": recommendations["recommendations"],
            "trades": trades,
            "trade_count": len(trades),
            "estimated_total_value": sum(
                t["estimated_value"] for t in trades if t["action"] == "BUY"
            ),
        }

        # 5. Save to database
        await self._save_order_batch(order_batch)

        # 6. If no approval required, execute immediately
        if not require_approval:
            execution_result = await self.execute_order_batch(order_batch["batch_id"])
            order_batch["execution_result"] = execution_result

        return order_batch

    async def execute_order_batch(self, batch_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Execute a batch of rebalancing orders.

        Args:
            batch_id: Order batch ID
            dry_run: If True, validate but don't execute

        Returns:
            Execution results for all orders
        """

        # Fetch order batch from database
        order_batch = await self._get_order_batch(batch_id)

        if not order_batch:
            return {"success": False, "error": f"Order batch {batch_id} not found"}

        if order_batch["status"] not in ["pending_approval", "ready"]:
            return {
                "success": False,
                "error": f'Order batch has invalid status: {order_batch["status"]}',
            }

        # Execute each trade in sequence
        results = []
        for trade in order_batch["trades"]:
            # Determine order type and action
            action = OrderAction.BUY if trade["action"] == "BUY" else OrderAction.SELL

            # Execute trade
            result = await self.trade_service.execute_trade(
                client_id=order_batch["client_id"],
                account_hash=order_batch["account_hash"],
                symbol=trade["symbol"],
                action=action,
                quantity=trade["quantity"],
                order_type=OrderType.MARKET,
                duration=OrderDuration.DAY,
                dry_run=dry_run,
            )

            results.append(
                {
                    "symbol": trade["symbol"],
                    "action": trade["action"],
                    "quantity": trade["quantity"],
                    "result": result,
                }
            )

            # Update trade status in database
            await self._update_trade_status(
                batch_id=batch_id,
                symbol=trade["symbol"],
                status="executed" if result.get("success") else "failed",
                result=result,
            )

        # Update batch status
        all_success = all(r["result"].get("success") for r in results)
        batch_status = "executed" if all_success else "partial_failure"
        if dry_run:
            batch_status = "dry_run_validated"

        await self._update_batch_status(batch_id, batch_status)

        return {
            "success": all_success,
            "batch_id": batch_id,
            "dry_run": dry_run,
            "status": batch_status,
            "trades": results,
            "executed_count": sum(1 for r in results if r["result"].get("success")),
            "failed_count": sum(1 for r in results if not r["result"].get("success")),
        }

    async def _calculate_rebalance_trades(
        self,
        current_positions: List[Dict[str, Any]],
        target_recommendations: List[Dict[str, Any]],
        account_value: float,
        cash_available: float,
    ) -> List[Dict[str, Any]]:
        """
        Calculate the trades needed to rebalance from current to target allocation.

        Args:
            current_positions: Current Schwab positions
            target_recommendations: RL target allocations
            account_value: Total account value
            cash_available: Available cash

        Returns:
            List of trade instructions (BUY/SELL)
        """

        trades = []

        # Build map of current positions
        current_map = {}
        for pos in current_positions:
            if pos.get("instrument_type") == "EQUITY":
                current_map[pos["symbol"]] = {
                    "quantity": pos["quantity"],
                    "current_value": pos["current_value"],
                    "current_price": (
                        pos["current_value"] / pos["quantity"] if pos["quantity"] > 0 else 0
                    ),
                    "weight": pos["current_value"] / account_value if account_value > 0 else 0,
                }

        # Build map of target positions
        target_map = {}
        for rec in target_recommendations:
            target_map[rec["symbol"]] = {
                "target_weight": rec["weight"],
                "target_value": rec["weight"] * account_value,
                "confidence": rec.get("confidence", 0.5),
            }

        # Calculate sells (positions to exit or reduce)
        for symbol, current in current_map.items():
            if symbol not in target_map:
                # Exit position completely
                trades.append(
                    {
                        "symbol": symbol,
                        "action": "SELL",
                        "quantity": int(current["quantity"]),
                        "current_quantity": int(current["quantity"]),
                        "target_quantity": 0,
                        "estimated_value": current["current_value"],
                        "reason": "Exit position (not in target allocation)",
                    }
                )
            else:
                # Check if we need to reduce position
                target = target_map[symbol]
                current_value = current["current_value"]
                target_value = target["target_value"]

                if current_value > target_value * 1.05:  # 5% tolerance
                    # Reduce position
                    value_to_sell = current_value - target_value
                    shares_to_sell = int(value_to_sell / current["current_price"])

                    if shares_to_sell > 0:
                        trades.append(
                            {
                                "symbol": symbol,
                                "action": "SELL",
                                "quantity": shares_to_sell,
                                "current_quantity": int(current["quantity"]),
                                "target_quantity": int(current["quantity"]) - shares_to_sell,
                                "estimated_value": value_to_sell,
                                "reason": f"Reduce position (overweight by ${value_to_sell:,.0f})",
                            }
                        )

        # Calculate buys (positions to enter or increase)
        for symbol, target in target_map.items():
            if symbol not in current_map:
                # New position
                target_value = target["target_value"]

                # Estimate shares to buy (use approximate price from market data)
                # In production, would fetch real-time quote
                estimated_price = await self._get_market_price(symbol) or 100  # Fallback price

                shares_to_buy = int(target_value / estimated_price)

                if shares_to_buy > 0:
                    trades.append(
                        {
                            "symbol": symbol,
                            "action": "BUY",
                            "quantity": shares_to_buy,
                            "current_quantity": 0,
                            "target_quantity": shares_to_buy,
                            "estimated_value": target_value,
                            "estimated_price": estimated_price,
                            "reason": f'Enter new position (target weight: {target["target_weight"]*100:.1f}%)',
                        }
                    )
            else:
                # Increase existing position if underweight
                current = current_map[symbol]
                current_value = current["current_value"]
                target_value = target["target_value"]

                if target_value > current_value * 1.05:  # 5% tolerance
                    value_to_buy = target_value - current_value
                    shares_to_buy = int(value_to_buy / current["current_price"])

                    if shares_to_buy > 0:
                        trades.append(
                            {
                                "symbol": symbol,
                                "action": "BUY",
                                "quantity": shares_to_buy,
                                "current_quantity": int(current["quantity"]),
                                "target_quantity": int(current["quantity"]) + shares_to_buy,
                                "estimated_value": value_to_buy,
                                "estimated_price": current["current_price"],
                                "reason": f"Increase position (underweight by ${value_to_buy:,.0f})",
                            }
                        )

        # Sort trades: SELL first, then BUY (to free up cash)
        trades.sort(key=lambda t: 0 if t["action"] == "SELL" else 1)

        return trades

    async def _fetch_schwab_portfolio(self, client_id: int, account_hash: str) -> Dict[str, Any]:
        """Fetch current portfolio from Schwab."""

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8000/api/schwab/portfolio/{client_id}/{account_hash}",
                timeout=30.0,
            )

            if response.status_code != 200:
                raise Exception(f"Failed to fetch portfolio: {response.status_code}")

            return response.json()

    async def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Get most recent daily bar
        cur.execute(
            """
            SELECT close
            FROM daily_bars
            WHERE symbol = %s
            ORDER BY date DESC
            LIMIT 1
        """,
            [symbol],
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return float(row["close"])
        return None

    def _generate_batch_id(self) -> str:
        """Generate unique batch ID."""
        import uuid

        return f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    async def _save_order_batch(self, order_batch: Dict[str, Any]) -> None:
        """Save order batch to database."""

        import json

        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()

        # Create table if not exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rl_order_batches (
                batch_id TEXT PRIMARY KEY,
                client_id INTEGER NOT NULL,
                account_hash TEXT NOT NULL,
                portfolio_id INTEGER NOT NULL,
                strategy_name TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP,
                current_portfolio JSONB,
                target_allocation JSONB,
                trades JSONB,
                execution_results JSONB
            )
        """
        )

        cur.execute(
            """
            INSERT INTO rl_order_batches (
                batch_id, client_id, account_hash, portfolio_id, strategy_name,
                status, created_at, current_portfolio, target_allocation, trades
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            [
                order_batch["batch_id"],
                order_batch["client_id"],
                order_batch["account_hash"],
                order_batch["portfolio_id"],
                order_batch["strategy_name"],
                order_batch["status"],
                datetime.now(),
                json.dumps(order_batch["current_portfolio"]),
                json.dumps(order_batch["target_allocation"]),
                json.dumps(order_batch["trades"]),
            ],
        )

        conn.commit()
        cur.close()
        conn.close()

    async def _get_order_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve order batch from database."""

        import json

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM rl_order_batches
            WHERE batch_id = %s
        """,
            [batch_id],
        )

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return None

        return dict(row)

    async def _update_batch_status(self, batch_id: str, status: str) -> None:
        """Update order batch status."""

        conn = psycopg2.connect(**self.db_config)
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE rl_order_batches
            SET status = %s, updated_at = %s
            WHERE batch_id = %s
        """,
            [status, datetime.now(), batch_id],
        )

        conn.commit()
        cur.close()
        conn.close()

    async def _update_trade_status(
        self, batch_id: str, symbol: str, status: str, result: Dict[str, Any]
    ) -> None:
        """Update individual trade status within a batch."""

        import json

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        # Get current batch
        cur.execute(
            """
            SELECT trades, execution_results
            FROM rl_order_batches
            WHERE batch_id = %s
        """,
            [batch_id],
        )

        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return

        trades = row["trades"]
        execution_results = row["execution_results"] or {}

        # Update execution results
        execution_results[symbol] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "result": result,
        }

        # Save back
        cur.execute(
            """
            UPDATE rl_order_batches
            SET execution_results = %s, updated_at = %s
            WHERE batch_id = %s
        """,
            [json.dumps(execution_results), datetime.now(), batch_id],
        )

        conn.commit()
        cur.close()
        conn.close()


# Singleton instance
_rl_pipeline_instance = None


def get_rl_trading_pipeline() -> RLTradingPipeline:
    """Get singleton instance of RL trading pipeline."""
    global _rl_pipeline_instance
    if _rl_pipeline_instance is None:
        _rl_pipeline_instance = RLTradingPipeline()
    return _rl_pipeline_instance
