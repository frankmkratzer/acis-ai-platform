"""
Model Evaluation and Monitoring Utilities

Provides tools for monitoring model performance, detecting drift, and
analyzing feature importance stability across walk-forward training periods.

Usage:
    from model_evaluation import load_walk_forward_results, plot_ic_over_time

    results = load_walk_forward_results()
    plot_ic_over_time(results, save_path='ic_over_time.png')
"""

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def load_walk_forward_results():
    """
    Load walk-forward training results

    Returns:
        DataFrame with columns: split, train_start, train_end, test_start,
        test_end, model_path, rmse, r2, information_coefficient, etc.
    """
    results_path = Path(__file__).parent / "models" / "walk_forward_results.csv"

    if not results_path.exists():
        raise FileNotFoundError(
            f"Walk-forward results not found at {results_path}. " "Run train_xgboost.py first."
        )

    return pd.read_csv(results_path)


def plot_ic_over_time(results: pd.DataFrame, save_path: str = None):
    """
    Plot Information Coefficient over time

    Args:
        results: DataFrame from load_walk_forward_results()
        save_path: Optional path to save the plot
    """
    plt.figure(figsize=(12, 6))

    # Convert test_start to datetime for plotting
    test_dates = pd.to_datetime(results["test_start"])

    # Plot IC
    plt.plot(
        test_dates,
        results["information_coefficient"],
        marker="o",
        linewidth=2,
        markersize=8,
        label="IC",
    )

    # Add horizontal lines for reference
    plt.axhline(y=0, color="red", linestyle="--", alpha=0.5, label="Zero Line")
    plt.axhline(y=0.03, color="green", linestyle="--", alpha=0.5, label="Good Threshold (0.03)")
    plt.axhline(y=0.05, color="blue", linestyle="--", alpha=0.5, label="Excellent Threshold (0.05)")

    # Formatting
    plt.title(
        "Information Coefficient Over Time (Walk-Forward Validation)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Test Period Start", fontsize=12)
    plt.ylabel("IC (Spearman Correlation)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to {save_path}")

    plt.show()


