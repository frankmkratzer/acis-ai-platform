"""
XGBoost Stock Ranker - Walk-Forward Training

Trains XGBoost models using walk-forward validation to prevent overfitting.

Usage:
    python train_xgboost.py --start-date 2015-01-01 --end-date 2025-01-01
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from dateutil.relativedelta import relativedelta
from feature_engineering import FeatureEngineer
from scipy.stats import spearmanr
from sklearn.metrics import mean_squared_error, r2_score

from utils import get_logger

logger = get_logger(__name__)


class XGBoostTrainer:
    """Train XGBoost models with walk-forward validation"""

    def __init__(
        self,
        train_months: int = 36,
        test_months: int = 12,
        step_months: int = 3,
        forward_return_days: int = 63,
    ):
        """
        Args:
            train_months: Training window size (default 36 = 3 years)
            test_months: Test window size (default 12 = 1 year)
            step_months: How much to step forward (default 3 months)
            forward_return_days: Prediction horizon (default 63 = 3 months)
        """
        self.train_months = train_months
        self.test_months = test_months
        self.step_months = step_months
        self.forward_return_days = forward_return_days

        # XGBoost hyperparameters (tuned for financial data)
        self.xgb_params = {
            "objective": "reg:squarederror",
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "gamma": 0.1,
            "reg_alpha": 0.1,  # L1 regularization
            "reg_lambda": 1.0,  # L2 regularization
            "random_state": 42,
            "n_jobs": -1,  # Use all CPU cores
        }

        # Create models directory
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)

        # Track results
        self.results = []

    def generate_walk_forward_dates(self, start_date: str, end_date: str) -> List[Dict[str, str]]:
        """Generate train/test date pairs for walk-forward validation"""
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        date_pairs = []
        current_train_start = start

        while True:
            # Calculate train window
            train_start = current_train_start
            train_end = train_start + relativedelta(months=self.train_months)

            # Calculate test window
            test_start = train_end
            test_end = test_start + relativedelta(months=self.test_months)

            # Stop if test end exceeds end date
            if test_end > end:
                break

            date_pairs.append(
                {
                    "train_start": train_start.strftime("%Y-%m-%d"),
                    "train_end": train_end.strftime("%Y-%m-%d"),
                    "test_start": test_start.strftime("%Y-%m-%d"),
                    "test_end": test_end.strftime("%Y-%m-%d"),
                }
            )

            # Step forward
            current_train_start = train_start + relativedelta(months=self.step_months)

        logger.info(f"Generated {len(date_pairs)} train/test splits")
        return date_pairs

    def prepare_data(self, start_date: str, end_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepare training data for a given period

        Returns:
            Tuple of (features, target)
        """
        logger.info(f"Preparing data from {start_date} to {end_date}")

        # Get all monthly snapshots in the period
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        all_data = []
        current_date = start

        while current_date <= end:
            # Create features for this month
            engineer = FeatureEngineer(as_of_date=current_date.strftime("%Y-%m-%d"))
            features = engineer.create_features()

            if len(features) > 0:
                # Add forward returns as target
                features = engineer.create_forward_returns(
                    features, horizon_days=self.forward_return_days
                )

                # Add date column for tracking
                features["as_of_date"] = current_date

                all_data.append(features)
                logger.info(f"  {current_date.date()}: {len(features)} stocks")

            # Move to next month
            current_date += relativedelta(months=1)

        if len(all_data) == 0:
            raise ValueError(f"No data found for period {start_date} to {end_date}")

        # Combine all snapshots
        combined = pd.concat(all_data, ignore_index=True)

        # Remove rows with missing target
        combined = combined.dropna(subset=["forward_return"])

        # Separate features and target
        exclude_cols = ["ticker", "forward_return", "as_of_date", "sector"]
        feature_cols = [col for col in combined.columns if col not in exclude_cols]

        X = combined[feature_cols]
        y = combined["forward_return"]

        logger.info(f"Prepared {len(X)} samples with {len(feature_cols)} features")
        logger.info(f"Target mean: {y.mean():.4f}, std: {y.std():.4f}")

        # Handle missing values in features (fill with median)
        X = X.fillna(X.median())

        return X, y, combined[["ticker", "as_of_date", "forward_return"]]

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None,
    ) -> xgb.XGBRegressor:
        """Train XGBoost model"""
        logger.info(f"Training XGBoost with {len(X_train)} samples...")

        model = xgb.XGBRegressor(**self.xgb_params)

        # Use early stopping if validation set provided
        eval_set = [(X_train, y_train)]
        if X_val is not None and y_val is not None:
            eval_set.append((X_val, y_val))

        model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

        logger.info("Training complete")
        return model

    def evaluate_model(
        self,
        model: xgb.XGBRegressor,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        test_info: pd.DataFrame,
    ) -> Dict:
        """Evaluate model performance"""
        # Make predictions
        y_pred = model.predict(X_test)

        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # Information Coefficient (Spearman rank correlation)
        ic, ic_pval = spearmanr(y_pred, y_test)

        # Rank correlation by month
        test_info["prediction"] = y_pred
        monthly_ic = []

        for date in test_info["as_of_date"].unique():
            month_data = test_info[test_info["as_of_date"] == date]
            if len(month_data) > 10:  # Need enough stocks
                corr, _ = spearmanr(month_data["prediction"], month_data["forward_return"])
                monthly_ic.append(corr)

        mean_monthly_ic = np.mean(monthly_ic) if monthly_ic else 0

        # Quintile analysis
        test_info["pred_quintile"] = pd.qcut(
            test_info["prediction"],
            q=5,
            labels=["Q1 (Low)", "Q2", "Q3", "Q4", "Q5 (High)"],
            duplicates="drop",
        )
        quintile_returns = test_info.groupby("pred_quintile")["forward_return"].mean()

        metrics = {
            "rmse": rmse,
            "r2": r2,
            "information_coefficient": ic,
            "ic_pvalue": ic_pval,
            "mean_monthly_ic": mean_monthly_ic,
            "n_months": len(monthly_ic),
            "top_quintile_return": quintile_returns.iloc[-1] if len(quintile_returns) > 0 else 0,
            "bottom_quintile_return": quintile_returns.iloc[0] if len(quintile_returns) > 0 else 0,
            "top_minus_bottom": (
                (quintile_returns.iloc[-1] - quintile_returns.iloc[0])
                if len(quintile_returns) > 0
                else 0
            ),
        }

        return metrics

    def walk_forward_train(self, start_date: str, end_date: str):
        """Execute walk-forward training"""
        logger.info("=" * 80)
        logger.info("Starting Walk-Forward Training")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Train window: {self.train_months} months")
        logger.info(f"Test window: {self.test_months} months")
        logger.info(f"Step size: {self.step_months} months")
        logger.info("=" * 80)

        # Generate date splits
        date_pairs = self.generate_walk_forward_dates(start_date, end_date)

        for i, dates in enumerate(date_pairs, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Split {i}/{len(date_pairs)}")
            logger.info(f"Train: {dates['train_start']} to {dates['train_end']}")
            logger.info(f"Test:  {dates['test_start']} to {dates['test_end']}")
            logger.info(f"{'='*80}")

            try:
                # Prepare training data
                X_train, y_train, train_info = self.prepare_data(
                    dates["train_start"], dates["train_end"]
                )

                # Prepare test data
                X_test, y_test, test_info = self.prepare_data(
                    dates["test_start"], dates["test_end"]
                )

                # Ensure same features
                common_features = X_train.columns.intersection(X_test.columns)
                X_train = X_train[common_features]
                X_test = X_test[common_features]

                # Train model
                model = self.train_model(X_train, y_train)

                # Evaluate
                metrics = self.evaluate_model(model, X_test, y_test, test_info)

                # Log results
                logger.info(f"\nTest Performance:")
                logger.info(f"  RMSE: {metrics['rmse']:.4f}")
                logger.info(f"  R²: {metrics['r2']:.4f}")
                logger.info(
                    f"  Information Coefficient: {metrics['information_coefficient']:.4f} (p={metrics['ic_pvalue']:.4f})"
                )
                logger.info(f"  Mean Monthly IC: {metrics['mean_monthly_ic']:.4f}")
                logger.info(f"  Top Quintile Return: {metrics['top_quintile_return']:.2%}")
                logger.info(f"  Bottom Quintile Return: {metrics['bottom_quintile_return']:.2%}")
                logger.info(f"  Top - Bottom Spread: {metrics['top_minus_bottom']:.2%}")

                # Save model
                model_filename = f"xgboost_ranker_{dates['test_start']}.pkl"
                model_path = self.models_dir / model_filename
                joblib.dump(model, model_path)
                logger.info(f"\nModel saved: {model_path}")

                # Save feature importance
                feature_importance = pd.DataFrame(
                    {"feature": common_features, "importance": model.feature_importances_}
                ).sort_values("importance", ascending=False)

                importance_filename = f"feature_importance_{dates['test_start']}.csv"
                importance_path = self.models_dir / importance_filename
                feature_importance.to_csv(importance_path, index=False)

                # Store results
                result = {
                    "split": i,
                    "train_start": dates["train_start"],
                    "train_end": dates["train_end"],
                    "test_start": dates["test_start"],
                    "test_end": dates["test_end"],
                    "model_path": str(model_path),
                    **metrics,
                }
                self.results.append(result)

            except Exception as e:
                logger.error(f"Error in split {i}: {str(e)}")
                continue

        # Save summary results
        self._save_results()

    def _save_results(self):
        """Save training results summary"""
        if len(self.results) == 0:
            logger.warning("No results to save")
            return

        results_df = pd.DataFrame(self.results)

        # Save to CSV
        results_path = self.models_dir / "walk_forward_results.csv"
        results_df.to_csv(results_path, index=False)
        logger.info(f"\nResults saved: {results_path}")

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("WALK-FORWARD TRAINING SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\nTotal Splits: {len(results_df)}")
        logger.info(f"\nAverage Metrics:")
        logger.info(f"  RMSE: {results_df['rmse'].mean():.4f}")
        logger.info(f"  R²: {results_df['r2'].mean():.4f}")
        logger.info(
            f"  Information Coefficient: {results_df['information_coefficient'].mean():.4f}"
        )
        logger.info(f"  Mean Monthly IC: {results_df['mean_monthly_ic'].mean():.4f}")
        logger.info(f"  Top - Bottom Spread: {results_df['top_minus_bottom'].mean():.2%}")
        logger.info(f"\nIC Statistics:")
        logger.info(f"  Min: {results_df['information_coefficient'].min():.4f}")
        logger.info(f"  Max: {results_df['information_coefficient'].max():.4f}")
        logger.info(f"  Std: {results_df['information_coefficient'].std():.4f}")


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost stock ranker")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--train-months", type=int, default=36, help="Training window in months")
    parser.add_argument("--test-months", type=int, default=12, help="Test window in months")
    parser.add_argument("--step-months", type=int, default=3, help="Step size in months")
    parser.add_argument(
        "--forward-days", type=int, default=63, help="Forward return horizon in days"
    )

    args = parser.parse_args()

    trainer = XGBoostTrainer(
        train_months=args.train_months,
        test_months=args.test_months,
        step_months=args.step_months,
        forward_return_days=args.forward_days,
    )

    trainer.walk_forward_train(args.start_date, args.end_date)


if __name__ == "__main__":
    main()
