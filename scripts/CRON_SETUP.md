# Cron Setup for Auto-Training

## Daily Model Training

Run daily at 6 PM Pacific (after market close) to retrain all ML models with latest data.

### Installation

Edit your crontab:
```bash
crontab -e
```

Add this line:
```
# ACIS AI - Daily model auto-training (6 PM Pacific)
0 18 * * * /home/fkratzer/acis-ai-platform/scripts/run_daily_training.sh
```

**Note**: This assumes your system timezone is set to Pacific. Verify with `date` command.

### Manual Execution

To run training manually:
```bash
cd /home/fkratzer/acis-ai-platform
./scripts/run_daily_training.sh
```

Or with specific models:
```bash
python scripts/auto_train_models.py --models growth_midcap value_largecap
```

### Logs

Training logs are saved to:
```
logs/auto_training_YYYYMMDD.log
```

View recent training status:
```sql
SELECT * FROM latest_training_status ORDER BY trained_at DESC;
```

### Monitoring

Check if cron job is running:
```bash
pgrep -f auto_train_models
```

View last 50 lines of today's log:
```bash
tail -50 logs/auto_training_$(date +%Y%m%d).log
```

### Troubleshooting

If training fails:
1. Check the log file for errors
2. Verify database connection
3. Check GPU availability (if using)
4. Ensure virtual environment is activated

Test the script manually:
```bash
cd /home/fkratzer/acis-ai-platform
source venv/bin/activate
python scripts/auto_train_models.py --models growth_midcap
```
