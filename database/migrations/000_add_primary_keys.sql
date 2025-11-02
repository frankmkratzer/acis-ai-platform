-- Migration: 000_add_primary_keys
-- Description: Add primary keys to existing clients and brokerages tables
-- Date: 2025-10-29

-- Add primary key to clients table
ALTER TABLE clients ADD PRIMARY KEY (client_id);

-- Add primary key to brokerages table
ALTER TABLE brokerages ADD PRIMARY KEY (brokerage_id);

-- Verify
SELECT 'Primary keys added successfully!' AS status;
