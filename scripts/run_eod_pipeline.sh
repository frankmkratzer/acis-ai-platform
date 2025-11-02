#!/bin/bash
#
# End-of-Day Pipeline
# Complete daily workflow after market close
#
# Tasks:
# 1. Data validation
# 2. Refresh materialized views
# 3. Train all ML models (XGBoost)
# 4. Train all RL models (PPO)
# 5. Database maintenance
# 6. Generate summary reports
#

set -e  # Exit on error

# Configuration
PROJECT_ROOT="/home/fkratzer/acis-ai-platform"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/eod_pipeline_$(date +%Y%m%d_%H%M%S).log"

# Load environment variables
source "$PROJECT_ROOT/.env.sh"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH="$PROJECT_ROOT"

# Start pipeline
log_info "================================================================================"
log_info "END-OF-DAY PIPELINE STARTED"
log_info "================================================================================"
log_info "Timestamp: $(date)"
log_info "Log file: $LOG_FILE"
log_info "================================================================================"

# Track overall success
PIPELINE_SUCCESS=true

# ============================================================================
# STEP 1: Data Validation
# ============================================================================
log_info "STEP 1: Validating data availability..."

# Check if we have data for today
DATA_CHECK=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c "
    SELECT COUNT(*) FROM daily_bars WHERE date = CURRENT_DATE
")

if [ "$DATA_CHECK" -gt 0 ]; then
    log_success "Today's market data is available ($DATA_CHECK records)"
else
    log_warning "No data for today yet - this is expected if market is closed or data ingestion pending"
fi

# ============================================================================
# STEP 2: Refresh Materialized Views
# ============================================================================
log_info ""
log_info "STEP 2: Refreshing materialized views..."
log_info "This may take 2-3 minutes..."

START_TIME=$(date +%s)

if PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -c "
    REFRESH MATERIALIZED VIEW ml_training_features;
" >> "$LOG_FILE" 2>&1; then
    DURATION=$(($(date +%s) - START_TIME))
    log_success "Materialized view refreshed in ${DURATION}s"
else
    log_error "Failed to refresh materialized view"
    PIPELINE_SUCCESS=false
fi

# ============================================================================
# STEP 3: Train ML Models
# ============================================================================
log_info ""
log_info "STEP 3: Training ML models..."
log_info "Training 7 models: growth (s/m/l), value (s/m/l), dividend"
log_info "This will take 30-60 minutes with GPU..."

START_TIME=$(date +%s)

if python scripts/auto_train_models.py \
    --start-date 2015-01-01 \
    --gpu \
    >> "$LOG_FILE" 2>&1; then
    DURATION=$(($(date +%s) - START_TIME))
    log_success "All ML models trained successfully in ${DURATION}s ($((DURATION/60)) minutes)"
else
    log_error "ML model training failed - check $LOG_FILE for details"
    PIPELINE_SUCCESS=false
fi

# ============================================================================
# STEP 4: Train RL Models
# ============================================================================
log_info ""
log_info "STEP 4: Training RL models (PPO agents)..."
log_info "Training 7 models: growth (s/m/l), value (s/m/l), dividend"
log_info "This will take 2-4 hours with CPU (PPO recommended on CPU)..."

START_TIME=$(date +%s)

if python scripts/auto_train_rl_models.py \
    --timesteps 1000000 \
    --device cpu \
    >> "$LOG_FILE" 2>&1; then
    DURATION=$(($(date +%s) - START_TIME))
    log_success "All RL models trained successfully in ${DURATION}s ($((DURATION/60)) minutes)"
else
    log_error "RL model training failed - check $LOG_FILE for details"
    PIPELINE_SUCCESS=false
fi

# ============================================================================
# STEP 5: Database Maintenance
# ============================================================================
log_info ""
log_info "STEP 5: Database maintenance..."

if PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -c "
    VACUUM ANALYZE ml_training_features;
    VACUUM ANALYZE auto_training_log;
" >> "$LOG_FILE" 2>&1; then
    log_success "Database maintenance completed"
else
    log_warning "Database maintenance had issues (non-critical)"
fi

# ============================================================================
# STEP 6: Generate Summary Report
# ============================================================================
log_info ""
log_info "STEP 6: Generating summary report..."

# Get training results from database
TRAINING_SUMMARY=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c "
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
        ROUND(AVG(duration_minutes)::numeric, 1) as avg_duration
    FROM auto_training_log
    WHERE DATE(trained_at) = CURRENT_DATE
")

log_info "Today's Training Summary:"
log_info "$TRAINING_SUMMARY"

# Get latest model performance
MODEL_PERFORMANCE=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c "
    SELECT model_name, status, duration_minutes
    FROM latest_training_status
    ORDER BY model_name
")

log_info ""
log_info "Model Performance:"
echo "$MODEL_PERFORMANCE" | tee -a "$LOG_FILE"

# ============================================================================
# Pipeline Complete
# ============================================================================
log_info ""
log_info "================================================================================"

if [ "$PIPELINE_SUCCESS" = true ]; then
    log_success "END-OF-DAY PIPELINE COMPLETED SUCCESSFULLY"
    EXIT_CODE=0
else
    log_error "END-OF-DAY PIPELINE COMPLETED WITH ERRORS"
    EXIT_CODE=1
fi

log_info "================================================================================"
log_info "Complete log: $LOG_FILE"
log_info "View training history: SELECT * FROM latest_training_status;"
log_info "================================================================================"

exit $EXIT_CODE
