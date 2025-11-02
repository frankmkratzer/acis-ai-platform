#!/usr/bin/env python3
"""
Autonomous Rebalancing Engine

Core orchestration layer that:
1. Detects market regime
2. Selects optimal strategy via meta-model
3. Generates target portfolio using ML+RL models
4. Calculates required trades
5. Applies risk management checks
6. Executes trades (paper trading initially)
7. Logs everything to database

This is the heart of the autonomous fund.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras

from autonomous.hybrid_portfolio_generator import HybridPortfolioGenerator

# Import our autonomous components
from autonomous.market_regime_detector import MarketRegimeDetector
from autonomous.meta_strategy_selector import MetaStrategySelector
from utils import get_logger

# Import balance manager for cash tracking
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
# Import Schwab connector for trade execution
import sys
from pathlib import Path

from api.services.balance_manager import BalanceManager

trading_path = Path(__file__).parent.parent / "trading"
sys.path.insert(0, str(trading_path))
from trading.schwab_connector import SchwabConnector

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


class RiskManager:
    """
    Risk management layer - enforces position limits and drawdown controls
    """

    def __init__(self):
        self.max_drawdown = 0.15  # 15% max drawdown from peak
        self.max_position_size = 0.10  # 10% max per stock
        self.max_daily_turnover = 0.30  # 30% max daily churn
        self.min_cash_reserve = 0.02  # 2% cash buffer
        self.max_concentration = 0.40  # 40% max in top 3 positions

    def check_position_sizing(self, target_portfolio, total_value):
        """Ensure no position exceeds max size"""
        violations = []

        for ticker, weight in target_portfolio.items():
            if weight > self.max_position_size:
                violations.append(
                    f"{ticker}: {weight:.2%} exceeds max {self.max_position_size:.2%}"
                )

        if violations:
            logger.error(f"Position sizing violations: {violations}")
            return False, violations

        return True, []

    def check_concentration(self, target_portfolio):
        """Check top 3 positions don't exceed max concentration"""
        if not target_portfolio:
            return True, []

        sorted_positions = sorted(target_portfolio.items(), key=lambda x: x[1], reverse=True)
        top_3_weight = sum([w for _, w in sorted_positions[:3]])

        if top_3_weight > self.max_concentration:
            msg = f"Top 3 concentration {top_3_weight:.2%} exceeds max {self.max_concentration:.2%}"
            logger.error(msg)
            return False, [msg]

        return True, []

    def check_turnover(self, trades, current_value, current_positions):
        """Check daily turnover doesn't exceed limit (skip for first rebalance)"""
        # Allow 100% turnover on first rebalance (empty portfolio)
        if len(current_positions) == 0:
            logger.info("First rebalance - skipping turnover check")
            return True, []

        total_turnover = sum([abs(t["dollar_amount"]) for t in trades])
        turnover_pct = total_turnover / current_value if current_value > 0 else 0

        if turnover_pct > self.max_daily_turnover:
            msg = f"Turnover {turnover_pct:.2%} exceeds max {self.max_daily_turnover:.2%}"
            logger.warning(msg)
            return False, [msg]

        return True, []

    def check_drawdown(self, conn, account_id):
        """Check if we're within drawdown limits"""
        cur = conn.cursor()

        # Get peak portfolio value
        cur.execute(
            """
            SELECT MAX(total_value) as peak_value
            FROM portfolio_value_history
            WHERE account_id = %s
        """,
            (account_id,),
        )

        result = cur.fetchone()
        if not result or not result[0]:
            return True, []  # No history yet

        peak_value = result[0]

        # Get current value
        cur.execute(
            """
            SELECT total_value
            FROM portfolio_value_history
            WHERE account_id = %s
            ORDER BY date DESC
            LIMIT 1
        """,
            (account_id,),
        )

        result = cur.fetchone()
        if not result:
            return True, []

        current_value = result[0]

        drawdown = (peak_value - current_value) / peak_value if peak_value > 0 else 0

        if drawdown > self.max_drawdown:
            msg = f"Drawdown {drawdown:.2%} exceeds max {self.max_drawdown:.2%}"
            logger.error(msg)
            return False, [msg]

        return True, []

    def approve_rebalance(
        self, current_positions, target_portfolio, trades, total_value, conn, account_id
    ):
        """
        Main approval method - runs all risk checks

        Returns: (approved: bool, violations: list)
        """
        violations = []

        # Check 1: Position sizing
        approved, msgs = self.check_position_sizing(target_portfolio, total_value)
        if not approved:
            violations.extend(msgs)

        # Check 2: Concentration
        approved, msgs = self.check_concentration(target_portfolio)
        if not approved:
            violations.extend(msgs)

        # Check 3: Turnover
        approved, msgs = self.check_turnover(trades, total_value, current_positions)
        if not approved:
            violations.extend(msgs)

        # Check 4: Drawdown
        approved, msgs = self.check_drawdown(conn, account_id)
        if not approved:
            violations.extend(msgs)

        if violations:
            logger.error(f"Risk checks failed: {len(violations)} violations")
            for v in violations:
                logger.error(f"  - {v}")
            return False, violations

        logger.info("✅ All risk checks passed")
        return True, []


