#!/bin/bash
#
# Monitor auto-training progress
#

LOG_FILE="logs/test_orchestrator.log"

if [ ! -f "$LOG_FILE" ]; then
    LOG_FILE="logs/auto_training_$(date +%Y%m%d).log"
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "No training log found"
    echo "Looking for: $LOG_FILE"
    exit 1
fi

echo "==================================="
echo "Auto-Training Progress Monitor"
echo "==================================="
echo "Log file: $LOG_FILE"
echo ""

# Check if training is running
if pgrep -f "auto_train_models.py" > /dev/null; then
    echo "Status: TRAINING IN PROGRESS"
    echo ""

    # Show current model being trained
    echo "Current model:"
    grep "TRAINING ML MODEL:" "$LOG_FILE" | tail -1
    echo ""

    # Show progress
    echo "Latest activity:"
    tail -20 "$LOG_FILE" | grep -E "INFO|ERROR|WARNING" | tail -5
else
    echo "Status: NOT RUNNING"
    echo ""

    # Show last training summary
    echo "Last training summary:"
    grep -A 10 "TRAINING SUMMARY" "$LOG_FILE" | tail -11
fi

echo ""
echo "==================================="
echo "Commands:"
echo "  tail -f $LOG_FILE       # Follow log in real-time"
echo "  cat $LOG_FILE           # View full log"
echo "==================================="
