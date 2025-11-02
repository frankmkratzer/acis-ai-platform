-- ETF Daily Bars Table
-- Separate table for ETF data (SPY, VTV, VUG, VYM, etc.)

CREATE TABLE IF NOT EXISTS etf_bars (
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open NUMERIC(12,4),
    high NUMERIC(12,4),
    low NUMERIC(12,4),
    close NUMERIC(12,4),
    volume BIGINT,
    vwap NUMERIC(12,4),
    transactions INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_etf_bars_ticker ON etf_bars(ticker);
CREATE INDEX IF NOT EXISTS idx_etf_bars_date ON etf_bars(date);
CREATE INDEX IF NOT EXISTS idx_etf_bars_ticker_date ON etf_bars(ticker, date DESC);

-- Comments
COMMENT ON TABLE etf_bars IS 'Daily OHLCV data for ETFs used in backtesting and benchmarking';
COMMENT ON COLUMN etf_bars.ticker IS 'ETF ticker symbol (e.g., SPY, VTV, VUG, VYM)';
COMMENT ON COLUMN etf_bars.date IS 'Trading date';
COMMENT ON COLUMN etf_bars.vwap IS 'Volume-weighted average price';
COMMENT ON COLUMN etf_bars.transactions IS 'Number of transactions/trades for the day';
