# Emergency Model Rollback Runbook

## When to Use This Runbook

Use this runbook when a production model is performing poorly and needs immediate rollback:

- Model predictions are significantly degraded
- Sharpe ratio dropped below acceptable threshold
- Large unexpected losses in paper/live trading
- Model errors or crashes
- Data quality issues affecting predictions

**Severity**: 🔴 CRITICAL - Execute immediately to stop losses

---

## Pre-Rollback Checklist

Before rolling back, quickly verify:

- [ ] Issue is confirmed (not a temporary market condition)
- [ ] Have access to database and model files
- [ ] Know which model is problematic
- [ ] Have backup or previous version available

---

## Step 1: Identify the Problem Model (2 minutes)

### Check which models are in production:

```bash
# Query production models
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost << 'EOF'
SELECT
  model_name,
  deployed_at,
  deployed_by,
  spearman_ic,
  sharpe_ratio
FROM model_deployment_log
WHERE is_production = true
ORDER BY deployed_at DESC
LIMIT 5;
EOF
```

### Review recent model performance:

```bash
# Check recent predictions vs actual
python ml_models/evaluate_production_model.py --last-n-days 7
```

### Identify the problematic model:
- Model name: `_________________`
- Deployed date: `_________________`
- Issue: `_________________`

---

## Step 2: Stop Automated Trading (1 minute)

**CRITICAL**: Prevent further trades using the bad model.

### Option A: Disable rebalancing

```bash
# Stop any running rebalance processes
pkill -f "run_daily_rebalance"

# Check no rebalance is running
ps aux | grep rebalance
```

### Option B: Set manual approval mode (if available)

```sql
UPDATE client_settings
SET auto_rebalance = false,
    require_manual_approval = true
WHERE client_id IN (SELECT client_id FROM clients WHERE active = true);
```

### Verification:
```bash
# Confirm no trades are being executed
tail -f logs/trading.log
# Should see no new trade entries
```

---

## Step 3: List Available Backup Models (2 minutes)

```bash
# List backup versions
MODEL_DIR="models/{strategy}_{marketcap}"
ls -lht $MODEL_DIR/

# Show metadata for recent backups
for backup in $MODEL_DIR/backup_*/metadata.json; do
    echo "=== $backup ==="
    cat $backup | jq '{
        deployed_at: .training_date,
        spearman_ic: .performance.spearman_ic,
        sharpe_ratio: .performance.sharpe_ratio
    }'
    echo ""
done
```

### Select rollback target:
- Target version: `_________________`
- Target date: `_________________`
- Target Sharpe: `_________________`

---

## Step 4: Execute Rollback (3 minutes)

### Backup current production model:

```bash
MODEL_NAME="{strategy}_{marketcap}"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p models/$MODEL_NAME/backup_emergency_$TIMESTAMP
cp models/$MODEL_NAME/model.json models/$MODEL_NAME/backup_emergency_$TIMESTAMP/
cp models/$MODEL_NAME/metadata.json models/$MODEL_NAME/backup_emergency_$TIMESTAMP/

echo "✅ Current model backed up to backup_emergency_$TIMESTAMP"
```

### Restore previous version:

```bash
# Replace with your selected backup version
BACKUP_VERSION="backup_2025-10-15"

cp models/$MODEL_NAME/$BACKUP_VERSION/model.json models/$MODEL_NAME/
cp models/$MODEL_NAME/$BACKUP_VERSION/metadata.json models/$MODEL_NAME/

echo "✅ Rolled back to $BACKUP_VERSION"
```

### Update database:

```sql
-- Log the rollback
INSERT INTO model_deployment_log (
  model_name,
  version,
  deployed_at,
  deployed_by,
  deployment_reason,
  is_production,
  is_rollback
) VALUES (
  '{MODEL_NAME}',
  '{BACKUP_VERSION}',
  NOW(),
  'emergency_rollback',
  'Emergency rollback due to: {REASON}',
  TRUE,
  TRUE
);

-- Mark previous as not production
UPDATE model_deployment_log
SET is_production = FALSE
WHERE model_name = '{MODEL_NAME}'
  AND deployed_at < NOW()
  AND is_production = TRUE;
```

---

## Step 5: Verify Rollback (2 minutes)

### Test model loads:

```python
# Test model can be loaded
python3 << 'EOF'
import xgboost as xgb
import json

model_path = "models/{MODEL_NAME}/model.json"
metadata_path = "models/{MODEL_NAME}/metadata.json"

# Load model
model = xgb.XGBClassifier()
model.load_model(model_path)
print("✅ Model loaded successfully")

# Check metadata
with open(metadata_path) as f:
    metadata = json.load(f)
    print(f"Model version: {metadata.get('training_date')}")
    print(f"Sharpe ratio: {metadata['performance']['sharpe_ratio']}")

print("✅ Rollback verified")
EOF
```

### Run quick prediction test:

