"""
Portfolio Strategy Configuration
All criteria from CLAUDE.md for Dividend, Growth, and Value strategies
"""

# Market Cap Definitions
MARKET_CAP_RANGES = {
    "large_cap": {"name": "Large Cap", "min": 10_000_000_000, "max": None},  # $10B+
    "mid_cap": {"name": "Mid Cap", "min": 2_000_000_000, "max": 10_000_000_000},  # $2B  # $10B
    "small_cap": {"name": "Small Cap", "min": 300_000_000, "max": 2_000_000_000},  # $300M  # $2B
}

# Universal Filters (Applied to ALL Portfolios)
UNIVERSAL_FILTERS = {
    "stock_type": "Common Stock",
    "min_price": 5.00,  # Stock price > $5
    "min_avg_volume": 100_000,  # Minimum daily volume for liquidity
    "fundamental_quality": {
        "min_roe": 0.15,  # Return on Equity >= 15%
        "max_debt_to_equity": 2.0,  # Conservative leverage
        "positive_cash_flow": True,
        "min_altman_z": 2.6,  # Bankruptcy risk < 5%
    },
}

# Dividend Strategy Criteria
# Eligible: Large Cap, Mid Cap ONLY (no small cap)
DIVIDEND_CRITERIA = {
    "eligible_market_caps": ["large_cap", "mid_cap"],
    "rebalance_frequency": "annual",
    "position_count": 15,
    # Dividend Quality
    "min_dividend_yield": 0.03,  # Minimum 3% yield
    "max_dividend_yield": 0.12,  # Maximum 12% (safety threshold)
    "max_payout_ratio": 0.75,  # Max 75% payout for sustainability
    "min_dividend_growth_5yr": 0.05,  # 5% annual dividend growth
    "consecutive_years_paid": 10,  # 10+ years dividend history
    # Dividend Safety Metrics
    "min_interest_coverage": 3.0,  # EBIT / Interest >= 3x
    "min_free_cash_flow_coverage": 1.2,  # FCF covers dividends 1.2x
    # Quality Filters
    "dividend_aristocrat_preferred": True,  # Prefer 25+ year track record
    "max_sector_concentration": 2,  # Max 2 stocks per sector (15 stocks / 8 sectors)
    # Technical/News (optional for dividend - less strict)
    "min_sentiment_score": 0.0,  # Neutral or better
}

# Growth Strategy Criteria
# Eligible: Large Cap, Mid Cap, Small Cap
GROWTH_CRITERIA = {
    "eligible_market_caps": ["large_cap", "mid_cap", "small_cap"],
    "rebalance_frequency": "quarterly",
    "position_count": 15,
    # Growth Metrics
    "min_revenue_growth_3yr": 0.20,  # 20%+ revenue CAGR
    "min_earnings_growth_3yr": 0.25,  # 25%+ earnings CAGR
    "max_peg_ratio": 2.0,  # PEG ratio < 2.0 (GARP)
    # Price Action Criteria
    "price_action": {
        "near_historical_low_threshold": 0.20,  # Within 20% of 52-week low
        "breakout_volume_multiplier": 2.0,  # Volume > 2x average
        "rsi_range": (30, 70),  # Not overbought/oversold
        "macd_signal": "bullish_crossover",  # MACD line > signal line
    },
    # Moving Average Signals
    "ema_12_above_ema_26": True,  # Short-term momentum
    "price_above_sma_50": True,  # Above 50-day average
    # News Sentiment
    "min_sentiment_score": 0.3,  # Positive sentiment required (-1 to 1 scale)
    "sentiment_timeframe_days": 30,  # Last 30 days of news
    # Innovation & Market Position
    "market_share_growing": True,  # Expanding market presence
}

# Value Strategy Criteria
# Eligible: Large Cap, Mid Cap, Small Cap
VALUE_CRITERIA = {
    "eligible_market_caps": ["large_cap", "mid_cap", "small_cap"],
    "rebalance_frequency": "quarterly",
    "position_count": 15,
    # Value Metrics
    "max_pe_ratio": 15,  # P/E < 15 (below market average)
    "max_pb_ratio": 3.0,  # P/B < 3.0
    "max_ps_ratio": 2.0,  # P/S < 2.0
    "min_fcf_yield": 0.05,  # Free cash flow yield >= 5%
    # Margin of Safety
    "discount_to_intrinsic_value": 0.30,  # Trading 30%+ below intrinsic value
    # Price Action Criteria (same as growth but different RSI range)
    "price_action": {
        "near_historical_low_threshold": 0.20,  # Within 20% of 52-week low
        "breakout_volume_multiplier": 2.0,  # Volume > 2x average
        "rsi_range": (20, 50),  # Oversold to neutral
        "macd_signal": "bullish_crossover",  # MACD line > signal line
    },
    # Moving Average Signals
    "ema_12_above_ema_26": True,
    "price_above_sma_50": True,
    # News Sentiment
    "min_sentiment_score": 0.2,  # Positive or neutral sentiment
    "sentiment_timeframe_days": 30,
    # Catalyst Identification
    "value_catalyst_required": True,  # Turnaround, activist, M&A, etc.
}

