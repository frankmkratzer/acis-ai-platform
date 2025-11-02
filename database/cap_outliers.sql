-- Cap outliers in ml_training_features materialized view
-- Realistic stock returns: -80% to +100% (extreme movements capped)

DROP MATERIALIZED VIEW IF EXISTS ml_training_features CASCADE;

CREATE MATERIALIZED VIEW ml_training_features AS
WITH features AS (
    SELECT
        b.ticker,
        b.date,

        -- Price features
        b.open,
        b.high,
        b.low,
        b.close,
        b.volume,
        b.vwap,

        -- Returns with OUTLIER CAPS: -0.80 to +1.00 (-80% to +100%)
        CASE
            WHEN r.return_1d > 1.0 THEN 1.0
            WHEN r.return_1d < -0.80 THEN -0.80
            ELSE r.return_1d
        END as return_1d,
        CASE
            WHEN r.return_5d > 1.0 THEN 1.0
            WHEN r.return_5d < -0.80 THEN -0.80
            ELSE r.return_5d
        END as return_5d,
        CASE
            WHEN r.return_20d > 1.0 THEN 1.0
            WHEN r.return_20d < -0.80 THEN -0.80
            ELSE r.return_20d
        END as return_20d,
        CASE
            WHEN r.return_60d > 1.0 THEN 1.0
            WHEN r.return_60d < -0.80 THEN -0.80
            ELSE r.return_60d
        END as return_60d,

        -- Volatility
        r.volatility_20d,
        r.volatility_60d,

        -- Volume indicators
        r.volume_ratio_5d,
        r.volume_ratio_20d,

        -- Technical indicators
        e.ema_12,
        e.ema_26,
        e.ema_50,
        e.ema_200,

        m.macd_value,
        m.signal_value,
        m.histogram,

        -- Fundamental ratios
        ra.pe_ratio,
        ra.pb_ratio,
        ra.ps_ratio,
        ra.pcf_ratio,
        ra.dividend_yield,
        ra.peg_ratio,
        ra.roe,
        ra.roa,
        ra.roic,
        ra.debt_to_equity,
        ra.current_ratio,
        ra.quick_ratio,
        ra.asset_turnover,
        ra.inventory_turnover,
        ra.receivables_turnover,
        ra.gross_margin,
        ra.operating_margin,
        ra.net_margin,
        ra.fcf_margin,
        ra.revenue_growth_yoy,
        ra.earnings_growth_yoy,
        ra.fcf_growth_yoy,

        -- Income statement
        inc.revenue,
        inc.gross_profit,
        inc.operating_income,
        inc.net_income,
        inc.eps_basic,
        inc.eps_diluted,
        inc.ebitda,

        -- Balance sheet
        bs.total_assets,
        bs.total_liabilities,
        bs.stockholders_equity,
        bs.total_debt,
        bs.cash_and_equivalents,
        bs.current_assets,
        bs.current_liabilities,

        -- Cash flow
        cf.operating_cash_flow,
        cf.investing_cash_flow,
        cf.financing_cash_flow,
        cf.free_cash_flow,
        cf.capex,

        -- TARGET: Forward 20-day return with CAPS at -50% to +50%
        -- This is more realistic for prediction targets
        CASE
            WHEN LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) IS NULL
                THEN NULL
            WHEN (LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) - b.close) / NULLIF(b.close, 0) > 0.50
                THEN 0.50
            WHEN (LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) - b.close) / NULLIF(b.close, 0) < -0.50
                THEN -0.50
            ELSE (LEAD(b.close, 20) OVER (PARTITION BY b.ticker ORDER BY b.date) - b.close) / NULLIF(b.close, 0)
        END as target_return

    FROM bars b
    LEFT JOIN returns r ON b.ticker = r.ticker AND b.date = r.date
    LEFT JOIN ema e ON b.ticker = e.ticker AND b.date = e.date
    LEFT JOIN macd m ON b.ticker = m.ticker AND b.date = m.date
    LEFT JOIN ratios ra ON b.ticker = ra.ticker AND b.date = ra.date
    LEFT JOIN income_statements inc ON b.ticker = inc.ticker AND b.date = inc.date
    LEFT JOIN balance_sheets bs ON b.ticker = bs.ticker AND b.date = bs.date
    LEFT JOIN cash_flow_statements cf ON b.ticker = cf.ticker AND b.date = cf.date
    WHERE b.date >= '2015-01-01'
)
SELECT * FROM features;

-- Create indexes for fast querying
CREATE INDEX idx_ml_features_ticker_date ON ml_training_features(ticker, date);
CREATE INDEX idx_ml_features_date ON ml_training_features(date);
CREATE INDEX idx_ml_features_target ON ml_training_features(target_return) WHERE target_return IS NOT NULL;

-- Analyze for query planning
ANALYZE ml_training_features;

-- Summary stats
SELECT
    'Total rows' as metric,
    COUNT(*)::text as value
FROM ml_training_features
UNION ALL
SELECT
    'Rows with targets' as metric,
    COUNT(*)::text as value
FROM ml_training_features
WHERE target_return IS NOT NULL
UNION ALL
SELECT
    'Min target' as metric,
    ROUND(MIN(target_return)::numeric, 4)::text as value
FROM ml_training_features
WHERE target_return IS NOT NULL
UNION ALL
SELECT
    'Max target' as metric,
    ROUND(MAX(target_return)::numeric, 4)::text as value
FROM ml_training_features
WHERE target_return IS NOT NULL
UNION ALL
SELECT
    'Median target' as metric,
    ROUND(percentile_cont(0.5) WITHIN GROUP (ORDER BY target_return)::numeric, 4)::text as value
FROM ml_training_features
WHERE target_return IS NOT NULL;
