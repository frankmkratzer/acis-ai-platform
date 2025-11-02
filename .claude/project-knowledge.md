# ACIS AI Platform - Project Knowledge Base

## Quick Reference for Claude

This document provides essential context for AI assistants working with the ACIS AI Platform codebase.

---

## System Architecture

### High-Level Flow
```
Market Data (Alpha Vantage API)
    ↓
PostgreSQL Database (daily_bars, ratios, etc.)
    ↓
Feature Engineering (100+ features)
    ↓
ml_training_features (Materialized View)
    ↓
XGBoost Models (2000+ stocks → Top 100 per strategy)
    ↓
RL Agent (PPO) (100 stocks → Optimal 50 positions)
    ↓
Portfolio Manager (Drift calculation, rebalancing)
    ↓
Trade Execution (Alpaca brokerage integration)
    ↓
Performance Tracking & Reporting
```

### Two-Stage ML+RL Pipeline

**Stage 1: XGBoost Screening**
- Trains on historical data with 100+ features
- Predicts top performing stocks (screening 2000+ → 100)
- Outputs: Stock rankings, predicted returns, confidence scores

**Stage 2: RL Optimization**
- Takes top 100 stocks from XGBoost
- Optimizes portfolio weights considering Sharpe ratio, diversification, turnover
- Outputs: Final 50 positions with optimal allocations

---

## Technology Stack

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI (REST API)
- **Database**: PostgreSQL 14+ with TimescaleDB extensions
- **ML**: XGBoost, scikit-learn, pandas, numpy
- **RL**: Stable-Baselines3, PyTorch, Gymnasium
- **Data**: Alpha Vantage API (market data), yfinance (supplemental)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React hooks
- **Charts**: Recharts, Chart.js

### Database Schema (47 tables)
**Critical Tables**:
- `daily_bars` - OHLCV price data
- `ratios` - Fundamental metrics (P/E, ROE, debt ratios, etc.)
- `ema`, `macd`, `rsi` - Technical indicators
- `ml_training_features` - Materialized view with all features
- `clients` - User accounts
- `paper_accounts`, `paper_positions` - Paper trading
- `trade_executions` - Transaction history
- `model_deployment_log` - Model versioning

---

## Feature Engineering

### Feature Categories (100+ total)

1. **Price-Based Features** (~30)
   - Returns: 1d, 5d, 21d, 63d, 252d
   - Volatility: rolling std, ATR
   - Volume metrics: volume ratio, price-volume correlation

2. **Fundamental Features** (~40)
   - Valuation: P/E, P/B, P/S, EV/EBITDA
   - Profitability: ROE, ROA, profit margin, ROIC
   - Growth: revenue growth, earnings growth
   - Financial Health: debt/equity, current ratio, quick ratio

3. **Technical Indicators** (~20)
   - Trend: EMA crossovers, MACD
   - Momentum: RSI, Stochastic
   - Volatility: Bollinger Bands, ATR

4. **Sector-Relative Features** (~10)
   - Sector performance relative to S&P 500
   - Stock performance relative to sector

---

## Key Workflows

### 1. Training New Models

**XGBoost Training**:
```bash
python ml_models/train_xgboost.py \
  --strategy growth \
  --market-cap mid \
  --start-date 2015-01-01 \
  --end-date 2025-10-30 \
  --gpu 0  # Optional GPU acceleration
```

**RL Agent Training**:
```bash
python rl_trading/train_hybrid_ppo.py \
  --strategy growth \
  --market-cap mid \
  --timesteps 100000 \
  --eval-freq 10000
```

### 2. Data Pipeline

**EOD (End-of-Day) Updates**:
```bash
bash scripts/run_eod_pipeline.sh
```

**Refresh Features**:
```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY ml_training_features;
```

### 3. Backtesting

```bash
python backtesting/autonomous_backtest.py \
  --start-date 2020-01-01 \
  --end-date 2024-12-31 \
  --capital 100000
```

### 4. Deployment

