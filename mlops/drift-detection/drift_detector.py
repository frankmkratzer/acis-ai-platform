"""
Data drift detection for ACIS AI Platform
Monitors feature distributions and triggers retraining when drift is detected
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats


class DataDriftDetector:
    """Detects data drift in model features"""

    def __init__(
        self,
        reference_data: pd.DataFrame,
        feature_columns: List[str],
        drift_threshold: float = 0.05,
    ):
        """
        Initialize drift detector

        Args:
            reference_data: Reference/baseline dataset
            feature_columns: List of feature column names
            drift_threshold: P-value threshold for drift detection (default 0.05)
        """
        self.reference_data = reference_data[feature_columns]
        self.feature_columns = feature_columns
        self.drift_threshold = drift_threshold

        # Calculate reference statistics
        self.reference_stats = self._calculate_statistics(self.reference_data)

    def _calculate_statistics(self, data: pd.DataFrame) -> Dict:
        """Calculate statistics for a dataset"""
        stats_dict = {}

        for col in self.feature_columns:
            stats_dict[col] = {
                "mean": data[col].mean(),
                "std": data[col].std(),
                "median": data[col].median(),
                "min": data[col].min(),
                "max": data[col].max(),
                "q25": data[col].quantile(0.25),
                "q75": data[col].quantile(0.75),
                "skew": data[col].skew(),
                "kurtosis": data[col].kurtosis(),
            }

        return stats_dict

    def detect_drift_ks(self, current_data: pd.DataFrame) -> Dict[str, Tuple[float, bool]]:
        """
        Detect drift using Kolmogorov-Smirnov test

        Args:
            current_data: Current production data

        Returns:
            Dictionary of feature -> (p-value, is_drifted)
        """
        drift_results = {}

        for col in self.feature_columns:
            # KS test
            statistic, p_value = stats.ks_2samp(self.reference_data[col], current_data[col])

            is_drifted = p_value < self.drift_threshold
            drift_results[col] = (p_value, is_drifted)

        return drift_results

    def detect_drift_psi(
        self, current_data: pd.DataFrame, n_bins: int = 10
    ) -> Dict[str, Tuple[float, bool]]:
        """
        Detect drift using Population Stability Index (PSI)

        PSI < 0.1: No significant change
        0.1 <= PSI < 0.2: Moderate change
        PSI >= 0.2: Significant change

        Args:
            current_data: Current production data
            n_bins: Number of bins for PSI calculation

        Returns:
            Dictionary of feature -> (PSI value, is_drifted)
        """
        drift_results = {}

        for col in self.feature_columns:
            # Calculate PSI
            psi = self._calculate_psi(self.reference_data[col], current_data[col], n_bins=n_bins)

            is_drifted = psi >= 0.2  # Significant drift threshold
            drift_results[col] = (psi, is_drifted)

        return drift_results

    def _calculate_psi(self, reference: pd.Series, current: pd.Series, n_bins: int = 10) -> float:
        """Calculate Population Stability Index"""
        # Create bins based on reference distribution
        breakpoints = np.percentile(reference, np.linspace(0, 100, n_bins + 1))
        breakpoints = np.unique(breakpoints)  # Remove duplicates

        if len(breakpoints) <= 1:
            return 0.0

        # Calculate distribution for each dataset
        ref_dist = np.histogram(reference, bins=breakpoints)[0] / len(reference)
        curr_dist = np.histogram(current, bins=breakpoints)[0] / len(current)

        # Avoid division by zero
        ref_dist = np.where(ref_dist == 0, 0.0001, ref_dist)
        curr_dist = np.where(curr_dist == 0, 0.0001, curr_dist)

        # Calculate PSI
        psi = np.sum((curr_dist - ref_dist) * np.log(curr_dist / ref_dist))

        return psi

    def comprehensive_drift_report(self, current_data: pd.DataFrame) -> Dict:
        """
        Generate comprehensive drift report

        Args:
            current_data: Current production data

        Returns:
            Dictionary with drift detection results
        """
        # Statistical tests
        ks_results = self.detect_drift_ks(current_data)
        psi_results = self.detect_drift_psi(current_data)

        # Calculate current statistics
        current_stats = self._calculate_statistics(current_data)

        # Summary
        drifted_features_ks = [col for col, (_, is_drift) in ks_results.items() if is_drift]
        drifted_features_psi = [col for col, (_, is_drift) in psi_results.items() if is_drift]

        report = {
            "timestamp": datetime.now().isoformat(),
            "n_features": len(self.feature_columns),
            "n_samples_reference": len(self.reference_data),
            "n_samples_current": len(current_data),
            "drift_threshold": self.drift_threshold,
            "summary": {
                "drifted_features_ks": len(drifted_features_ks),
                "drifted_features_psi": len(drifted_features_psi),
                "drift_detected": len(drifted_features_ks) > 0 or len(drifted_features_psi) > 0,
            },
            "ks_test": {
                col: {"p_value": p_val, "drifted": is_drift}
                for col, (p_val, is_drift) in ks_results.items()
            },
            "psi": {
                col: {"psi_value": psi_val, "drifted": is_drift}
                for col, (psi_val, is_drift) in psi_results.items()
            },
            "feature_statistics": {
                col: {
                    "reference": self.reference_stats[col],
                    "current": current_stats[col],
                    "mean_diff_pct": (
                        (current_stats[col]["mean"] - self.reference_stats[col]["mean"])
                        / self.reference_stats[col]["mean"]
                        * 100
                        if self.reference_stats[col]["mean"] != 0
                        else 0
                    ),
                }
                for col in self.feature_columns
            },
        }

        return report

    def save_report(self, report: Dict, filepath: str) -> None:
        """Save drift report to JSON file"""
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)


def load_data_for_drift_detection(
    conn_string: str, strategy: str, reference_days: int = 90, current_days: int = 7
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load reference and current data for drift detection

    Args:
        conn_string: Database connection string
        strategy: Trading strategy
        reference_days: Number of days for reference data
        current_days: Number of days for current data

    Returns:
        Tuple of (reference_data, current_data)
    """
    import psycopg2

    conn = psycopg2.connect(conn_string)

    # Reference data (older data)
    ref_end = datetime.now() - timedelta(days=current_days)
    ref_start = ref_end - timedelta(days=reference_days)

    ref_query = f"""
    SELECT *
    FROM ml_training_features
    WHERE strategy = '{strategy}'
    AND date >= '{ref_start.date()}'
    AND date < '{ref_end.date()}'
    """

    # Current data (recent data)
    curr_start = datetime.now() - timedelta(days=current_days)

    curr_query = f"""
    SELECT *
    FROM ml_training_features
    WHERE strategy = '{strategy}'
    AND date >= '{curr_start.date()}'
    """

    reference_data = pd.read_sql(ref_query, conn)
    current_data = pd.read_sql(curr_query, conn)

    conn.close()

    return reference_data, current_data


