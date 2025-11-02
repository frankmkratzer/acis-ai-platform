#!/usr/bin/env python3
"""
Stock Screener
Applies universal and strategy-specific filters to find portfolio candidates
"""
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.config import (
    DIVIDEND_CRITERIA,
    GROWTH_CRITERIA,
    MARKET_CAP_RANGES,
    RSI_SIGNALS,
    UNIVERSAL_FILTERS,
    VALUE_CRITERIA,
)
from utils import get_logger, get_psycopg2_connection

logger = get_logger(__name__)


class StockScreener:
    """Screen stocks based on universal and strategy-specific criteria"""

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_psycopg2_connection().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.__exit__(exc_type, exc_val, exc_tb)

    def get_universe(self, market_cap: str, as_of_date: Optional[date] = None) -> List[str]:
        """
        Get universe of tickers filtered by market cap

        Args:
            market_cap: 'large_cap', 'mid_cap', or 'small_cap'
            as_of_date: Date for filtering (default: today)

        Returns:
            List of ticker symbols
        """
        if as_of_date is None:
            as_of_date = date.today()

        cap_config = MARKET_CAP_RANGES[market_cap]
        min_cap = cap_config["min"]
        max_cap = cap_config["max"]

        query = """
            SELECT ticker
            FROM ticker_overview
            WHERE active = true
              AND type = %s
              AND market_cap >= %s
        """
        params = [UNIVERSAL_FILTERS["stock_type"], min_cap]

        if max_cap is not None:
            query += " AND market_cap < %s"
            params.append(max_cap)

        query += " ORDER BY ticker;"

        with self.conn.cursor() as cur:
            cur.execute(query, params)
            tickers = [row[0] for row in cur.fetchall()]

        logger.info(f"Found {len(tickers)} tickers in {cap_config['name']} universe")
        return tickers

    def apply_universal_filters(
        self, tickers: List[str], as_of_date: Optional[date] = None
    ) -> List[str]:
        """
        Apply universal filters to ticker list

        Filters:
        - Price > $5
        - Average volume > 100K
        - ROE >= 15%
        - Debt-to-Equity <= 2.0
        - Positive operating cash flow

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for filtering (default: today)

        Returns:
            Filtered list of tickers
        """
        if not tickers:
            return []

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Applying universal filters to {len(tickers)} tickers...")

        # Get latest price and volume data
        price_query = """
            WITH latest_prices AS (
                SELECT
                    ticker,
                    close as price,
                    volume,
                    date,
                    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                FROM daily_bars
                WHERE ticker = ANY(%s)
                  AND date <= %s
            ),
            avg_volumes AS (
                SELECT
                    ticker,
                    AVG(volume) as avg_volume
                FROM daily_bars
                WHERE ticker = ANY(%s)
                  AND date >= %s
                  AND date <= %s
                GROUP BY ticker
            )
            SELECT
                lp.ticker,
                lp.price,
                av.avg_volume
            FROM latest_prices lp
            JOIN avg_volumes av ON lp.ticker = av.ticker
            WHERE lp.rn = 1
              AND lp.price >= %s
              AND av.avg_volume >= %s;
        """

        lookback_date = as_of_date - timedelta(days=30)

        with self.conn.cursor() as cur:
            cur.execute(
                price_query,
                [
                    tickers,
                    as_of_date,
                    tickers,
                    lookback_date,
                    as_of_date,
                    UNIVERSAL_FILTERS["min_price"],
                    UNIVERSAL_FILTERS["min_avg_volume"],
                ],
            )
            price_passed = {row[0] for row in cur.fetchall()}

        logger.info(f"  Price/Volume filter: {len(price_passed)} passed")

        if not price_passed:
            return []

        # Get latest fundamental ratios
        ratios_query = """
            SELECT
                ticker,
                return_on_equity,
                debt_to_equity_ratio,
                operating_cash_flow_ratio
            FROM ratios
            WHERE ticker = ANY(%s)
              AND period_ending <= %s
            ORDER BY ticker, period_ending DESC;
        """

        fundamentals_passed = set()
        with self.conn.cursor() as cur:
            cur.execute(ratios_query, [list(price_passed), as_of_date])

            seen_tickers = set()
            for row in cur.fetchall():
                ticker, roe, debt_to_equity, opcf_ratio = row

                # Only take latest record per ticker
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Check fundamental quality filters
                if roe is None or debt_to_equity is None or opcf_ratio is None:
                    continue

                if (
                    roe >= UNIVERSAL_FILTERS["fundamental_quality"]["min_roe"]
                    and debt_to_equity
                    <= UNIVERSAL_FILTERS["fundamental_quality"]["max_debt_to_equity"]
                    and opcf_ratio > 0
                ):  # Positive cash flow
                    fundamentals_passed.add(ticker)

        logger.info(f"  Fundamental filter: {len(fundamentals_passed)} passed")
        logger.info(f"Total passed universal filters: {len(fundamentals_passed)}")

        return sorted(list(fundamentals_passed))

    def apply_dividend_filters(
        self, tickers: List[str], as_of_date: Optional[date] = None
    ) -> List[str]:
        """
        Apply dividend-specific filters

        Filters:
        - Dividend yield: 3-12%
        - Payout ratio <= 75%
        - 10+ years dividend history
        - Positive FCF coverage

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for filtering (default: today)

        Returns:
            Filtered list of tickers
        """
        if not tickers:
            return []

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Applying dividend filters to {len(tickers)} tickers...")

        # Check dividend metrics from ratios table
        query = """
            SELECT
                r.ticker,
                r.dividend_yield,
                r.payout_ratio,
                r.debt_service_coverage_ratio
            FROM ratios r
            WHERE r.ticker = ANY(%s)
              AND r.period_ending <= %s
            ORDER BY r.ticker, r.period_ending DESC;
        """

        passed_tickers = set()
        with self.conn.cursor() as cur:
            cur.execute(query, [tickers, as_of_date])

            seen_tickers = set()
            for row in cur.fetchall():
                ticker, div_yield, payout_ratio, debt_coverage = row

                # Only take latest record per ticker
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Check dividend criteria
                if div_yield is None or payout_ratio is None:
                    continue

                min_yield = DIVIDEND_CRITERIA["min_dividend_yield"]
                max_yield = DIVIDEND_CRITERIA["max_dividend_yield"]
                max_payout = DIVIDEND_CRITERIA["max_payout_ratio"]

                if min_yield <= div_yield <= max_yield and payout_ratio <= max_payout:
                    passed_tickers.add(ticker)

        # Check dividend history (at least 10 years)
        if passed_tickers:
            history_query = """
                SELECT ticker, COUNT(DISTINCT EXTRACT(YEAR FROM ex_dividend_date)) as years_paid
                FROM dividends
                WHERE ticker = ANY(%s)
                  AND ex_dividend_date >= %s
                  AND ex_dividend_date <= %s
                GROUP BY ticker
                HAVING COUNT(DISTINCT EXTRACT(YEAR FROM ex_dividend_date)) >= %s;
            """

            lookback_years = DIVIDEND_CRITERIA["consecutive_years_paid"]
            start_date = as_of_date - timedelta(days=lookback_years * 365)

            with self.conn.cursor() as cur:
                cur.execute(
                    history_query, [list(passed_tickers), start_date, as_of_date, lookback_years]
                )
                history_passed = {row[0] for row in cur.fetchall()}

            passed_tickers = passed_tickers.intersection(history_passed)

        logger.info(f"Total passed dividend filters: {len(passed_tickers)}")
        return sorted(list(passed_tickers))

    def apply_growth_filters(
        self, tickers: List[str], as_of_date: Optional[date] = None
    ) -> List[str]:
        """
        Apply growth-specific filters

        Filters:
        - Revenue growth >= 20% (3-year)
        - Earnings growth >= 25% (3-year)
        - PEG ratio < 2.0
        - EMA 12 > EMA 26
        - Price > SMA 50
        - RSI 30-70
        - Positive sentiment

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for filtering (default: today)

        Returns:
            Filtered list of tickers
        """
        if not tickers:
            return []

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Applying growth filters to {len(tickers)} tickers...")

        # Check growth metrics from ratios
        query = """
            SELECT
                ticker,
                revenue_growth,
                earnings_growth,
                peg_ratio
            FROM ratios
            WHERE ticker = ANY(%s)
              AND period_ending <= %s
            ORDER BY ticker, period_ending DESC;
        """

        passed_tickers = set()
        with self.conn.cursor() as cur:
            cur.execute(query, [tickers, as_of_date])

            seen_tickers = set()
            for row in cur.fetchall():
                ticker, rev_growth, earn_growth, peg = row

                # Only take latest record per ticker
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Check growth criteria
                if rev_growth is None or earn_growth is None or peg is None:
                    continue

                min_rev = GROWTH_CRITERIA["min_revenue_growth_3yr"]
                min_earn = GROWTH_CRITERIA["min_earnings_growth_3yr"]
                max_peg = GROWTH_CRITERIA["max_peg_ratio"]

                if rev_growth >= min_rev and earn_growth >= min_earn and peg < max_peg:
                    passed_tickers.add(ticker)

        logger.info(f"  Growth metrics filter: {len(passed_tickers)} passed")

        # Apply technical filters
        passed_tickers = self._apply_technical_filters(
            list(passed_tickers), as_of_date, GROWTH_CRITERIA["price_action"]["rsi_range"]
        )

        # Apply sentiment filter
        passed_tickers = self._apply_sentiment_filter(
            passed_tickers, as_of_date, GROWTH_CRITERIA["min_sentiment_score"]
        )

        logger.info(f"Total passed growth filters: {len(passed_tickers)}")
        return sorted(list(passed_tickers))

    def apply_value_filters(
        self, tickers: List[str], as_of_date: Optional[date] = None
    ) -> List[str]:
        """
        Apply value-specific filters

        Filters:
        - P/E < 15
        - P/B < 3.0
        - P/S < 2.0
        - FCF yield >= 5%
        - EMA 12 > EMA 26
        - Price > SMA 50
        - RSI 20-50
        - Neutral+ sentiment

        Args:
            tickers: List of ticker symbols
            as_of_date: Date for filtering (default: today)

        Returns:
            Filtered list of tickers
        """
        if not tickers:
            return []

        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Applying value filters to {len(tickers)} tickers...")

        # Check value metrics from ratios
        query = """
            SELECT
                ticker,
                price_to_earnings_ratio,
                price_to_book_ratio,
                price_to_sales_ratio,
                free_cash_flow_per_share,
                close_price
            FROM ratios
            WHERE ticker = ANY(%s)
              AND period_ending <= %s
            ORDER BY ticker, period_ending DESC;
        """

        passed_tickers = set()
        with self.conn.cursor() as cur:
            cur.execute(query, [tickers, as_of_date])

            seen_tickers = set()
            for row in cur.fetchall():
                ticker, pe, pb, ps, fcf_per_share, price = row

                # Only take latest record per ticker
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)

                # Check value criteria
                if pe is None or pb is None or ps is None or fcf_per_share is None or price is None:
                    continue

                if price <= 0:
                    continue

                fcf_yield = fcf_per_share / price

                max_pe = VALUE_CRITERIA["max_pe_ratio"]
                max_pb = VALUE_CRITERIA["max_pb_ratio"]
                max_ps = VALUE_CRITERIA["max_ps_ratio"]
                min_fcf = VALUE_CRITERIA["min_fcf_yield"]

                if pe < max_pe and pb < max_pb and ps < max_ps and fcf_yield >= min_fcf:
                    passed_tickers.add(ticker)

        logger.info(f"  Value metrics filter: {len(passed_tickers)} passed")

        # Apply technical filters (different RSI range for value)
        passed_tickers = self._apply_technical_filters(
            list(passed_tickers), as_of_date, VALUE_CRITERIA["price_action"]["rsi_range"]
        )

        # Apply sentiment filter
        passed_tickers = self._apply_sentiment_filter(
            passed_tickers, as_of_date, VALUE_CRITERIA["min_sentiment_score"]
        )

        logger.info(f"Total passed value filters: {len(passed_tickers)}")
        return sorted(list(passed_tickers))

    def _apply_technical_filters(
        self, tickers: List[str], as_of_date: date, rsi_range: tuple
    ) -> List[str]:
        """Apply technical indicator filters"""
        if not tickers:
            return []

        # Get latest technical indicators
        tech_query = """
            WITH latest_data AS (
                SELECT
                    db.ticker,
                    db.close,
                    ema12.value as ema_12,
                    ema26.value as ema_26,
                    sma50.value as sma_50,
                    rsi14.value as rsi_14,
                    macd.macd_value,
                    macd.signal_value
                FROM daily_bars db
                LEFT JOIN ema ema12 ON db.ticker = ema12.ticker
                    AND db.date = ema12.date
                    AND ema12.window_size = 12
                LEFT JOIN ema ema26 ON db.ticker = ema26.ticker
                    AND db.date = ema26.date
                    AND ema26.window_size = 26
                LEFT JOIN sma sma50 ON db.ticker = sma50.ticker
                    AND db.date = sma50.date
                    AND sma50.window_size = 50
                LEFT JOIN rsi rsi14 ON db.ticker = rsi14.ticker
                    AND db.date = rsi14.date
                    AND rsi14.window_size = 14
                LEFT JOIN macd ON db.ticker = macd.ticker
                    AND db.date = macd.date
                WHERE db.ticker = ANY(%s)
                  AND db.date <= %s
                ORDER BY db.ticker, db.date DESC
            )
            SELECT DISTINCT ON (ticker)
                ticker, close, ema_12, ema_26, sma_50, rsi_14, macd_value, signal_value
            FROM latest_data
            WHERE ema_12 IS NOT NULL
              AND ema_26 IS NOT NULL
              AND sma_50 IS NOT NULL
              AND rsi_14 IS NOT NULL
              AND macd_value IS NOT NULL
              AND signal_value IS NOT NULL;
        """

        passed_tickers = set()
        with self.conn.cursor() as cur:
            cur.execute(tech_query, [tickers, as_of_date])

            for row in cur.fetchall():
                ticker, close, ema_12, ema_26, sma_50, rsi_14, macd_val, signal_val = row

                # Check technical criteria
                rsi_min, rsi_max = rsi_range

                if (
                    ema_12 > ema_26
                    and close > sma_50  # Short-term momentum
                    and rsi_min <= rsi_14 <= rsi_max  # Above 50-day average
                    and macd_val > signal_val  # RSI in range
                ):  # MACD bullish crossover
                    passed_tickers.add(ticker)

        logger.info(f"  Technical indicators filter: {len(passed_tickers)} passed")
        return sorted(list(passed_tickers))

    def _apply_sentiment_filter(
        self, tickers: List[str], as_of_date: date, min_score: float
    ) -> List[str]:
        """Apply news sentiment filter"""
        if not tickers:
            return []

        # Get recent news sentiment (last 30 days)
        lookback_date = as_of_date - timedelta(days=30)

        sentiment_query = """
            SELECT
                unnest(tickers) as ticker,
                AVG(CASE
                    WHEN sentiment = 'positive' THEN 0.6
                    WHEN sentiment = 'negative' THEN -0.6
                    WHEN sentiment = 'neutral' THEN 0.0
                    ELSE 0.0
                END) as avg_sentiment
            FROM news
            WHERE published_utc >= %s
              AND published_utc <= %s
              AND tickers && %s
            GROUP BY ticker
            HAVING AVG(CASE
                WHEN sentiment = 'positive' THEN 0.6
                WHEN sentiment = 'negative' THEN -0.6
                WHEN sentiment = 'neutral' THEN 0.0
                ELSE 0.0
            END) >= %s;
        """

        passed_tickers = set()
        with self.conn.cursor() as cur:
            cur.execute(sentiment_query, [lookback_date, as_of_date, tickers, min_score])
            passed_tickers = {row[0] for row in cur.fetchall()}

        logger.info(f"  Sentiment filter: {len(passed_tickers)} passed")
        return sorted(list(passed_tickers))

    def screen(
        self, strategy: str, market_cap: str, as_of_date: Optional[date] = None
    ) -> List[str]:
        """
        Run complete screening process

        Args:
            strategy: 'dividend', 'growth', or 'value'
            market_cap: 'large_cap', 'mid_cap', or 'small_cap'
            as_of_date: Date for filtering (default: today)

        Returns:
            List of ticker symbols passing all filters
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting {strategy.upper()} - {market_cap.upper()} screen")
        logger.info(f"{'='*60}")

        # Step 1: Get universe by market cap
        universe = self.get_universe(market_cap, as_of_date)

        # Step 2: Apply universal filters
        candidates = self.apply_universal_filters(universe, as_of_date)

        # Step 3: Apply strategy-specific filters
        if strategy == "dividend":
            candidates = self.apply_dividend_filters(candidates, as_of_date)
        elif strategy == "growth":
            candidates = self.apply_growth_filters(candidates, as_of_date)
        elif strategy == "value":
            candidates = self.apply_value_filters(candidates, as_of_date)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        logger.info(f"\nFinal candidates: {len(candidates)}")
        return candidates


if __name__ == "__main__":
    # Test the screener
    with StockScreener() as screener:
        # Test growth large cap
        candidates = screener.screen("growth", "large_cap")
        print(f"\nGrowth Large Cap Candidates: {len(candidates)}")
        if candidates:
            print("Sample tickers:", candidates[:10])
