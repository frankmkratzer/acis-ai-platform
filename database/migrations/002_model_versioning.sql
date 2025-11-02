/*
 * Model Versioning and Management System
 *
 * Tracks trained ML models with metadata, performance metrics,
 * and production status for safe model lifecycle management.
 */

-- Create model_versions table
CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    framework VARCHAR(50) NOT NULL,

    -- Training metadata
    trained_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    training_config JSONB,
    training_duration_seconds INTEGER,

    -- Dataset metadata
    training_start_date DATE,
    training_end_date DATE,
    n_training_samples BIGINT,
    n_features INTEGER,

    -- Performance metrics
    spearman_ic NUMERIC(10, 6),
    pearson_correlation NUMERIC(10, 6),
    train_rmse NUMERIC(15, 6),
    val_rmse NUMERIC(15, 6),
    additional_metrics JSONB,

    -- File locations
    model_path VARCHAR(500) NOT NULL,
    size_mb NUMERIC(10, 2),

    -- Status and lifecycle
    status VARCHAR(50) NOT NULL DEFAULT 'trained',  -- trained, validated, production, archived, deleted
    is_production BOOLEAN NOT NULL DEFAULT FALSE,
    promoted_to_production_at TIMESTAMP,

    -- Metadata
    description TEXT,
    created_by VARCHAR(100),
    notes TEXT,
    tags TEXT[],

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    UNIQUE(model_name, version),
    CONSTRAINT check_status CHECK (status IN ('trained', 'validated', 'production', 'archived', 'deleted'))
);

-- Create index on production models for fast lookup
CREATE INDEX idx_model_versions_production ON model_versions(is_production) WHERE is_production = TRUE;
CREATE INDEX idx_model_versions_status ON model_versions(status);
CREATE INDEX idx_model_versions_trained_at ON model_versions(trained_at DESC);
CREATE INDEX idx_model_versions_framework ON model_versions(framework);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_model_versions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_model_versions_updated_at
    BEFORE UPDATE ON model_versions
    FOR EACH ROW
    EXECUTE FUNCTION update_model_versions_updated_at();

-- Create trigger to ensure only one production model per framework
CREATE OR REPLACE FUNCTION ensure_single_production_model()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting a model to production
    IF NEW.is_production = TRUE AND (OLD.is_production IS NULL OR OLD.is_production = FALSE) THEN
        -- Set all other models of same framework to non-production
        UPDATE model_versions
        SET is_production = FALSE,
            status = CASE
                WHEN status = 'production' THEN 'validated'
                ELSE status
            END,
            updated_at = CURRENT_TIMESTAMP
        WHERE framework = NEW.framework
          AND id != NEW.id
          AND is_production = TRUE;

        -- Update promotion timestamp
        NEW.promoted_to_production_at = CURRENT_TIMESTAMP;
        NEW.status = 'production';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_single_production_model
    BEFORE UPDATE OF is_production ON model_versions
    FOR EACH ROW
    EXECUTE FUNCTION ensure_single_production_model();

