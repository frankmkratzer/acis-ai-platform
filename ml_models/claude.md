# ML Models Directory - XGBoost Stock Prediction

## Purpose
This directory contains XGBoost-based machine learning models for stock screening and prediction. These models form the first stage of the two-stage ML+RL pipeline, screening thousands of stocks down to the top 100 candidates based on predicted future returns.

## Key Files

### Training Scripts
- **`train_growth_strategy.py`** - Growth strategy model (3 market cap variants)
- **`train_value_strategy.py`** - Value strategy model (3 market cap variants)
- **`train_dividend_strategy.py`** - Dividend strategy model
- **`train_momentum_strategy.py`** - Momentum strategy model
- **`train_xgboost_optimized.py`** - Generic optimized XGBoost trainer using materialized view

### Supporting Files
- **`model_evaluation.py`** - Evaluate and compare trained models
- **`feature_engineering.py`** - Feature calculation and engineering logic

## Model Architecture

### XGBoost Configuration
```python
{
    'objective': 'reg:squarederror',
    'tree_method': 'hist',  # GPU: 'gpu_hist'
    'device': 'cuda:0',     # GPU device
    'max_depth': 6,
    'learning_rate': 0.01,
    'n_estimators': 1000,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,       # L1 regularization
    'reg_lambda': 1.0,      # L2 regularization
    'random_state': 42
}
```

### Target Variable
- **Target**: Forward 20-day return (configurable via `--horizon`)
- **Calculation**: `(future_close - current_close) / current_close`
- **Prediction**: Continuous regression (not classification)

## Feature Engineering

### Feature Categories (100+ features total)

#### 1. Fundamental Features
- **Growth Metrics**: Revenue growth, earnings growth, cash flow growth
- **Profitability**: ROE, ROA, gross margin, operating margin, net margin
- **Valuation**: P/E, P/B, P/S, PEG ratio, EV/EBITDA
- **Financial Health**: Current ratio, debt-to-equity, interest coverage
- **Efficiency**: Asset turnover, inventory turnover

#### 2. Technical Features
- **Moving Averages**: SMA/EMA (10, 20, 50, 200 days)
- **Momentum**: RSI, MACD, Stochastic Oscillator
- **Volatility**: Bollinger Bands, ATR, Historical volatility
- **Volume**: Volume trends, volume ratios, on-balance volume

#### 3. Sector-Relative Features
- Features normalized by sector averages
- Example: `pe_ratio_vs_sector`, `roe_vs_sector`

#### 4. Temporal Features
- Quarter, month, day of week
- Days since last earnings report
- Seasonality indicators

## Data Loading

### Materialized View (FAST - Recommended)
Uses pre-computed `ml_training_features` materialized view:
```python
df = pd.read_sql("SELECT * FROM ml_training_features WHERE date >= %s AND date <= %s", engine)
```
**Performance**: 5-30 seconds for 10 years of data

### Complex Query (SLOW - Deprecated)
Joins 15+ tables on-the-fly: 10+ minutes for same data

**Always refresh materialized view after data updates:**
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features;
```

## Training Process

### Command Line Usage
```bash
# Growth strategy - mid cap
python train_growth_strategy.py --market-cap mid --start-date 2015-01-01 --end-date 2025-10-30 --gpu 0

# Value strategy - large cap
python train_value_strategy.py --market-cap large --gpu 0

