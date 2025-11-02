/*
 * BUILD CLEAN ML TRAINING VIEW - Fix Root Causes
 *
 * Strategy: Filter out bad data instead of capping
 * - Exclude penny stocks (< $0.50)
 * - Exclude extreme single-day moves (> 200%)
 * - Works with actual EMA/MACD pivot schemas
 */

DROP MATERIALIZED VIEW IF EXISTS ml_training_features CASCADE;

CREATE MATERIALIZED VIEW ml_training_features AS
WITH clean_bars AS (
    -- Step 1: Filter out low-quality data and compute forward returns
    SELECT
        b.*,
        LAG(b.close) OVER (PARTITION BY b.ticker ORDER BY b.date) as prev_close,
        LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) as future_close_20d
    FROM daily_bars b
    WHERE b.close >= 0.50  -- Exclude penny stocks
      AND b.volume > 0     -- Exclude zero-volume days
      AND b.date >= '2010-01-01'  -- Need lookback period
),
filtered_bars AS (
    -- Step 2: Exclude extreme single-day moves (likely bad data/splits)
    SELECT *
    FROM clean_bars
    WHERE prev_close IS NULL  -- Keep first row
       OR ABS((close - prev_close) / NULLIF(prev_close, 0)) <= 2.0  -- Max 200% single-day
)
SELECT
    -- Identifiers
    b.ticker,
    b.date,

    -- PRICE FEATURES
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

    -- EMA features (pivot from ema table)
    ema12.value as ema_12,
    ema26.value as ema_26,
    ema50.value as ema_50,
    ema200.value as ema_200,
    b.close / NULLIF(ema50.value, 0) - 1 as price_vs_ema50,
    b.close / NULLIF(ema200.value, 0) - 1 as price_vs_ema200,

    -- MACD features (from macd table)
    macd.macd_value as macd_line,
    macd.signal_value as macd_signal,
    macd.histogram_value as macd_histogram,
    macd.macd_value - macd.signal_value as macd_signal_diff,
    CASE WHEN macd.histogram_value > 0 THEN 1 ELSE 0 END as macd_positive,

    -- FUNDAMENTAL FEATURES (from ratios table)
    r.price_to_earnings as pe_ratio,
    r.price_to_book as pb_ratio,
    r.price_to_sales as ps_ratio,
    r.price_to_cash_flow as pcf_ratio,
    r.price_to_free_cash_flow as p_fcf_ratio,
    r.ev_to_ebitda,
    r.ev_to_sales,
    r.return_on_equity as roe,
    r.return_on_assets as roa,
    r.current as current_ratio,
    r.quick as quick_ratio,
    r.cash as cash_ratio,
    r.debt_to_equity,
    r.dividend_yield,
    r.earnings_per_share as eps,
    r.free_cash_flow,
    -- Calculate market_cap from ticker_overview shares outstanding * current price
    -- Falls back to ratios.market_cap if shares outstanding not available
    COALESCE(
        t.share_class_shares_outstanding * b.close,
        r.market_cap
    ) as market_cap,
    r.enterprise_value,
    r.average_volume,

    -- TARGET: Forward 20-day return (cleaned)
    CASE
        WHEN b.future_close_20d IS NULL THEN NULL
        WHEN b.future_close_20d < 0.50 THEN NULL  -- Future penny stock
        WHEN ABS((b.future_close_20d - b.close) / NULLIF(b.close, 0)) > 2.0 THEN NULL  -- Extreme future move
        ELSE (b.future_close_20d - b.close) / NULLIF(b.close, 0)
    END as target_return

FROM filtered_bars b

-- Join EMA indicators (pivot structure)
LEFT JOIN ema ema12 ON b.ticker = ema12.ticker
    AND b.date = ema12.date
    AND ema12.window_size = 12
    AND ema12.series_type = 'close'
LEFT JOIN ema ema26 ON b.ticker = ema26.ticker
    AND b.date = ema26.date
    AND ema26.window_size = 26
    AND ema26.series_type = 'close'
LEFT JOIN ema ema50 ON b.ticker = ema50.ticker
    AND b.date = ema50.date
    AND ema50.window_size = 50
    AND ema50.series_type = 'close'
LEFT JOIN ema ema200 ON b.ticker = ema200.ticker
    AND b.date = ema200.date
    AND ema200.window_size = 200
    AND ema200.series_type = 'close'

-- Join MACD indicators
LEFT JOIN macd ON b.ticker = macd.ticker
    AND b.date = macd.date
    AND macd.short_window = 12
    AND macd.long_window = 26
    AND macd.signal_window = 9
    AND macd.series_type = 'close'

-- Join fundamentals (latest as of date)
LEFT JOIN LATERAL (
    SELECT *
    FROM ratios r2
    WHERE r2.ticker = b.ticker
      AND r2.date <= b.date
    ORDER BY r2.date DESC
    LIMIT 1
) r ON true

-- Join ticker_overview for shares outstanding (for market cap calculation)
LEFT JOIN ticker_overview t ON b.ticker = t.ticker

WHERE b.date >= '2015-01-01'  -- Final training period

WINDOW w AS (PARTITION BY b.ticker ORDER BY b.date);

-- Create indices
CREATE INDEX idx_ml_features_ticker_date ON ml_training_features(ticker, date);
CREATE INDEX idx_ml_features_date ON ml_training_features(date);
CREATE INDEX idx_ml_features_target ON ml_training_features(target_return) WHERE target_return IS NOT NULL;

-- Analyze
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
    extreme_count BIGINT;
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

    SELECT COUNT(*)
    INTO extreme_count
    FROM ml_training_features
    WHERE target_return IS NOT NULL
      AND ABS(target_return) > 1.0;  -- More than 100%

    RAISE NOTICE '================================================================';
    RAISE NOTICE 'ML TRAINING FEATURES - CLEAN DATA (ROOT CAUSE FIX)';
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Total rows: %', total_rows;
    RAISE NOTICE 'Rows with target: %', rows_with_target;
    RAISE NOTICE 'Unique tickers: %', unique_tickers;
    RAISE NOTICE 'Date range: % to %', min_date, max_date;
    RAISE NOTICE '';
    RAISE NOTICE 'Target Return Statistics:';
    RAISE NOTICE '  Min: % (%.2f%%)', min_return, min_return * 100;
    RAISE NOTICE '  Max: % (%.2f%%)', max_return, max_return * 100;
    RAISE NOTICE '  Mean: % (%.2f%%)', avg_return, avg_return * 100;
    RAISE NOTICE '  Std Dev: % (%.2f%%)', stddev_return, stddev_return * 100;
    RAISE NOTICE '';
    RAISE NOTICE 'Data Quality:';
    RAISE NOTICE '  Rows with |return| > 100%%: %', extreme_count;
    RAISE NOTICE '  ✅ Penny stocks excluded (price < $0.50)';
    RAISE NOTICE '  ✅ Extreme moves excluded (single-day > 200%%)';
    RAISE NOTICE '  ✅ Zero volume days excluded';
    RAISE NOTICE '================================================================';
END $$;
