"""
MLflow client for ACIS AI Platform
Handles model tracking, registration, and versioning
"""

import os
from typing import Any, Dict, List, Optional

import mlflow
import pandas as pd
from mlflow.entities import ViewType
from mlflow.tracking import MlflowClient


class ACISMLflowClient:
    """MLflow client for managing ML models in ACIS AI Platform"""

    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "acis-ai-models"):
        """
        Initialize MLflow client

        Args:
            tracking_uri: MLflow tracking server URI (default: from env or http://localhost:5000)
            experiment_name: Name of the MLflow experiment
        """
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "http://localhost:5000"
        )
        mlflow.set_tracking_uri(self.tracking_uri)

        self.experiment_name = experiment_name
        self.experiment = mlflow.set_experiment(experiment_name)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def start_run(self, run_name: str, tags: Optional[Dict[str, str]] = None) -> mlflow.ActiveRun:
        """
        Start a new MLflow run

        Args:
            run_name: Name of the run
            tags: Optional tags for the run

        Returns:
            Active MLflow run
        """
        return mlflow.start_run(run_name=run_name, tags=tags or {})

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log model parameters"""
        mlflow.log_params(params)

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log model metrics"""
        mlflow.log_metrics(metrics, step=step)

    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: Optional[str] = None,
        signature: Optional[Any] = None,
        input_example: Optional[Any] = None,
    ) -> None:
        """
        Log and optionally register a model

        Args:
            model: The model object to log
            artifact_path: Path within the run's artifact directory
            registered_model_name: Name to register the model under
            signature: Model signature
            input_example: Example input for the model
        """
        mlflow.sklearn.log_model(
            model,
            artifact_path=artifact_path,
            registered_model_name=registered_model_name,
            signature=signature,
            input_example=input_example,
        )

    def log_artifacts(self, local_dir: str, artifact_path: Optional[str] = None) -> None:
        """Log local directory as artifacts"""
        mlflow.log_artifacts(local_dir, artifact_path)

    def register_model(
        self,
        model_uri: str,
        name: str,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ) -> Any:
        """
        Register a model in the MLflow Model Registry

        Args:
            model_uri: URI of the model to register
            name: Name for the registered model
            tags: Optional tags
            description: Optional description

        Returns:
            ModelVersion object
        """
        model_version = mlflow.register_model(model_uri, name)

        if tags:
            for key, value in tags.items():
                self.client.set_model_version_tag(name, model_version.version, key, value)

        if description:
            self.client.update_model_version(
                name=name, version=model_version.version, description=description
            )

        return model_version

    def transition_model_stage(
        self, name: str, version: str, stage: str, archive_existing: bool = True
    ) -> Any:
        """
        Transition a model version to a new stage

        Args:
            name: Registered model name
            version: Model version
            stage: Target stage (Staging, Production, Archived)
            archive_existing: Whether to archive existing versions in the target stage

        Returns:
            Updated ModelVersion
        """
        return self.client.transition_model_version_stage(
            name=name, version=version, stage=stage, archive_existing_versions=archive_existing
        )

    def get_latest_model_version(
        self, name: str, stage: Optional[str] = "Production"
    ) -> Optional[Any]:
        """
        Get the latest model version for a given stage

        Args:
            name: Registered model name
            stage: Model stage (None for all stages)

        Returns:
            Latest ModelVersion or None
        """
        try:
            versions = self.client.get_latest_versions(name, stages=[stage] if stage else None)
            return versions[0] if versions else None
        except Exception as e:
            print(f"Error getting latest model version: {e}")
            return None

    def load_model(self, model_uri: str) -> Any:
        """
        Load a model from MLflow

        Args:
            model_uri: URI of the model (e.g., models:/model_name/Production)

        Returns:
            Loaded model
        """
        return mlflow.sklearn.load_model(model_uri)

    def search_runs(
        self, filter_string: str = "", order_by: Optional[List[str]] = None, max_results: int = 1000
    ) -> pd.DataFrame:
        """
        Search for runs in the current experiment

        Args:
            filter_string: Filter query string
            order_by: List of columns to order by
            max_results: Maximum number of results

        Returns:
            DataFrame of runs
        """
        return mlflow.search_runs(
            experiment_ids=[self.experiment.experiment_id],
            filter_string=filter_string,
            order_by=order_by,
            max_results=max_results,
        )

    def get_best_run(
        self, metric: str, filter_string: str = "", ascending: bool = False
    ) -> Optional[Any]:
        """
        Get the best run based on a metric

        Args:
            metric: Metric name to optimize
            filter_string: Filter query string
            ascending: Whether to sort ascending (True) or descending (False)

        Returns:
            Best run or None
        """
        runs = self.search_runs(
            filter_string=filter_string,
            order_by=[f"metrics.{metric} {'ASC' if ascending else 'DESC'}"],
            max_results=1,
        )

        if runs.empty:
            return None

        run_id = runs.iloc[0]["run_id"]
        return self.client.get_run(run_id)

    def compare_models(self, model_names: List[str], stage: str = "Production") -> pd.DataFrame:
        """
        Compare metrics across multiple registered models

        Args:
            model_names: List of registered model names
            stage: Model stage to compare

        Returns:
            DataFrame with model comparison
        """
        comparison_data = []

        for name in model_names:
            version = self.get_latest_model_version(name, stage)
            if version:
                run = self.client.get_run(version.run_id)
                comparison_data.append(
                    {
                        "model_name": name,
                        "version": version.version,
                        "stage": stage,
                        **run.data.metrics,
                    }
                )

        return pd.DataFrame(comparison_data)

    def delete_experiment_runs(self, filter_string: str = "", dry_run: bool = True) -> int:
        """
        Delete runs from the experiment

        Args:
            filter_string: Filter query string
            dry_run: If True, only print what would be deleted

        Returns:
            Number of runs deleted (or would be deleted)
        """
        runs = self.search_runs(filter_string=filter_string)

        if dry_run:
            print(f"Would delete {len(runs)} runs")
            return len(runs)

        for _, run in runs.iterrows():
            self.client.delete_run(run["run_id"])

        return len(runs)

    def get_model_artifacts(
        self, model_name: str, version: Optional[str] = None, stage: Optional[str] = "Production"
    ) -> Dict[str, str]:
        """
        Get artifacts for a model version

        Args:
            model_name: Registered model name
            version: Specific version (if None, uses latest from stage)
            stage: Stage to get version from (if version not specified)

        Returns:
            Dictionary of artifact paths
        """
        if version:
            model_version = self.client.get_model_version(model_name, version)
        else:
            model_version = self.get_latest_model_version(model_name, stage)

        if not model_version:
            return {}

        run = self.client.get_run(model_version.run_id)
        return {
            "run_id": run.info.run_id,
            "artifact_uri": run.info.artifact_uri,
            "source": model_version.source,
        }
