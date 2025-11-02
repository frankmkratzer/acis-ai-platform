# End-of-Day Pipeline

Comprehensive daily workflow that runs after market close to process data and update models.

## Pipeline Steps

### 1. Data Validation
- Checks if today's market data is available
- Validates data completeness

### 2. Refresh Materialized Views
- Refreshes `ml_training_features` view with latest data
- Ensures all models train on current data
- Takes 2-3 minutes

### 3. Train ML Models (XGBoost)
- Trains all 7 ML models for stock selection:
  - Growth: small, mid, large cap
  - Value: small, mid, large cap
  - Dividend: single model
- Uses data from 2015-present
- Takes 30-60 minutes with GPU
- Logs all results to database

### 4. Train RL Models (PPO)
- Trains all 7 RL agents for portfolio allocation:
  - Growth: small, mid, large cap
  - Value: small, mid, large cap
  - Dividend: single model
- Uses Proximal Policy Optimization (PPO)
- 1M timesteps per model
- Takes 2-4 hours with CPU (recommended)
- Logs all results to database

### 5. Database Maintenance
- Runs VACUUM ANALYZE on key tables
- Optimizes query performance

### 6. Summary Report
- Generates training statistics
- Shows model performance for both ML and RL
- Logs results for monitoring

## Usage

### Manual Execution

Run the complete EOD pipeline:
```bash
./scripts/run_eod_pipeline.sh
```

Run only model training:
```bash
source venv/bin/activate
python scripts/auto_train_models.py --gpu
```

### Automated Execution

The pipeline runs automatically via cron at 6 PM Pacific daily.

Install cron job:
```bash
./scripts/install_cron.sh
```

Verify cron is installed:
```bash
crontab -l | grep "ACIS AI"
```

## Monitoring

### Check if pipeline is running
```bash
pgrep -f "eod_pipeline"
```

### View live progress
```bash
tail -f logs/eod_pipeline_*.log
```

### View today's results
```bash
ls -lt logs/eod_pipeline_*.log | head -1 | xargs cat
```

### Check training status
```sql
SELECT * FROM latest_training_status ORDER BY trained_at DESC;
```

### View training history
```sql
SELECT
    DATE(trained_at) as date,
    COUNT(*) as models_trained,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(duration_minutes)::numeric, 1) as avg_duration_min
FROM auto_training_log
GROUP BY DATE(trained_at)
ORDER BY date DESC
LIMIT 30;
```

## Pipeline Schedule

```
4:00 PM PT - Market closes
6:00 PM PT - EOD pipeline starts (2 hour buffer for data ingestion)
6:03 PM PT - ML model training begins
7:00 PM PT - Pipeline typically completes
```

## Logs

All pipeline runs create timestamped logs:
```
logs/eod_pipeline_YYYYMMDD_HHMMSS.log
```

## Troubleshooting

### Pipeline fails at materialized view refresh
```bash
# Check PostgreSQL connection
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "\dt"

# Manually refresh view
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "
    REFRESH MATERIALIZED VIEW ml_training_features;
"
```

### Model training fails
```bash
# Check GPU availability
nvidia-smi

# Run single model test
source venv/bin/activate
python scripts/auto_train_models.py --models growth_midcap --gpu

# Check training log
tail -100 logs/eod_pipeline_*.log | grep ERROR
```

### Pipeline doesn't run
```bash
# Check if cron job exists
crontab -l

# Check cron logs
grep CRON /var/log/syslog | tail -20

# Test script manually
./scripts/run_eod_pipeline.sh
```

## Customization

### Change pipeline schedule
Edit crontab:
```bash
crontab -e
# Change: 0 18 * * * to desired time
```

### Skip certain steps
Edit `scripts/run_eod_pipeline.sh` and comment out unwanted sections

### Add new models
Edit `scripts/auto_train_models.py` and add to `ML_MODEL_CONFIGS` list

## Performance

Typical execution times:
- Data validation: < 1 second
- Materialized view refresh: 2-3 minutes
- ML model training (7 models): 30-60 minutes with GPU
- RL model training (7 models): 2-4 hours with CPU
- Database maintenance: 10-30 seconds
- **Total: 3-5 hours**

Notes:
- ML training uses GPU acceleration (~10x faster than CPU)
- RL training recommended on CPU for PPO+MLP architecture
- Can run ML and RL training in parallel to reduce total time (advanced)
