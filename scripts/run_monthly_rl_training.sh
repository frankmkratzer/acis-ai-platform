#!/bin/bash

##############################################################################
# Monthly RL Training Script
# Purpose: Retrain all RL agents (PPO) for portfolio optimization
# Frequency: Run monthly on the 1st (automated via cron)
# Duration: ~2-4 hours
##############################################################################

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/pipeline"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/monthly_rl_${TIMESTAMP}.log"

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
    log_error "RL training failed at: $CURRENT_AGENT"
    log_error "Check log file: $LOG_FILE"
    exit 1
}

trap error_handler ERR

##############################################################################
# Pre-Training Validation
##############################################################################

log "════════════════════════════════════════════════════════════════"
log "Monthly RL Training Pipeline"
log "════════════════════════════════════════════════════════════════"
log ""

# Activate virtual environment
cd "$PROJECT_DIR"
source venv/bin/activate

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    GPU_AVAILABLE=true
    log_success "GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | tee -a "$LOG_FILE"
    DEVICE="cuda"
else
    GPU_AVAILABLE=false
    log_warning "No GPU detected. Training will use CPU (slower)"
    DEVICE="cpu"
fi

# Check if ML models exist (RL training requires them)
log ""
log "Validating ML models..."
ML_MODEL_DIR="$PROJECT_DIR/models/ml"
ML_MODEL_COUNT=$(find "$ML_MODEL_DIR" -name "*.joblib" 2>/dev/null | wc -l)

if [ "$ML_MODEL_COUNT" -lt 1 ]; then
    log_error "No ML models found in $ML_MODEL_DIR"
    log_error "Please run weekly ML training first (run_weekly_ml_training.sh)"
    exit 1
else
    log_success "Found $ML_MODEL_COUNT ML models"
fi

##############################################################################
# Train RL Agents
##############################################################################

PIPELINE_START=$(date +%s)

# Define all RL agents to train
STRATEGIES=("growth" "momentum" "dividend" "value")
MARKET_CAPS=("large" "mid" "small")

# RL training parameters
TIMESTEPS=500000  # More timesteps for production models
EVAL_FREQ=50000
SAVE_FREQ=50000

TOTAL_AGENTS=$((${#STRATEGIES[@]} * ${#MARKET_CAPS[@]}))
CURRENT_AGENT_NUM=0
FAILED_AGENTS=()
SUCCESSFUL_AGENTS=()

log ""
log "Training $TOTAL_AGENTS RL agents (${#STRATEGIES[@]} strategies × ${#MARKET_CAPS[@]} market caps)"
log "Training parameters: timesteps=$TIMESTEPS, device=$DEVICE"
log ""

for STRATEGY in "${STRATEGIES[@]}"; do
    for MARKET_CAP in "${MARKET_CAPS[@]}"; do
        CURRENT_AGENT_NUM=$((CURRENT_AGENT_NUM + 1))
        CURRENT_AGENT="${STRATEGY}_${MARKET_CAP}"

        log "════════════════════════════════════════════════════════════════"
        log "[$CURRENT_AGENT_NUM/$TOTAL_AGENTS] Training RL Agent: $CURRENT_AGENT"
        log "════════════════════════════════════════════════════════════════"

        AGENT_START=$(date +%s)

        # Train the agent using hybrid PPO
        if python rl_trading/train_hybrid_ppo.py \
            --strategy "$STRATEGY" \
            --market-cap "$MARKET_CAP" \
            --timesteps "$TIMESTEPS" \
            --eval-freq "$EVAL_FREQ" \
            --save-freq "$SAVE_FREQ" \
            --device "$DEVICE" \
            >> "$LOG_FILE" 2>&1; then

            AGENT_END=$(date +%s)
            AGENT_DURATION=$((AGENT_END - AGENT_START))
            AGENT_MINUTES=$((AGENT_DURATION / 60))
            AGENT_SECONDS=$((AGENT_DURATION % 60))
            log_success "Agent $CURRENT_AGENT trained successfully in ${AGENT_MINUTES}m ${AGENT_SECONDS}s"
            SUCCESSFUL_AGENTS+=("$CURRENT_AGENT")
        else
            AGENT_END=$(date +%s)
            AGENT_DURATION=$((AGENT_END - AGENT_START))
            AGENT_MINUTES=$((AGENT_DURATION / 60))
            AGENT_SECONDS=$((AGENT_DURATION % 60))
            log_error "Agent $CURRENT_AGENT failed after ${AGENT_MINUTES}m ${AGENT_SECONDS}s"
            FAILED_AGENTS+=("$CURRENT_AGENT")
        fi

        log ""

        # Clear GPU memory between runs if using GPU
        if [ "$GPU_AVAILABLE" = true ]; then
            log "Clearing GPU memory..."
            sleep 5
        fi
    done
done

##############################################################################
# Summary Report
##############################################################################

PIPELINE_END=$(date +%s)
TOTAL_DURATION=$((PIPELINE_END - PIPELINE_START))
HOURS=$((TOTAL_DURATION / 3600))
MINUTES=$(((TOTAL_DURATION % 3600) / 60))
SECONDS=$((TOTAL_DURATION % 60))

log "════════════════════════════════════════════════════════════════"
log "Monthly RL Training Summary"
log "════════════════════════════════════════════════════════════════"
log ""
log "Total Duration: ${HOURS}h ${MINUTES}m ${SECONDS}s"
log "Successful Agents: ${#SUCCESSFUL_AGENTS[@]}/$TOTAL_AGENTS"
log "Failed Agents: ${#FAILED_AGENTS[@]}/$TOTAL_AGENTS"
log ""

if [ ${#SUCCESSFUL_AGENTS[@]} -gt 0 ]; then
    log_success "Successfully trained agents:"
    for AGENT in "${SUCCESSFUL_AGENTS[@]}"; do
        # Get model file size
        MODEL_PATH="$PROJECT_DIR/models/rl/${AGENT}_ppo.zip"
        if [ -f "$MODEL_PATH" ]; then
            MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
            log "  ✓ $AGENT ($MODEL_SIZE)"
        else
            log "  ✓ $AGENT"
        fi
    done
fi

if [ ${#FAILED_AGENTS[@]} -gt 0 ]; then
    log ""
    log_error "Failed agents:"
    for AGENT in "${FAILED_AGENTS[@]}"; do
        log "  ✗ $AGENT"
    done
fi

log ""
log "Log file: $LOG_FILE"
log ""

if [ ${#FAILED_AGENTS[@]} -gt 0 ]; then
    log_warning "Some agents failed. Check log file for details."
    exit 1
else
    log_success "All RL agents trained successfully!"
    exit 0
fi
