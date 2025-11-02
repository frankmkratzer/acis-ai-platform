#!/bin/bash

##############################################################################
# Daily Data Pipeline Script
# Purpose: Refresh data and materialized views without ML/RL training
# Frequency: Run daily (automated via cron)
# Duration: ~5 minutes
##############################################################################

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs/pipeline"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/daily_data_${TIMESTAMP}.log"

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
    log_error "Pipeline failed at step: $CURRENT_STEP"
    log_error "Check log file: $LOG_FILE"
    exit 1
}

trap error_handler ERR

##############################################################################
# STEP 1: Data Validation
##############################################################################

CURRENT_STEP="Data Validation"
log "════════════════════════════════════════════════════════════════"
log "STEP 1: Data Validation"
log "════════════════════════════════════════════════════════════════"

# Check database connectivity
log "Checking database connectivity..."
if PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -c "SELECT 1" > /dev/null 2>&1; then
    log_success "Database connection successful"
else
    log_error "Cannot connect to database"
    exit 1
fi

# Validate critical tables have recent data
log "Validating data freshness..."

# Check daily_bars table
BARS_COUNT=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT COUNT(*) FROM daily_bars WHERE date >= CURRENT_DATE - INTERVAL '7 days'")

if [ "$BARS_COUNT" -gt 0 ]; then
    log_success "daily_bars table has $BARS_COUNT recent records"
else
    log_warning "daily_bars table has no recent data (last 7 days)"
fi

# Check if we have data for today or most recent trading day
TODAY=$(date +%Y-%m-%d)
RECENT_DATE=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT MAX(date) FROM daily_bars")

log "Most recent data date: $RECENT_DATE"

##############################################################################
# STEP 2: Refresh Materialized Views
##############################################################################

CURRENT_STEP="Refresh Materialized Views"
log ""
log "════════════════════════════════════════════════════════════════"
log "STEP 2: Refresh Materialized Views"
log "════════════════════════════════════════════════════════════════"

START_TIME=$(date +%s)

log "Refreshing ml_training_features materialized view..."
PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -c \
    "REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features" >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
log_success "Materialized view refreshed in ${DURATION}s"

# Get row count
VIEW_COUNT=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT COUNT(*) FROM ml_training_features")
log_success "ml_training_features now has $VIEW_COUNT rows"

##############################################################################
# STEP 3: Database Maintenance
##############################################################################

CURRENT_STEP="Database Maintenance"
log ""
log "════════════════════════════════════════════════════════════════"
log "STEP 3: Database Maintenance"
log "════════════════════════════════════════════════════════════════"

START_TIME=$(date +%s)

log "Running VACUUM ANALYZE on critical tables..."

# Vacuum analyze main tables
TABLES=("daily_bars" "ml_training_features" "fundamentals" "ticker_overview" "paper_accounts" "paper_orders" "paper_positions")

for TABLE in "${TABLES[@]}"; do
    log "  - Vacuuming $TABLE..."
    PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -c \
        "VACUUM ANALYZE $TABLE" >> "$LOG_FILE" 2>&1
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
log_success "Database maintenance completed in ${DURATION}s"

##############################################################################
# STEP 4: Generate Summary Report
##############################################################################

CURRENT_STEP="Summary Report"
log ""
log "════════════════════════════════════════════════════════════════"
log "STEP 4: Summary Report"
log "════════════════════════════════════════════════════════════════"

# Database size
DB_SIZE=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT pg_size_pretty(pg_database_size('acis-ai'))")
log "Database size: $DB_SIZE"

# Table counts
log ""
log "Table Statistics:"
log "  - daily_bars: $(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c 'SELECT COUNT(*) FROM daily_bars') rows"
log "  - ml_training_features: $(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c 'SELECT COUNT(*) FROM ml_training_features') rows"
log "  - ticker_overview: $(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c 'SELECT COUNT(*) FROM ticker_overview') rows"
log "  - paper_accounts: $(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c 'SELECT COUNT(*) FROM paper_accounts') rows"
log "  - paper_positions: $(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c 'SELECT COUNT(*) FROM paper_positions') rows"

# Active clients
ACTIVE_CLIENTS=$(PGPASSWORD="${DB_PASSWORD}" psql -U postgres -d acis-ai -h localhost -t -c \
    "SELECT COUNT(*) FROM clients WHERE status = 'active'")
log "  - Active clients: $ACTIVE_CLIENTS"

##############################################################################
# COMPLETION
##############################################################################

log ""
log "════════════════════════════════════════════════════════════════"
log_success "Daily Data Pipeline Completed Successfully!"
log "════════════════════════════════════════════════════════════════"
log "Log file: $LOG_FILE"
log ""
log "Next Steps:"
log "  - Weekly ML training runs on Sundays (use run_weekly_ml_training.sh)"
log "  - Monthly RL training runs on 1st of month (use run_monthly_rl_training.sh)"
log ""

exit 0
