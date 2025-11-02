#!/usr/bin/env bash
# Backfill Runner Script
# Runs backfill scripts with proper logging to logs/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Usage function
usage() {
    echo "Usage: $0 <script_name>"
    echo ""
    echo "Available scripts:"
    echo "  daily_bars"
    echo "  dividends"
    echo "  splits"
    echo "  balance_sheets"
    echo "  income_statements"
    echo "  cash_flow_statements"
    echo "  ratios"
    echo "  short_interest"
    echo "  sma"
    echo "  ema"
    echo "  rsi"
    echo "  macd"
    echo "  news"
    echo "  ipos"
    echo "  ticker_events"
    echo "  ticker_overview"
    echo "  tickers"
    echo "  exchanges"
    echo "  market_holidays"
    echo ""
    echo "Example: $0 daily_bars"
    exit 1
}

# Check if script name provided
if [ -z "$1" ]; then
    usage
fi

SCRIPT_NAME="$1"
SCRIPT_FILE="$SCRIPT_DIR/populate_${SCRIPT_NAME}.py"
LOG_FILE="$LOGS_DIR/${SCRIPT_NAME}_backfill.log"

# Check if script exists
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "Error: Script not found: $SCRIPT_FILE"
    echo ""
    usage
fi

# Run the script with logging
echo "Running backfill script: $SCRIPT_NAME"
echo "Log file: $LOG_FILE"
echo ""

cd "$PROJECT_ROOT"
python "$SCRIPT_FILE" 2>&1 | tee "$LOG_FILE"

echo ""
echo "Backfill complete. Check log file for details: $LOG_FILE"