def monitor_drift_and_alert(
    strategy: str, conn_string: str = None, alert_threshold: float = 0.3
) -> bool:
    """
    Monitor data drift and determine if retraining is needed

    Args:
        strategy: Trading strategy
        conn_string: Database connection string
        alert_threshold: Percentage of features that need drift to trigger alert

    Returns:
        True if retraining is recommended
    """
    import os

    if conn_string is None:
        conn_string = os.getenv(
            "DATABASE_URL", "postgresql://postgres:$@nJose420@localhost:5432/acis-ai"
        )

    print(f"Monitoring drift for {strategy} strategy...")

    # Load data
    reference_data, current_data = load_data_for_drift_detection(
        conn_string, strategy, reference_days=90, current_days=7
    )

    if len(current_data) == 0:
        print("No current data available")
        return False

    # Prepare features
    exclude_cols = ["ticker", "date", "strategy", "target_return"]
    feature_cols = [col for col in reference_data.columns if col not in exclude_cols]

    # Detect drift
    detector = DataDriftDetector(
        reference_data=reference_data, feature_columns=feature_cols, drift_threshold=0.05
    )

    report = detector.comprehensive_drift_report(current_data)

    # Save report
    report_file = f"/tmp/drift_report_{strategy}_{datetime.now().strftime('%Y%m%d')}.json"
    detector.save_report(report, report_file)
    print(f"Drift report saved to: {report_file}")

    # Check if retraining is needed
    drift_ratio = report["summary"]["drifted_features_psi"] / report["n_features"]
    retraining_needed = drift_ratio >= alert_threshold

    print(f"\nDrift Detection Summary:")
    print(f"  Features analyzed: {report['n_features']}")
    print(f"  Features with drift (KS): {report['summary']['drifted_features_ks']}")
    print(f"  Features with drift (PSI): {report['summary']['drifted_features_psi']}")
    print(f"  Drift ratio: {drift_ratio:.2%}")
    print(f"  Retraining threshold: {alert_threshold:.2%}")
    print(f"  Retraining needed: {'YES ⚠️' if retraining_needed else 'NO ✓'}")

    return retraining_needed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor data drift")
    parser.add_argument(
        "--strategy",
        type=str,
        default="growth",
        choices=["growth", "value", "dividend", "momentum"],
        help="Trading strategy",
    )
    parser.add_argument(
        "--alert-threshold",
        type=float,
        default=0.3,
        help="Drift threshold for triggering retraining alert (0-1)",
    )

    args = parser.parse_args()

    needs_retraining = monitor_drift_and_alert(
        strategy=args.strategy, alert_threshold=args.alert_threshold
    )

    # Exit code indicates if retraining is needed
    sys.exit(0 if not needs_retraining else 1)
