#!/usr/bin/env python3
"""
Autonomous Fund Backtesting Framework

Simulates the complete autonomous fund system on historical data:
1. Market regime detection at each rebalancing date
2. Meta-strategy selection based on regime
3. Portfolio generation using selected strategy
4. Trade execution and position tracking
5. Performance measurement and reporting

This validates the autonomous system before live deployment.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import psycopg2

# Import hybrid portfolio generator for real ML models
from autonomous.hybrid_portfolio_generator import HybridPortfolioGenerator
from utils import get_logger

logger = get_logger(__name__)

DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}


class AutonomousBacktest:
    """
    Complete backtest of autonomous fund system
    """

    def __init__(
        self,
        initial_capital=None,
        client_id=None,
        account_id=None,
        rebalance_frequency="monthly",
        use_real_models=True,
    ):
        """
        Initialize backtest.

        Args:
            initial_capital: Starting capital (if None, fetches from paper_accounts for client)
            client_id: Client ID to fetch actual balance from paper_accounts
            account_id: Account ID/hash to fetch actual balance from paper_accounts
            rebalance_frequency: How often to rebalance ('monthly' or 'quarterly')
            use_real_models: Use real ML models (True) or mock portfolios (False)
        """
        self.rebalance_frequency = rebalance_frequency
        self.use_real_models = use_real_models
        self.conn = psycopg2.connect(**DB_CONFIG)

        # Fetch client-specific starting capital if provided
        if client_id and account_id and initial_capital is None:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT cash_balance
                FROM paper_accounts
                WHERE account_id = %s
            """,
                (account_id,),
            )
            result = cursor.fetchone()
            cursor.close()

            if result and result[0] > 0:
                self.initial_capital = float(result[0])
                logger.info(f"Using client-specific starting capital: ${self.initial_capital:,.2f}")
            else:
                self.initial_capital = 100000  # Default fallback
                logger.warning(
                    f"No balance found for account {account_id}, using default: ${self.initial_capital:,.2f}"
                )
        else:
            self.initial_capital = initial_capital or 100000

        # Portfolio state
        self.cash = self.initial_capital
        self.positions = {}  # {ticker: {'quantity': float, 'avg_cost': float}}
        self.portfolio_value = self.initial_capital

        # Performance tracking
        self.equity_curve = []
        self.rebalancing_log = []
        self.trade_log = []
        self.daily_returns = []

        # Initialize portfolio generator for real models
        if use_real_models:
            self.portfolio_generator = HybridPortfolioGenerator()
            logger.info("Backtest using REAL ML models")
        else:
            self.portfolio_generator = None
            logger.info("Backtest using MOCK portfolios")

    def get_trading_days(self, start_date, end_date):
        """Get list of trading days from database"""
        query = """
        SELECT DISTINCT date
        FROM daily_bars
        WHERE date >= %s AND date <= %s
        ORDER BY date
        """
        df = pd.read_sql(query, self.conn, params=(start_date, end_date))
        return df["date"].tolist()

    def get_rebalance_dates(self, trading_days):
        """Get rebalancing dates based on frequency"""
        if self.rebalance_frequency == "monthly":
            # First trading day of each month
            rebalance_dates = []
            prev_month = None
            for date in trading_days:
                if prev_month is None or date.month != prev_month:
                    rebalance_dates.append(date)
                    prev_month = date.month
            return rebalance_dates
        elif self.rebalance_frequency == "quarterly":
            # First trading day of each quarter
            rebalance_dates = []
            prev_quarter = None
            for date in trading_days:
                quarter = (date.month - 1) // 3
                if prev_quarter is None or quarter != prev_quarter:
                    rebalance_dates.append(date)
                    prev_quarter = quarter
            return rebalance_dates
        else:
            raise ValueError(f"Unsupported rebalance frequency: {self.rebalance_frequency}")

    def get_market_prices(self, date, tickers):
        """Get closing prices for tickers on specific date"""
        if not tickers:
            return {}

        query = """
        SELECT ticker, close
        FROM daily_bars
        WHERE date = %s AND ticker = ANY(%s)
        """
        df = pd.read_sql(query, self.conn, params=(date, list(tickers)))
        return dict(zip(df["ticker"], df["close"]))

    def update_portfolio_value(self, date):
        """Mark-to-market portfolio valuation"""
        if not self.positions:
            self.portfolio_value = self.cash
            return self.portfolio_value

        tickers = list(self.positions.keys())
        prices = self.get_market_prices(date, tickers)

        positions_value = 0.0
        for ticker, position in self.positions.items():
            price = prices.get(ticker, position["avg_cost"])  # Fallback to cost basis if no price
            position["current_price"] = price
            position["market_value"] = position["quantity"] * price
            positions_value += position["market_value"]

        self.portfolio_value = self.cash + positions_value
        return self.portfolio_value

    def detect_market_regime(self, date):
        """
        Simplified regime detection for backtest
        Uses SPY moving averages and volatility
        """
        # Get SPY data up to this date
        query = """
        SELECT date, close
        FROM etf_bars
        WHERE ticker = 'SPY'
          AND date <= %s
        ORDER BY date DESC
        LIMIT 200
        """
        df = pd.read_sql(query, self.conn, params=(date,))

        if len(df) < 50:
            return "bull_medium_vol"  # Default if insufficient data

        df = df.sort_values("date")

        # Calculate indicators
        df["sma_50"] = df["close"].rolling(50).mean()
        df["sma_200"] = df["close"].rolling(200).mean()
        df["returns"] = df["close"].pct_change()
        df["volatility_20d"] = df["returns"].rolling(20).std() * np.sqrt(252)

        latest = df.iloc[-1]

        # Trend
        if latest["close"] > latest["sma_50"] > latest["sma_200"]:
            trend = "bull"
        elif latest["close"] < latest["sma_50"] < latest["sma_200"]:
            trend = "bear"
        else:
            trend = "sideways"

        # Volatility
        vol = latest["volatility_20d"]
        if pd.isna(vol):
            vol_regime = "medium"
        elif vol < 0.12:
            vol_regime = "low"
        elif vol < 0.18:
            vol_regime = "medium"
        elif vol < 0.25:
            vol_regime = "high"
        else:
            vol_regime = "extreme"

        regime = f"{trend}_{vol_regime}_vol"
        logger.info(f"  Regime: {regime} (vol: {vol:.2%})")

        return regime

    def select_strategy(self, regime):
        """
        Select strategy based on regime (rule-based)
        Matches the logic from meta_strategy_selector.py
        """
        if "bull" in regime:
            if "low" in regime or "medium" in regime:
                strategy = "growth_largecap"
            else:
                strategy = "value_largecap"  # Defensive in high vol
        elif "bear" in regime:
            if "low" in regime or "medium" in regime:
                strategy = "dividend_strategy"
            else:
                strategy = "value_largecap"
        else:  # sideways
            if "low" in regime or "medium" in regime:
                strategy = "growth_midcap"
            else:
                strategy = "dividend_strategy"

        logger.info(f"  Selected strategy: {strategy}")
        return strategy

    def generate_target_portfolio(self, strategy, target_value, date):
        """
        Generate target portfolio for strategy using ML models or mock
        """
        if self.use_real_models and self.portfolio_generator:
            # Use real ML models
            portfolio_weights = self.portfolio_generator.generate_portfolio(
                strategy=strategy,
                total_value=target_value,
                as_of_date=date,
                use_rl=True,  # Enable RL for optimal weight allocation (falls back to equal weight if no model)
                top_n=50,
                max_position=0.10,
            )
            if portfolio_weights:
                # Convert weight-based format to expected format with prices
                # portfolio_weights is {ticker: weight}
                # Need to convert to {ticker: {'weight': float, 'target_value': float, 'price': float}}

                tickers = list(portfolio_weights.keys())
                prices = self.get_market_prices(date, tickers)

                target_portfolio = {}
                for ticker, weight in portfolio_weights.items():
                    if ticker in prices:
                        target_portfolio[ticker] = {
                            "weight": weight,
                            "target_value": target_value * weight,
                            "price": prices[ticker],
                        }
                    else:
                        logger.warning(f"  No price available for {ticker} on {date}, skipping")

                # Renormalize weights if some tickers were skipped
                if target_portfolio:
                    total_weight = sum(p["weight"] for p in target_portfolio.values())
                    if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
                        for ticker in target_portfolio:
                            target_portfolio[ticker]["weight"] /= total_weight
                            target_portfolio[ticker]["target_value"] = (
                                target_value * target_portfolio[ticker]["weight"]
                            )

                logger.info(f"  Target portfolio: {len(target_portfolio)} positions (ML-generated)")
                return target_portfolio

            # Fallback to mock if ML fails
            logger.warning(f"ML models failed for {strategy}, using mock")

        # Mock portfolios (fallback)
        mock_portfolios = {
            "growth_largecap": [
                "AAPL",
                "MSFT",
                "GOOGL",
                "AMZN",
                "NVDA",
                "META",
                "TSLA",
                "NFLX",
                "AMD",
                "CRM",
            ],
            "growth_midcap": [
                "SQ",
                "SHOP",
                "DDOG",
                "SNOW",
                "NET",
                "CRWD",
                "ZS",
                "OKTA",
                "TWLO",
                "DOCU",
            ],
            "growth_smallcap": [
                "BILL",
                "FROG",
                "UPST",
                "PATH",
                "OPEN",
                "SOFI",
                "AFRM",
                "HOOD",
                "COIN",
                "RBLX",
            ],
            "value_largecap": ["JPM", "BAC", "WFC", "XOM", "CVX", "JNJ", "PG", "KO", "PFE", "MRK"],
            "value_midcap": [
                "KEY",
                "FITB",
                "RF",
                "HBAN",
                "MTB",
                "CFG",
                "ZION",
                "CMA",
                "FHN",
                "ONB",
            ],
            "value_smallcap": [
                "UBSI",
                "WAFD",
                "CATY",
                "FFIN",
                "NWBI",
                "INDB",
                "BHLB",
                "FIBK",
                "TOWN",
                "FULT",
            ],
            "dividend_strategy": ["T", "VZ", "IBM", "ABBV", "BMY", "MO", "SO", "D", "DUK", "KMI"],
        }

        tickers = mock_portfolios.get(strategy, mock_portfolios["value_largecap"])

        # Get prices for available tickers
        prices = self.get_market_prices(date, tickers)
        available_tickers = [t for t in tickers if t in prices]

        if not available_tickers:
            logger.warning(f"  No prices available for {strategy} tickers on {date}")
            return {}

        # Equal weight portfolio
        weight_per_ticker = 1.0 / len(available_tickers)

        target_portfolio = {}
        for ticker in available_tickers:
            target_portfolio[ticker] = {
                "weight": weight_per_ticker,
                "target_value": target_value * weight_per_ticker,
                "price": prices[ticker],
            }

        logger.info(f"  Target portfolio: {len(target_portfolio)} positions")
        return target_portfolio

    def calculate_trades(self, date, target_portfolio):
        """Calculate required trades to reach target portfolio"""
        trades = []

        # Current positions value
        current_tickers = set(self.positions.keys())
        target_tickers = set(target_portfolio.keys())

        # Sells (positions to close or reduce)
        for ticker in current_tickers:
            target_value = target_portfolio.get(ticker, {}).get("target_value", 0)
            current_value = self.positions[ticker]["market_value"]

            if target_value < current_value - 100:  # Sell if difference > $100
                quantity_to_sell = self.positions[ticker]["quantity"]
                if target_value > 0:
                    # Partial sell
                    price = self.positions[ticker]["current_price"]
                    quantity_to_sell = (current_value - target_value) / price

                trades.append(
                    {
                        "ticker": ticker,
                        "side": "SELL",
                        "quantity": quantity_to_sell,
                        "price": self.positions[ticker]["current_price"],
                        "value": quantity_to_sell * self.positions[ticker]["current_price"],
                    }
                )

        # Buys (new positions or additions)
        for ticker, target in target_portfolio.items():
            current_value = 0
            if ticker in self.positions:
                current_value = self.positions[ticker]["market_value"]

            target_value = target["target_value"]

            if target_value > current_value + 100:  # Buy if difference > $100
                quantity_to_buy = (target_value - current_value) / target["price"]

                trades.append(
                    {
                        "ticker": ticker,
                        "side": "BUY",
                        "quantity": quantity_to_buy,
                        "price": target["price"],
                        "value": quantity_to_buy * target["price"],
                    }
                )

        return trades

    def execute_trades(self, date, trades):
        """Execute trades and update positions"""
        for trade in trades:
            ticker = trade["ticker"]
            side = trade["side"]
            quantity = trade["quantity"]
            price = trade["price"]
            value = quantity * price

            if side == "SELL":
                if ticker in self.positions:
                    # Sell position
                    position = self.positions[ticker]
                    sell_value = min(quantity, position["quantity"]) * price
                    self.cash += sell_value

                    # Update or remove position
                    position["quantity"] -= quantity
                    if position["quantity"] <= 0:
                        del self.positions[ticker]

                    self.trade_log.append(
                        {
                            "date": date,
                            "ticker": ticker,
                            "side": "SELL",
                            "quantity": quantity,
                            "price": price,
                            "value": sell_value,
                        }
                    )

            elif side == "BUY":
                # Check if we have enough cash
                if value <= self.cash:
                    if ticker not in self.positions:
                        self.positions[ticker] = {
                            "quantity": 0,
                            "avg_cost": price,
                            "current_price": price,
                            "market_value": 0,
                        }

                    # Update position
                    position = self.positions[ticker]
                    old_quantity = position["quantity"]
                    old_cost = position["avg_cost"]

                    new_quantity = old_quantity + quantity
                    new_avg_cost = ((old_quantity * old_cost) + (quantity * price)) / new_quantity

                    position["quantity"] = new_quantity
                    position["avg_cost"] = new_avg_cost
                    position["current_price"] = price
                    position["market_value"] = new_quantity * price

                    self.cash -= value

                    self.trade_log.append(
                        {
                            "date": date,
                            "ticker": ticker,
                            "side": "BUY",
                            "quantity": quantity,
                            "price": price,
                            "value": value,
                        }
                    )

    def rebalance(self, date):
        """Execute full rebalancing process"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Rebalancing on {date}")

        # Update current portfolio value
        portfolio_value = self.update_portfolio_value(date)
        logger.info(f"  Portfolio value: ${portfolio_value:,.2f}")
        logger.info(f"  Cash: ${self.cash:,.2f}")
        logger.info(f"  Positions: {len(self.positions)}")

        # Detect market regime
        regime = self.detect_market_regime(date)

        # Select strategy
        strategy = self.select_strategy(regime)

        # Generate target portfolio
        target_portfolio = self.generate_target_portfolio(strategy, portfolio_value, date)

        # Calculate trades
        trades = self.calculate_trades(date, target_portfolio)
        logger.info(
            f"  Trades: {len(trades)} ({sum(1 for t in trades if t['side']=='BUY')} buys, {sum(1 for t in trades if t['side']=='SELL')} sells)"
        )

        # Execute trades
        self.execute_trades(date, trades)

        # Update portfolio value after trades
        new_value = self.update_portfolio_value(date)

        # Log rebalancing event
        self.rebalancing_log.append(
            {
                "date": date,
                "regime": regime,
                "strategy": strategy,
                "pre_rebalance_value": portfolio_value,
                "post_rebalance_value": new_value,
                "num_trades": len(trades),
                "num_positions": len(self.positions),
            }
        )

    def run(self, start_date="2015-01-01", end_date="2025-10-30"):
        """
        Run complete backtest

        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
        """
        logger.info("=" * 80)
        logger.info("AUTONOMOUS FUND BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        logger.info(f"Rebalance frequency: {self.rebalance_frequency}")
        logger.info("=" * 80)

        # Get trading days
        trading_days = self.get_trading_days(start_date, end_date)
        logger.info(f"\nTotal trading days: {len(trading_days)}")

        # Get rebalance dates
        rebalance_dates = self.get_rebalance_dates(trading_days)
        logger.info(f"Rebalance dates: {len(rebalance_dates)}")

        # Run backtest
        for i, date in enumerate(trading_days):
            # Rebalance if needed
            if date in rebalance_dates:
                self.rebalance(date)
            else:
                # Daily mark-to-market
                self.update_portfolio_value(date)

            # Record daily equity
            self.equity_curve.append(
                {
                    "date": date,
                    "portfolio_value": self.portfolio_value,
                    "cash": self.cash,
                    "positions_value": self.portfolio_value - self.cash,
                }
            )

            # Calculate daily return
            if len(self.equity_curve) > 1:
                prev_value = self.equity_curve[-2]["portfolio_value"]
                daily_return = (self.portfolio_value / prev_value) - 1
                self.daily_returns.append(daily_return)

            # Progress update
            if (i + 1) % 250 == 0:  # Every ~year
                logger.info(
                    f"Progress: {i+1}/{len(trading_days)} days ({(i+1)/len(trading_days)*100:.1f}%)"
                )

        # Generate report
        return self.generate_report()

    def generate_report(self):
        """Generate comprehensive performance report"""
        equity_df = pd.DataFrame(self.equity_curve)
        returns_series = pd.Series(self.daily_returns)

        # Calculate metrics
        final_value = equity_df["portfolio_value"].iloc[-1]
        total_return = (final_value / self.initial_capital) - 1

        years = len(equity_df) / 252
        cagr = ((final_value / self.initial_capital) ** (1 / years)) - 1

        # Calculate max drawdown
        cummax = equity_df["portfolio_value"].cummax()
        drawdown = (equity_df["portfolio_value"] - cummax) / cummax
        max_drawdown = drawdown.min()

        # Risk metrics
        sharpe_ratio = (
            (returns_series.mean() / returns_series.std()) * np.sqrt(252)
            if returns_series.std() > 0
            else 0
        )
        sortino_ratio = (
            (returns_series.mean() / returns_series[returns_series < 0].std()) * np.sqrt(252)
            if len(returns_series[returns_series < 0]) > 0
            else 0
        )

        # Win rate
        win_rate = (returns_series > 0).mean()

        # Volatility
        annual_volatility = returns_series.std() * np.sqrt(252)

        report = {
            "period": {
                "start_date": equity_df["date"].iloc[0],
                "end_date": equity_df["date"].iloc[-1],
                "total_days": len(equity_df),
                "years": years,
            },
            "returns": {
                "total_return": total_return,
                "cagr": cagr,
                "best_day": returns_series.max() if len(returns_series) > 0 else 0,
                "worst_day": returns_series.min() if len(returns_series) > 0 else 0,
            },
            "risk": {
                "max_drawdown": max_drawdown,
                "annual_volatility": annual_volatility,
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
            },
            "trading": {
                "num_rebalances": len(self.rebalancing_log),
                "num_trades": len(self.trade_log),
                "win_rate": win_rate,
                "avg_positions": np.mean([r["num_positions"] for r in self.rebalancing_log]),
            },
            "final_state": {
                "initial_capital": self.initial_capital,
                "final_value": final_value,
                "cash": self.cash,
                "positions_value": final_value - self.cash,
                "num_positions": len(self.positions),
            },
        }

        return report, equity_df

    def print_report(self, report):
        """Print formatted report"""
        logger.info("\n" + "=" * 80)
        logger.info("BACKTEST RESULTS")
        logger.info("=" * 80)

        logger.info("\nPERIOD:")
        logger.info(f"  Start: {report['period']['start_date']}")
        logger.info(f"  End: {report['period']['end_date']}")
        logger.info(
            f"  Duration: {report['period']['years']:.1f} years ({report['period']['total_days']} days)"
        )

        logger.info("\nRETURNS:")
        logger.info(f"  Total Return: {report['returns']['total_return']:.2%}")
        logger.info(f"  CAGR: {report['returns']['cagr']:.2%}")
        logger.info(f"  Best Day: {report['returns']['best_day']:.2%}")
        logger.info(f"  Worst Day: {report['returns']['worst_day']:.2%}")

        logger.info("\nRISK:")
        logger.info(f"  Max Drawdown: {report['risk']['max_drawdown']:.2%}")
        logger.info(f"  Annual Volatility: {report['risk']['annual_volatility']:.2%}")
        logger.info(f"  Sharpe Ratio: {report['risk']['sharpe_ratio']:.2f}")
        logger.info(f"  Sortino Ratio: {report['risk']['sortino_ratio']:.2f}")

        logger.info("\nTRADING:")
        logger.info(f"  Rebalances: {report['trading']['num_rebalances']}")
        logger.info(f"  Total Trades: {report['trading']['num_trades']}")
        logger.info(f"  Win Rate: {report['trading']['win_rate']:.2%}")
        logger.info(f"  Avg Positions: {report['trading']['avg_positions']:.1f}")

        logger.info("\nFINAL STATE:")
        logger.info(f"  Initial Capital: ${report['final_state']['initial_capital']:,.2f}")
        logger.info(f"  Final Value: ${report['final_state']['final_value']:,.2f}")
        logger.info(f"  Cash: ${report['final_state']['cash']:,.2f}")
        logger.info(f"  Positions Value: ${report['final_state']['positions_value']:,.2f}")
        logger.info(f"  Current Positions: {report['final_state']['num_positions']}")

        logger.info("\n" + "=" * 80)

    def close(self):
        self.conn.close()


def main():
    """Run autonomous backtest"""
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Fund Backtest")
    parser.add_argument("--start-date", default="2015-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default="2025-10-30", help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--capital",
        type=float,
        default=None,
        help="Initial capital (if not specified, fetches from paper_accounts)",
    )
    parser.add_argument(
        "--client-id",
        type=int,
        default=None,
        help="Client ID to fetch actual balance from paper_accounts",
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default=None,
        help="Account ID/hash to fetch actual balance from paper_accounts",
    )
    parser.add_argument(
        "--frequency",
        choices=["monthly", "quarterly"],
        default="monthly",
        help="Rebalance frequency",
    )
    parser.add_argument(
        "--mock", action="store_true", help="Use mock portfolios instead of real ML models"
    )
    args = parser.parse_args()

    backtest = AutonomousBacktest(
        initial_capital=args.capital,
        client_id=args.client_id,
        account_id=args.account_id,
        rebalance_frequency=args.frequency,
        use_real_models=not args.mock,
    )

    try:
        report, equity_df = backtest.run(start_date=args.start_date, end_date=args.end_date)

        backtest.print_report(report)

        # Save results
        output_dir = Path(__file__).parent / "results"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        equity_df.to_csv(output_dir / f"equity_curve_{timestamp}.csv", index=False)

        with open(output_dir / f"report_{timestamp}.json", "w") as f:
            # Convert dates to strings for JSON serialization
            json_report = report.copy()
            json_report["period"]["start_date"] = str(json_report["period"]["start_date"])
            json_report["period"]["end_date"] = str(json_report["period"]["end_date"])
            json.dump(json_report, f, indent=2)

        logger.info(f"\nResults saved to {output_dir}")

        return 0

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        backtest.close()


if __name__ == "__main__":
    sys.exit(main())
