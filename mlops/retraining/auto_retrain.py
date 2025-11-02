"""
Automated model retraining pipeline
Checks for drift and retrains models when necessary
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from mlops.drift_detection.drift_detector import monitor_drift_and_alert

from mlops.mlflow.mlflow_client import ACISMLflowClient
from mlops.mlflow.train_with_mlflow import promote_model_to_production, train_model_with_mlflow

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AutoRetrainingPipeline:
    """Automated model retraining pipeline"""

    def __init__(
        self,
        strategies: List[str] = None,
        drift_threshold: float = 0.3,
        min_accuracy: float = 0.7,
        db_connection: str = None,
    ):
        """
        Initialize retraining pipeline

        Args:
            strategies: List of strategies to monitor (default: all)
            drift_threshold: Drift threshold for triggering retraining
            min_accuracy: Minimum accuracy for production promotion
            db_connection: Database connection string
        """
        self.strategies = strategies or ["growth", "value", "dividend", "momentum"]
        self.drift_threshold = drift_threshold
        self.min_accuracy = min_accuracy
        self.db_connection = db_connection or os.getenv(
            "DATABASE_URL", "postgresql://postgres:$@nJose420@localhost:5432/acis-ai"
        )
        self.mlflow_client = ACISMLflowClient()

    def check_and_retrain_strategy(self, strategy: str) -> Dict:
        """
        Check drift and retrain model for a strategy if needed

        Args:
            strategy: Trading strategy name

        Returns:
            Dictionary with results
        """
        logger.info(f"Processing strategy: {strategy}")

        result = {
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "drift_detected": False,
            "retrained": False,
            "promoted_to_production": False,
            "error": None,
        }

        try:
            # Check for drift
            logger.info(f"Checking data drift for {strategy}...")
            drift_detected = monitor_drift_and_alert(
                strategy=strategy,
                conn_string=self.db_connection,
                alert_threshold=self.drift_threshold,
            )

            result["drift_detected"] = drift_detected

            if not drift_detected:
                logger.info(f"No significant drift detected for {strategy}")
                return result

            # Drift detected - retrain model
            logger.info(f"Drift detected for {strategy}. Starting retraining...")

            run_id, model_name = train_model_with_mlflow(
                strategy=strategy, db_connection=self.db_connection
            )

            result["retrained"] = True
            result["run_id"] = run_id
            result["model_name"] = model_name

            logger.info(f"Retraining completed. Run ID: {run_id}")

            # Promote to production if meets criteria
            logger.info(f"Evaluating model for production promotion...")
            promoted = promote_model_to_production(
                model_name=model_name, min_accuracy=self.min_accuracy
            )

            result["promoted_to_production"] = promoted

            if promoted:
                logger.info(f"Model promoted to production for {strategy}")
            else:
                logger.warning(f"Model did not meet criteria for production promotion")

        except Exception as e:
            logger.error(f"Error processing {strategy}: {str(e)}", exc_info=True)
            result["error"] = str(e)

        return result

    def run_pipeline(self) -> List[Dict]:
        """
        Run the retraining pipeline for all strategies

        Returns:
            List of results for each strategy
        """
        logger.info("=" * 80)
        logger.info("Starting Automated Retraining Pipeline")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Strategies: {', '.join(self.strategies)}")
        logger.info(f"Drift threshold: {self.drift_threshold}")
        logger.info(f"Min accuracy: {self.min_accuracy}")
        logger.info("=" * 80)

        results = []

        for strategy in self.strategies:
            result = self.check_and_retrain_strategy(strategy)
            results.append(result)

            logger.info("-" * 80)

        # Summary
        logger.info("=" * 80)
        logger.info("Pipeline Summary:")
        logger.info(f"Total strategies processed: {len(results)}")
        logger.info(f"Drift detected: {sum(1 for r in results if r['drift_detected'])}")
        logger.info(f"Models retrained: {sum(1 for r in results if r['retrained'])}")
        logger.info(
            f"Promoted to production: {sum(1 for r in results if r['promoted_to_production'])}"
        )
        logger.info(f"Errors: {sum(1 for r in results if r['error'])}")
        logger.info("=" * 80)

        return results

    def get_model_versions_summary(self) -> Dict:
        """Get summary of all model versions"""
        summary = {}

        for strategy in self.strategies:
            model_name = f"acis_{strategy}_classifier"

            try:
                # Get production version
                prod_version = self.mlflow_client.get_latest_model_version(
                    model_name, stage="Production"
                )

                if prod_version:
                    run = self.mlflow_client.client.get_run(prod_version.run_id)
                    summary[strategy] = {
                        "model_name": model_name,
                        "production_version": prod_version.version,
                        "accuracy": run.data.metrics.get("accuracy", None),
                        "f1": run.data.metrics.get("f1", None),
                        "creation_time": datetime.fromtimestamp(
                            prod_version.creation_timestamp / 1000
                        ).isoformat(),
                    }
                else:
                    summary[strategy] = {
                        "model_name": model_name,
                        "production_version": None,
                        "message": "No production model",
                    }

            except Exception as e:
                summary[strategy] = {"model_name": model_name, "error": str(e)}

        return summary


def schedule_retraining(
    strategies: List[str] = None, drift_threshold: float = 0.3, min_accuracy: float = 0.7
):
    """
    Schedule and run automated retraining

    This function is designed to be called by a cron job or scheduler

    Args:
        strategies: List of strategies to monitor
        drift_threshold: Drift threshold
        min_accuracy: Minimum accuracy for production
    """
    pipeline = AutoRetrainingPipeline(
        strategies=strategies, drift_threshold=drift_threshold, min_accuracy=min_accuracy
    )

    results = pipeline.run_pipeline()

    # Save results
    results_file = f"/tmp/retraining_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results saved to: {results_file}")

    # Return exit code based on results
    # 0: Success
    # 1: At least one error occurred
    has_errors = any(r["error"] for r in results)
    return 1 if has_errors else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Automated model retraining pipeline")
    parser.add_argument(
        "--strategies",
        type=str,
        nargs="+",
        default=None,
        help="Strategies to process (default: all)",
    )
    parser.add_argument(
        "--drift-threshold",
        type=float,
        default=0.3,
        help="Drift threshold for triggering retraining",
    )
    parser.add_argument(
        "--min-accuracy", type=float, default=0.7, help="Minimum accuracy for production promotion"
    )
    parser.add_argument(
        "--summary", action="store_true", help="Show current model versions summary"
    )

    args = parser.parse_args()

    if args.summary:
        # Just show summary
        pipeline = AutoRetrainingPipeline()
        summary = pipeline.get_model_versions_summary()

        print("\nCurrent Production Models:")
        print("=" * 80)
        for strategy, info in summary.items():
            print(f"\n{strategy.upper()}:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        print("=" * 80)
    else:
        # Run retraining pipeline
        exit_code = schedule_retraining(
            strategies=args.strategies,
            drift_threshold=args.drift_threshold,
            min_accuracy=args.min_accuracy,
        )
        sys.exit(exit_code)
