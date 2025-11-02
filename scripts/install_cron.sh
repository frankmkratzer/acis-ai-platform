#!/bin/bash
#
# Install cron job for daily auto-training
#

CRON_JOB="0 18 * * * /home/fkratzer/acis-ai-platform/scripts/run_daily_training.sh"
CRON_COMMENT="# ACIS AI - Daily model auto-training (6 PM Pacific)"

echo "Installing cron job for daily auto-training..."
echo "Schedule: Daily at 6:00 PM Pacific"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_daily_training.sh"; then
    echo "Cron job already exists!"
    echo "Current crontab:"
    crontab -l | grep -A1 "ACIS AI"
    echo ""
    read -p "Replace existing job? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
    # Remove old job
    crontab -l | grep -v "run_daily_training.sh" | grep -v "ACIS AI - Daily" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMENT"; echo "$CRON_JOB") | crontab -

echo "✅ Cron job installed successfully!"
echo ""
echo "Installed job:"
crontab -l | grep -A1 "ACIS AI"
echo ""
echo "To view all cron jobs: crontab -l"
echo "To edit cron jobs: crontab -e"
echo "To remove this job: crontab -e (then delete the ACIS AI lines)"
echo ""
echo "Next run: Today at 6:00 PM Pacific (if current time < 6 PM)"
echo "Logs will be saved to: logs/auto_training_YYYYMMDD.log"
