-- Backfill market_cap in ml_training_features table
-- Calculate as shares_outstanding * close_price

-- First, verify we have the data we need
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN market_cap IS NULL THEN 1 END) as null_market_cap,
    MIN(date) as earliest_date,
    MAX(date) as latest_date
FROM ml_training_features;

-- Update market_cap using ticker_overview shares outstanding and daily close price
UPDATE ml_training_features f
SET market_cap = t.share_class_shares_outstanding * f.close
FROM ticker_overview t
WHERE f.ticker = t.ticker
  AND f.market_cap IS NULL
  AND t.share_class_shares_outstanding IS NOT NULL
  AND t.share_class_shares_outstanding > 0
  AND f.close IS NOT NULL
  AND f.close > 0;

-- Verify the update
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN market_cap IS NULL THEN 1 END) as null_market_cap,
    COUNT(CASE WHEN market_cap IS NOT NULL THEN 1 END) as has_market_cap,
    MIN(market_cap) as min_market_cap,
    MAX(market_cap) as max_market_cap,
    AVG(market_cap) as avg_market_cap
FROM ml_training_features;

-- Show date-wise coverage
SELECT
    date,
    COUNT(*) as total_tickers,
    COUNT(CASE WHEN market_cap IS NOT NULL THEN 1 END) as with_market_cap,
    ROUND(100.0 * COUNT(CASE WHEN market_cap IS NOT NULL THEN 1 END) / COUNT(*), 2) as coverage_pct
FROM ml_training_features
WHERE date >= '2020-01-01'
GROUP BY date
ORDER BY date DESC
LIMIT 20;
