"""
Schwab API Client

Handles API calls to Schwab for:
- Account information
- Positions
- Orders
- Market data

Requires valid OAuth token from SchwabOAuthService.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx

# Schwab API Base URL
SCHWAB_API_BASE = "https://api.schwabapi.com/trader/v1"


class SchwabAPIClient:
    """
    Client for Schwab API calls.
    """

    def __init__(self, access_token: str):
        """
        Initialize Schwab API client.

        Args:
            access_token: Valid OAuth access token
        """
        self.access_token = access_token
        self.base_url = SCHWAB_API_BASE
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_account_numbers(self) -> List[Dict[str, Any]]:
        """
        Get list of account numbers for the authenticated user.

        Returns:
            List of account numbers with account hash IDs
        """
        url = f"{self.base_url}/accounts/accountNumbers"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)

            if response.status_code != 200:
                raise Exception(
                    f"Failed to get account numbers: {response.status_code} - {response.text}"
                )

            return response.json()

    async def get_account(self, account_hash: str, fields: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account details including positions.

        Args:
            account_hash: Account hash ID from get_account_numbers()
            fields: Optional fields to include (e.g., "positions")

        Returns:
            Account details with positions, balances, etc.
        """
        url = f"{self.base_url}/accounts/{account_hash}"

        params = {}
        if fields:
            params["fields"] = fields

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to get account: {response.status_code} - {response.text}")

            return response.json()

    async def get_all_accounts(self, fields: Optional[str] = "positions") -> List[Dict[str, Any]]:
        """
        Get all accounts with positions.

        Args:
            fields: Fields to include (default: "positions")

        Returns:
            List of all accounts with details
        """
        url = f"{self.base_url}/accounts"

        params = {}
        if fields:
            params["fields"] = fields

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to get accounts: {response.status_code} - {response.text}")

            return response.json()

    async def get_positions(self, account_hash: str) -> List[Dict[str, Any]]:
        """
        Get positions for an account.

        Args:
            account_hash: Account hash ID

        Returns:
            List of positions with symbol, quantity, value, etc.
        """
        account_data = await self.get_account(account_hash, fields="positions")

        # Extract positions from account data
        positions = []

        if "securitiesAccount" in account_data:
            account = account_data["securitiesAccount"]

            if "positions" in account:
                for position in account["positions"]:
                    # Extract key position data
                    instrument = position.get("instrument", {})
                    symbol = instrument.get("symbol", "")

                    positions.append(
                        {
                            "symbol": symbol,
                            "quantity": position.get("longQuantity", 0)
                            + position.get("shortQuantity", 0),
                            "average_price": position.get("averagePrice", 0),
                            "current_value": position.get("marketValue", 0),
                            "cost_basis": position.get("averagePrice", 0)
                            * position.get("longQuantity", 0),
                            "day_gain": position.get("currentDayProfitLoss", 0),
                            "day_gain_percent": position.get("currentDayProfitLossPercentage", 0),
                            "total_gain": position.get("longOpenProfitLoss", 0),
                            "instrument_type": instrument.get("assetType", ""),
                            "cusip": instrument.get("cusip", ""),
                        }
                    )

        return positions

    async def get_balances(self, account_hash: str) -> Dict[str, Any]:
        """
        Get account balances.

        Args:
            account_hash: Account hash ID

        Returns:
            Dict with cash balance, buying power, account value, etc.
        """
        account_data = await self.get_account(account_hash)

        balances = {}

        if "securitiesAccount" in account_data:
            account = account_data["securitiesAccount"]

            if "currentBalances" in account:
                current = account["currentBalances"]

                balances = {
                    "cash": current.get("cashBalance", 0),
                    "cash_available_for_trading": current.get("cashAvailableForTrading", 0),
                    "buying_power": current.get("buyingPower", 0),
                    "account_value": current.get("liquidationValue", 0),
                    "equity": current.get("equity", 0),
                    "long_market_value": current.get("longMarketValue", 0),
                    "short_market_value": current.get("shortMarketValue", 0),
                    "maintenance_requirement": current.get("maintenanceRequirement", 0),
                }

        return balances

    async def get_orders(
        self,
        account_hash: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get orders for an account.

        Args:
            account_hash: Account hash ID
            from_date: Start date (ISO format)
            to_date: End date (ISO format)
            status: Order status filter

        Returns:
            List of orders
        """
        url = f"{self.base_url}/accounts/{account_hash}/orders"

        params = {}
        if from_date:
            params["fromEnteredTime"] = from_date
        if to_date:
            params["toEnteredTime"] = to_date
        if status:
            params["status"] = status

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to get orders: {response.status_code} - {response.text}")

            return response.json()

    async def place_order(self, account_hash: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place an order.

        Args:
            account_hash: Account hash ID
            order: Order details (dict matching Schwab order schema)

        Returns:
            Order confirmation
        """
        url = f"{self.base_url}/accounts/{account_hash}/orders"

        # Add Content-Type header for POST requests
        post_headers = {**self.headers, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=post_headers, json=order, timeout=30.0)

            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to place order: {response.status_code} - {response.text}")

            # Get order ID from Location header
            location = response.headers.get("Location", "")
            order_id = location.split("/")[-1] if location else None

            return {
                "order_id": order_id,
                "status": "ACCEPTED",
                "message": "Order placed successfully",
            }

    async def cancel_order(self, account_hash: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order.

        Args:
            account_hash: Account hash ID
            order_id: Order ID to cancel

        Returns:
            Cancellation confirmation
        """
        url = f"{self.base_url}/accounts/{account_hash}/orders/{order_id}"

        async with httpx.AsyncClient() as client:
            response = await client.delete(url, headers=self.headers, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to cancel order: {response.status_code} - {response.text}")

            return {
                "order_id": order_id,
                "status": "CANCELLED",
                "message": "Order cancelled successfully",
            }

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time quote for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Quote data with price, volume, etc.
        """
        url = f"{self.base_url}/marketdata/quotes"

        params = {"symbols": symbol}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to get quote: {response.status_code} - {response.text}")

            data = response.json()
            return data.get(symbol, {})

    async def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get real-time quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dict of symbol -> quote data
        """
        url = f"{self.base_url}/marketdata/quotes"

        params = {"symbols": ",".join(symbols)}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)

            if response.status_code != 200:
                raise Exception(f"Failed to get quotes: {response.status_code} - {response.text}")

            return response.json()


def create_market_order(symbol: str, quantity: int, instruction: str = "BUY") -> Dict[str, Any]:
    """
    Create a market order object for Schwab API.

    Args:
        symbol: Stock symbol
        quantity: Number of shares
        instruction: "BUY" or "SELL"

    Returns:
        Order object for Schwab API
    """
    return {
        "orderType": "MARKET",
        "session": "NORMAL",
        "duration": "DAY",
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": instruction,
                "quantity": quantity,
                "instrument": {"symbol": symbol, "assetType": "EQUITY"},
            }
        ],
    }


def create_limit_order(
    symbol: str, quantity: int, price: float, instruction: str = "BUY"
) -> Dict[str, Any]:
    """
    Create a limit order object for Schwab API.

    Args:
        symbol: Stock symbol
        quantity: Number of shares
        price: Limit price
        instruction: "BUY" or "SELL"

    Returns:
        Order object for Schwab API
    """
    return {
        "orderType": "LIMIT",
        "session": "NORMAL",
        "duration": "DAY",
        "price": price,
        "orderStrategyType": "SINGLE",
        "orderLegCollection": [
            {
                "instruction": instruction,
                "quantity": quantity,
                "instrument": {"symbol": symbol, "assetType": "EQUITY"},
            }
        ],
    }
