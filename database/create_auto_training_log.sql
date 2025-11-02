-- Auto-training log table
CREATE TABLE IF NOT EXISTS auto_training_log (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    strategy VARCHAR(50) NOT NULL,
    market_cap VARCHAR(20),
    status VARCHAR(20) NOT NULL,  -- 'success', 'failed'
    duration_minutes NUMERIC(10, 2),
    error_message TEXT,
    trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_auto_training_model ON auto_training_log(model_name);
CREATE INDEX IF NOT EXISTS idx_auto_training_status ON auto_training_log(status);
CREATE INDEX IF NOT EXISTS idx_auto_training_date ON auto_training_log(trained_at);

-- View for latest training status
CREATE OR REPLACE VIEW latest_training_status AS
SELECT DISTINCT ON (model_name)
    model_name,
    strategy,
    market_cap,
    status,
    duration_minutes,
    trained_at
FROM auto_training_log
ORDER BY model_name, trained_at DESC;
