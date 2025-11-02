-- Autonomous Fund Database Schema
-- Tables for meta-strategy selection and autonomous rebalancing

-- ============================================================================
-- Market Regime Detection
-- ============================================================================

CREATE TABLE IF NOT EXISTS market_regime (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,

    -- Volatility indicators
    vix NUMERIC(6, 2),
    realized_volatility_20d NUMERIC(8, 4),
    volatility_regime VARCHAR(20),  -- 'low', 'medium', 'high', 'extreme'

    -- Trend indicators
    spy_sma_50 NUMERIC(10, 2),
    spy_sma_200 NUMERIC(10, 2),
    trend_regime VARCHAR(20),  -- 'bull', 'bear', 'sideways'

    -- Market breadth
    advance_decline_ratio NUMERIC(6, 4),
    new_highs_lows_ratio NUMERIC(6, 4),

    -- Sector rotation
    sector_momentum JSONB,  -- Top performing sectors

    -- Economic indicators
    treasury_10y NUMERIC(6, 4),
    treasury_2y NUMERIC(6, 4),
    yield_curve_slope NUMERIC(6, 4),

    -- Overall regime classification
    regime_label VARCHAR(50),  -- 'bull_low_vol', 'bear_high_vol', etc.
    regime_confidence NUMERIC(4, 3),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_market_regime_date ON market_regime(date);
CREATE INDEX idx_market_regime_label ON market_regime(regime_label);

-- ============================================================================
-- Strategy Performance Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS strategy_performance (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    strategy VARCHAR(50) NOT NULL,  -- 'growth_small', 'value_large', etc.

    -- Daily metrics
    daily_return NUMERIC(10, 6),
    portfolio_value NUMERIC(15, 2),
    num_positions INT,

    -- Rolling metrics (updated daily)
    sharpe_ratio_30d NUMERIC(6, 4),
    max_drawdown_30d NUMERIC(6, 4),
    win_rate_30d NUMERIC(4, 3),

    -- Risk metrics
    volatility_30d NUMERIC(6, 4),
    beta NUMERIC(6, 4),

    -- Relative performance
    outperformance_vs_spy NUMERIC(10, 6),

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_strategy_date UNIQUE(date, strategy)
);

CREATE INDEX idx_strategy_perf_date ON strategy_performance(date);
CREATE INDEX idx_strategy_perf_strategy ON strategy_performance(strategy);
CREATE INDEX idx_strategy_perf_sharpe ON strategy_performance(sharpe_ratio_30d);

-- View for latest strategy rankings
CREATE OR REPLACE VIEW strategy_rankings AS
SELECT
    strategy,
    daily_return,
    sharpe_ratio_30d,
    max_drawdown_30d,
    win_rate_30d,
    outperformance_vs_spy,
    RANK() OVER (ORDER BY sharpe_ratio_30d DESC) as sharpe_rank,
    RANK() OVER (ORDER BY outperformance_vs_spy DESC) as performance_rank,
    date
FROM strategy_performance
WHERE date = (SELECT MAX(date) FROM strategy_performance)
ORDER BY sharpe_ratio_30d DESC;

-- ============================================================================
-- Meta-Strategy Selection Log
-- ============================================================================

CREATE TABLE IF NOT EXISTS meta_strategy_selection (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,

    -- Model predictions
    strategy_probabilities JSONB,  -- {growth_small: 0.15, value_large: 0.30, ...}
    selected_strategy VARCHAR(50),
    selection_confidence NUMERIC(4, 3),

    -- Model features used
    market_regime VARCHAR(50),
    recent_performance JSONB,  -- Last 30 days strategy performance

    -- Model metadata
    model_version VARCHAR(50),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_meta_selection_date ON meta_strategy_selection(date);
CREATE INDEX idx_meta_selection_strategy ON meta_strategy_selection(selected_strategy);

-- ============================================================================
-- Portfolio Positions (Current Holdings)
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolio_positions (
    id SERIAL PRIMARY KEY,
    account_id INT REFERENCES clients(client_id),
    ticker VARCHAR(10) NOT NULL,

    -- Position details
    quantity NUMERIC(12, 4),
    average_cost NUMERIC(12, 4),
    current_price NUMERIC(12, 4),
    market_value NUMERIC(15, 2),

    -- P&L
    cost_basis NUMERIC(15, 2),
    unrealized_pnl NUMERIC(15, 2),
    unrealized_pnl_pct NUMERIC(8, 4),

    -- Position metadata
    opened_date DATE,
    last_updated TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_account_ticker UNIQUE(account_id, ticker)
);

CREATE INDEX idx_positions_account ON portfolio_positions(account_id);
CREATE INDEX idx_positions_ticker ON portfolio_positions(ticker);

-- ============================================================================
-- Rebalancing History
-- ============================================================================

CREATE TABLE IF NOT EXISTS rebalancing_log (
    id SERIAL PRIMARY KEY,
    rebalance_date DATE NOT NULL,
    account_id INT REFERENCES clients(client_id),

    -- Strategy selection
    strategy_selected VARCHAR(50),
    meta_model_confidence NUMERIC(4, 3),
    market_regime VARCHAR(50),

    -- Portfolio state
    pre_rebalance_value NUMERIC(15, 2),
    post_rebalance_value NUMERIC(15, 2),
    num_positions_before INT,
    num_positions_after INT,

    -- Trading activity
    num_buys INT,
    num_sells INT,
    total_turnover NUMERIC(15, 2),
    total_transaction_costs NUMERIC(12, 2),

    -- Detailed trades
    trades JSONB,  -- Array of {ticker, side, quantity, price, ...}

    -- Execution status
    status VARCHAR(20),  -- 'completed', 'partial', 'failed'
    execution_time_seconds NUMERIC(8, 2),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rebalancing_date ON rebalancing_log(rebalance_date);
CREATE INDEX idx_rebalancing_account ON rebalancing_log(account_id);
CREATE INDEX idx_rebalancing_strategy ON rebalancing_log(strategy_selected);

-- ============================================================================
-- Trade Executions (Individual Trades)
-- ============================================================================

CREATE TABLE IF NOT EXISTS trade_executions (
    id SERIAL PRIMARY KEY,
    rebalance_id INT REFERENCES rebalancing_log(id),
    account_id INT REFERENCES clients(client_id),

    -- Trade details
    ticker VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    quantity NUMERIC(12, 4),

    -- Pricing
    target_price NUMERIC(12, 4),
    execution_price NUMERIC(12, 4),
    slippage NUMERIC(12, 4),

    -- Costs
    commission NUMERIC(12, 2),
    sec_fee NUMERIC(12, 2),
    total_cost NUMERIC(12, 2),

    -- Execution metadata
    order_type VARCHAR(20),  -- 'MARKET', 'LIMIT', etc.
    brokerage_order_id VARCHAR(100),
    execution_status VARCHAR(20),  -- 'filled', 'partial', 'rejected'

    -- Timestamps
    submitted_at TIMESTAMP,
    executed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trades_rebalance ON trade_executions(rebalance_id);
CREATE INDEX idx_trades_account ON trade_executions(account_id);
CREATE INDEX idx_trades_ticker ON trade_executions(ticker);
CREATE INDEX idx_trades_date ON trade_executions(executed_at);

-- ============================================================================
-- Portfolio Value History (Daily Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS portfolio_value_history (
    id SERIAL PRIMARY KEY,
    account_id INT REFERENCES clients(client_id),
    date DATE NOT NULL,

    -- Value components
    total_value NUMERIC(15, 2),
    cash_balance NUMERIC(15, 2),
    positions_value NUMERIC(15, 2),

    -- Performance metrics
    daily_return NUMERIC(10, 6),
    cumulative_return NUMERIC(10, 6),

    -- Benchmark comparison
    spy_return NUMERIC(10, 6),
    alpha NUMERIC(10, 6),

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_account_date UNIQUE(account_id, date)
);

CREATE INDEX idx_portfolio_value_account ON portfolio_value_history(account_id);
CREATE INDEX idx_portfolio_value_date ON portfolio_value_history(date);

-- ============================================================================
-- Risk Alerts
-- ============================================================================

CREATE TABLE IF NOT EXISTS risk_alerts (
    id SERIAL PRIMARY KEY,
    alert_date DATE,
    account_id INT REFERENCES clients(client_id),

    -- Alert details
    alert_type VARCHAR(50),  -- 'max_drawdown', 'high_volatility', 'trade_failure', etc.
    severity VARCHAR(20),  -- 'info', 'warning', 'critical'
    message TEXT,

    -- Metrics at time of alert
    current_drawdown NUMERIC(6, 4),
    portfolio_value NUMERIC(15, 2),
    positions_affected JSONB,

    -- Resolution
    acknowledged BOOLEAN DEFAULT FALSE,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_notes TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_risk_alerts_date ON risk_alerts(alert_date);
CREATE INDEX idx_risk_alerts_account ON risk_alerts(account_id);
CREATE INDEX idx_risk_alerts_severity ON risk_alerts(severity);
CREATE INDEX idx_risk_alerts_unresolved ON risk_alerts(resolved) WHERE resolved = FALSE;

-- ============================================================================
-- Summary Statistics View
-- ============================================================================

CREATE OR REPLACE VIEW portfolio_summary AS
SELECT
    p.account_id,
    c.name as account_name,
    COUNT(*) as num_positions,
    SUM(p.market_value) as total_positions_value,
    SUM(p.unrealized_pnl) as total_unrealized_pnl,
    AVG(p.unrealized_pnl_pct) as avg_position_return,
    MAX(p.last_updated) as last_updated
FROM portfolio_positions p
JOIN clients c ON p.account_id = c.id
GROUP BY p.account_id, c.name;

COMMENT ON TABLE market_regime IS 'Daily market regime classification for meta-strategy selection';
COMMENT ON TABLE strategy_performance IS 'Track daily performance of each strategy for meta-model training';
COMMENT ON TABLE meta_strategy_selection IS 'Log of meta-model decisions on which strategy to use';
COMMENT ON TABLE portfolio_positions IS 'Current holdings for each account';
COMMENT ON TABLE rebalancing_log IS 'History of all rebalancing events';
COMMENT ON TABLE trade_executions IS 'Individual trade details for audit trail';
COMMENT ON TABLE portfolio_value_history IS 'Daily portfolio value tracking';
COMMENT ON TABLE risk_alerts IS 'Automated risk management alerts';
