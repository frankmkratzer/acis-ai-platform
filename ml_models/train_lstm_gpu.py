#!/usr/bin/env python3
"""
LSTM Price Prediction Model (GPU-Accelerated)
Deep learning model for predicting stock price movements

Architecture:
- Bidirectional LSTM with attention mechanism
- Input: 60-day sequences of OHLCV + indicators
- Output: 5/20/63-day forward return predictions
- Multi-output regression (3 prediction horizons)

Expected performance:
- Information Coefficient: 0.05-0.08 (vs 0.02-0.03 for linear models)
- Training time: 2-4 hours on DGX Spark (vs days on CPU)
"""
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mlflow
import mlflow.pytorch
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

from utils import get_logger
from utils.db_config import engine

logger = get_logger(__name__)


class StockSequenceDataset(Dataset):
    """Dataset for time-series stock data"""

    def __init__(self, sequences: np.ndarray, targets: np.ndarray):
        """
        Args:
            sequences: Shape (n_samples, sequence_length, n_features)
            targets: Shape (n_samples, n_horizons)
        """
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


class AttentionLSTM(nn.Module):
    """Bidirectional LSTM with attention for stock prediction"""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        num_outputs: int = 3,
    ):
        """
        Args:
            input_size: Number of input features
            hidden_size: LSTM hidden dimension
            num_layers: Number of LSTM layers
            dropout: Dropout rate
            num_outputs: Number of prediction horizons (5/20/63 days)
        """
        super(AttentionLSTM, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True,
        )

        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size), nn.Tanh(), nn.Linear(hidden_size, 1)
        )

        # Output layers (separate head for each horizon)
        self.fc_layers = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(hidden_size * 2, hidden_size),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size, 1),
                )
                for _ in range(num_outputs)
            ]
        )

    def forward(self, x):
        """
        Args:
            x: (batch_size, sequence_length, input_size)

        Returns:
            (batch_size, num_outputs) - predictions for each horizon
        """
        # LSTM layer
        lstm_out, _ = self.lstm(x)  # (batch, seq, hidden*2)

        # Attention weights
        attention_weights = self.attention(lstm_out)  # (batch, seq, 1)
        attention_weights = torch.softmax(attention_weights, dim=1)

        # Apply attention
        context = torch.sum(attention_weights * lstm_out, dim=1)  # (batch, hidden*2)

        # Predict each horizon separately
        outputs = []
        for fc in self.fc_layers:
            out = fc(context)  # (batch, 1)
            outputs.append(out)

        return torch.cat(outputs, dim=1)  # (batch, num_outputs)


