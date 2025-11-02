-- Paper Trading Tables
-- Stores simulated trading account data for testing before going live

-- Paper trading accounts
CREATE TABLE IF NOT EXISTS paper_accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    cash_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
    buying_power DECIMAL(15, 2) NOT NULL DEFAULT 0,
    total_value DECIMAL(15, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Paper trading positions
CREATE TABLE IF NOT EXISTS paper_positions (
    account_id VARCHAR(50) NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL DEFAULT 0,
    avg_price DECIMAL(15, 4) NOT NULL,
    market_value DECIMAL(15, 2) NOT NULL,
    unrealized_pnl DECIMAL(15, 2) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (account_id, ticker),
    FOREIGN KEY (account_id) REFERENCES paper_accounts(account_id)
);

-- Trade executions log (both paper and live)
CREATE TABLE IF NOT EXISTS trade_executions (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE NOT NULL,
    account_id VARCHAR(50),
    ticker VARCHAR(10) NOT NULL,
    quantity DECIMAL(15, 4) NOT NULL,
    order_type VARCHAR(20) NOT NULL,  -- MARKET, LIMIT
    side VARCHAR(10) NOT NULL,  -- BUY, SELL
    price DECIMAL(15, 4),
    status VARCHAR(20) NOT NULL,  -- PENDING, FILLED, CANCELLED, REJECTED
    created_at TIMESTAMP DEFAULT NOW(),
    filled_at TIMESTAMP,
    notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_paper_positions_account ON paper_positions(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_executions_account ON trade_executions(account_id);
CREATE INDEX IF NOT EXISTS idx_trade_executions_ticker ON trade_executions(ticker);
CREATE INDEX IF NOT EXISTS idx_trade_executions_created ON trade_executions(created_at);

-- Initialize default paper account for Autonomous Fund
INSERT INTO paper_accounts (account_id, cash_balance, buying_power, total_value)
VALUES ('PAPER_AUTONOMOUS_FUND', 100000.00, 100000.00, 100000.00)
ON CONFLICT (account_id) DO NOTHING;

COMMENT ON TABLE paper_accounts IS 'Paper trading accounts for simulated trading';
COMMENT ON TABLE paper_positions IS 'Current positions in paper trading accounts';
COMMENT ON TABLE trade_executions IS 'Log of all trade executions (paper and live)';
