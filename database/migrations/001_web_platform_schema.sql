-- Web Platform Database Schema
-- Migration: 001_web_platform_schema
-- Description: Add NEW tables for web platform (works with existing schema)
-- Date: 2025-10-29
-- Database: acis-ai (existing)

-- NOTE: This adds NEW tables only. Your existing tables remain unchanged:
--   ✓ clients (client_id, client_name, email, etc.)
--   ✓ brokerages (brokerage_id, name, api_type, etc.)
--   ✓ portfolios (portfolio_id, name, strategy, etc.)
--   ✓ portfolio_holdings (existing ML-based holdings)

-- ============================================
-- CLIENT BROKERAGE ACCOUNTS
-- ============================================
-- Links clients to their brokerage accounts (many-to-many)
CREATE TABLE IF NOT EXISTS client_brokerage_accounts (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    brokerage_id INT NOT NULL REFERENCES brokerages(brokerage_id) ON DELETE CASCADE,
    account_number VARCHAR(255) NOT NULL,
    account_type VARCHAR(50),  -- 'individual', 'ira', 'roth_ira', 'joint', '401k'
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, brokerage_id, account_number)
);

CREATE INDEX idx_client_brokerage_client ON client_brokerage_accounts(client_id);
CREATE INDEX idx_client_brokerage_brokerage ON client_brokerage_accounts(brokerage_id);

-- ============================================
-- SCHWAB OAUTH TOKENS
-- ============================================
CREATE TABLE IF NOT EXISTS brokerage_oauth_tokens (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    brokerage_id INT NOT NULL REFERENCES brokerages(brokerage_id) ON DELETE CASCADE,
    account_id INT REFERENCES client_brokerage_accounts(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    scope TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, brokerage_id)
);

CREATE INDEX idx_oauth_tokens_client ON brokerage_oauth_tokens(client_id);
CREATE INDEX idx_oauth_tokens_expires ON brokerage_oauth_tokens(expires_at);

-- ============================================
-- TRADE RECOMMENDATIONS
-- ============================================
CREATE TABLE IF NOT EXISTS trade_recommendations (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    account_id INT REFERENCES client_brokerage_accounts(id) ON DELETE CASCADE,
    rl_portfolio_id INT,  -- 1=Growth/Momentum, 2=Portfolio2, 3=Portfolio3
    rl_portfolio_name VARCHAR(100),
    recommendation_type VARCHAR(50) NOT NULL,
    trades JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    total_trades INT NOT NULL DEFAULT 0,
    total_buy_value DECIMAL(20, 2),
    total_sell_value DECIMAL(20, 2),
    expected_turnover DECIMAL(5, 4),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP,
    executed_at TIMESTAMP
);

CREATE INDEX idx_trade_recommendations_client ON trade_recommendations(client_id);
CREATE INDEX idx_trade_recommendations_status ON trade_recommendations(status);
CREATE INDEX idx_trade_recommendations_rl_portfolio ON trade_recommendations(rl_portfolio_id);

