-- RL Trading Tables
-- Creates tables and views needed for RL trading functionality

-- ====================================================================
-- 1. Create rl_order_batches table
-- ====================================================================
CREATE TABLE IF NOT EXISTS rl_order_batches (
    batch_id TEXT PRIMARY KEY,
    client_id INTEGER NOT NULL,
    account_hash TEXT NOT NULL,
    portfolio_id INTEGER NOT NULL,
    strategy_name TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    current_portfolio JSONB,
    target_allocation JSONB,
    trades JSONB,
    execution_results JSONB,

    -- Add indexes for common queries
    CONSTRAINT rl_order_batches_client_id_fkey FOREIGN KEY (client_id)
        REFERENCES clients(client_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_rl_order_batches_client_id ON rl_order_batches(client_id);
CREATE INDEX IF NOT EXISTS idx_rl_order_batches_status ON rl_order_batches(status);
CREATE INDEX IF NOT EXISTS idx_rl_order_batches_created_at ON rl_order_batches(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rl_order_batches_portfolio_id ON rl_order_batches(portfolio_id);

COMMENT ON TABLE rl_order_batches IS 'Stores batches of RL-generated rebalancing orders awaiting approval or execution';
COMMENT ON COLUMN rl_order_batches.batch_id IS 'Unique identifier for the order batch';
COMMENT ON COLUMN rl_order_batches.status IS 'Status: pending_approval, approved, rejected, executed';
COMMENT ON COLUMN rl_order_batches.portfolio_id IS 'Portfolio strategy: 1=Growth, 2=Dividend, 3=Value';

-- ====================================================================
-- 2. Create brokerage_accounts view for backward compatibility
-- ====================================================================
-- This view provides backward compatibility for code that references brokerage_accounts
-- The actual table is client_brokerage_accounts
CREATE OR REPLACE VIEW brokerage_accounts AS
SELECT
    id,
    client_id,
    brokerage_id,
    account_number,
    account_hash,
    account_type,
    is_active,
    notes,
    created_at,
    updated_at
FROM client_brokerage_accounts;

COMMENT ON VIEW brokerage_accounts IS 'View providing backward compatibility for brokerage account lookups';

-- ====================================================================
-- Verify tables and views created successfully
-- ====================================================================
-- Check rl_order_batches
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rl_order_batches') THEN
        RAISE NOTICE 'SUCCESS: rl_order_batches table created';
    ELSE
        RAISE EXCEPTION 'FAILED: rl_order_batches table not found';
    END IF;
END $$;

-- Check brokerage_accounts view
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'brokerage_accounts') THEN
        RAISE NOTICE 'SUCCESS: brokerage_accounts view created';
    ELSE
        RAISE EXCEPTION 'FAILED: brokerage_accounts view not found';
    END IF;
END $$;

-- Show summary
SELECT
    'rl_order_batches' as object_name,
    'table' as object_type,
    COUNT(*) as row_count
FROM rl_order_batches
UNION ALL
SELECT
    'brokerage_accounts' as object_name,
    'view' as object_type,
    COUNT(*) as row_count
FROM brokerage_accounts;