# Dividend strategy (no market cap filter)
python train_dividend_strategy.py --start-date 2015-01-01 --end-date 2025-10-30
```

### Training Pipeline
1. **Load Data**: Query materialized view for date range
2. **Feature Preparation**: Drop NaNs, separate features from target
3. **Model Training**: XGBoost regression with GPU acceleration
4. **Evaluation**: Calculate Spearman IC (Information Coefficient)
5. **Save Artifacts**:
   - Model: `models/{strategy}_{market_cap}cap/model.json`
   - Feature importance: `feature_importance/feature_importance_{strategy}_{market_cap}cap.csv`
   - Metadata: `models/{strategy}_{market_cap}cap/metadata.json`

## Model Performance

### Target Metrics
- **Spearman IC**: 0.08 - 0.12 (good predictive power)
- **Pearson Correlation**: 0.05 - 0.10
- **Universe Reduction**: 2000+ stocks → Top 100 by predicted return

### Expected Training Time
- **CPU**: 30-60 minutes (10 years of data)
- **GPU**: 5-15 minutes (10 years of data)

## Output Structure

### Trained Models Directory
```
models/
├── growth_smallcap/
│   ├── model.json              # XGBoost model file
│   ├── metadata.json           # Training metadata
│   └── feature_names.json      # Feature list
├── growth_midcap/
├── growth_largecap/
├── value_smallcap/
├── value_midcap/
├── value_largecap/
└── dividend/
```

### Feature Importance Directory
```
feature_importance/
├── feature_importance_growth_smallcap.csv
├── feature_importance_growth_midcap.csv
├── feature_importance_growth_largecap.csv
├── feature_importance_value_smallcap.csv
├── feature_importance_value_midcap.csv
├── feature_importance_value_largecap.csv
├── feature_importance_dividend.csv
└── feature_importance.csv      # From train_xgboost_optimized.py
```

## Strategy-Specific Logic

### Growth Strategy
- Emphasizes: Revenue growth, earnings growth, high P/E acceptable
- Market cap segments: small, mid, large
- Features: Growth rates, momentum indicators, expansion metrics

### Value Strategy
- Emphasizes: Low P/E, low P/B, high dividend yield
- Market cap segments: small, mid, large
- Features: Valuation ratios, dividend metrics, financial stability

### Dividend Strategy
- Emphasizes: High dividend yield, dividend growth, payout sustainability
- No market cap segmentation
- Features: Dividend metrics, payout ratio, free cash flow

### Momentum Strategy
- Emphasizes: Strong price trends, relative strength
- Features: Technical indicators, volume patterns, trend strength

## Usage in Portfolio Generation

### Integration with RL Agent
```python
# 1. ML Model screens 2000+ stocks → Top 100
ml_manager = MLPortfolioManager(strategy='growth', market_cap_segment='mid')
predictions = ml_manager.generate_predictions(features_df)
top_100 = predictions.head(100)

# 2. RL Agent optimizes Top 100 → Final 50 positions
rl_agent = RLTradingAgent(strategy='growth', market_cap='mid')
target_portfolio = rl_agent.optimize(top_100_tickers)
```

## Model Versioning

### Database Tracking
All trained models logged to `model_versions` table:
- `model_name`: e.g., "growth_midcap"
- `version`: Auto-incremented version number
- `framework`: "xgboost"
- `spearman_ic`: Model performance metric
- `trained_at`: Training timestamp
- `is_production`: Production status flag

### Promotion to Production
```bash
curl -X POST http://localhost:8000/api/ml-models/growth_midcap/set-production
```

## Common Issues

### Low Spearman IC (< 0.05)
- Check data quality (NaNs, outliers)
- Verify feature engineering calculations
- Consider retraining with different date range
- Check if materialized view needs refresh

### GPU Out of Memory
- Reduce batch size (use `max_bin` parameter)
- Use CPU training instead
- Reduce feature count (feature selection)

### Slow Data Loading
- Ensure materialized view is being used (not complex query)
- Check database indexes on `date` and `ticker` columns
- Consider date range - 10+ years can be large

## Best Practices

1. **Always use GPU** when available (20x faster)
2. **Refresh materialized view** after data updates
3. **Train multiple strategies** to compare performance
4. **Use consistent date ranges** across strategies for fair comparison
5. **Monitor feature importance** to understand model behavior
6. **Version control models** via database tracking
7. **Test in paper trading** before production deployment

## Dependencies
- `xgboost>=2.0.0` - Core ML framework
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical operations
- `sqlalchemy>=2.0.0` - Database connection
- `scipy>=1.10.0` - Statistical functions (Spearman correlation)

## Related Files
- Portfolio manager: `../portfolio/ml_portfolio_manager.py`
- RL training: `../rl_trading/train_hybrid_ppo.py`
- Database schema: `../database/create_tables.sql`
- API endpoints: `../backend/api/ml_models.py`, `../backend/api/ml_portfolio.py`
