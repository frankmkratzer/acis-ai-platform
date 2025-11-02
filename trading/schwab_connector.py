#!/usr/bin/env python3
"""
Schwab API Connector for Live Trading

Handles authentication, order placement, and position management
via Schwab's trading API.

Features:
- OAuth 2.0 authentication
- Account information retrieval
- Order placement (market, limit)
- Position and balance queries
- Paper trading mode support
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import psycopg2
import requests

from utils import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


class SchwabConnector:
    """
    Connector for Schwab trading API

    Usage:
        connector = SchwabConnector(paper_trading=True)
        connector.authenticate()

        # Place order
        order_id = connector.place_order(
            ticker='AAPL',
            quantity=10,
            order_type='MARKET',
            side='BUY'
        )

        # Get positions
        positions = connector.get_positions()
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        paper_trading: bool = True,
        account_id: Optional[str] = None,
    ):
        """
        Initialize Schwab connector

        Args:
            client_id: Schwab API client ID (from database if None)
            client_secret: Schwab API secret (from database if None)
            paper_trading: Use paper trading mode (default True)
            account_id: Schwab account number (from database if None)
        """
        self.paper_trading = paper_trading
        self.conn = psycopg2.connect(**DB_CONFIG)

        # Load credentials from database if not provided
        if client_id is None or client_secret is None or account_id is None:
            self._load_credentials_from_db()
        else:
            self.client_id = client_id
            self.client_secret = client_secret
            self.account_id = account_id

        # API endpoints
        self.base_url = "https://api.schwabapi.com/trader/v1"
        self.auth_url = "https://api.schwabapi.com/v1/oauth"

        # Tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        logger.info(f"Schwab Connector initialized (Paper Trading: {paper_trading})")

    def _load_credentials_from_db(self):
        """Load Schwab credentials from database"""
        cur = self.conn.cursor()

        # For paper trading, we don't need real credentials
        if self.paper_trading:
            self.client_id = "PAPER_TRADING_CLIENT_ID"
            self.client_secret = "PAPER_TRADING_CLIENT_SECRET"
            self.account_id = "PAPER_AUTONOMOUS_FUND"
            logger.info("Using paper trading credentials")
            return

        # Load from brokerage_oauth_tokens table
        cur.execute(
            """
            SELECT access_token, refresh_token, expires_at, scope
            FROM brokerage_oauth_tokens
            WHERE brokerage_id = (SELECT id FROM brokerages WHERE name = 'Schwab')
              AND client_id = (SELECT client_id FROM clients WHERE client_name = 'Autonomous Fund' LIMIT 1)
            ORDER BY updated_at DESC
            LIMIT 1
        """
        )

        row = cur.fetchone()
        if row:
            self.access_token, self.refresh_token, self.token_expires_at, scope = row
            logger.info("Loaded existing OAuth tokens from database")
        else:
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None
            logger.warning("No existing OAuth tokens found in database")

        # Load client credentials
        cur.execute(
            """
            SELECT api_key, api_secret, account_number
            FROM brokerage_accounts
            WHERE brokerage_id = (SELECT id FROM brokerages WHERE name = 'Schwab')
              AND client_id = (SELECT client_id FROM clients WHERE client_name = 'Autonomous Fund' LIMIT 1)
            LIMIT 1
        """
        )

        row = cur.fetchone()
        if row:
            self.client_id, self.client_secret, self.account_id = row
            logger.info(f"Loaded Schwab credentials for account: {self.account_id}")
        else:
            logger.error("No Schwab account found in database")
            self.client_id = None
            self.client_secret = None
            self.account_id = None

    def _save_tokens_to_db(self):
        """Save OAuth tokens to database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            INSERT INTO brokerage_oauth_tokens (
                client_id, brokerage_id, access_token, refresh_token,
                expires_at, scope, updated_at
            )
            VALUES (
                (SELECT client_id FROM clients WHERE client_name = 'Autonomous Fund' LIMIT 1),
                (SELECT id FROM brokerages WHERE name = 'Schwab'),
                %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (client_id, brokerage_id) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                updated_at = NOW()
        """,
            (self.access_token, self.refresh_token, self.token_expires_at, "trader"),  # scope
        )

        self.conn.commit()
        logger.info("✅ OAuth tokens saved to database")

    def authenticate(self, auth_code: Optional[str] = None) -> bool:
        """
        Authenticate with Schwab API

        Args:
            auth_code: Authorization code from OAuth flow (required for first-time auth)

        Returns:
            True if authentication successful
        """
        # Paper trading doesn't need authentication
        if self.paper_trading:
            logger.info("✅ Paper trading mode - authentication skipped")
            return True

        # Check if we have valid access token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                logger.info("✅ Using existing valid access token")
                return True
            else:
                logger.info("Access token expired, refreshing...")
                return self._refresh_access_token()

        # Need to get new tokens
        if auth_code:
            return self._get_initial_tokens(auth_code)
        else:
            # Try to refresh with existing refresh token
            if self.refresh_token:
                return self._refresh_access_token()
            else:
                logger.error("No auth code or refresh token available")
                logger.error("Please provide auth_code parameter for initial authentication")
                return False

    def _get_initial_tokens(self, auth_code: str) -> bool:
        """Get initial access and refresh tokens using authorization code"""
        try:
            response = requests.post(
                f"{self.auth_url}/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": "https://localhost:8080/callback",
                },
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                expires_in = data.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                self._save_tokens_to_db()
                logger.info("✅ Successfully authenticated with Schwab API")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False

    def _refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        try:
            response = requests.post(
                f"{self.auth_url}/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                # Refresh token may also be updated
                if "refresh_token" in data:
                    self.refresh_token = data["refresh_token"]

                self._save_tokens_to_db()
                logger.info("✅ Access token refreshed")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False

    def _make_api_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make authenticated API request to Schwab

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request payload (for POST/PUT)

        Returns:
            Response JSON or None if error
        """
        if not self.authenticate():
            logger.error("Authentication failed, cannot make API request")
            return None

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            if response.status_code in [200, 201]:
                return response.json() if response.text else {}
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return None

    def get_account_info(self) -> Optional[Dict]:
        """Get account information including balances"""
        if self.paper_trading:
            return self._get_paper_account_info()

        return self._make_api_request("GET", f"/accounts/{self.account_id}")

    def _get_paper_account_info(self) -> Dict:
        """Get paper trading account info from database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT cash_balance, buying_power, total_value
            FROM paper_accounts
            WHERE account_id = %s
        """,
            (self.account_id,),
        )

        row = cur.fetchone()
        if row:
            cash, buying_power, total_value = row
            return {
                "cash": float(cash),
                "buying_power": float(buying_power),
                "total_value": float(total_value),
            }
        else:
            # Initialize paper account
            logger.info("Initializing paper trading account with $100,000")
            cur.execute(
                """
                INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
                VALUES (%s, 100000, 100000, 100000)
            """,
                (self.account_id,),
            )
            self.conn.commit()

            return {"cash": 100000.0, "buying_power": 100000.0, "total_value": 100000.0}

    def get_positions(self) -> List[Dict]:
        """
        Get current positions

        Returns:
            List of position dicts with keys: ticker, quantity, avg_price, market_value
        """
        if self.paper_trading:
            return self._get_paper_positions()

        data = self._make_api_request("GET", f"/accounts/{self.account_id}/positions")

        if data and "positions" in data:
            positions = []
            for pos in data["positions"]:
                positions.append(
                    {
                        "ticker": pos["instrument"]["symbol"],
                        "quantity": pos["longQuantity"] - pos["shortQuantity"],
                        "avg_price": pos["averagePrice"],
                        "market_value": pos["marketValue"],
                    }
                )
            return positions

        return []

    def _get_paper_positions(self) -> List[Dict]:
        """Get paper trading positions from database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT ticker, quantity, avg_price, market_value
            FROM paper_positions
            WHERE account_id = %s
              AND quantity > 0
        """,
            (self.account_id,),
        )

        positions = []
        for row in cur.fetchall():
            positions.append(
                {
                    "ticker": row[0],
                    "quantity": float(row[1]),
                    "avg_price": float(row[2]),
                    "market_value": float(row[3]),
                }
            )

        return positions

    def place_order(
        self,
        ticker: str,
        quantity: float,
        order_type: str = "MARKET",
        side: str = "BUY",
        limit_price: Optional[float] = None,
    ) -> Optional[str]:
        """
        Place an order

        Args:
            ticker: Stock symbol
            quantity: Number of shares
            order_type: 'MARKET' or 'LIMIT'
            side: 'BUY' or 'SELL'
            limit_price: Limit price (required if order_type='LIMIT')

        Returns:
            Order ID if successful, None otherwise
        """
        if self.paper_trading:
            return self._place_paper_order(ticker, quantity, order_type, side, limit_price)

        # Build order payload
        order_data = {
            "orderType": order_type,
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": side,
                    "quantity": quantity,
                    "instrument": {"symbol": ticker, "assetType": "EQUITY"},
                }
            ],
        }

        if order_type == "LIMIT":
            if limit_price is None:
                logger.error("Limit price required for LIMIT orders")
                return None
            order_data["price"] = limit_price

        # Place order
        response = self._make_api_request("POST", f"/accounts/{self.account_id}/orders", order_data)

        if response and "orderId" in response:
            order_id = response["orderId"]
            logger.info(
                f"✅ Order placed: {side} {quantity} {ticker} @ {order_type} (Order ID: {order_id})"
            )

            # Log to database
            self._log_order(order_id, ticker, quantity, order_type, side, limit_price, "PENDING")

            return order_id

        return None

    def _place_paper_order(
        self, ticker: str, quantity: float, order_type: str, side: str, limit_price: Optional[float]
    ) -> str:
        """Simulate order placement for paper trading"""
        import uuid

        order_id = str(uuid.uuid4())

        # Get current market price
        price = self._get_market_price(ticker)

        if price is None:
            logger.error(f"Cannot get market price for {ticker}")
            return None

        # Execute order immediately for paper trading (market orders)
        if order_type == "MARKET":
            execution_price = price
        elif order_type == "LIMIT":
            # For simplicity, execute immediately at limit price if within market price
            if side == "BUY" and limit_price >= price:
                execution_price = limit_price
            elif side == "SELL" and limit_price <= price:
                execution_price = limit_price
            else:
                logger.info(
                    f"Paper LIMIT order not filled: {side} {ticker} @ {limit_price} (market: {price})"
                )
                self._log_order(
                    order_id, ticker, quantity, order_type, side, limit_price, "PENDING"
                )
                return order_id

        # Update paper account
        cur = self.conn.cursor()

        if side == "BUY":
            cost = quantity * execution_price

            # Check buying power
            cur.execute(
                "SELECT buying_power FROM paper_accounts WHERE account_id = %s", (self.account_id,)
            )
            buying_power = float(cur.fetchone()[0])

            if cost > buying_power:
                logger.error(
                    f"Insufficient buying power: need ${cost:,.2f}, have ${buying_power:,.2f}"
                )
                return None

            # Deduct cash
            cur.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance - %s,
                    buying_power = buying_power - %s
                WHERE account_id = %s
            """,
                (cost, cost, self.account_id),
            )

            # Add position
            cur.execute(
                """
                INSERT INTO paper_positions (account_id, ticker, quantity, avg_price, market_value)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (account_id, ticker) DO UPDATE SET
                    quantity = paper_positions.quantity + EXCLUDED.quantity,
                    avg_price = (paper_positions.avg_price * paper_positions.quantity + EXCLUDED.avg_price * EXCLUDED.quantity) / (paper_positions.quantity + EXCLUDED.quantity),
                    market_value = paper_positions.market_value + EXCLUDED.market_value
            """,
                (self.account_id, ticker, quantity, execution_price, quantity * execution_price),
            )

        elif side == "SELL":
            # Check position
            cur.execute(
                """
                SELECT quantity FROM paper_positions
                WHERE account_id = %s AND ticker = %s
            """,
                (self.account_id, ticker),
            )

            row = cur.fetchone()
            if not row or float(row[0]) < quantity:
                logger.error(
                    f"Insufficient shares to sell: need {quantity}, have {row[0] if row else 0}"
                )
                return None

            proceeds = quantity * execution_price

            # Add cash
            cur.execute(
                """
                UPDATE paper_accounts
                SET cash_balance = cash_balance + %s,
                    buying_power = buying_power + %s
                WHERE account_id = %s
            """,
                (proceeds, proceeds, self.account_id),
            )

            # Reduce position
            cur.execute(
                """
                UPDATE paper_positions
                SET quantity = quantity - %s,
                    market_value = market_value - %s
                WHERE account_id = %s AND ticker = %s
            """,
                (quantity, quantity * execution_price, self.account_id, ticker),
            )

        self.conn.commit()

        logger.info(
            f"✅ Paper order filled: {side} {quantity} {ticker} @ ${execution_price:.2f} (Order ID: {order_id})"
        )

        # Log order
        self._log_order(order_id, ticker, quantity, order_type, side, execution_price, "FILLED")

        return order_id

    def _get_market_price(self, ticker: str) -> Optional[float]:
        """Get current market price for ticker"""
        cur = self.conn.cursor()

        # Get latest close price
        cur.execute(
            """
            SELECT close
            FROM daily_bars
            WHERE ticker = %s
            ORDER BY date DESC
            LIMIT 1
        """,
            (ticker,),
        )

        row = cur.fetchone()
        if row:
            return float(row[0])

        return None

    def _log_order(
        self,
        order_id: str,
        ticker: str,
        quantity: float,
        order_type: str,
        side: str,
        price: Optional[float],
        status: str,
    ):
        """Log order to database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            INSERT INTO trade_executions (
                order_id, ticker, quantity, order_type, side, price, status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """,
            (order_id, ticker, quantity, order_type, side, price, status),
        )

        self.conn.commit()

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of an order"""
        if self.paper_trading:
            return self._get_paper_order_status(order_id)

        return self._make_api_request("GET", f"/accounts/{self.account_id}/orders/{order_id}")

    def _get_paper_order_status(self, order_id: str) -> Optional[Dict]:
        """Get paper order status from database"""
        cur = self.conn.cursor()

        cur.execute(
            """
            SELECT ticker, quantity, order_type, side, price, status
            FROM trade_executions
            WHERE order_id = %s
        """,
            (order_id,),
        )

        row = cur.fetchone()
        if row:
            return {
                "order_id": order_id,
                "ticker": row[0],
                "quantity": float(row[1]),
                "order_type": row[2],
                "side": row[3],
                "price": float(row[4]) if row[4] else None,
                "status": row[5],
            }

        return None

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Test Schwab connector"""
    import argparse

    parser = argparse.ArgumentParser(description="Test Schwab API Connector")
    parser.add_argument("--paper", action="store_true", help="Use paper trading mode")
    parser.add_argument(
        "--auth-code", type=str, help="OAuth authorization code for initial authentication"
    )

    args = parser.parse_args()

    connector = SchwabConnector(paper_trading=args.paper)

    try:
        # Authenticate
        if connector.authenticate(auth_code=args.auth_code):
            logger.info("✅ Authentication successful")

            # Get account info
            account_info = connector.get_account_info()
            logger.info(f"Account Info: {account_info}")

            # Get positions
            positions = connector.get_positions()
            logger.info(f"Positions ({len(positions)}):")
            for pos in positions:
                logger.info(
                    f"  {pos['ticker']}: {pos['quantity']} shares @ ${pos['avg_price']:.2f}"
                )
        else:
            logger.error("❌ Authentication failed")

    finally:
        connector.close()


if __name__ == "__main__":
    main()
