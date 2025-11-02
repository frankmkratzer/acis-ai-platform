-- Add autonomous trading settings to clients table
-- Phase 1: Client Opt-in for Automated Trading

-- Add autonomous trading columns
ALTER TABLE clients ADD COLUMN IF NOT EXISTS auto_trading_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS risk_tolerance VARCHAR(20) DEFAULT 'moderate';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS rebalance_frequency VARCHAR(20) DEFAULT 'weekly';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS drift_threshold NUMERIC(5,4) DEFAULT 0.05;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS max_position_size NUMERIC(5,4) DEFAULT 0.10;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS allowed_strategies TEXT[] DEFAULT ARRAY['growth_largecap', 'growth_midcap', 'dividend', 'value'];
ALTER TABLE clients ADD COLUMN IF NOT EXISTS min_cash_balance NUMERIC(12,2) DEFAULT 1000.00;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS tax_optimization_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS esg_preferences JSONB DEFAULT '{}';
ALTER TABLE clients ADD COLUMN IF NOT EXISTS sector_limits JSONB DEFAULT '{}';

-- Add comments for documentation
COMMENT ON COLUMN clients.auto_trading_enabled IS 'Whether client has opted into autonomous trading';
COMMENT ON COLUMN clients.risk_tolerance IS 'Client risk profile: conservative, moderate, aggressive';
COMMENT ON COLUMN clients.rebalance_frequency IS 'How often to rebalance: daily, weekly, monthly, quarterly';
COMMENT ON COLUMN clients.drift_threshold IS 'Threshold for triggering rebalancing (e.g., 0.05 = 5%)';
COMMENT ON COLUMN clients.max_position_size IS 'Maximum allocation to single position (e.g., 0.10 = 10%)';
COMMENT ON COLUMN clients.allowed_strategies IS 'Array of strategies client allows';
COMMENT ON COLUMN clients.min_cash_balance IS 'Minimum cash balance to maintain';
COMMENT ON COLUMN clients.tax_optimization_enabled IS 'Enable tax-loss harvesting and optimization';
COMMENT ON COLUMN clients.esg_preferences IS 'ESG filters and preferences (JSON)';
COMMENT ON COLUMN clients.sector_limits IS 'Maximum allocation per sector (JSON)';

-- Create index for faster querying of auto-trading enabled clients
CREATE INDEX IF NOT EXISTS idx_clients_auto_trading ON clients(auto_trading_enabled) WHERE auto_trading_enabled = TRUE;

-- Add constraint to validate risk tolerance
ALTER TABLE clients ADD CONSTRAINT IF NOT EXISTS chk_risk_tolerance
  CHECK (risk_tolerance IN ('conservative', 'moderate', 'aggressive'));

-- Add constraint to validate rebalance frequency
ALTER TABLE clients ADD CONSTRAINT IF NOT EXISTS chk_rebalance_frequency
  CHECK (rebalance_frequency IN ('daily', 'weekly', 'monthly', 'quarterly', 'threshold'));

-- Add constraint to validate drift threshold (0-100%)
ALTER TABLE clients ADD CONSTRAINT IF NOT EXISTS chk_drift_threshold
  CHECK (drift_threshold >= 0.01 AND drift_threshold <= 1.0);

-- Add constraint to validate max position size (1-100%)
ALTER TABLE clients ADD CONSTRAINT IF NOT EXISTS chk_max_position_size
  CHECK (max_position_size >= 0.01 AND max_position_size <= 1.0);

COMMIT;