def plot_top_bottom_spread(results: pd.DataFrame, save_path: str = None):
    """
    Plot top-bottom quintile spread over time

    Args:
        results: DataFrame from load_walk_forward_results()
        save_path: Optional path to save the plot
    """
    plt.figure(figsize=(12, 6))

    # Convert test_start to datetime for plotting
    test_dates = pd.to_datetime(results["test_start"])

    # Plot spreads
    plt.plot(
        test_dates,
        results["top_minus_bottom"] * 100,
        marker="o",
        linewidth=2,
        markersize=8,
        label="Top - Bottom Spread",
    )

    # Add reference line
    plt.axhline(y=10, color="green", linestyle="--", alpha=0.5, label="Strong (10%)")

    # Formatting
    plt.title("Top-Bottom Quintile Spread Over Time", fontsize=14, fontweight="bold")
    plt.xlabel("Test Period Start", fontsize=12)
    plt.ylabel("Spread (%)", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to {save_path}")

    plt.show()


def check_model_drift(current_ic: float, historical_ic: pd.Series, threshold: float = 2.0):
    """
    Check if current IC indicates model drift

    Uses z-score to determine if current IC is significantly different from historical mean.

    Args:
        current_ic: Current Information Coefficient
        historical_ic: Series of historical IC values
        threshold: Z-score threshold (default 2.0 = 95% confidence)

    Returns:
        Tuple of (is_drift: bool, message: str)
    """
    mean_ic = historical_ic.mean()
    std_ic = historical_ic.std()

    if std_ic == 0:
        return False, "Not enough variance to determine drift"

    z_score = (current_ic - mean_ic) / std_ic

    if abs(z_score) > threshold:
        direction = "below" if z_score < 0 else "above"
        return (
            True,
            f"⚠️ Model drift detected! IC z-score: {z_score:.2f} ({direction} historical mean by {abs(z_score):.1f}σ)",
        )

    return False, f"✓ Model performance stable (IC z-score: {z_score:.2f})"


def get_feature_importance_stability():
    """
    Check feature importance stability across models

    Returns:
        DataFrame with top features and their average importance across all models
    """
    models_dir = Path(__file__).parent
    importance_files = list(models_dir.glob("feature_importance/feature_importance_*.csv"))

    if not importance_files:
        raise FileNotFoundError("No feature importance files found. Run train_xgboost.py first.")

    all_importances = []
    for f in importance_files:
        df = pd.read_csv(f)
        df["model_date"] = f.stem.split("_")[-1]
        all_importances.append(df)

    combined = pd.concat(all_importances, ignore_index=True)

    # Get top 20 features by average importance
    top_features = (
        combined.groupby("feature")["importance"]
        .agg(["mean", "std", "count"])
        .sort_values("mean", ascending=False)
        .head(20)
    )

    return top_features


def analyze_feature_importance_drift(top_n: int = 10, threshold: float = 0.3):
    """
    Analyze if top feature importance has drifted significantly

    Args:
        top_n: Number of top features to track
        threshold: Threshold for coefficient of variation (std/mean) to flag drift

    Returns:
        DataFrame with drift analysis
    """
    models_dir = Path(__file__).parent
    importance_files = sorted(list(models_dir.glob("feature_importance/feature_importance_*.csv")))

    if len(importance_files) < 2:
        print("Need at least 2 models to analyze drift")
        return None

    # Load first model to get baseline top features
    first_df = pd.read_csv(importance_files[0])
    baseline_top_features = first_df.nlargest(top_n, "importance")["feature"].tolist()

    # Track these features across all models
    feature_tracking = {feat: [] for feat in baseline_top_features}
    model_dates = []

    for f in importance_files:
        df = pd.read_csv(f)
        model_dates.append(f.stem.split("_")[-1])

        for feat in baseline_top_features:
            if feat in df["feature"].values:
                imp = df[df["feature"] == feat]["importance"].values[0]
                feature_tracking[feat].append(imp)
            else:
                feature_tracking[feat].append(0)

    # Calculate drift metrics
    drift_analysis = []
    for feat, importances in feature_tracking.items():
        mean_imp = np.mean(importances)
        std_imp = np.std(importances)
        cv = std_imp / mean_imp if mean_imp > 0 else 0

        drift_analysis.append(
            {
                "feature": feat,
                "mean_importance": mean_imp,
                "std_importance": std_imp,
                "coefficient_of_variation": cv,
                "drift_detected": cv > threshold,
            }
        )

    drift_df = pd.DataFrame(drift_analysis).sort_values("coefficient_of_variation", ascending=False)

    print(f"\nFeature Importance Drift Analysis (Top {top_n} features)")
    print("=" * 80)
    print(drift_df.to_string(index=False))

    drifted_features = drift_df[drift_df["drift_detected"]]
    if len(drifted_features) > 0:
        print(f"\n⚠️ {len(drifted_features)} features show significant drift (CV > {threshold})")
    else:
        print(f"\n✓ All tracked features stable (CV < {threshold})")

    return drift_df


def summarize_walk_forward_results():
    """
    Print a comprehensive summary of walk-forward training results
    """
    results = load_walk_forward_results()

    print("\n" + "=" * 80)
    print("WALK-FORWARD TRAINING SUMMARY")
    print("=" * 80)

    print(f"\nTotal Splits: {len(results)}")
    print(f"Date Range: {results['train_start'].min()} to {results['test_end'].max()}")

    print("\n" + "-" * 80)
    print("PERFORMANCE METRICS (Average Across All Splits)")
    print("-" * 80)

    metrics = {
        "RMSE": results["rmse"].mean(),
        "R²": results["r2"].mean(),
        "Information Coefficient": results["information_coefficient"].mean(),
        "Mean Monthly IC": results["mean_monthly_ic"].mean(),
        "Top Quintile Return": results["top_quintile_return"].mean(),
        "Bottom Quintile Return": results["bottom_quintile_return"].mean(),
        "Top - Bottom Spread": results["top_minus_bottom"].mean(),
    }

    for metric, value in metrics.items():
        if "Return" in metric or "Spread" in metric:
            print(f"{metric:.<40} {value:>10.2%}")
        else:
            print(f"{metric:.<40} {value:>10.4f}")

    print("\n" + "-" * 80)
    print("INFORMATION COEFFICIENT STATISTICS")
    print("-" * 80)
    print(f"{'Mean':.<40} {results['information_coefficient'].mean():>10.4f}")
    print(f"{'Median':.<40} {results['information_coefficient'].median():>10.4f}")
    print(f"{'Std Dev':.<40} {results['information_coefficient'].std():>10.4f}")
    print(f"{'Min':.<40} {results['information_coefficient'].min():>10.4f}")
    print(f"{'Max':.<40} {results['information_coefficient'].max():>10.4f}")

    # Determine quality
    mean_ic = results["information_coefficient"].mean()
    if mean_ic > 0.05:
        quality = "🌟 EXCELLENT"
    elif mean_ic > 0.03:
        quality = "✓ GOOD"
    elif mean_ic > 0.02:
        quality = "⚠️ MODERATE"
    else:
        quality = "❌ WEAK"

    print(f"\n{'Overall Quality':.<40} {quality}")

    print("\n" + "=" * 80)


def compare_periods(results: pd.DataFrame):
    """
    Compare model performance across different time periods

    Useful for identifying regime changes or market conditions that affect model performance.
    """
    results = results.copy()
    results["test_year"] = pd.to_datetime(results["test_start"]).dt.year

    yearly_stats = (
        results.groupby("test_year")
        .agg({"information_coefficient": ["mean", "std", "count"], "top_minus_bottom": "mean"})
        .round(4)
    )

    print("\n" + "=" * 80)
    print("PERFORMANCE BY YEAR")
    print("=" * 80)
    print(yearly_stats)
    print("\n")


if __name__ == "__main__":
    """
    Example usage when running as standalone script
    """
    try:
        # Load and summarize results
        print("Loading walk-forward results...")
        results = load_walk_forward_results()

        # Print comprehensive summary
        summarize_walk_forward_results()

        # Compare across periods
        compare_periods(results)

        # Plot IC over time
        print("\nGenerating IC plot...")
        plot_ic_over_time(results, save_path="ic_over_time.png")

        # Plot top-bottom spread
        print("Generating spread plot...")
        plot_top_bottom_spread(results, save_path="spread_over_time.png")

        # Analyze feature importance
        print("\nAnalyzing feature importance stability...")
        top_features = get_feature_importance_stability()
        print("\nTop 10 Features (Average Across All Models):")
        print(top_features.head(10))

        # Check for feature drift
        analyze_feature_importance_drift(top_n=10, threshold=0.3)

        # Check for model drift (using last period vs historical)
        if len(results) > 3:
            current_ic = results.iloc[-1]["information_coefficient"]
            historical_ic = results.iloc[:-1]["information_coefficient"]
            is_drift, message = check_model_drift(current_ic, historical_ic)
            print(f"\n{message}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease run train_xgboost.py first to generate model results.")
