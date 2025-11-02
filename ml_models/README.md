# XGBoost Stock Ranking - ML Pipeline

## Overview

This directory contains the machine learning pipeline for stock ranking using XGBoost with walk-forward validation.

## Files Created

1. **feature_engineering.py** ✓ - Feature engineering module
2. **train_xgboost.py** - Model training with walk-forward validation
3. **backtest_ml_strategy.py** - Backtesting framework
4. **model_evaluation.py** - Model performance metrics

## Quick Start (After Backfills Complete)

### 1. Train Model (2015-2025 Walk-Forward)

```bash
cd ml_models
python train_xgboost.py --start-date 2015-01-01 --end-date 2025-01-01 --train-months 36 --test-months 12
```

This will:
- Create quarterly snapshots from 2015-2025
- Train on rolling 3-year windows
- Test on following 1-year periods
- Save models to `models/xgboost_ranker_{date}.pkl`
- Generate performance reports

### 2. Backtest ML Strategy

```bash
python backtest_ml_strategy.py --start-date 2020-01-01 --end-date 2025-01-01 --initial-capital 1000000
```

### 3. Compare to Baseline

```bash
python backtest_ml_strategy.py --comparison --baseline momentum
```

## Feature Groups

### Technical Indicators (from database)
- **SMA**: 20, 50, 200-day
- **EMA**: 12, 26, 50-day
- **RSI**: 14-period
- **MACD**: Line, signal, histogram
- **Derived**: price/SMA ratios, EMA crossovers

### Fundamentals (from mid_large_quarterly_financials)
- **Profitability**: ROE, ROA, profit margins
- **Valuation**: P/E, P/S, P/B ratios
- **Quality**: FCF yield, debt/equity
- **Growth**: Revenue, earnings metrics

### Momentum
- **Returns**: 1mo, 3mo, 6mo, 12mo
- **Relative Strength**: Distance from 52-week high

### Interaction Features
- **Momentum × Quality**: return_6mo × ROE
- **Value × Momentum**: fcf_yield × return_3mo
- **Volatility-Adjusted**: return_12mo / daily_range

### Sector-Relative
- **Normalized metrics**: PE/sector_median, return_3mo/sector_median

## Walk-Forward Validation

```
Train: 2015-2017 (36 months) → Test: 2018 (12 months)
Train: 2016-2018 (36 months) → Test: 2019 (12 months)
Train: 2017-2019 (36 months) → Test: 2020 (12 months)
Train: 2018-2020 (36 months) → Test: 2021 (12 months)
Train: 2019-2021 (36 months) → Test: 2022 (12 months)
Train: 2020-2022 (36 months) → Test: 2023 (12 months)
Train: 2021-2023 (36 months) → Test: 2024 (12 months)
Train: 2022-2024 (36 months) → Test: 2025 (12 months)
```

## Expected Performance

Based on research and similar implementations:

- **Information Coefficient (IC)**: 0.03-0.05 (monthly predictions)
- **Rank Correlation**: 0.30-0.40
- **Sharpe Improvement**: 15-30% vs baseline momentum
- **Hit Rate**: 52-58% (stocks outperform median)

## Model Configuration

```python
XGBOOST_PARAMS = {
    'objective': 'reg:squarederror',
    'n_estimators': 200,
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 5,
    'gamma': 0.1,
    'reg_alpha': 0.1,  # L1 regularization
    'reg_lambda': 1.0,  # L2 regularization
    'random_state': 42
}
```

## Feature Importance Analysis

After training, check feature importance:

```python
import joblib
model = joblib.load('models/xgboost_ranker_2024-01-01.pkl')
importances = model.feature_importances_

# Typically top features:
# 1. return_3mo, return_6mo (momentum)
# 2. roe, roa (quality)
# 3. rsi_14, macd_histogram (technical)
# 4. momentum_quality (interaction)
# 5. pe_sector_relative (valuation)
```

## Database Requirements

All data should be backfilled before training:

Required tables:
- [x] daily_bars (price/volume)
- [x] sma, ema, rsi, macd (technical indicators)
- [ ] mid_large_quarterly_financials (fundamentals) **← Currently backfilling**
- [x] ticker_overview (sector, market cap)

## Troubleshooting

### "Not enough data" error
- Ensure backfills are complete
- Check date ranges in database
- Verify at least 1000+ stocks have complete data

### Poor IC scores
- Check for data quality issues (missing values, outliers)
- Verify forward returns are calculated correctly
- Ensure no look-ahead bias in features

### Overfitting
- Reduce max_depth (try 3-4)
- Increase min_child_weight
- Add more regularization (reg_alpha, reg_lambda)

## Next Steps (After Implementation)

1. **Phase 2**: Add LightGBM for ensemble
2. **Phase 3**: Implement FinBERT sentiment features
3. **Phase 4**: LSTM for Growth portfolio (requires GPU)
4. **Phase 5**: Reinforcement learning for position sizing

## Performance Monitoring

Track these metrics monthly:
- Information Coefficient (IC)
- Rank correlation
- Top/bottom quintile spreads
- Feature importance drift
- Prediction distribution

Retrain when:
- IC < 0.02 for 3 consecutive months
- Feature importance shifts >30%
- Market regime change (VIX spike, recession)
