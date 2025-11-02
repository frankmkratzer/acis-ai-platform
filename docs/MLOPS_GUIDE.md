# ACIS AI Platform - MLOps Guide

**Last Updated:** January 2025

## Overview

This guide covers the MLOps (Machine Learning Operations) infrastructure in ACIS AI Platform, including MLflow integration, data drift detection, automated retraining pipelines, and model lifecycle management.

## Table of Contents

- [MLflow Setup](#mlflow-setup)
- [Model Training with MLflow](#model-training-with-mlflow)
- [Model Registry](#model-registry)
- [Data Drift Detection](#data-drift-detection)
- [Automated Retraining](#automated-retraining)
- [Model Versioning](#model-versioning)
- [Using the UI](#using-the-ui)

## MLflow Setup

### Local Development

Start MLflow server using Docker Compose:

```bash
cd mlops/mlflow
docker-compose -f docker-compose.mlflow.yml up -d
```

Access MLflow UI at: http://localhost:5000

### Production (Kubernetes)

Deploy MLflow to Kubernetes:

```bash
kubectl apply -f k8s/base/mlflow-deployment.yaml
```

MLflow will:
- Use PostgreSQL for backend metadata storage
- Store artifacts in persistent volume (50Gi)
- Be accessible at `mlflow.acis-ai.svc.cluster.local:5000`

## Model Training with MLflow

### Training XGBoost Models

Use the MLflow-integrated training script:

```bash
# Train a single strategy
python mlops/mlflow/train_with_mlflow.py --strategy growth

# Train and auto-promote to production if meets criteria
python mlops/mlflow/train_with_mlflow.py --strategy growth --promote
```

The script will:
1. Load training data from `ml_training_features` view
2. Train XGBoost model with configured parameters
3. Log all parameters, metrics, and artifacts to MLflow
4. Register model in MLflow Model Registry
5. (Optional) Promote to Production if accuracy > 70%

### What Gets Logged

**Parameters:**
- All XGBoost hyperparameters (max_depth, learning_rate, etc.)
- Training configuration (train_samples, test_samples, n_features)
- Strategy name

**Metrics:**
- accuracy
- precision
- recall
- f1_score
- roc_auc

**Artifacts:**
- Trained model (model.pkl)
- Feature importance CSV
- Training plots (optional)

### Viewing in MLflow UI

1. Navigate to http://localhost:5000
2. Click on "acis-ai-models" experiment
3. View all runs with metrics comparison
4. Click into a run to see details

## Model Registry

### Model Stages

MLflow supports stage-based model promotion:

- **None**: Newly registered models
- **Staging**: Models being tested/validated
- **Production**: Active models used for inference
- **Archived**: Old versions no longer in use

### Registering a Model

Models are automatically registered during training:

```python
from mlops.mlflow.mlflow_client import ACISMLflowClient

client = ACISMLflowClient()

# During training
client.log_model(
    model=xgb_model,
    artifact_path="model",
    registered_model_name="acis_growth_classifier",
    signature=signature,
    input_example=X_train.head(5)
)
```

### Promoting to Production

**Automatic Promotion** (if meets criteria):
```python
from mlops.mlflow.train_with_mlflow import promote_model_to_production

promoted = promote_model_to_production(
    model_name="acis_growth_classifier",
    min_accuracy=0.7
)
```

**Manual Promotion** (via UI or CLI):
```python
client.transition_model_stage(
    name="acis_growth_classifier",
    version="3",
    stage="Production",
    archive_existing=True  # Archive current production version
)
```

### Loading Production Models

```python
# Load latest production model
model_uri = "models:/acis_growth_classifier/Production"
model = client.load_model(model_uri)

# Use for inference
predictions = model.predict(X_new)
```

## Data Drift Detection

### Overview

Data drift detection monitors whether the distribution of incoming data has changed significantly compared to the reference (training) data. If drift is detected, it may be time to retrain models.

### Methods Implemented

**1. Kolmogorov-Smirnov (KS) Test**
- Statistical test for distribution similarity
- P-value < 0.05 indicates significant drift
- Fast and works well for continuous features

**2. Population Stability Index (PSI)**
- Measures shift in population distribution
- PSI < 0.1: No significant change
- 0.1 ≤ PSI < 0.2: Moderate change
- PSI ≥ 0.2: Significant change (retraining recommended)

### Running Drift Detection

**From Command Line:**
```bash
python mlops/drift_detection/drift_detector.py \
    --strategy growth \
    --alert-threshold 0.3
```

**From Python:**
```python
from mlops.drift_detection.drift_detector import monitor_drift_and_alert

needs_retraining = monitor_drift_and_alert(
    strategy="growth",
    alert_threshold=0.3  # 30% of features need drift to trigger
)
```

**From UI:**
Go to System Admin → MLOps → "Check Data Drift"

### Drift Report

Drift detection generates JSON report saved to `/tmp/drift_report_{strategy}_{date}.json`:

```json
{
  "timestamp": "2025-01-02T10:30:00",
  "n_features": 45,
  "n_samples_reference": 50000,
  "n_samples_current": 500,
  "drift_threshold": 0.05,
  "summary": {
    "drifted_features_ks": 12,
    "drifted_features_psi": 15,
    "drift_detected": true
  },
  "ks_test": {
    "pe_ratio": {"p_value": 0.001, "drifted": true},
    "momentum_50d": {"p_value": 0.15, "drifted": false}
  },
  "psi": {
    "pe_ratio": {"psi_value": 0.35, "drifted": true},
    "momentum_50d": {"psi_value": 0.08, "drifted": false}
  }
}
```

## Automated Retraining

### Auto-Retraining Pipeline

The automated retraining pipeline:
1. Checks for data drift
2. If drift detected → retrains model
3. Evaluates model performance
4. Promotes to production if meets criteria

**Run for all strategies:**
```bash
python mlops/retraining/auto_retrain.py
```

**Run for specific strategies:**
```bash
python mlops/retraining/auto_retrain.py \
    --strategies growth momentum \
    --drift-threshold 0.3 \
    --min-accuracy 0.7
```

**From UI:**
System Admin → MLOps → "Auto-Retrain All Models"

### Pipeline Output

```
Processing strategy: growth
Checking data drift for growth...
Drift report saved to: /tmp/drift_report_growth_20250102.json

Drift Detection Summary:
  Features analyzed: 45
  Features with drift (KS): 12
  Features with drift (PSI): 15
  Drift ratio: 33.33%
  Retraining threshold: 30.00%
  Retraining needed: True

Drift detected for growth. Starting retraining...
Training XGBoost model...
Retraining completed. Run ID: abc123xyz

Model: acis_growth_classifier v4
Accuracy: 0.742
Required: 0.700
✅ Model promoted to Production

Pipeline Summary:
Total strategies processed: 4
Drift detected: 2
Models retrained: 2
Promoted to production: 2
Errors: 0
```

### Scheduled Retraining

**Kubernetes CronJobs** (production):
```yaml
# Daily drift check at 3 AM UTC
apiVersion: batch/v1
kind: CronJob
metadata:
  name: model-drift-check
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: drift-check
            image: acis-ai-backend:latest
            command:
            - python
            - mlops/retraining/auto_retrain.py
            - --drift-threshold
            - "0.3"
```

**Cron** (local/VM):
```bash
# Add to crontab
0 3 * * * cd /home/fkratzer/acis-ai-platform && source venv/bin/activate && python mlops/retraining/auto_retrain.py
```

## Model Versioning

### Version Naming

Models are versioned automatically by MLflow:
- **Model Name**: `acis_{strategy}_classifier` (e.g., `acis_growth_classifier`)
- **Version**: Auto-incremented integer (1, 2, 3, ...)
- **Run ID**: Unique identifier for training run

### Model Comparison

Compare multiple model versions:

```python
from mlops.mlflow.mlflow_client import ACISMLflowClient

client = ACISMLflowClient()

# Compare all strategies in Production
comparison = client.compare_models(
    model_names=[
        "acis_growth_classifier",
        "acis_value_classifier",
        "acis_dividend_classifier"
    ],
    stage="Production"
)

print(comparison)
```

Output:
```
           model_name  version   accuracy  precision  recall  f1_score  roc_auc
0  acis_growth_classifier      3     0.742      0.738   0.725     0.731    0.821
1  acis_value_classifier       2     0.698      0.701   0.682     0.691    0.765
2  acis_dividend_classifier    4     0.715      0.710   0.698     0.704    0.788
```

### Rollback to Previous Version

If a new model performs poorly, roll back to previous version:

```python
# Transition old version back to Production
client.transition_model_stage(
    name="acis_growth_classifier",
    version="2",  # Previous stable version
    stage="Production",
    archive_existing=True
)
```

**From UI:**
System Admin → MLOps → Model Registry → Select version → "Promote to Production"

## Using the UI

### System Admin - MLOps Section

Navigate to **System Admin** page (http://192.168.50.234:3000/admin):

#### MLflow Status
- **MLflow URL**: Link to MLflow UI
- **Experiments**: Number of experiments tracked
- **Models Registered**: Total models in registry

#### Data Drift Detection
- **Check Data Drift**: Button to run drift detection for all strategies
- **View Drift Reports**: Link to recent drift detection reports
- **Drift Threshold**: Configure threshold (default: 30%)

#### Model Training
- **Train All Models**: Full retraining of all ML models (30-60 min)
- **Incremental Update**: Fast fine-tuning with recent data (5-10 min)
- **Auto-Retrain**: Drift-triggered automated retraining

#### Model Registry
- **View Models**: List all registered models with versions
- **Production Models**: Current production model for each strategy
- **Model Performance**: Accuracy, F1, ROC-AUC for each model

#### Scheduled Jobs
- **View Cron Schedule**: Show configured automated tasks
- **Last Run Times**: When each job last executed
- **Next Run Times**: When each job will run next

### MLflow UI

Access at http://localhost:5000 (local) or http://mlflow-url (production)

**Key Pages:**
1. **Experiments**: View all training runs
2. **Models**: Model registry with versions and stages
3. **Compare Runs**: Side-by-side metric comparison
4. **Artifacts**: Download models, plots, data

## Best Practices

### Training

1. **Always log to MLflow**: Use `train_with_mlflow.py` instead of direct training scripts
2. **Meaningful run names**: Include strategy, date, and key parameters
3. **Tag appropriately**: Add tags like "production", "experiment", "baseline"
4. **Log everything**: Parameters, metrics, artifacts, plots

### Model Registry

1. **Use staging first**: Test models in Staging before Production
2. **Document transitions**: Add notes when promoting/archiving models
3. **Keep history**: Don't delete old model versions (archive instead)
4. **Monitor production**: Track inference metrics for production models

### Drift Detection

1. **Check regularly**: Daily drift checks via cron
2. **Set appropriate thresholds**: 30% drift ratio is a good starting point
3. **Investigate drift**: Don't blindly retrain, understand what changed
4. **Keep reports**: Archive drift reports for post-mortem analysis

### Retraining

1. **Validate before promoting**: Check accuracy, precision, recall, ROC-AUC
2. **A/B test new models**: Run Staging and Production in parallel
3. **Gradual rollout**: Start with small client subset
4. **Monitor closely**: Watch for performance degradation after deployment

## Troubleshooting

### MLflow Server Not Starting

**Issue**: `docker-compose up` fails for MLflow

**Solution**:
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check logs
docker-compose -f mlops/mlflow/docker-compose.mlflow.yml logs

# Recreate database
PGPASSWORD='$@nJose420' psql -U postgres -c "DROP DATABASE mlflow;"
PGPASSWORD='$@nJose420' psql -U postgres -c "CREATE DATABASE mlflow;"
```

### Model Not Logging to MLflow

**Issue**: Training completes but no run appears in MLflow UI

**Solution**:
```python
# Check MLflow tracking URI
import mlflow
print(mlflow.get_tracking_uri())  # Should be http://localhost:5000

# Set explicitly if needed
mlflow.set_tracking_uri("http://localhost:5000")
```

### Drift Detection Fails

**Issue**: `monitor_drift_and_alert()` raises errors

**Solution**:
```bash
# Check database connection
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -c "SELECT COUNT(*) FROM ml_training_features;"

# Verify sufficient data
python -c "
from mlops.drift_detection.drift_detector import load_data_for_drift_detection
ref, curr = load_data_for_drift_detection('postgresql://...', 'growth')
print(f'Reference: {len(ref)} rows, Current: {len(curr)} rows')
"

# Need at least 100 samples in current_data
```

### Automated Retraining Fails

**Issue**: `auto_retrain.py` exits with errors

**Solution**:
```bash
# Run with verbose logging
python mlops/retraining/auto_retrain.py --drift-threshold 0.3 2>&1 | tee retrain.log

# Check specific strategy
python mlops/retraining/auto_retrain.py --strategies growth

# Verify models exist
ls -lh ml_models/

# Check MLflow connectivity
curl http://localhost:5000/health
```

## Metrics to Monitor

### Training Metrics

- **Accuracy**: % of correct predictions (target: > 70%)
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1 Score**: Harmonic mean of precision and recall
- **ROC-AUC**: Area under ROC curve (target: > 0.75)

### Drift Metrics

- **KS Statistic**: Distribution difference (closer to 0 = less drift)
- **PSI**: Population shift (< 0.1 good, 0.1-0.2 monitor, > 0.2 retrain)
- **Drift Ratio**: % of features with drift (< 30% acceptable)

### System Metrics

- **Training Time**: ML ~30 min, RL ~3 hours
- **Inference Latency**: < 50ms per stock
- **Model Size**: XGBoost ~5-10MB, RL ~50-100MB
- **Artifact Storage**: Grows ~1GB per month

## Advanced Topics

### Custom Metrics

Log custom metrics during training:

```python
with mlflow.start_run():
    # Train model
    model.fit(X_train, y_train)

    # Log standard metrics
    mlflow.log_metric("accuracy", accuracy)

    # Log custom metrics
    mlflow.log_metric("sharpe_ratio", sharpe)
    mlflow.log_metric("max_drawdown", max_dd)
    mlflow.log_metric("win_rate", win_rate)
```

### Hyperparameter Tuning

Use MLflow with hyperparameter optimization:

```python
import optuna
from optuna.integration.mlflow import MLflowCallback

def objective(trial):
    params = {
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'n_estimators': trial.suggest_int('n_estimators', 50, 200)
    }

    with mlflow.start_run(nested=True):
        model = XGBClassifier(**params)
        model.fit(X_train, y_train)
        score = accuracy_score(y_test, model.predict(X_test))

        mlflow.log_params(params)
        mlflow.log_metric("accuracy", score)

    return score

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50, callbacks=[MLflowCallback()])
```

### A/B Testing Models

Run two model versions in parallel:

```python
# Route 50% traffic to each version
import random

def get_model():
    if random.random() < 0.5:
        # Control: Current production
        return mlflow.sklearn.load_model("models:/acis_growth_classifier/Production")
    else:
        # Treatment: New challenger
        return mlflow.sklearn.load_model("models:/acis_growth_classifier/Staging")

# Track which version was used
with mlflow.start_run():
    model = get_model()
    predictions = model.predict(X)
    mlflow.log_param("model_version", "production" if ... else "staging")
```

### S3 Artifact Storage

For production, use S3 for artifact storage:

```yaml
# docker-compose.mlflow.yml
environment:
  MLFLOW_ARTIFACT_ROOT: s3://my-bucket/mlflow-artifacts
  AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
  AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
```

## References

- MLflow Documentation: https://mlflow.org/docs/latest/index.html
- MLflow Model Registry: https://mlflow.org/docs/latest/model-registry.html
- Data Drift: https://en.wikipedia.org/wiki/Concept_drift
- PSI Calculation: https://mwburke.github.io/data%20science/2018/04/29/population-stability-index.html

---

**Next Steps:**
- Explore MLflow UI: http://localhost:5000
- Run drift detection: `python mlops/drift_detection/drift_detector.py --strategy growth`
- Try automated retraining: `python mlops/retraining/auto_retrain.py`
- Check System Admin UI: http://192.168.50.234:3000/admin