**Start Backend**:
```bash
cd backend
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend**:
```bash
cd frontend
npm run dev
```

---

## Strategies

### Growth Strategy
- Focus: High revenue/earnings growth
- Market caps: Small, Mid, Large
- Key features: Revenue growth, EPS growth, momentum

### Value Strategy
- Focus: Undervalued fundamentals
- Market caps: Small, Mid, Large
- Key features: Low P/E, P/B, high dividend yield

### Dividend Strategy
- Focus: Stable dividend income
- Market caps: Large, Mid
- Key features: Dividend yield, payout ratio, consistency

### Momentum Strategy
- Focus: Price trends and technical signals
- Market caps: All
- Key features: Returns, volume, RSI, MACD

---

## Model Performance Metrics

### XGBoost Metrics
- **Spearman IC** (Information Coefficient): Rank correlation between predictions and actual returns
  - Target: >0.05 (good), >0.10 (excellent)
- **Precision@K**: Accuracy of top-K predictions
- **Sharpe Ratio**: Risk-adjusted returns

### RL Agent Metrics
- **Sharpe Ratio**: Primary reward signal
- **Max Drawdown**: Risk control
- **Turnover**: Trading cost management
- **Diversification Score**: Portfolio concentration

### Backtest Metrics
- Cumulative return
- Sharpe ratio
- Max drawdown
- Win rate
- Annual return
- Total trades

---

## Database Access Patterns

### Common Queries

**Get latest prices**:
```sql
SELECT ticker, close, volume, date
FROM daily_bars
WHERE date = (SELECT MAX(date) FROM daily_bars)
ORDER BY ticker;
```

**Get ML features for date range**:
```sql
SELECT *
FROM ml_training_features
WHERE date BETWEEN '2023-01-01' AND '2024-12-31'
  AND ticker IN ('AAPL', 'MSFT', 'GOOGL')
ORDER BY date DESC;
```

**Check portfolio positions**:
```sql
SELECT
  p.ticker,
  p.quantity,
  p.avg_cost,
  db.close as current_price,
  (db.close - p.avg_cost) * p.quantity as unrealized_pnl
FROM paper_positions p
JOIN daily_bars db ON p.ticker = db.ticker
WHERE p.account_id = 'xxx'
  AND db.date = (SELECT MAX(date) FROM daily_bars);
```

---

## API Endpoints

### ML Models
- `GET /api/ml-models/` - List all models
- `GET /api/ml-models/production` - Get production model
- `POST /api/ml-models/train` - Start training job
- `POST /api/ml-models/{name}/set-production` - Promote to production
- `GET /api/ml-models/jobs/{id}` - Check training status

### Portfolio
- `GET /api/portfolio/health` - Portfolio health check
- `POST /api/portfolio/generate-signals` - Generate trade signals
- `POST /api/portfolio/rebalance` - Execute rebalancing
- `GET /api/portfolio/positions/{account_id}` - Get current positions

### Clients
- `GET /api/clients/` - List clients
- `GET /api/clients/{id}` - Get client details
- `POST /api/clients/` - Create new client
- `PUT /api/clients/{id}` - Update client

---

## File Structure & Conventions

### Directory Layout
```
acis-ai-platform/
├── ml_models/          # XGBoost training scripts
├── rl_trading/         # PPO RL agent
├── backend/            # FastAPI REST API
│   └── api/
│       ├── main.py
│       └── routes/
├── frontend/           # Next.js dashboard
│   ├── app/           # App Router pages
│   └── components/    # React components
├── database/          # SQL schemas and migrations
├── portfolio/         # Portfolio management logic
├── backtesting/       # Backtesting engine
├── scripts/           # Automation scripts
├── models/            # Trained model artifacts
├── rl_models/         # RL agent checkpoints
├── logs/              # Application logs
└── .claude/           # Claude Code configuration
    └── skills/        # Automation workflows