class AutonomousRebalancer:
    """
    Main autonomous rebalancing orchestrator
    """

    def __init__(
        self,
        account_id=None,
        dry_run=True,
        use_real_models=True,
        paper_trading=True,
        client_id=None,
    ):
        self.account_id = account_id
        self.client_id = client_id
        self.dry_run = dry_run
        self.use_real_models = use_real_models
        self.paper_trading = paper_trading
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.risk_manager = RiskManager()
        self.regime_detector = MarketRegimeDetector()
        self.meta_selector = MetaStrategySelector()
        self.balance_manager = BalanceManager()

        # Check client's trading_mode preference if client_id provided
        if client_id:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT trading_mode, auto_trading_enabled, first_name, last_name
                FROM clients
                WHERE client_id = %s
            """,
                (client_id,),
            )
            result = cur.fetchone()

            if result:
                client_mode, auto_enabled, first_name, last_name = result
                logger.info(f"Client: {first_name} {last_name} (ID: {client_id})")
                logger.info(f"  Trading Mode: {client_mode}")
                logger.info(f"  Auto Trading: {'Enabled' if auto_enabled else 'Disabled'}")

                # Override paper_trading if client prefers paper mode
                if client_mode == "paper":
                    if not self.paper_trading:
                        logger.warning(
                            f"⚠️  Client trading_mode is 'paper' - overriding live trading flag"
                        )
                    self.paper_trading = True
                    logger.info("  → Forcing PAPER TRADING mode based on client preference")

                # Respect auto_trading_enabled flag
                if not auto_enabled:
                    logger.warning(f"⚠️  Auto trading is DISABLED for this client")
                    logger.warning("  → Trades will be generated but NOT executed")
                    self.dry_run = True
            else:
                logger.warning(f"Client ID {client_id} not found in database")

        # Initialize portfolio generator (real ML+RL or mock)
        if use_real_models:
            self.portfolio_generator = HybridPortfolioGenerator()
            logger.info("Using REAL ML+RL models for portfolio generation")
        else:
            self.portfolio_generator = None
            logger.info("Using MOCK portfolios")

        # Initialize Schwab connector for trade execution
        if not dry_run:
            self.schwab = SchwabConnector(paper_trading=paper_trading)
            logger.info(
                f"Schwab connector initialized ({'Paper Trading' if paper_trading else 'LIVE TRADING'})"
            )
        else:
            self.schwab = None
            logger.info("Dry run mode - Schwab connector disabled")

    def get_account_balances(self):
        """
        Get account balances from paper_accounts table

        Returns:
            dict with cash_balance, buying_power, total_value, positions_value
        """
        if not self.account_id:
            logger.info("No account_id specified - assuming zero balances")
            return {
                "cash_balance": 0.0,
                "buying_power": 0.0,
                "total_value": 0.0,
                "positions_value": 0.0,
            }

        cur = self.conn.cursor()

        # First ensure account exists in paper_accounts
        cur.execute(
            """
            INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
            VALUES (%s, 0, 0, 0)
            ON CONFLICT (account_id) DO NOTHING
        """,
            (self.account_id,),
        )
        self.conn.commit()

        # Fetch balances
        cur.execute(
            """
            SELECT cash_balance, buying_power, total_value
            FROM paper_accounts
            WHERE account_id = %s
        """,
            (self.account_id,),
        )

        result = cur.fetchone()
        if not result:
            logger.warning(f"No account found for {self.account_id} even after insert")
            return {
                "cash_balance": 0.0,
                "buying_power": 0.0,
                "total_value": 0.0,
                "positions_value": 0.0,
            }

        cash_balance, buying_power, total_value = result

        # Calculate positions value from paper_positions
        cur.execute(
            """
            SELECT COALESCE(SUM(market_value), 0) as positions_value
            FROM paper_positions
            WHERE account_id = %s
        """,
            (self.account_id,),
        )

        positions_value = cur.fetchone()[0] or 0.0

        balances = {
            "cash_balance": float(cash_balance),
            "buying_power": float(buying_power),
            "total_value": float(total_value),
            "positions_value": float(positions_value),
        }

        logger.info(
            f"Account balances: cash=${cash_balance:,.2f}, buying_power=${buying_power:,.2f}, "
            f"positions=${positions_value:,.2f}, total=${total_value:,.2f}"
        )

        return balances

    def get_current_positions(self):
        """
        Get current portfolio positions from paper_positions table

        Returns:
            tuple: (positions dict, total_value float, account_balances dict)
        """
        if not self.account_id:
            logger.info("No account_id specified - assuming empty portfolio")
            return {}, 0.0, {"cash_balance": 0.0, "buying_power": 0.0, "total_value": 0.0}

        # Get account balances first
        balances = self.get_account_balances()

        cur = self.conn.cursor()

        # Get positions from paper_positions (current system of record)
        cur.execute(
            """
            SELECT ticker, quantity, avg_price, market_value
            FROM paper_positions
            WHERE account_id = %s
        """,
            (self.account_id,),
        )

        positions = {}
        total_value = 0.0

        for row in cur.fetchall():
            ticker, quantity, avg_price, market_value = row
            positions[ticker] = {
                "quantity": float(quantity),
                "average_cost": float(avg_price),
                "market_value": float(market_value),
            }
            total_value += float(market_value)

        logger.info(
            f"Current positions: {len(positions)} holdings, ${total_value:,.2f} total value, ${balances['cash_balance']:,.2f} cash"
        )

        return positions, total_value, balances

    def generate_target_portfolio(self, strategy, total_value):
        """
        Generate target portfolio using ML+RL models

        1. Load ML model for stock selection
        2. Load RL model for portfolio allocation
        3. Run ML model to get top stocks
        4. Run RL model to get optimal weights
        """
        logger.info(f"Generating target portfolio for strategy: {strategy}")

        if self.use_real_models and self.portfolio_generator:
            # Use real ML+RL models
            logger.info("Using REAL ML+RL models")
            portfolio = self.portfolio_generator.generate_portfolio(
                strategy=strategy,
                total_value=total_value,
                use_rl=True,  # Enable RL for optimal weight allocation
                top_n=50,
                max_position=0.10,
            )

            if not portfolio:
                logger.error("Real models returned empty portfolio, falling back to mock")
                return self._mock_portfolio(strategy)

            logger.info(f"Generated portfolio: {len(portfolio)} positions (ML+RL)")
            return portfolio

        else:
            # Fallback to mock portfolios
            logger.warning("Using mock portfolio generator")
            return self._mock_portfolio(strategy)

    def _mock_portfolio(self, strategy):
        """Fallback mock portfolios for testing"""
        mock_portfolios = {
            "growth_largecap": {
                "AAPL": 0.10,
                "MSFT": 0.10,
                "GOOGL": 0.10,
                "AMZN": 0.10,
                "NVDA": 0.10,
                "META": 0.10,
                "TSLA": 0.10,
                "NFLX": 0.10,
                "AMD": 0.10,
                "CRM": 0.10,
            },
            "growth_midcap": {
                "SQ": 0.10,
                "SHOP": 0.10,
                "DDOG": 0.10,
                "SNOW": 0.10,
                "NET": 0.10,
                "CRWD": 0.10,
                "ZS": 0.10,
                "OKTA": 0.10,
                "TWLO": 0.10,
                "DOCU": 0.10,
            },
            "growth_smallcap": {
                "BILL": 0.10,
                "FROG": 0.10,
                "UPST": 0.10,
                "PATH": 0.10,
                "OPEN": 0.10,
                "SOFI": 0.10,
                "AFRM": 0.10,
                "HOOD": 0.10,
                "COIN": 0.10,
                "RBLX": 0.10,
            },
            "value_largecap": {
                "JPM": 0.10,
                "BAC": 0.10,
                "WFC": 0.10,
                "XOM": 0.10,
                "CVX": 0.10,
                "JNJ": 0.10,
                "PG": 0.10,
                "KO": 0.10,
                "PFE": 0.10,
                "MRK": 0.10,
            },
            "value_midcap": {
                "KEY": 0.10,
                "FITB": 0.10,
                "RF": 0.10,
                "HBAN": 0.10,
                "MTB": 0.10,
                "CFG": 0.10,
                "ZION": 0.10,
                "CMA": 0.10,
                "FHN": 0.10,
                "ONB": 0.10,
            },
            "value_smallcap": {
                "UBSI": 0.10,
                "WAFD": 0.10,
                "CATY": 0.10,
                "FFIN": 0.10,
                "NWBI": 0.10,
                "INDB": 0.10,
                "BHLB": 0.10,
                "FIBK": 0.10,
                "TOWN": 0.10,
                "FULT": 0.10,
            },
            "dividend_strategy": {
                "T": 0.10,
                "VZ": 0.10,
                "IBM": 0.10,
                "ABBV": 0.10,
                "BMY": 0.10,
                "MO": 0.10,
                "SO": 0.10,
                "D": 0.10,
                "DUK": 0.10,
                "KMI": 0.10,
            },
        }

        portfolio = mock_portfolios.get(strategy, mock_portfolios["value_largecap"])

        # Normalize weights to sum to 1.0
        total_weight = sum(portfolio.values())
        portfolio = {k: v / total_weight for k, v in portfolio.items()}

        logger.info(f"Generated mock portfolio: {len(portfolio)} positions")
        return portfolio

    def calculate_trades(self, current_positions, target_portfolio, total_value):
        """
        Calculate required trades to move from current to target portfolio

        Returns: list of trade dicts with ticker, side, quantity, dollar_amount
        """
        trades = []

        # Get current prices (mock for now)
        # In production, fetch real-time prices from database or API
        current_prices = self.get_current_prices(
            list(set(list(current_positions.keys()) + list(target_portfolio.keys())))
        )

        # Calculate target dollar amounts
        target_dollars = {
            ticker: weight * total_value for ticker, weight in target_portfolio.items()
        }

        # Calculate current dollar amounts
        current_dollars = {ticker: pos["market_value"] for ticker, pos in current_positions.items()}

        # Find all tickers (current + target)
        all_tickers = set(list(current_dollars.keys()) + list(target_dollars.keys()))

        for ticker in all_tickers:
            current_amt = current_dollars.get(ticker, 0.0)
            target_amt = target_dollars.get(ticker, 0.0)
            delta = target_amt - current_amt

            if abs(delta) < 100:  # Skip trades < $100
                continue

            price = current_prices.get(ticker, 100.0)  # Default price if not found
            quantity = delta / price

            trade = {
                "ticker": ticker,
                "side": "BUY" if delta > 0 else "SELL",
                "quantity": abs(quantity),
                "price": price,
                "dollar_amount": abs(delta),
                "current_amount": current_amt,
                "target_amount": target_amt,
            }

            trades.append(trade)

        # Sort by dollar amount (largest first)
        trades.sort(key=lambda x: x["dollar_amount"], reverse=True)

        logger.info(f"Calculated {len(trades)} required trades")
        logger.info(f"  Buys: {sum(1 for t in trades if t['side'] == 'BUY')}")
        logger.info(f"  Sells: {sum(1 for t in trades if t['side'] == 'SELL')}")
        logger.info(f"  Total turnover: ${sum(t['dollar_amount'] for t in trades):,.2f}")

        return trades

    def get_current_prices(self, tickers):
        """
        Get current prices for tickers

        For now returns mock prices.
        In production, query from daily_bars or real-time API.
        """
        # Mock prices - in production, fetch from database
        prices = {}
        for ticker in tickers:
            # Use a simple hash to generate consistent mock prices
            prices[ticker] = 50 + (hash(ticker) % 200)

        return prices

    def should_rebalance(self, current_positions, target_portfolio, total_value, threshold=0.05):
        """
        Determine if rebalancing is needed

        Rebalances if any position drifts > threshold from target weight
        """
        if not current_positions and target_portfolio:
            logger.info("Empty portfolio - rebalancing needed to establish positions")
            return True

        current_weights = {}
        for ticker, pos in current_positions.items():
            current_weights[ticker] = pos["market_value"] / total_value if total_value > 0 else 0

        max_drift = 0.0
        drift_ticker = None

        all_tickers = set(list(current_weights.keys()) + list(target_portfolio.keys()))

        for ticker in all_tickers:
            current_wt = current_weights.get(ticker, 0.0)
            target_wt = target_portfolio.get(ticker, 0.0)
            drift = abs(current_wt - target_wt)

            if drift > max_drift:
                max_drift = drift
                drift_ticker = ticker

        needs_rebalance = max_drift > threshold

        if needs_rebalance:
            logger.info(
                f"Rebalancing needed: max drift {max_drift:.2%} on {drift_ticker} (threshold: {threshold:.2%})"
            )
        else:
            logger.info(
                f"No rebalancing needed: max drift {max_drift:.2%} (threshold: {threshold:.2%})"
            )

        return needs_rebalance

    def execute_trades(self, trades):
        """
        Execute trades via Schwab API (or paper trading)

        Dry run mode: Just logs trades without execution
        Non-dry run with paper_trading=True: Executes in paper trading (simulated)
        Non-dry run with paper_trading=False: Executes LIVE trades via Schwab API
        """
        if self.dry_run:
            logger.info("DRY RUN MODE - Trades not actually executed")

        executed_trades = []

        for trade in trades:
            logger.info(
                f"  {'[DRY RUN] ' if self.dry_run else ''}{trade['side']:4s} {trade['quantity']:8.2f} {trade['ticker']:6s} @ ${trade['price']:.2f} = ${trade['dollar_amount']:,.2f}"
            )

            exec_time = datetime.now()

            # Execute via Schwab connector if not in dry run
            if not self.dry_run and self.schwab:
                try:
                    # Authenticate
                    if not self.schwab.authenticate():
                        logger.error(f"Failed to authenticate with Schwab for {trade['ticker']}")
                        continue

                    # Place order
                    order_id = self.schwab.place_order(
                        ticker=trade["ticker"],
                        quantity=abs(trade["quantity"]),
                        order_type="MARKET",
                        side=trade["side"],
                    )

                    if order_id:
                        logger.info(f"✅ Order executed: {order_id}")
                        execution_price = trade["price"]  # In paper trading, use estimated price
                        status = "filled"
                    else:
                        logger.error(f"❌ Order failed for {trade['ticker']}")
                        execution_price = trade["price"]
                        status = "failed"

                except Exception as e:
                    logger.error(f"Error executing trade for {trade['ticker']}: {e}")
                    execution_price = trade["price"]
                    status = "error"
            else:
                # Dry run or no connector
                execution_price = trade["price"]
                status = "paper" if self.dry_run else "simulated"

            # Update cash balance based on trading mode
            # Skip if dry run
            if not self.dry_run:
                commission = 0.0  # Schwab has $0 commission
                try:
                    if self.paper_trading:
                        # PAPER TRADING: Update cash in database directly
                        if trade["side"] == "BUY":
                            balance_result = self.balance_manager.update_balance_after_buy(
                                account_id=self.account_id,
                                shares=trade["quantity"],
                                price=execution_price,
                                commission=commission,
                                validate=False,  # Don't validate - we manage risk separately
                            )
                            if balance_result["success"]:
                                logger.info(
                                    f"  💰 Cash balance updated: ${balance_result['old_balance']:,.2f} → ${balance_result['new_balance']:,.2f}"
                                )
                            else:
                                logger.warning(
                                    f"  ⚠️  Failed to update cash balance: {balance_result.get('error')}"
                                )
                        elif trade["side"] == "SELL":
                            balance_result = self.balance_manager.update_balance_after_sell(
                                account_id=self.account_id,
                                shares=trade["quantity"],
                                price=execution_price,
                                commission=commission,
                            )
                            if balance_result["success"]:
                                logger.info(
                                    f"  💰 Cash balance updated: ${balance_result['old_balance']:,.2f} → ${balance_result['new_balance']:,.2f}"
                                )
                            else:
                                logger.warning(
                                    f"  ⚠️  Failed to update cash balance: {balance_result.get('error')}"
                                )
                    else:
                        # LIVE TRADING: Sync balances FROM Schwab (Schwab is source of truth)
                        if self.schwab:
                            try:
                                # Fetch current balances from Schwab
                                schwab_balances = self.schwab.get_balances(self.account_id)
                                # Sync to database
                                balance_result = self.balance_manager.sync_from_schwab(
                                    account_id=self.account_id, schwab_balances=schwab_balances
                                )
                                if balance_result["success"]:
                                    logger.info(
                                        f"  💰 Synced balances from Schwab: Cash=${balance_result.get('cash_balance', 0):,.2f}"
                                    )
                                else:
                                    logger.warning(
                                        f"  ⚠️  Failed to sync from Schwab: {balance_result.get('error')}"
                                    )
                            except Exception as sync_err:
                                logger.error(f"  ❌ Error syncing from Schwab: {sync_err}")
                except Exception as e:
                    logger.error(f"  ❌ Error updating balance: {e}")

            executed_trade = {
                **trade,
                "executed_at": exec_time.isoformat(),  # Convert to string for JSON serialization
                "execution_price": execution_price,
                "slippage": 0.0,
                "commission": 0.0,  # Schwab has no commission
                "status": status,
                "_executed_at_dt": exec_time,  # Keep datetime version for SQL insert
            }

            executed_trades.append(executed_trade)

        return executed_trades

    def log_rebalance(
        self,
        strategy,
        meta_confidence,
        market_regime,
        current_positions,
        target_portfolio,
        trades,
        executed_trades,
        pre_value,
        post_value,
    ):
        """Save rebalancing event to database"""
        cur = self.conn.cursor()

        # Clean executed_trades for JSON serialization (remove datetime objects)
        trades_for_json = []
        for trade in executed_trades:
            clean_trade = {k: v for k, v in trade.items() if k != "_executed_at_dt"}
            trades_for_json.append(clean_trade)

        # Insert rebalancing log
        cur.execute(
            """
            INSERT INTO rebalancing_log (
                rebalance_date, account_id, strategy_selected,
                meta_model_confidence, market_regime,
                pre_rebalance_value, post_rebalance_value,
                num_positions_before, num_positions_after,
                num_buys, num_sells, total_turnover,
                total_transaction_costs, trades, status,
                execution_time_seconds
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """,
            (
                datetime.now().date(),
                self.account_id,
                strategy,
                meta_confidence,
                market_regime,
                pre_value,
                post_value,
                len(current_positions),
                len(target_portfolio),
                sum(1 for t in trades if t["side"] == "BUY"),
                sum(1 for t in trades if t["side"] == "SELL"),
                sum(t["dollar_amount"] for t in trades),
                sum(t.get("commission", 0) for t in executed_trades),
                psycopg2.extras.Json(trades_for_json),  # Use cleaned version
                "paper" if self.dry_run else "completed",
                0.0,  # execution time - would measure in production
            ),
        )

        rebalance_id = cur.fetchone()[0]

        # Insert individual trade executions
        for trade in executed_trades:
            cur.execute(
                """
                INSERT INTO trade_executions (
                    rebalance_id, account_id, ticker, side,
                    quantity, target_price, execution_price,
                    slippage, commission, sec_fee, total_cost,
                    order_type, execution_status, submitted_at, executed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """,
                (
                    rebalance_id,
                    self.account_id,
                    trade["ticker"],
                    trade["side"],
                    trade["quantity"],
                    trade["price"],
                    trade["execution_price"],
                    trade["slippage"],
                    trade["commission"],
                    0.0,  # SEC fee
                    trade["commission"],
                    "MARKET",
                    trade["status"],
                    trade["_executed_at_dt"],  # Use datetime version for SQL
                    trade["_executed_at_dt"],
                ),
            )

        self.conn.commit()
        logger.info(f"✅ Rebalancing logged to database (ID: {rebalance_id})")

        return rebalance_id

    def run(self):
        """
        Main autonomous rebalancing pipeline

        This is the entry point that orchestrates everything
        """
        logger.info("=" * 80)
        logger.info("AUTONOMOUS REBALANCING ENGINE")
        logger.info("=" * 80)
        logger.info(f"Account ID: {self.account_id or 'None (mock mode)'}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE TRADING'}")
        logger.info("=" * 80)

        try:
            # Step 1: Detect market regime
            logger.info("\n[1/7] Detecting market regime...")
            regime_data = self.regime_detector.detect_current_regime()
            logger.info(
                f"✅ Regime: {regime_data['regime_label']} (confidence: {regime_data['regime_confidence']:.2%})"
            )

            # Step 2: Select strategy
            logger.info("\n[2/7] Selecting optimal strategy...")
            selection = self.meta_selector.select_strategy(use_ml=False)
            strategy = selection["selected_strategy"]
            meta_confidence = selection["selection_confidence"]
            logger.info(f"✅ Selected: {strategy} (confidence: {meta_confidence:.2%})")

            # Step 3: Get current positions and account balances
            logger.info("\n[3/7] Loading current positions and account balances...")
            current_positions, total_value, account_balances = self.get_current_positions()

            # Use actual account balances - total_value should be positions_value + cash_balance
            cash_balance = account_balances["cash_balance"]
            buying_power = account_balances["buying_power"]
            account_total = total_value + cash_balance

            logger.info(
                f"Account status: ${total_value:,.2f} in positions, ${cash_balance:,.2f} cash, "
                f"${account_total:,.2f} total, ${buying_power:,.2f} buying power"
            )

            # If no positions and no cash, initialize with starting balance
            if account_total == 0:
                account_total = 100000.0  # Default starting balance for new accounts
                cash_balance = account_total
                logger.info(f"New account - initializing with ${account_total:,.2f}")

            # Step 4: Generate target portfolio
            logger.info("\n[4/7] Generating target portfolio...")
            target_portfolio = self.generate_target_portfolio(strategy, total_value)
            logger.info(f"✅ Target: {len(target_portfolio)} positions")

            # Step 5: Check if rebalancing needed
            logger.info("\n[5/7] Checking if rebalancing needed...")
            needs_rebalance = self.should_rebalance(
                current_positions, target_portfolio, total_value
            )

            if not needs_rebalance:
                logger.info("✅ Portfolio within tolerance - no rebalancing needed")
                return {
                    "status": "skipped",
                    "reason": "within_tolerance",
                    "strategy": strategy,
                    "regime": regime_data["regime_label"],
                }

            # Step 6: Calculate trades
            logger.info("\n[6/7] Calculating required trades...")
            trades = self.calculate_trades(current_positions, target_portfolio, total_value)

            # Step 7: Risk checks
            logger.info("\n[7/7] Running risk management checks...")
            approved, violations = self.risk_manager.approve_rebalance(
                current_positions, target_portfolio, trades, total_value, self.conn, self.account_id
            )

            if not approved:
                logger.error(f"❌ Risk checks FAILED - {len(violations)} violations")
                logger.error("Rebalancing BLOCKED")
                return {
                    "status": "blocked",
                    "reason": "risk_violations",
                    "violations": violations,
                    "strategy": strategy,
                    "regime": regime_data["regime_label"],
                }

            # Step 8: Execute trades
            logger.info("\n[8/8] Executing trades...")
            executed_trades = self.execute_trades(trades)
            logger.info(f"✅ Executed {len(executed_trades)} trades")

            # Step 9: Log everything
            logger.info("\n[9/9] Logging rebalancing event...")
            rebalance_id = self.log_rebalance(
                strategy,
                meta_confidence,
                regime_data["regime_label"],
                current_positions,
                target_portfolio,
                trades,
                executed_trades,
                total_value,
                total_value,  # post-value same for now
            )

            logger.info("=" * 80)
            logger.info("✅ AUTONOMOUS REBALANCING COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Rebalance ID: {rebalance_id}")
            logger.info(f"Strategy: {strategy}")
            logger.info(f"Market Regime: {regime_data['regime_label']}")
            logger.info(f"Trades Executed: {len(executed_trades)}")
            logger.info(f"Total Turnover: ${sum(t['dollar_amount'] for t in trades):,.2f}")
            logger.info("=" * 80)

            return {
                "status": "success",
                "rebalance_id": rebalance_id,
                "strategy": strategy,
                "regime": regime_data["regime_label"],
                "trades": len(executed_trades),
                "turnover": sum(t["dollar_amount"] for t in trades),
            }

        except Exception as e:
            logger.error(f"❌ Autonomous rebalancing FAILED: {e}")
            import traceback

            traceback.print_exc()

            return {"status": "failed", "error": str(e)}

    def close(self):
        self.conn.close()
        self.regime_detector.close()
        self.meta_selector.close()


def main():
    """Run autonomous rebalancing"""
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Rebalancing Engine")
    parser.add_argument("--account-id", type=int, help="Account ID to rebalance")
    parser.add_argument("--live", action="store_true", help="Run in live mode (default: dry run)")
    parser.add_argument(
        "--use-real-models",
        action="store_true",
        default=True,
        help="Use real ML+RL models (default: True)",
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock portfolios instead of real models"
    )
    args = parser.parse_args()

    rebalancer = AutonomousRebalancer(
        account_id=args.account_id,
        dry_run=not args.live,
        use_real_models=args.use_real_models and not args.mock,
    )

    try:
        result = rebalancer.run()
        return 0 if result["status"] in ["success", "skipped"] else 1
    finally:
        rebalancer.close()


if __name__ == "__main__":
    sys.exit(main())
