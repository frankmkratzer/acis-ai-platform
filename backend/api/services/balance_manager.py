"""
Balance Manager Service

Centralized service for managing account cash balances across all trading modes.
Ensures accurate balance tracking for live, paper, and autonomous trading.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor


class BalanceManager:
    """
    Manages account cash balances with transaction-safe updates.

    Ensures balances are correctly updated after trade executions
    and validates sufficient funds before trades.
    """

    def __init__(self, db_config: Optional[Dict[str, Any]] = None):
        """
        Initialize balance manager.

        Args:
            db_config: Database configuration dict (defaults to acis-ai database)
        """
        self.db_config = db_config or {
            "dbname": "acis-ai",
            "user": "postgres",
            "password": "$@nJose420",
            "host": "localhost",
            "port": 5432,
        }

    def get_balance(self, account_id: str) -> Dict[str, float]:
        """
        Get current account balances.

        Args:
            account_id: Account hash or ID

        Returns:
            Dict with cash_balance, buying_power, total_value, positions_value
        """
        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        try:
            cursor = conn.cursor()

            # Ensure account exists
            cursor.execute(
                """
                INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
                VALUES (%s, 0, 0, 0)
                ON CONFLICT (account_id) DO NOTHING
            """,
                (account_id,),
            )
            conn.commit()

            # Get balances
            cursor.execute(
                """
                SELECT cash_balance, buying_power, total_value
                FROM paper_accounts
                WHERE account_id = %s
            """,
                (account_id,),
            )

            result = cursor.fetchone()

            # Calculate positions value
            cursor.execute(
                """
                SELECT COALESCE(SUM(market_value), 0) as positions_value
                FROM paper_positions
                WHERE account_id = %s
            """,
                (account_id,),
            )

            positions_row = cursor.fetchone()
            positions_value = float(positions_row["positions_value"]) if positions_row else 0.0

            return {
                "cash_balance": float(result["cash_balance"]) if result else 0.0,
                "buying_power": float(result["buying_power"]) if result else 0.0,
                "total_value": float(result["total_value"]) if result else 0.0,
                "positions_value": positions_value,
            }

        finally:
            cursor.close()
            conn.close()

    def validate_buy_order(
        self, account_id: str, order_value: float, commission: float = 0.0
    ) -> Dict[str, Any]:
        """
        Validate that account has sufficient cash for a buy order.

        Args:
            account_id: Account hash or ID
            order_value: Total value of order (shares * price)
            commission: Optional commission/fees

        Returns:
            Dict with 'valid' (bool), 'cash_balance' (float), 'shortfall' (float if invalid)
        """
        balances = self.get_balance(account_id)
        cash = balances["cash_balance"]
        total_cost = order_value + commission

        if cash >= total_cost:
            return {
                "valid": True,
                "cash_balance": cash,
                "order_value": order_value,
                "commission": commission,
                "total_cost": total_cost,
                "remaining_cash": cash - total_cost,
            }
        else:
            return {
                "valid": False,
                "cash_balance": cash,
                "order_value": order_value,
                "commission": commission,
                "total_cost": total_cost,
                "shortfall": total_cost - cash,
            }

    def update_balance_after_buy(
        self,
        account_id: str,
        shares: float,
        price: float,
        commission: float = 0.0,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Update cash balance after a BUY order execution.

        Args:
            account_id: Account hash or ID
            shares: Number of shares bought
            price: Price per share
            commission: Optional commission/fees
            validate: If True, validate sufficient funds first

        Returns:
            Dict with 'success', 'old_balance', 'new_balance', 'amount_deducted'
        """
        order_value = shares * price
        total_cost = order_value + commission

        # Validate first if requested
        if validate:
            validation = self.validate_buy_order(account_id, order_value, commission)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Insufficient funds: need ${total_cost:,.2f}, have ${validation['cash_balance']:,.2f}",
                    "shortfall": validation["shortfall"],
                }

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        try:
            cursor = conn.cursor()

            # Get current balance
            cursor.execute(
                """
                SELECT cash_balance FROM paper_accounts WHERE account_id = %s
            """,
                (account_id,),
            )
            result = cursor.fetchone()
            old_balance = float(result["cash_balance"]) if result else 0.0

            # Update balance (deduct cost)
            cursor.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance - %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = %s
                RETURNING cash_balance
            """,
                (total_cost, account_id),
            )

            result = cursor.fetchone()
            new_balance = float(result["cash_balance"]) if result else 0.0

            conn.commit()

            return {
                "success": True,
                "old_balance": old_balance,
                "new_balance": new_balance,
                "amount_deducted": total_cost,
                "order_value": order_value,
                "commission": commission,
            }

        except Exception as e:
            conn.rollback()
            return {"success": False, "error": f"Failed to update balance: {str(e)}"}
        finally:
            cursor.close()
            conn.close()

    def update_balance_after_sell(
        self, account_id: str, shares: float, price: float, commission: float = 0.0
    ) -> Dict[str, Any]:
        """
        Update cash balance after a SELL order execution.

        Args:
            account_id: Account hash or ID
            shares: Number of shares sold
            price: Price per share
            commission: Optional commission/fees

        Returns:
            Dict with 'success', 'old_balance', 'new_balance', 'amount_added'
        """
        order_value = shares * price
        net_proceeds = order_value - commission

        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        try:
            cursor = conn.cursor()

            # Get current balance
            cursor.execute(
                """
                SELECT cash_balance FROM paper_accounts WHERE account_id = %s
            """,
                (account_id,),
            )
            result = cursor.fetchone()
            old_balance = float(result["cash_balance"]) if result else 0.0

            # Update balance (add proceeds)
            cursor.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance + %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE account_id = %s
                RETURNING cash_balance
            """,
                (net_proceeds, account_id),
            )

            result = cursor.fetchone()
            new_balance = float(result["cash_balance"]) if result else 0.0

            conn.commit()

            return {
                "success": True,
                "old_balance": old_balance,
                "new_balance": new_balance,
                "amount_added": net_proceeds,
                "order_value": order_value,
                "commission": commission,
            }

        except Exception as e:
            conn.rollback()
            return {"success": False, "error": f"Failed to update balance: {str(e)}"}
        finally:
            cursor.close()
            conn.close()

    def set_balance(
        self,
        account_id: str,
        cash_balance: float,
        buying_power: Optional[float] = None,
        total_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Directly set account balances (for initialization or Schwab sync).

        Args:
            account_id: Account hash or ID
            cash_balance: New cash balance
            buying_power: Optional new buying power
            total_value: Optional new total value

        Returns:
            Dict with 'success' and updated balances
        """
        conn = psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
        try:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = ["cash_balance = %s"]
            params = [cash_balance]

            if buying_power is not None:
                updates.append("buying_power = %s")
                params.append(buying_power)

            if total_value is not None:
                updates.append("total_value = %s")
                params.append(total_value)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(account_id)

            query = f"""
                INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
                VALUES (%s, %s, {buying_power or 0}, {total_value or 0})
                ON CONFLICT (account_id) DO UPDATE SET
                    {', '.join(updates)}
                RETURNING cash_balance, buying_power, total_value
            """

            cursor.execute(
                """
                INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (account_id) DO UPDATE SET
                    cash_balance = EXCLUDED.cash_balance,
                    buying_power = EXCLUDED.buying_power,
                    total_value = EXCLUDED.total_value,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING cash_balance, buying_power, total_value
            """,
                (account_id, cash_balance, buying_power or 0, total_value or 0),
            )

            result = cursor.fetchone()
            conn.commit()

            return {
                "success": True,
                "cash_balance": float(result["cash_balance"]),
                "buying_power": float(result["buying_power"]),
                "total_value": float(result["total_value"]),
            }

        except Exception as e:
            conn.rollback()
            return {"success": False, "error": f"Failed to set balance: {str(e)}"}
        finally:
            cursor.close()
            conn.close()

    def initialize_account(self, account_id: str, initial_cash: float = 100000.0) -> Dict[str, Any]:
        """
        Initialize a new account with starting cash balance.

        Args:
            account_id: Account hash or ID
            initial_cash: Starting cash balance (default $100,000)

        Returns:
            Dict with 'success' and account info
        """
        return self.set_balance(
            account_id=account_id,
            cash_balance=initial_cash,
            buying_power=initial_cash,
            total_value=initial_cash,
        )

    def sync_from_schwab(
        self, account_id: str, schwab_balances: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Sync balances FROM Schwab API (Schwab is source of truth for live accounts).

        This should be called after:
        - Live trade execution
        - Position sync
        - Any operation that modifies account state

        Args:
            account_id: Account hash
            schwab_balances: Dict from Schwab API with keys:
                - cash: Available cash
                - buying_power: Buying power (typically 2x cash for margin)
                - account_value: Total account value

        Returns:
            Dict with 'success' and updated balances
        """
        cash = schwab_balances.get("cash", 0) or 0
        buying_power = schwab_balances.get("buying_power", 0) or 0
        account_value = schwab_balances.get("account_value", 0) or 0

        return self.set_balance(
            account_id=account_id,
            cash_balance=cash,
            buying_power=buying_power,
            total_value=account_value,
        )


# Singleton instance
_balance_manager = None


def get_balance_manager() -> BalanceManager:
    """Get singleton instance of balance manager."""
    global _balance_manager
    if _balance_manager is None:
        _balance_manager = BalanceManager()
    return _balance_manager
