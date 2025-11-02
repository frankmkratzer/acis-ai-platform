-- Add account_hash column to client_brokerage_accounts
-- This stores the Schwab API hash ID used for API calls

ALTER TABLE client_brokerage_accounts
ADD COLUMN IF NOT EXISTS account_hash VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_client_brokerage_account_hash
ON client_brokerage_accounts(account_hash);

-- Update notes column comment
COMMENT ON COLUMN client_brokerage_accounts.account_hash IS 'Schwab API hash ID for making API calls';
