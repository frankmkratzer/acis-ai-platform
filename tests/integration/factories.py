"""
Test Data Factories

Provides factory functions for creating test data in integration tests.
"""

import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict


class ClientFactory:
    """Factory for creating test client data"""

    @staticmethod
    def build(**kwargs) -> Dict[str, Any]:
        """Build client data with defaults"""
        defaults = {
            "first_name": f"Test{random.randint(1000, 9999)}",
            "last_name": f"User{random.randint(1000, 9999)}",
            "email": f"test.user.{random.randint(1000, 9999)}@example.com",
            "risk_tolerance": random.choice(["conservative", "moderate", "aggressive"]),
            "investment_goal": random.choice(["income", "growth", "balanced"]),
            "is_active": True,
        }
        defaults.update(kwargs)
        return defaults


class AccountFactory:
    """Factory for creating test brokerage account data"""

    @staticmethod
    def build(**kwargs) -> Dict[str, Any]:
        """Build account data with defaults"""
        defaults = {
            "account_number": f"ACC{random.randint(100000, 999999)}",
            "account_hash": f"hash_{''.join(random.choices(string.ascii_lowercase + string.digits, k=16))}",
            "account_type": random.choice(["cash", "margin"]),
            "brokerage_id": 1,  # Schwab
            "is_active": True,
        }
        defaults.update(kwargs)
        return defaults


class PortfolioFactory:
    """Factory for creating test portfolio data"""

    @staticmethod
    def build(**kwargs) -> Dict[str, Any]:
        """Build portfolio data with defaults"""
        defaults = {
            "portfolio_name": f"Test Portfolio {random.randint(1000, 9999)}",
            "strategy": random.choice(["growth", "value", "dividend"]),
            "max_positions": random.choice([10, 15, 20, 25, 30]),
            "rebalance_frequency": "monthly",
        }
        defaults.update(kwargs)
        return defaults


class TradeFactory:
    """Factory for creating test trade data"""

    @staticmethod
    def build(**kwargs) -> Dict[str, Any]:
        """Build trade data with defaults"""
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
        defaults = {
            "ticker": random.choice(tickers),
            "action": random.choice(["buy", "sell"]),
            "shares": random.randint(1, 100),
            "price": round(random.uniform(50, 500), 2),
            "order_type": "market",
        }
        defaults.update(kwargs)
        return defaults


class RebalanceRequestFactory:
    """Factory for creating rebalance request data"""

    @staticmethod
    def build(**kwargs) -> Dict[str, Any]:
        """Build rebalance request data with defaults"""
        defaults = {
            "max_positions": 10,
            "require_approval": True,
            "dry_run": False,
        }
        defaults.update(kwargs)
        return defaults


class OrderBatchFactory:
    """Factory for creating order batch test data"""

    @staticmethod
    def build_current_portfolio(**kwargs) -> Dict[str, Any]:
        """Build sample current portfolio"""
        defaults = {
            "AAPL": {"shares": 10, "value": 1800.0},
            "MSFT": {"shares": 5, "value": 1900.0},
            "GOOGL": {"shares": 8, "value": 1120.0},
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def build_target_allocation(**kwargs) -> Dict[str, Any]:
        """Build sample target allocation"""
        defaults = {
            "AAPL": 0.25,
            "MSFT": 0.25,
            "GOOGL": 0.20,
            "NVDA": 0.15,
            "TSLA": 0.15,
        }
        defaults.update(kwargs)
        return defaults


def random_date(start_days_ago=30, end_days_ago=0):
    """Generate random date within the specified range"""
    start = datetime.now() - timedelta(days=start_days_ago)
    end = datetime.now() - timedelta(days=end_days_ago)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)


def random_ticker(count=1):
    """Get random ticker symbols"""
    tickers = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "NFLX",
        "AMD",
        "INTC",
        "CSCO",
        "ORCL",
        "IBM",
        "CRM",
        "ADBE",
        "PYPL",
    ]
    if count == 1:
        return random.choice(tickers)
    return random.sample(tickers, count)
