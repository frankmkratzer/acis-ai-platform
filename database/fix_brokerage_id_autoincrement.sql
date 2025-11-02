-- Fix brokerage_id auto-increment
-- This adds a PostgreSQL sequence to automatically generate brokerage_id values

-- Create sequence for brokerage_id
CREATE SEQUENCE IF NOT EXISTS brokerages_brokerage_id_seq;

-- Set sequence to start after highest existing brokerage_id
SELECT setval('brokerages_brokerage_id_seq', COALESCE((SELECT MAX(brokerage_id) FROM brokerages), 0) + 1, false);

-- Set column default to use sequence
ALTER TABLE brokerages ALTER COLUMN brokerage_id SET DEFAULT nextval('brokerages_brokerage_id_seq'::regclass);

-- Make sequence owned by column (will be dropped if column is dropped)
ALTER SEQUENCE brokerages_brokerage_id_seq OWNED BY brokerages.brokerage_id;

-- Verify the fix
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_sequences
        WHERE schemaname = 'public'
        AND sequencename = 'brokerages_brokerage_id_seq'
    ) THEN
        RAISE NOTICE 'SUCCESS: brokerages_brokerage_id_seq sequence created';
    ELSE
        RAISE EXCEPTION 'FAILED: sequence not found';
    END IF;
END $$;

-- Show current sequence value
SELECT 'brokerages_brokerage_id_seq' as sequence_name, last_value, is_called
FROM brokerages_brokerage_id_seq;