# Risk Management Framework
RISK_MANAGEMENT = {
    # Position Limits
    "max_position_size": 0.10,  # 10% max per position
    "min_position_size": 0.04,  # 4% minimum (for 15 stocks ~6.67% average)
    # Stop Loss Rules
    "stop_loss_percentage": 0.15,  # 15% stop loss per position
    "portfolio_stop_loss": 0.20,  # 20% portfolio drawdown triggers review
    # Concentration Limits
    "max_sector_exposure": 0.30,  # 30% max per sector
    "min_sector_count": 5,  # Diversify across 5+ sectors
    # Correlation Limits
    "max_position_correlation": 0.7,  # Avoid highly correlated positions
    # Liquidity Requirements
    "min_daily_volume": 100_000,  # shares
    "max_position_as_adv": 0.05,  # Position <= 5% of avg daily volume
    # Volatility Targeting
    "target_portfolio_volatility": 0.15,  # 15% annualized
    "max_portfolio_volatility": 0.25,  # 25% ceiling
}

# Technical Indicator Thresholds
RSI_SIGNALS = {
    "oversold": 30,  # Buy signal for value
    "neutral_low": 40,
    "neutral_high": 60,
    "overbought": 70,  # Caution for growth
    "extreme_overbought": 80,  # Strong sell signal
}

MACD_SIGNALS = {
    "bullish_crossover": "MACD line crosses above signal line",
    "bearish_crossover": "MACD line crosses below signal line",
    "histogram_divergence": "Price vs MACD histogram mismatch",
    "zero_line_cross": "MACD crosses zero line",
}

MA_SIGNALS = {
    "golden_cross": "EMA-50 crosses above EMA-200 (bullish)",
    "death_cross": "EMA-50 crosses below EMA-200 (bearish)",
    "ema_12_26_bullish": "EMA-12 > EMA-26 (short-term momentum)",
    "price_above_sma_50": "Confirmation of uptrend",
    "price_above_sma_200": "Long-term bullish trend",
}

# Sentiment Score Thresholds (-1 to +1 scale)
SENTIMENT_THRESHOLDS = {
    "very_negative": -0.6,
    "negative": -0.2,
    "neutral": 0.0,
    "positive": 0.3,
    "very_positive": 0.6,
}

# Portfolio Configuration (8 total portfolios)
PORTFOLIO_CONFIG = {
    # Dividend Portfolios (2)
    "dividend_large": {
        "name": "Dividend - Large Cap",
        "strategy": "dividend",
        "market_cap": "large_cap",
        "criteria": DIVIDEND_CRITERIA,
    },
    "dividend_mid": {
        "name": "Dividend - Mid Cap",
        "strategy": "dividend",
        "market_cap": "mid_cap",
        "criteria": DIVIDEND_CRITERIA,
    },
    # Growth Portfolios (3)
    "growth_large": {
        "name": "Growth - Large Cap",
        "strategy": "growth",
        "market_cap": "large_cap",
        "criteria": GROWTH_CRITERIA,
    },
    "growth_mid": {
        "name": "Growth - Mid Cap",
        "strategy": "growth",
        "market_cap": "mid_cap",
        "criteria": GROWTH_CRITERIA,
    },
    "growth_small": {
        "name": "Growth - Small Cap",
        "strategy": "growth",
        "market_cap": "small_cap",
        "criteria": GROWTH_CRITERIA,
    },
    # Value Portfolios (3)
    "value_large": {
        "name": "Value - Large Cap",
        "strategy": "value",
        "market_cap": "large_cap",
        "criteria": VALUE_CRITERIA,
    },
    "value_mid": {
        "name": "Value - Mid Cap",
        "strategy": "value",
        "market_cap": "mid_cap",
        "criteria": VALUE_CRITERIA,
    },
    "value_small": {
        "name": "Value - Small Cap",
        "strategy": "value",
        "market_cap": "small_cap",
        "criteria": VALUE_CRITERIA,
    },
}
