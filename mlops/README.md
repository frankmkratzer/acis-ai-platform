# MLOps: Model Operations for ACIS AI Platform

Complete MLOps infrastructure for production ML model management, including MLflow tracking, automated retraining, and data drift detection.

## Overview

The MLOps system provides:

- **MLflow Tracking & Registry**: Central model versioning and experiment tracking
- **Data Drift Detection**: Automated monitoring of feature distributions
- **Automated Retraining**: Trigger retraining when drift is detected
- **Model Promotion**: Promote models to production based on performance criteria
- **Version Control**: Track and rollback model versions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   MLflow Tracking Server                     │
│  - Experiment Tracking                                       │
│  - Model Registry                                            │
│  - Artifact Storage (S3 or local)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├──────────────┬──────────────┐
                              ▼              ▼              ▼
┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐
│  Model Training  │  │ Drift Check  │  │ Auto Retrain    │
│  with Tracking   │  │  (Daily)     │  │  (Weekly)       │
└──────────────────┘  └──────────────┘  └─────────────────┘
```

## Components

### 1. MLflow Tracking Server

Central server for tracking experiments and managing model registry.

**Features**:
- PostgreSQL backend for metadata
- S3 or local storage for artifacts
- Web UI for model management
- REST API for programmatic access

**Setup**:
```bash
# Local deployment with Docker Compose
cd mlops/mlflow
docker-compose -f docker-compose.mlflow.yml up -d

# Kubernetes deployment
kubectl apply -f k8s/base/mlflow-deployment.yaml

# Access UI
open http://localhost:5000
```

### 2. MLflow Client

Python client for ML model operations.

**Usage**:
```python
from mlops.mlflow.mlflow_client import ACISMLflowClient

# Initialize client
client = ACISMLflowClient(
    tracking_uri="http://localhost:5000",
    experiment_name="acis-ai-models"
)

# Start run
with client.start_run(run_name="growth_model_v1"):
    # Log parameters
    client.log_params({"max_depth": 6, "learning_rate": 0.1})

    # Log metrics
    client.log_metrics({"accuracy": 0.85, "f1": 0.82})

    # Log model
    client.log_model(
        model=trained_model,
        artifact_path="model",
        registered_model_name="acis_growth_classifier"
    )

# Promote to production
client.transition_model_stage(
    name="acis_growth_classifier",
    version="3",
    stage="Production"
)
```

### 3. Data Drift Detection

Monitors feature distributions and detects when retraining is needed.

**Methods**:
- **Kolmogorov-Smirnov Test**: Statistical test for distribution changes
- **Population Stability Index (PSI)**: Measures population shift

**Usage**:
```bash
# Check drift for a strategy
python mlops/drift-detection/drift_detector.py \
    --strategy growth \
    --alert-threshold 0.3

# Output:
# Drift Detection Summary:
#   Features analyzed: 50
#   Features with drift (KS): 8
#   Features with drift (PSI): 12
#   Drift ratio: 24.00%
#   Retraining needed: NO ✓
```

**Automated Monitoring** (Kubernetes):
```bash
kubectl apply -f k8s/base/model-retraining-cronjob.yaml
```

### 4. Automated Retraining

Pipeline that checks for drift and retrains models automatically.

**Features**:
- Drift detection for all strategies
- Automatic model training when drift exceeds threshold
- Performance-based production promotion
- Comprehensive logging

**Usage**:
```bash
# Run pipeline for all strategies
python mlops/retraining/auto_retrain.py

# Run for specific strategies
python mlops/retraining/auto_retrain.py \
    --strategies growth value \
    --drift-threshold 0.3 \
    --min-accuracy 0.7

# Show current production models
python mlops/retraining/auto_retrain.py --summary
```

**Kubernetes CronJobs**:
- **Daily Drift Check**: Runs at 3 AM UTC
- **Weekly Retrain**: Runs Sunday at 4 AM UTC

## Workflows

### Training a Model with MLflow

```python
from mlops.mlflow.train_with_mlflow import train_model_with_mlflow

# Train and track with MLflow
run_id, model_name = train_model_with_mlflow(
    strategy="growth",
    model_params={
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 100
    }
)

print(f"Model trained: {model_name}")
print(f"Run ID: {run_id}")
```

### Promoting a Model

```python
from mlops.mlflow.train_with_mlflow import promote_model_to_production

# Promote if meets criteria
promoted = promote_model_to_production(
    model_name="acis_growth_classifier",
    version="5",  # or None for latest
    min_accuracy=0.75
)
```

### Loading Production Model

```python
from mlops.mlflow.mlflow_client import ACISMLflowClient

client = ACISMLflowClient()

# Load latest production model
model_uri = "models:/acis_growth_classifier/Production"
model = client.load_model(model_uri)

# Make predictions
predictions = model.predict(features)
```

### Monitoring Drift

```python
from mlops.drift_detection.drift_detector import monitor_drift_and_alert

# Check if retraining is needed
needs_retrain = monitor_drift_and_alert(
    strategy="growth",
    alert_threshold=0.3
)

if needs_retrain:
    print("⚠️ Significant drift detected - retraining recommended")
```

## Model Lifecycle

```
1. Training
   ├── Track experiments with MLflow
   ├── Log parameters, metrics, artifacts
   └── Register model in Model Registry

2. Staging
   ├── Evaluate model performance
   ├── Run validation tests
   └── Promote to staging environment

