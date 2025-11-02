#!/bin/bash
#
# Daily Autonomous Rebalancing Wrapper Script
#
# This script is intended to be run daily via cron job.
# It activates the virtual environment and runs the rebalancing script.
#
# Cron example (run daily at 4:30 PM ET, after market close):
#   30 16 * * 1-5 /home/fkratzer/acis-ai-platform/scripts/run_daily_rebalance.sh
#

set -e  # Exit on error

# Change to project directory
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Set timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="logs/rebalancing"
mkdir -p "$LOG_DIR"

# Log file
LOG_FILE="$LOG_DIR/rebalance_${TIMESTAMP}.log"

echo "==================================================================" | tee -a "$LOG_FILE"
echo "Daily Autonomous Rebalancing - $(date)" | tee -a "$LOG_FILE"
echo "==================================================================" | tee -a "$LOG_FILE"

# Run in paper trading mode by default
# Change to --live for real trading (after testing!)
python scripts/run_daily_rebalance.py \
    --paper-trading \
    --account-id PAPER_AUTONOMOUS_FUND \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Rebalancing completed successfully" | tee -a "$LOG_FILE"
else
    echo "❌ Rebalancing failed with exit code $EXIT_CODE" | tee -a "$LOG_FILE"
fi

echo "Log saved to: $LOG_FILE"

exit $EXIT_CODE
