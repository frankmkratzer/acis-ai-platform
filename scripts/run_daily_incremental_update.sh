#!/bin/bash
################################################################################
# Daily Incremental Model Update Script
#
# Purpose:
#   - Runs daily incremental updates for all ML/RL models
#   - Fast updates using last 7 days of data
#   - Complements weekly/monthly full retraining
#
# Schedule:
#   - Daily (via cron): 2:00 AM
#   - Takes ~5-10 minutes (much faster than full retraining)
#
# Usage:
#   ./scripts/run_daily_incremental_update.sh
################################################################################

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/daily_updates"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/incremental_update_$TIMESTAMP.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=================================================="
log "DAILY INCREMENTAL MODEL UPDATE"
log "=================================================="
log "Started at: $(date)"
log ""

# Activate virtual environment
cd "$PROJECT_ROOT" || exit 1
source venv/bin/activate

# Model configurations
STRATEGIES=("growth" "value" "dividend")
MARKET_CAPS=("small" "mid" "large")
DAYS=7  # Use last 7 days of data
ML_ITERATIONS=100  # Fewer iterations for incremental
RL_TIMESTEPS=50000  # Fewer timesteps for incremental

#-------------------------------------------------------------------------------
# 1. Incremental ML Model Updates
#-------------------------------------------------------------------------------
log "Step 1: Incremental ML Model Updates"
log "-------------------------------------"

ML_SUCCESS=0
ML_TOTAL=0

for strategy in "${STRATEGIES[@]}"; do
    for market_cap in "${MARKET_CAPS[@]}"; do
        ML_TOTAL=$((ML_TOTAL + 1))
        log ""
        log "Updating ML model: $strategy $market_cap"

        if python ml_models/incremental_train_xgboost.py \
            --strategy "$strategy" \
            --market-cap "$market_cap" \
            --mode incremental \
            --days "$DAYS" \
            --iterations "$ML_ITERATIONS" \
            >> "$LOG_FILE" 2>&1; then

            log "✓ ML model updated: $strategy $market_cap"
            ML_SUCCESS=$((ML_SUCCESS + 1))
        else
            log "✗ ML model update failed: $strategy $market_cap"
        fi
    done
done

log ""
log "ML Update Summary: $ML_SUCCESS / $ML_TOTAL models updated successfully"

#-------------------------------------------------------------------------------
# 2. Incremental RL Agent Updates (Optional - comment out if too slow)
#-------------------------------------------------------------------------------
log ""
log "Step 2: Incremental RL Agent Updates"
log "-------------------------------------"

# Note: RL incremental updates are optional for daily runs
# Uncomment if you want daily RL fine-tuning (will take longer)

# RL_SUCCESS=0
# RL_TOTAL=0
#
# for strategy in "${STRATEGIES[@]}"; do
#     for market_cap in "${MARKET_CAPS[@]}"; do
#         RL_TOTAL=$((RL_TOTAL + 1))
#         log ""
#         log "Updating RL agent: $strategy $market_cap"
#
#         if python rl_trading/incremental_train_ppo.py \
#             --strategy "$strategy" \
#             --market-cap "$market_cap" \
#             --mode incremental \
#             --timesteps "$RL_TIMESTEPS" \
#             --device auto \
#             >> "$LOG_FILE" 2>&1; then
#
#             log "✓ RL agent updated: $strategy $market_cap"
#             RL_SUCCESS=$((RL_SUCCESS + 1))
#         else
#             log "✗ RL agent update failed: $strategy $market_cap"
#         fi
#     done
# done
#
# log ""
# log "RL Update Summary: $RL_SUCCESS / $RL_TOTAL agents updated successfully"

log "Note: RL incremental updates are disabled by default for daily runs."
log "Enable them in the script if you need daily RL fine-tuning."

#-------------------------------------------------------------------------------
# 3. Summary
#-------------------------------------------------------------------------------
log ""
log "=================================================="
log "DAILY UPDATE SUMMARY"
log "=================================================="
log "ML Models Updated: $ML_SUCCESS / $ML_TOTAL"
# log "RL Agents Updated: $RL_SUCCESS / $RL_TOTAL"
log "Duration: $SECONDS seconds"
log "Log file: $LOG_FILE"
log "Completed at: $(date)"
log "=================================================="

# Exit with success if all updates succeeded
if [ "$ML_SUCCESS" -eq "$ML_TOTAL" ]; then
    log "✓ All daily updates completed successfully"
    exit 0
else
    log "✗ Some daily updates failed - check logs"
    exit 1
fi
