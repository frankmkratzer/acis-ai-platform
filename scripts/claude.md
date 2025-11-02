# Scripts Directory - Automation & Utilities

## Purpose
Automation scripts for model training, data pipelines, and system maintenance.

## Key Scripts
- **`auto_train_models.py`** - Orchestrates ML and RL model training
- **`run_eod_pipeline.sh`** - End-of-day data pipeline (market data fetch, feature calc)
- **`manage_models.py`** - Model lifecycle management (promote, archive, delete)
- **`backfill_data.py`** - Historical data backfill
- **`refresh_materialized_views.sh`** - Refresh ML feature views

## Usage
```bash
# Train all models
python scripts/auto_train_models.py --models all --gpu

# Run EOD pipeline
./scripts/run_eod_pipeline.sh

# Promote model to production
python scripts/manage_models.py promote growth_midcap
```