class LSTMTrainer:
    """Trainer for LSTM stock prediction model"""

    def __init__(
        self,
        sequence_length: int = 60,
        prediction_horizons: List[int] = [5, 20, 63],
        hidden_size: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2,
        batch_size: int = 256,
        learning_rate: float = 0.001,
        device: str = "cuda:0",
    ):
        """
        Args:
            sequence_length: Number of days to look back
            prediction_horizons: Days ahead to predict [5, 20, 63]
            hidden_size: LSTM hidden dimension
            num_layers: Number of LSTM layers
            dropout: Dropout rate
            batch_size: Training batch size
            learning_rate: Adam learning rate
            device: Device to train on ('cuda:0', 'cuda:1', etc.)
        """
        self.sequence_length = sequence_length
        self.prediction_horizons = prediction_horizons
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")

        logger.info(f"Using device: {self.device}")

        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None

    def load_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load stock data from database"""
        logger.info(f"Loading data from {start_date} to {end_date}...")

        # Get max horizon for forward returns
        max_horizon = max(self.prediction_horizons)

        query = """
        WITH daily_data AS (
            SELECT
                ticker,
                date,
                close,
                volume,
                (high - low) / close as hl_ratio,
                LAG(close, 1) OVER (PARTITION BY ticker ORDER BY date) as prev_close,
                LAG(close, 5) OVER (PARTITION BY ticker ORDER BY date) as close_5d_ago,
                LAG(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_20d_ago,
                LEAD(close, 5) OVER (PARTITION BY ticker ORDER BY date) as close_5d_ahead,
                LEAD(close, 20) OVER (PARTITION BY ticker ORDER BY date) as close_20d_ahead,
                LEAD(close, 63) OVER (PARTITION BY ticker ORDER BY date) as close_63d_ahead,
                AVG(volume) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) as avg_volume_20d
            FROM daily_bars
            WHERE date >= %(start_date)s AND date <= %(end_date)s
        )
        SELECT
            dd.ticker,
            dd.date,
            dd.close,
            dd.volume,
            dd.hl_ratio,
            (dd.close / dd.prev_close - 1) as ret_1d,
            (dd.close / dd.close_5d_ago - 1) as ret_5d,
            (dd.close / dd.close_20d_ago - 1) as ret_20d,
            (dd.volume / dd.avg_volume_20d) as volume_ratio,

            -- Technical indicators
            rsi.value as rsi_14,
            macd.macd_value,
            macd.signal_value,
            sma20.value / dd.close - 1 as sma20_ratio,
            sma50.value / dd.close - 1 as sma50_ratio,
            ema12.value / ema26.value - 1 as ema_ratio,

            -- Forward returns (targets)
            (dd.close_5d_ahead / dd.close - 1) as target_5d,
            (dd.close_20d_ahead / dd.close - 1) as target_20d,
            (dd.close_63d_ahead / dd.close - 1) as target_63d

        FROM daily_data dd
        LEFT JOIN rsi ON dd.ticker = rsi.ticker AND dd.date = rsi.date AND rsi.window_size = 14
        LEFT JOIN macd ON dd.ticker = macd.ticker AND dd.date = macd.date
        LEFT JOIN sma sma20 ON dd.ticker = sma20.ticker AND dd.date = sma20.date AND sma20.window_size = 20
        LEFT JOIN sma sma50 ON dd.ticker = sma50.ticker AND dd.date = sma50.date AND sma50.window_size = 50
        LEFT JOIN ema ema12 ON dd.ticker = ema12.ticker AND dd.date = ema12.date AND ema12.window_size = 12
        LEFT JOIN ema ema26 ON dd.ticker = ema26.ticker AND dd.date = ema26.date AND ema26.window_size = 26

        WHERE dd.close_63d_ahead IS NOT NULL  -- Must have all targets
        ORDER BY ticker, date;
        """

        df = pd.read_sql(query, engine, params={"start_date": start_date, "end_date": end_date})
        logger.info(f"Loaded {len(df):,} samples for {df['ticker'].nunique()} tickers")

        return df

    def create_sequences(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create sequences for LSTM training

        Returns:
            sequences: (n_samples, sequence_length, n_features)
            targets: (n_samples, n_horizons)
            dates: (n_samples,) - corresponding dates
        """
        logger.info(f"Creating sequences with length {self.sequence_length}...")

        # Feature columns (exclude ticker, date, targets)
        feature_cols = [
            col
            for col in df.columns
            if col not in ["ticker", "date", "target_5d", "target_20d", "target_63d"]
        ]
        target_cols = ["target_5d", "target_20d", "target_63d"]

        self.feature_names = feature_cols

        sequences_list = []
        targets_list = []
        dates_list = []

        # Process each ticker separately
        for ticker in df["ticker"].unique():
            ticker_df = df[df["ticker"] == ticker].sort_values("date")

            # Skip if not enough data
            if len(ticker_df) < self.sequence_length:
                continue

            # Extract features and targets
            X = ticker_df[feature_cols].values
            y = ticker_df[target_cols].values
            dates = ticker_df["date"].values

            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            y = np.nan_to_num(y, nan=0.0)

            # Create sliding windows
            for i in range(len(X) - self.sequence_length):
                sequences_list.append(X[i : i + self.sequence_length])
                targets_list.append(y[i + self.sequence_length - 1])  # Target at end of sequence
                dates_list.append(dates[i + self.sequence_length - 1])

        sequences = np.array(sequences_list)
        targets = np.array(targets_list)
        dates = np.array(dates_list)

        logger.info(f"Created {len(sequences):,} sequences")
        logger.info(f"Shape: sequences={sequences.shape}, targets={targets.shape}")

        return sequences, targets, dates

    def normalize_data(
        self, sequences: np.ndarray, targets: np.ndarray, fit: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Normalize sequences and targets"""
        # Flatten sequences for fitting scaler
        n_samples, seq_len, n_features = sequences.shape
        sequences_flat = sequences.reshape(-1, n_features)

        if fit:
            sequences_flat = self.scaler.fit_transform(sequences_flat)
        else:
            sequences_flat = self.scaler.transform(sequences_flat)

        sequences_norm = sequences_flat.reshape(n_samples, seq_len, n_features)

        return sequences_norm, targets

    def train(
        self,
        train_sequences: np.ndarray,
        train_targets: np.ndarray,
        val_sequences: np.ndarray,
        val_targets: np.ndarray,
        epochs: int = 50,
    ) -> Dict:
        """Train LSTM model"""
        logger.info(f"Training LSTM model for {epochs} epochs...")

        # Create datasets and loaders
        train_dataset = StockSequenceDataset(train_sequences, train_targets)
        val_dataset = StockSequenceDataset(val_sequences, val_targets)

        train_loader = DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True, num_workers=4, pin_memory=True
        )
        val_loader = DataLoader(
            val_dataset, batch_size=self.batch_size, shuffle=False, num_workers=4, pin_memory=True
        )

        # Initialize model
        n_features = train_sequences.shape[2]
        n_outputs = len(self.prediction_horizons)

        self.model = AttentionLSTM(
            input_size=n_features,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            num_outputs=n_outputs,
        ).to(self.device)

        logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")

        # Loss and optimizer
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )

        # Training loop
        best_val_loss = float("inf")
        history = {"train_loss": [], "val_loss": [], "val_ic": []}

        for epoch in range(epochs):
            # Training
            self.model.train()
            train_loss = 0.0

            for sequences, targets in train_loader:
                sequences = sequences.to(self.device)
                targets = targets.to(self.device)

                optimizer.zero_grad()
                outputs = self.model(sequences)
                loss = criterion(outputs, targets)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()

            train_loss /= len(train_loader)

            # Validation
            self.model.eval()
            val_loss = 0.0
            all_preds = []
            all_targets = []

            with torch.no_grad():
                for sequences, targets in val_loader:
                    sequences = sequences.to(self.device)
                    targets = targets.to(self.device)

                    outputs = self.model(sequences)
                    loss = criterion(outputs, targets)

                    val_loss += loss.item()
                    all_preds.append(outputs.cpu().numpy())
                    all_targets.append(targets.cpu().numpy())

            val_loss /= len(val_loader)

            # Calculate Information Coefficient
            all_preds = np.vstack(all_preds)
            all_targets = np.vstack(all_targets)
            ic_per_horizon = [
                np.corrcoef(all_preds[:, i], all_targets[:, i])[0, 1] for i in range(n_outputs)
            ]
            avg_ic = np.mean(ic_per_horizon)

            # Learning rate scheduling
            scheduler.step(val_loss)

            # Log progress
            if (epoch + 1) % 5 == 0 or epoch == 0:
                logger.info(f"Epoch {epoch+1}/{epochs}")
                logger.info(f"  Train Loss: {train_loss:.6f}")
                logger.info(f"  Val Loss:   {val_loss:.6f}")
                logger.info(f"  Val IC:     {avg_ic:.4f}")
                logger.info(
                    f"  IC by horizon: {' | '.join([f'{ic:.4f}' for ic in ic_per_horizon])}"
                )

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_ic"].append(avg_ic)

            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(
                    {
                        "epoch": epoch,
                        "model_state_dict": self.model.state_dict(),
                        "optimizer_state_dict": optimizer.state_dict(),
                        "val_loss": val_loss,
                        "val_ic": avg_ic,
                    },
                    "models/lstm_best.pt",
                )

        logger.info(f"\nTraining complete! Best val loss: {best_val_loss:.6f}")

        return history

    def save_model(self, output_path: str):
        """Save model and scaler"""
        if self.model is None:
            raise ValueError("No model to save")

        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "scaler_mean": self.scaler.mean_,
                "scaler_scale": self.scaler.scale_,
                "feature_names": self.feature_names,
                "config": {
                    "sequence_length": self.sequence_length,
                    "prediction_horizons": self.prediction_horizons,
                    "hidden_size": self.hidden_size,
                    "num_layers": self.num_layers,
                    "dropout": self.dropout,
                },
            },
            output_path,
        )

        logger.info(f"Model saved to: {output_path}")


def main():
    """Main training pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="Train LSTM model on GPU")
    parser.add_argument("--start-date", type=str, default="2015-01-01")
    parser.add_argument("--end-date", type=str, default=str(date.today()))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--output", type=str, default="models/lstm_gpu.pt")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("LSTM GPU Training Pipeline")
    logger.info("=" * 60)

    # Initialize MLflow
    mlflow.set_experiment("lstm_stock_prediction")

    with mlflow.start_run():
        mlflow.log_param("start_date", args.start_date)
        mlflow.log_param("end_date", args.end_date)
        mlflow.log_param("epochs", args.epochs)
        mlflow.log_param("gpu", args.gpu)

        # Initialize trainer
        trainer = LSTMTrainer(device=f"cuda:{args.gpu}")

        # Load data
        df = trainer.load_data(args.start_date, args.end_date)

        # Create sequences
        sequences, targets, dates = trainer.create_sequences(df)

        # Train/val split (80/20 temporal split)
        split_idx = int(len(sequences) * 0.8)
        train_seq, val_seq = sequences[:split_idx], sequences[split_idx:]
        train_tgt, val_tgt = targets[:split_idx], targets[split_idx:]

        # Normalize
        train_seq, train_tgt = trainer.normalize_data(train_seq, train_tgt, fit=True)
        val_seq, val_tgt = trainer.normalize_data(val_seq, val_tgt, fit=False)

        # Train
        history = trainer.train(train_seq, train_tgt, val_seq, val_tgt, epochs=args.epochs)

        # Log final metrics
        mlflow.log_metric("final_val_loss", history["val_loss"][-1])
        mlflow.log_metric("final_val_ic", history["val_ic"][-1])
        mlflow.log_metric("best_val_ic", max(history["val_ic"]))

        # Save model
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(output_path))
        mlflow.log_artifact(str(output_path))

        logger.info(f"\nTraining complete! Model saved to: {output_path}")


if __name__ == "__main__":
    main()