```

### Naming Conventions
- **Models**: `{strategy}_{marketcap}` (e.g., `growth_midcap`, `value_large`)
- **Tables**: `snake_case` (e.g., `daily_bars`, `client_brokerage_accounts`)
- **API Routes**: `/api/{resource}/{action}` (e.g., `/api/ml-models/train`)
- **Python**: PEP 8, type hints, docstrings
- **TypeScript**: camelCase variables, PascalCase components

---

## Common Development Tasks

### Adding a New Feature
1. Add SQL column to appropriate table
2. Update feature engineering query in `database/build_clean_ml_view.sql`
3. Refresh materialized view
4. Retrain models with new feature

### Adding a New Strategy
1. Create training script variant in `ml_models/`
2. Define strategy-specific feature weights
3. Train XGBoost model
4. Train corresponding RL agent
5. Run backtest to validate
6. Add to production rotation

### Debugging Model Performance
1. Check logs in `logs/` directory
2. Verify feature data quality (no NaN, outliers)
3. Review backtest results
4. Compare Spearman IC across time periods
5. Analyze feature importance

### Database Maintenance
1. Check view freshness: `SELECT last_refresh FROM pg_matviews;`
2. Vacuum tables: `VACUUM ANALYZE daily_bars;`
3. Check index usage: `SELECT * FROM pg_stat_user_indexes;`
4. Monitor size: `SELECT pg_size_pretty(pg_total_relation_size('table_name'));`

---

## Error Handling Patterns

### ML Training Errors
- **NaN in features**: Check data quality, handle missing values
- **Memory errors**: Reduce batch size, use GPU
- **Low Spearman IC**: Review feature engineering, extend training period

### RL Training Errors
- **Divergence**: Reduce learning rate, adjust reward function
- **Poor Sharpe**: Increase transaction cost penalty, adjust risk parameters
- **Crashes**: Check environment step logic, validate state/action spaces

### API Errors
- **500 errors**: Check backend logs, verify database connection
- **Slow responses**: Add caching, optimize queries, use async
- **CORS issues**: Update FastAPI CORS middleware

---

## Production Deployment Checklist

1. ✅ Train model on full historical data
2. ✅ Validate Spearman IC > 0.05
3. ✅ Run backtest with realistic transaction costs
4. ✅ Test on paper trading account for 1-2 weeks
5. ✅ Review logs for errors
6. ✅ Backup current production model
7. ✅ Deploy new model via API
8. ✅ Monitor performance for 48 hours
9. ✅ Document deployment in `model_deployment_log`

---

## Useful Commands Reference

**Database**:
```bash
# Connect to database
PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai

# List tables
\dt

# Describe table
\d table_name

# Check view definition
\d+ ml_training_features
```

**Model Management**:
```bash
# List models
ls -lh models/

# Check model metadata
cat models/growth_midcap/metadata.json

# Compare model performance
python scripts/compare_models.py growth_midcap value_midcap
```

**Logs**:
```bash
# Watch training logs
tail -f logs/growth_momentum.log

# Search for errors
grep -i error logs/*.log

# Count warnings
grep -c warning logs/api.log
```

---

## Critical Files to Review

When working on specific tasks, reference these files:

**Understanding ML Pipeline**:
- `ml_models/train_xgboost.py` - Main training logic
- `ml_models/feature_engineering.py` - Feature definitions
- `database/build_clean_ml_view.sql` - Feature view creation

**Understanding RL Pipeline**:
- `rl_trading/train_hybrid_ppo.py` - RL training
- `rl_trading/portfolio_env.py` - Gymnasium environment
- `rl_trading/reward_functions.py` - Reward design

**Understanding API**:
- `backend/api/main.py` - FastAPI app setup
- `backend/api/routes/ml_models.py` - Model endpoints
- `backend/api/routes/portfolio.py` - Portfolio endpoints

**Understanding Frontend**:
- `frontend/app/layout.tsx` - Root layout
- `frontend/app/ml-models/page.tsx` - ML dashboard
- `frontend/components/` - Reusable components

---

## Links & Resources

- **Claude Code Skills**: `.claude/skills/README.md`
- **Database Schema**: `database/schema.sql`
- **Architecture Docs**: `claude.md` (root directory)
- **Component Docs**: `{directory}/claude.md`

---

**Last Updated**: November 2, 2025
**Platform Version**: 1.0.0
**Database Version**: PostgreSQL 14.x
