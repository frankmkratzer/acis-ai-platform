#!/bin/bash

##############################################################################
# Weekly ML Training Script
# Purpose: Retrain all ML models (XGBoost) for stock screening
# Frequency: Run weekly on Sundays (automated via cron)
# Duration: ~30-60 minutes
##############################################################################

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/pipeline"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/weekly_ml_${TIMESTAMP}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $1" | tee -a "$LOG_FILE"
}

# Error handler
error_handler() {
    log_error "ML training failed at: $CURRENT_MODEL"
    log_error "Check log file: $LOG_FILE"
    exit 1
}

trap error_handler ERR

##############################################################################
# Pre-Training Validation
##############################################################################

log "════════════════════════════════════════════════════════════════"
log "Weekly ML Training Pipeline"
log "════════════════════════════════════════════════════════════════"
log ""

# Activate virtual environment
cd "$PROJECT_DIR"
source venv/bin/activate

# Check if ml_training_features view is up to date
log "Validating ml_training_features view..."
VIEW_COUNT=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT COUNT(*) FROM ml_training_features")

if [ "$VIEW_COUNT" -lt 1000 ]; then
    log_warning "ml_training_features has only $VIEW_COUNT rows. Consider running daily pipeline first."
else
    log_success "ml_training_features has $VIEW_COUNT rows"
fi

##############################################################################
# Train ML Models
##############################################################################

PIPELINE_START=$(date +%s)

# Define all ML models to train
STRATEGIES=("growth" "momentum" "dividend" "value")
MARKET_CAPS=("large" "mid" "small")

TOTAL_MODELS=$((${#STRATEGIES[@]} * ${#MARKET_CAPS[@]}))
CURRENT_MODEL_NUM=0
FAILED_MODELS=()
SUCCESSFUL_MODELS=()

log ""
log "Training $TOTAL_MODELS ML models (${#STRATEGIES[@]} strategies × ${#MARKET_CAPS[@]} market caps)"
log ""

for STRATEGY in "${STRATEGIES[@]}"; do
    for MARKET_CAP in "${MARKET_CAPS[@]}"; do
        CURRENT_MODEL_NUM=$((CURRENT_MODEL_NUM + 1))
        CURRENT_MODEL="${STRATEGY}_${MARKET_CAP}"

        log "════════════════════════════════════════════════════════════════"
        log "[$CURRENT_MODEL_NUM/$TOTAL_MODELS] Training ML Model: $CURRENT_MODEL"
        log "════════════════════════════════════════════════════════════════"

        MODEL_START=$(date +%s)

        # Train the model
        if python scripts/auto_train_models.py \
            --models "${STRATEGY}_${MARKET_CAP}cap" \
            --start-date 2015-01-01 \
            --end-date $(date +%Y-%m-%d) \
            >> "$LOG_FILE" 2>&1; then

            MODEL_END=$(date +%s)
            MODEL_DURATION=$((MODEL_END - MODEL_START))
            log_success "Model $CURRENT_MODEL trained successfully in ${MODEL_DURATION}s"
            SUCCESSFUL_MODELS+=("$CURRENT_MODEL")
        else
            MODEL_END=$(date +%s)
            MODEL_DURATION=$((MODEL_END - MODEL_START))
            log_error "Model $CURRENT_MODEL failed after ${MODEL_DURATION}s"
            FAILED_MODELS+=("$CURRENT_MODEL")
        fi

        log ""
    done
done

##############################################################################
# Summary Report
##############################################################################

PIPELINE_END=$(date +%s)
TOTAL_DURATION=$((PIPELINE_END - PIPELINE_START))
MINUTES=$((TOTAL_DURATION / 60))
SECONDS=$((TOTAL_DURATION % 60))

log "════════════════════════════════════════════════════════════════"
log "Weekly ML Training Summary"
log "════════════════════════════════════════════════════════════════"
log ""
log "Total Duration: ${MINUTES}m ${SECONDS}s"
log "Successful Models: ${#SUCCESSFUL_MODELS[@]}/$TOTAL_MODELS"
log "Failed Models: ${#FAILED_MODELS[@]}/$TOTAL_MODELS"
log ""

if [ ${#SUCCESSFUL_MODELS[@]} -gt 0 ]; then
    log_success "Successfully trained models:"
    for MODEL in "${SUCCESSFUL_MODELS[@]}"; do
        log "  ✓ $MODEL"
    done
fi

if [ ${#FAILED_MODELS[@]} -gt 0 ]; then
    log ""
    log_error "Failed models:"
    for MODEL in "${FAILED_MODELS[@]}"; do
        log "  ✗ $MODEL"
    done
fi

log ""
log "Log file: $LOG_FILE"
log ""

if [ ${#FAILED_MODELS[@]} -gt 0 ]; then
    log_warning "Some models failed. Check log file for details."
    exit 1
else
    log_success "All ML models trained successfully!"
    exit 0
fi