```bash
# Test predictions on recent data
python ml_models/test_model_prediction.py \
  --model {MODEL_NAME} \
  --test-date $(date -d "yesterday" +%Y-%m-%d)
```

---

## Step 6: Re-enable Trading (1 minute)

### Turn automated trading back on:

```sql
-- Re-enable auto-rebalancing for clients
UPDATE client_settings
SET auto_rebalance = true,
    require_manual_approval = false
WHERE client_id IN (SELECT client_id FROM clients WHERE active = true);
```

### Monitor for next 30 minutes:

```bash
# Watch logs for any issues
tail -f logs/trading.log

# Watch for errors
tail -f logs/api.log | grep -i error
```

---

## Step 7: Post-Rollback Actions (15 minutes)

### Document the incident:

```bash
# Create incident report
cat > incidents/model_rollback_$(date +%Y%m%d).md << 'EOF'
# Model Rollback Incident Report

**Date**: $(date)
**Model**: {MODEL_NAME}
**Severity**: CRITICAL

## Issue Description
{Describe what went wrong}

## Impact
- Affected portfolios: {COUNT}
- Duration: {START} to {END}
- Estimated loss: ${AMOUNT}

## Root Cause
{What caused the model to fail}

## Actions Taken
1. Stopped automated trading
2. Rolled back to version: {BACKUP_VERSION}
3. Re-enabled trading
4. Monitoring for 24 hours

## Prevention
{How to prevent this in the future}

## Next Steps
1. Investigate root cause
2. Retrain model with fixes
3. Enhanced monitoring
4. Update deployment checklist
EOF
```

### Notify stakeholders:

```bash
# Send alert (if email configured)
echo "Production model {MODEL_NAME} rolled back at $(date). Issue: {REASON}" | \
  mail -s "ALERT: Model Rollback" team@acis.ai
```

### Set up enhanced monitoring:

```bash
# Monitor model performance closely for next 24 hours
# Add to crontab:
# */30 * * * * python /path/to/ml_models/monitor_production_performance.py
```

---

## Step 8: Root Cause Analysis (Next 2 hours)

### Investigate what went wrong:

1. **Data Quality Issues**
   ```sql
   -- Check for data anomalies
   SELECT date, COUNT(*) as ticker_count
   FROM daily_bars
   WHERE date >= CURRENT_DATE - INTERVAL '7 days'
   GROUP BY date
   ORDER BY date DESC;

   -- Check for NULL features
   SELECT COUNT(*) FROM ml_training_features WHERE return_1d IS NULL;
   ```

2. **Model Training Issues**
   ```bash
   # Review training logs
   grep -i "error\|warning\|nan" logs/growth_momentum.log

   # Check feature distributions
   python ml_models/analyze_feature_distributions.py --model {MODEL_NAME}
   ```

3. **Market Regime Change**
   ```bash
   # Check if market conditions changed significantly
   python analysis/detect_regime_change.py --last-n-days 30
   ```

---

## Common Issues and Quick Fixes

### Issue: Model file corrupted
**Fix**: Restore from backup immediately
```bash
cp models/{MODEL_NAME}/backup_*/model.json models/{MODEL_NAME}/
```

### Issue: Database connection failed
**Fix**: Check PostgreSQL status
```bash
systemctl status postgresql
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -h localhost -c "SELECT 1;"
```

### Issue: Feature view out of date
**Fix**: Refresh materialized view
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features;
```

### Issue: Model overfitted to recent data
**Fix**: Retrain with longer historical period
```bash
python ml_models/train_xgboost.py \
  --strategy {strategy} \
  --market-cap {marketcap} \
  --start-date 2015-01-01
```

---

## Rollback Complete Checklist

- [ ] Bad model stopped from making predictions
- [ ] Previous model version restored
- [ ] Database updated with rollback record
- [ ] Model loads and predicts correctly
- [ ] Trading re-enabled
- [ ] Logs monitored for 30 minutes
- [ ] Incident documented
- [ ] Stakeholders notified
- [ ] Root cause analysis initiated
- [ ] Prevention measures identified

---

## Escalation

If rollback doesn't resolve the issue or you need help:

1. **Check for system-wide issues**: Database, API, data pipeline
2. **Contact**: {PRIMARY_CONTACT}
3. **Emergency contact**: {BACKUP_CONTACT}
4. **Escalation criteria**: Losses exceed ${THRESHOLD} or issue persists >2 hours

---

## Recovery Timeline

| Time | Action |
|------|--------|
| T+0 min | Issue identified |
| T+2 min | Trading stopped |
| T+5 min | Rollback executed |
| T+7 min | Rollback verified |
| T+10 min | Trading resumed |
| T+30 min | Monitoring complete |
| T+2 hours | Root cause identified |
| T+24 hours | Enhanced monitoring |

---

**Last Updated**: 2025-11-02
**Review Frequency**: After each incident
**Owner**: Platform Team
