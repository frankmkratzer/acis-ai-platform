"""
Example: Training XGBoost model with MLflow tracking
Integrates with existing ACIS AI training pipeline
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import mlflow
import mlflow.xgboost
import pandas as pd
import xgboost as xgb
from mlflow.models import infer_signature
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from mlops.mlflow.mlflow_client import ACISMLflowClient


def load_training_data(conn_string: str, strategy: str = "growth") -> pd.DataFrame:
    """Load training data from database"""
    import psycopg2

    conn = psycopg2.connect(conn_string)

    query = f"""
    SELECT *
    FROM ml_training_features
    WHERE strategy = '{strategy}'
    AND date >= CURRENT_DATE - INTERVAL '2 years'
    ORDER BY date DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Prepare features and target for training"""
    # Remove non-feature columns
    exclude_cols = ["ticker", "date", "strategy", "target_return"]
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    X = df[feature_cols]
    y = (df["target_return"] > 0).astype(int)  # Binary classification

    return X, y, feature_cols


def train_model_with_mlflow(
    strategy: str = "growth", db_connection: str = None, model_params: dict = None
):
    """
    Train XGBoost model with MLflow tracking

    Args:
        strategy: Trading strategy (growth, value, dividend, momentum)
        db_connection: Database connection string
        model_params: XGBoost hyperparameters
    """
    # Initialize MLflow client
    mlflow_client = ACISMLflowClient()

    # Default parameters
    if model_params is None:
        model_params = {
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "objective": "binary:logistic",
            "eval_metric": "auc",
            "random_state": 42,
        }

    # Load data
    print(f"Loading training data for {strategy} strategy...")
    if db_connection is None:
        db_connection = os.getenv(
            "DATABASE_URL", "postgresql://postgres:$@nJose420@localhost:5432/acis-ai"
        )

    df = load_training_data(db_connection, strategy)
    print(f"Loaded {len(df)} samples")

    # Prepare features
    X, y, feature_names = prepare_features(df)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Start MLflow run
    run_name = f"{strategy}_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    with mlflow_client.start_run(
        run_name=run_name,
        tags={
            "strategy": strategy,
            "model_type": "xgboost",
            "training_date": datetime.now().isoformat(),
        },
    ):
        # Log parameters
        mlflow_client.log_params(model_params)
        mlflow_client.log_params(
            {
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "n_features": len(feature_names),
                "strategy": strategy,
            }
        )

        # Train model
        print("Training XGBoost model...")
        model = xgb.XGBClassifier(**model_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # Calculate metrics
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_pred_proba),
        }

        # Log metrics
        mlflow_client.log_metrics(metrics)
        print(f"\nModel Metrics:")
        for name, value in metrics.items():
            print(f"  {name}: {value:.4f}")

        # Feature importance
        feature_importance = pd.DataFrame(
            {"feature": feature_names, "importance": model.feature_importances_}
        ).sort_values("importance", ascending=False)

        print(f"\nTop 10 Features:")
        print(feature_importance.head(10).to_string(index=False))

        # Save feature importance as artifact
        importance_file = f"/tmp/feature_importance_{strategy}.csv"
        feature_importance.to_csv(importance_file, index=False)
        mlflow.log_artifact(importance_file)

        # Infer model signature
        signature = infer_signature(X_train, y_pred_proba)

        # Log model
        registered_model_name = f"acis_{strategy}_classifier"
        mlflow_client.log_model(
            model=model,
            artifact_path="model",
            registered_model_name=registered_model_name,
            signature=signature,
            input_example=X_train.head(5),
        )

        # Get run info
        run = mlflow.active_run()
        print(f"\nMLflow Run ID: {run.info.run_id}")
        print(f"Model registered as: {registered_model_name}")

        return run.info.run_id, registered_model_name


def promote_model_to_production(model_name: str, version: str = None, min_accuracy: float = 0.7):
    """
    Promote a model version to production if it meets criteria

    Args:
        model_name: Registered model name
        version: Specific version to promote (if None, uses latest)
        min_accuracy: Minimum accuracy required
    """
    mlflow_client = ACISMLflowClient()

    # Get the version to promote
    if version is None:
        # Get latest staging version
        model_version = mlflow_client.get_latest_model_version(model_name, "Staging")
        if model_version is None:
            # Get any latest version
            model_version = mlflow_client.get_latest_model_version(model_name, None)
    else:
        model_version = mlflow_client.client.get_model_version(model_name, version)

    if not model_version:
        print(f"No model version found for {model_name}")
        return False

    # Get run metrics
    run = mlflow_client.client.get_run(model_version.run_id)
    accuracy = run.data.metrics.get("accuracy", 0)

    print(f"\nModel: {model_name} v{model_version.version}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Required: {min_accuracy:.4f}")

    # Check if meets criteria
    if accuracy >= min_accuracy:
        # Promote to production
        mlflow_client.transition_model_stage(
            name=model_name,
            version=model_version.version,
            stage="Production",
            archive_existing=True,
        )
        print(f"✅ Model promoted to Production")
        return True
    else:
        print(f"❌ Model does not meet accuracy threshold")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train model with MLflow tracking")
    parser.add_argument(
        "--strategy",
        type=str,
        default="growth",
        choices=["growth", "value", "dividend", "momentum"],
        help="Trading strategy",
    )
    parser.add_argument(
        "--promote", action="store_true", help="Promote model to production if it meets criteria"
    )

    args = parser.parse_args()

    # Train model
    run_id, model_name = train_model_with_mlflow(strategy=args.strategy)

    # Promote if requested
    if args.promote:
        promote_model_to_production(model_name)
