/*
 * CLEAN ML TRAINING DATA - Fix Root Causes
 *
 * This script creates a materialized view with clean data by:
 * 1. Excluding penny stocks (close < $0.50)
 * 2. Excluding rows with extreme price jumps (likely bad data)
 * 3. Excluding rows where volume = 0 (likely stale/bad data)
 * 4. Computing forward returns only where data quality is good
 */

DROP MATERIALIZED VIEW IF EXISTS ml_training_features CASCADE;

CREATE MATERIALIZED VIEW ml_training_features AS
WITH clean_bars AS (
    -- Step 1: Filter out low-quality data
    SELECT
        b.*,
        LAG(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date) as prev_close,
        LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) as future_close
    FROM daily_bars b
    WHERE b.close >= 0.50  -- Exclude penny stocks (major filter!)
      AND b.volume > 0     -- Exclude zero-volume days (stale data)
      AND b.date >= '2010-01-01'  -- Start from 2010 for lookback
),
filtered_bars AS (
    -- Step 2: Exclude extreme single-day moves (likely bad data)
    SELECT *
    FROM clean_bars
    WHERE prev_close IS NULL  -- Keep first row for each ticker
       OR ABS((close - prev_close) / NULLIF(prev_close, 0)) <= 2.0  -- Max 200% single-day move
)
SELECT
    -- Identifiers
    b.ticker,
    b.date,

    -- PRICE FEATURES (20 features)
    b.open,
    b.high,
    b.low,
    b.close,
    b.volume,
    b.vwap,

    -- Returns
    (b.close - LAG(b.close, 1) OVER w) / NULLIF(LAG(b.close, 1) OVER w, 0) as return_1d,
    (b.close - LAG(b.close, 5) OVER w) / NULLIF(LAG(b.close, 5) OVER w, 0) as return_5d,
    (b.close - LAG(b.close, 20) OVER w) / NULLIF(LAG(b.close, 20) OVER w, 0) as return_20d,

    -- Volatility
    STDDEV(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) /
        NULLIF(AVG(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW), 0) as volatility_20d,

    -- Volume features
    b.volume / NULLIF(AVG(b.volume) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW), 0) as volume_ratio_20d,

    -- Price vs moving averages
    b.close / NULLIF(AVG(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW), 0) - 1 as price_vs_sma20,
    b.close / NULLIF(AVG(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 50 PRECEDING AND CURRENT ROW), 0) - 1 as price_vs_sma50,

    -- High/Low ranges
    (b.high - b.low) / NULLIF(b.close, 0) as daily_range,
    (MAX(b.high) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) -
     MIN(b.low) OVER (PARTITION BY b.ticker ORDER BY b.date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW)) /
     NULLIF(b.close, 0) as range_20d,

    -- TECHNICAL INDICATORS (11 features from separate tables)
    ema.ema_12,
    ema.ema_26,
    ema.ema_50,
    ema.ema_200,
    b.close / NULLIF(ema.ema_50, 0) - 1 as price_vs_ema50,
    b.close / NULLIF(ema.ema_200, 0) - 1 as price_vs_ema200,

    macd.macd_line,
    macd.signal_line,
    macd.histogram,
    macd.macd_line - macd.signal_line as macd_signal_diff,
    CASE WHEN macd.histogram > 0 THEN 1 ELSE 0 END as macd_positive,

    -- FUNDAMENTAL FEATURES (57 features)
    -- Valuation ratios
    r.pe_ratio,
    r.pb_ratio,
    r.ps_ratio,
    r.pcf_ratio,
    r.ev_to_ebitda,
    r.ev_to_sales,
    r.price_to_book_value,
    r.price_to_tangible_book,

    -- Profitability
    r.roe,
    r.roa,
    r.roic,
    r.gross_margin,
    r.operating_margin,
    r.profit_margin,
    r.ebitda_margin,

    -- Growth
    r.revenue_growth,
    r.earnings_growth,
    r.book_value_growth,
    r.fcf_growth,

    -- Financial health
    r.current_ratio,
    r.quick_ratio,
    r.debt_to_equity,
    r.debt_to_assets,
    r.interest_coverage,
    r.altman_z_score,

    -- Cash flow
    r.fcf_to_revenue,
    r.fcf_to_net_income,
    r.capex_to_revenue,
    r.capex_to_operating_cf,

    -- Dividends
    r.dividend_yield,
    r.payout_ratio,
    r.dividend_growth_rate,

    -- Efficiency
    r.asset_turnover,
    r.inventory_turnover,
    r.receivables_turnover,
    r.days_sales_outstanding,
    r.days_inventory_outstanding,
    r.cash_conversion_cycle,

    -- Per share
    r.eps,
    r.book_value_per_share,
    r.fcf_per_share,
    r.revenue_per_share,
    r.tangible_book_per_share,

    -- Market metrics
    r.market_cap,
    r.enterprise_value,
    r.shares_outstanding,
    r.float_shares,

    -- Balance sheet strength
    r.cash_and_equivalents,
    r.total_debt,
    r.net_debt,
    r.working_capital,
    r.tangible_assets,
    r.intangible_assets,
    r.goodwill,

    -- Additional
    r.beta,
    r.peg_ratio,

    -- TARGET: Forward 20-day return (cleaned)
    -- Only compute if future price exists and is reasonable
    CASE
        WHEN b.future_close IS NULL THEN NULL
        WHEN b.future_close < 0.50 THEN NULL  -- Future price too low
        WHEN ABS((b.future_close - b.close) / NULLIF(b.close, 0)) > 2.0 THEN NULL  -- Extreme future move (likely bad data)
        ELSE (b.future_close - b.close) / NULLIF(b.close, 0)
    END as target_return