3. Production
   ├── Meet performance criteria (accuracy > threshold)
   ├── Transition to production stage
   └── Archive previous production version

4. Monitoring
   ├── Track predictions
   ├── Monitor data drift
   └── Detect performance degradation

5. Retraining
   ├── Drift detected OR weekly schedule
   ├── Train new model version
   └── Evaluate and promote if better
```

## Environment Variables

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_ARTIFACT_ROOT=/mlflow/artifacts  # or s3://bucket/path

# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/acis-ai

# AWS S3 (Optional)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
MLFLOW_S3_ENDPOINT_URL=https://s3.amazonaws.com
```

## Metrics & Monitoring

### Model Performance Metrics

Tracked for each model:
- **Accuracy**: Overall classification accuracy
- **Precision**: Positive predictive value
- **Recall**: True positive rate
- **F1 Score**: Harmonic mean of precision and recall
- **ROC AUC**: Area under ROC curve

### Drift Metrics

- **KS Statistic**: Kolmogorov-Smirnov test statistic
- **PSI**: Population Stability Index
- **Feature Statistics**: Mean, std, quantiles, skewness, kurtosis

### MLflow UI Dashboards

Access at `http://localhost:5000`:

1. **Experiments**: View all training runs
2. **Models**: Manage registered models
3. **Artifacts**: Download model files and reports
4. **Compare**: Compare metrics across runs

## API Integration

Integrate with ACIS backend API:

```python
# backend/api/ml_models.py

from mlops.mlflow.mlflow_client import ACISMLflowClient

client = ACISMLflowClient()

@app.get("/api/ml/models/{strategy}")
def get_production_model(strategy: str):
    """Get current production model info"""
    model_name = f"acis_{strategy}_classifier"
    version = client.get_latest_model_version(model_name, "Production")

    if not version:
        raise HTTPException(404, "No production model found")

    run = client.client.get_run(version.run_id)

    return {
        "model_name": model_name,
        "version": version.version,
        "metrics": run.data.metrics,
        "created_at": version.creation_timestamp
    }
```

## Troubleshooting

### MLflow Server Won't Start

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check MLflow logs
docker logs acis-mlflow

# Verify database connection
psql -h localhost -U postgres -d mlflow -c "SELECT 1"
```

### Drift Detection Fails

```bash
# Check if sufficient data available
psql -h localhost -U postgres -d acis-ai <<EOF
SELECT
  strategy,
  COUNT(*) as samples,
  MIN(date) as earliest,
  MAX(date) as latest
FROM ml_training_features
GROUP BY strategy;
EOF

# Need at least 90 days of reference data + 7 days current
```

### Model Not Promoting

```bash
# Check model metrics
python mlops/retraining/auto_retrain.py --summary

# Lower min_accuracy threshold if needed
python mlops/retraining/auto_retrain.py --min-accuracy 0.65
```

## Best Practices

### 1. Experiment Naming

Use descriptive run names:
```python
run_name = f"{strategy}_{timestamp}_{experiment_type}"
# Example: "growth_20250102_hyperparameter_tuning"
```

### 2. Parameter Logging

Log all hyperparameters and data characteristics:
```python
params = {
    # Model hyperparameters
    "max_depth": 6,
    "learning_rate": 0.1,

    # Data characteristics
    "train_samples": len(X_train),
    "n_features": X_train.shape[1],
    "lookback_days": 90
}
```

### 3. Artifact Organization

Save comprehensive artifacts:
```python
# Feature importance
mlflow.log_artifact("feature_importance.csv")

# Training plots
mlflow.log_artifact("confusion_matrix.png")

# Model documentation
mlflow.log_artifact("model_card.md")
```

### 4. Production Criteria

Define clear promotion criteria:
- Accuracy > 0.70
- F1 Score > 0.65
- ROC AUC > 0.75
- Passes validation tests
- No significant bias

### 5. Drift Thresholds

Tune thresholds based on strategy:
```python
# Conservative (more frequent retraining)
drift_threshold = 0.2  # 20% of features

# Moderate
drift_threshold = 0.3  # 30% of features

# Aggressive (less frequent retraining)
drift_threshold = 0.5  # 50% of features
```

## Scaling

### Distributed Training

For large datasets, use distributed training:
```python
# Add to model_params
params = {
    "tree_method": "hist",  # GPU-accelerated
    "n_jobs": -1,  # Use all cores
}
```

### Artifact Storage

For production, use S3:
```bash
# Set in environment
export MLFLOW_ARTIFACT_ROOT=s3://my-bucket/mlflow-artifacts
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### High Availability

Run multiple MLflow server replicas:
```yaml
# k8s/base/mlflow-deployment.yaml
spec:
  replicas: 3  # Multiple instances
```

## Security

### Access Control

Implement authentication:
```python
# Use MLflow with authentication
os.environ["MLFLOW_TRACKING_USERNAME"] = "user"
os.environ["MLFLOW_TRACKING_PASSWORD"] = "password"
```

### Secrets Management

Use Kubernetes secrets:
```bash
kubectl create secret generic mlflow-secrets \
  --from-literal=tracking-username=admin \
  --from-literal=tracking-password=secure_password \
  -n acis-ai
```

### Audit Logging

Enable MLflow audit logs:
```python
# In MLflow server config
--logging-level DEBUG
```

## Support

- **Documentation**: [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md)
- **MLflow Docs**: https://mlflow.org/docs/latest/
- **GitHub Issues**: https://github.com/frankmkratzer/acis-ai-platform/issues