-- ============================================
-- TRADE EXECUTIONS
-- ============================================
CREATE TABLE IF NOT EXISTS trade_executions (
    id SERIAL PRIMARY KEY,
    recommendation_id INT REFERENCES trade_recommendations(id) ON DELETE SET NULL,
    client_id INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    account_id INT NOT NULL REFERENCES client_brokerage_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL,
    shares INT NOT NULL,
    price DECIMAL(10, 4),
    limit_price DECIMAL(10, 4),
    order_type VARCHAR(20),
    commission DECIMAL(10, 2) DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    order_id VARCHAR(255),
    error_message TEXT,
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_executions_client ON trade_executions(client_id);
CREATE INDEX idx_trade_executions_account ON trade_executions(account_id);
CREATE INDEX idx_trade_executions_recommendation ON trade_executions(recommendation_id);
CREATE INDEX idx_trade_executions_status ON trade_executions(status);
CREATE INDEX idx_trade_executions_symbol ON trade_executions(symbol);
CREATE INDEX idx_trade_executions_date ON trade_executions(executed_at DESC);

-- ============================================
-- RL TRAINING JOBS
-- ============================================
CREATE TABLE IF NOT EXISTS rl_training_jobs (
    id SERIAL PRIMARY KEY,
    rl_portfolio_id INT NOT NULL,  -- 1=Growth/Momentum, 2=Portfolio2, 3=Portfolio3
    rl_portfolio_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    timesteps INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    progress DECIMAL(5, 2) DEFAULT 0,
    current_step INT DEFAULT 0,
    metrics JSONB,
    model_path VARCHAR(500),
    log_path VARCHAR(500),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rl_training_portfolio ON rl_training_jobs(rl_portfolio_id);
CREATE INDEX idx_rl_training_status ON rl_training_jobs(status);
CREATE INDEX idx_rl_training_created ON rl_training_jobs(created_at DESC);

-- ============================================
-- BACKTEST RESULTS
-- ============================================
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    rl_portfolio_id INT NOT NULL,
    rl_portfolio_name VARCHAR(100) NOT NULL,
    model_path VARCHAR(500) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(20, 2) NOT NULL,
    final_value DECIMAL(20, 2) NOT NULL,
    total_return DECIMAL(10, 4) NOT NULL,
    annualized_return DECIMAL(10, 4) NOT NULL,
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    num_trades INT,
    avg_turnover DECIMAL(5, 4),
    trades_file VARCHAR(500),
    positions_file VARCHAR(500),
    rebalance_file VARCHAR(500),
    report_file VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_backtest_rl_portfolio ON backtest_results(rl_portfolio_id);
CREATE INDEX idx_backtest_created ON backtest_results(created_at DESC);

-- ============================================
-- AI CHAT HISTORY
-- ============================================
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    context JSONB,
    tokens_used INT,
    response_time_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ai_chat_user ON ai_chat_history(user_email);
CREATE INDEX idx_ai_chat_created ON ai_chat_history(created_at DESC);

-- ============================================
-- CLIENT RL PORTFOLIO ASSIGNMENTS
-- ============================================
CREATE TABLE IF NOT EXISTS client_rl_portfolio_assignments (
    id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES clients(client_id) ON DELETE CASCADE,
    account_id INT NOT NULL REFERENCES client_brokerage_accounts(id) ON DELETE CASCADE,
    rl_portfolio_id INT NOT NULL,  -- 1=Growth/Momentum, 2=Portfolio2, 3=Portfolio3
    rl_portfolio_name VARCHAR(100) NOT NULL,
    allocation_percent DECIMAL(5, 2) NOT NULL DEFAULT 100.00,
    auto_rebalance BOOLEAN DEFAULT FALSE,
    rebalance_frequency VARCHAR(20) DEFAULT 'monthly',
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, account_id, rl_portfolio_id)
);

CREATE INDEX idx_rl_portfolio_assignments_client ON client_rl_portfolio_assignments(client_id);
CREATE INDEX idx_rl_portfolio_assignments_rl_portfolio ON client_rl_portfolio_assignments(rl_portfolio_id);
CREATE INDEX idx_rl_portfolio_assignments_auto_rebalance ON client_rl_portfolio_assignments(auto_rebalance);

-- ============================================
-- MIGRATION COMPLETE
-- ============================================
-- Summary of new tables:
--   ✓ client_brokerage_accounts - Link clients to brokerage accounts
--   ✓ brokerage_oauth_tokens - Schwab OAuth tokens
--   ✓ trade_recommendations - AI-generated trade recommendations
--   ✓ trade_executions - Trade execution log
--   ✓ rl_training_jobs - RL training job tracking
--   ✓ backtest_results - Backtest results storage
--   ✓ ai_chat_history - AI chat conversation log
--   ✓ client_rl_portfolio_assignments - Assign clients to RL portfolios