FROM filtered_bars b

-- Join technical indicators
LEFT JOIN ema ON b.ticker = ema.ticker AND b.date = ema.date
LEFT JOIN macd ON b.ticker = macd.ticker AND b.date = macd.date

-- Join fundamental ratios (latest available as of date)
LEFT JOIN LATERAL (
    SELECT *
    FROM ratios r2
    WHERE r2.ticker = b.ticker
      AND r2.date <= b.date
    ORDER BY r2.date DESC
    LIMIT 1
) r ON true

WHERE b.date >= '2015-01-01'  -- Final training period

WINDOW w AS (PARTITION BY b.ticker ORDER BY b.date);

-- Create indices for fast queries
CREATE INDEX idx_ml_features_ticker_date ON ml_training_features(ticker, date);
CREATE INDEX idx_ml_features_date ON ml_training_features(date);
CREATE INDEX idx_ml_features_target ON ml_training_features(target_return) WHERE target_return IS NOT NULL;

-- Analyze for query optimization
ANALYZE ml_training_features;

-- Report statistics
DO $$
DECLARE
    total_rows BIGINT;
    rows_with_target BIGINT;
    unique_tickers INT;
    min_date DATE;
    max_date DATE;
    min_return NUMERIC;
    max_return NUMERIC;
    avg_return NUMERIC;
    stddev_return NUMERIC;
BEGIN
    SELECT
        COUNT(*),
        COUNT(target_return),
        COUNT(DISTINCT ticker),
        MIN(date),
        MAX(date)
    INTO total_rows, rows_with_target, unique_tickers, min_date, max_date
    FROM ml_training_features;

    SELECT
        MIN(target_return),
        MAX(target_return),
        AVG(target_return),
        STDDEV(target_return)
    INTO min_return, max_return, avg_return, stddev_return
    FROM ml_training_features
    WHERE target_return IS NOT NULL;

    RAISE NOTICE '================================================================';
    RAISE NOTICE 'ML TRAINING FEATURES - CLEAN DATA STATS';
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Total rows: %', total_rows;
    RAISE NOTICE 'Rows with target: %', rows_with_target;
    RAISE NOTICE 'Unique tickers: %', unique_tickers;
    RAISE NOTICE 'Date range: % to %', min_date, max_date;
    RAISE NOTICE '';
    RAISE NOTICE 'Target Return Statistics (AFTER CLEANING):';
    RAISE NOTICE '  Min: % (%.2f%%)', min_return, min_return * 100;
    RAISE NOTICE '  Max: % (%.2f%%)', max_return, max_return * 100;
    RAISE NOTICE '  Mean: % (%.2f%%)', avg_return, avg_return * 100;
    RAISE NOTICE '  Std Dev: % (%.2f%%)', stddev_return, stddev_return * 100;
    RAISE NOTICE '================================================================';
END $$;