-- Create model_evaluation_history table for tracking model performance over time
CREATE TABLE IF NOT EXISTS model_evaluation_history (
    id SERIAL PRIMARY KEY,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(id) ON DELETE CASCADE,

    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evaluation_period_start DATE,
    evaluation_period_end DATE,

    -- Performance metrics
    spearman_ic NUMERIC(10, 6),
    pearson_correlation NUMERIC(10, 6),
    rmse NUMERIC(15, 6),
    mae NUMERIC(15, 6),

    -- Additional metrics
    metrics JSONB,

    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_model_eval_history_model ON model_evaluation_history(model_version_id, evaluated_at DESC);

-- Create model_deployment_log table for audit trail
CREATE TABLE IF NOT EXISTS model_deployment_log (
    id SERIAL PRIMARY KEY,
    model_version_id INTEGER NOT NULL REFERENCES model_versions(id) ON DELETE CASCADE,

    action VARCHAR(50) NOT NULL,  -- promoted, demoted, deleted, archived
    previous_status VARCHAR(50),
    new_status VARCHAR(50),

    performed_by VARCHAR(100),
    performed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    reason TEXT,
    metadata JSONB,

    CONSTRAINT check_action CHECK (action IN ('promoted', 'demoted', 'deleted', 'archived', 'restored'))
);

CREATE INDEX idx_model_deployment_log_model ON model_deployment_log(model_version_id, performed_at DESC);
CREATE INDEX idx_model_deployment_log_action ON model_deployment_log(action);

-- Insert a sample entry for the existing production model
INSERT INTO model_versions (
    model_name,
    version,
    framework,
    trained_at,
    model_path,
    status,
    is_production,
    description,
    notes
) VALUES (
    'xgboost_optimized',
    'v1.0',
    'xgboost',
    CURRENT_TIMESTAMP,
    'models/xgboost_optimized',
    'production',
    TRUE,
    'Initial production XGBoost model',
    'Baseline production model - do not delete without setting replacement'
) ON CONFLICT (model_name, version) DO NOTHING;

-- Create helper function to get current production model
CREATE OR REPLACE FUNCTION get_production_model(p_framework VARCHAR)
RETURNS TABLE (
    id INTEGER,
    model_name VARCHAR,
    version VARCHAR,
    model_path VARCHAR,
    spearman_ic NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mv.id,
        mv.model_name,
        mv.version,
        mv.model_path,
        mv.spearman_ic
    FROM model_versions mv
    WHERE mv.framework = p_framework
      AND mv.is_production = TRUE
      AND mv.status = 'production'
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Create helper function to promote model to production
CREATE OR REPLACE FUNCTION promote_model_to_production(
    p_model_version_id INTEGER,
    p_performed_by VARCHAR DEFAULT 'system',
    p_reason TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_framework VARCHAR;
    v_previous_production_id INTEGER;
BEGIN
    -- Get the framework of the model being promoted
    SELECT framework INTO v_framework
    FROM model_versions
    WHERE id = p_model_version_id;

    IF v_framework IS NULL THEN
        RAISE EXCEPTION 'Model version not found';
    END IF;

    -- Get current production model for this framework
    SELECT id INTO v_previous_production_id
    FROM model_versions
    WHERE framework = v_framework
      AND is_production = TRUE
      AND id != p_model_version_id;

    -- Log demotion of previous production model if exists
    IF v_previous_production_id IS NOT NULL THEN
        INSERT INTO model_deployment_log (
            model_version_id,
            action,
            previous_status,
            new_status,
            performed_by,
            reason
        ) VALUES (
            v_previous_production_id,
            'demoted',
            'production',
            'validated',
            p_performed_by,
            p_reason
        );
    END IF;

    -- Promote new model
    UPDATE model_versions
    SET is_production = TRUE,
        status = 'production'
    WHERE id = p_model_version_id;

    -- Log promotion
    INSERT INTO model_deployment_log (
        model_version_id,
        action,
        previous_status,
        new_status,
        performed_by,
        reason
    ) VALUES (
        p_model_version_id,
        'promoted',
        'validated',
        'production',
        p_performed_by,
        p_reason
    );

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Report
DO $$
BEGIN
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Model Versioning System Initialized';
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Created tables:';
    RAISE NOTICE '  - model_versions (tracks all trained models)';
    RAISE NOTICE '  - model_evaluation_history (tracks performance over time)';
    RAISE NOTICE '  - model_deployment_log (audit trail)';
    RAISE NOTICE '';
    RAISE NOTICE 'Features:';
    RAISE NOTICE '  ✓ Only one production model per framework enforced';
    RAISE NOTICE '  ✓ Safe model promotion/demotion with audit logging';
    RAISE NOTICE '  ✓ Prevent deletion of production models';
    RAISE NOTICE '  ✓ Track model performance and metadata';
    RAISE NOTICE '';
    RAISE NOTICE 'Helper functions:';
    RAISE NOTICE '  - get_production_model(framework) - Get current production model';
    RAISE NOTICE '  - promote_model_to_production(id, user, reason) - Safely promote model';
    RAISE NOTICE '================================================================';
END $$;
