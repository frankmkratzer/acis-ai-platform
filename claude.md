# ACIS AI Platform - Root Context

## Project Overview
ACIS AI is an autonomous investment management platform that combines machine learning (XGBoost) and reinforcement learning (PPO) to generate optimized portfolio recommendations and execute trades via the Schwab API.

## System Architecture

### Core Components
1. **ML Models** (`ml_models/`) - XGBoost models for stock screening and prediction
2. **RL Trading** (`rl_trading/`) - PPO reinforcement learning agents for portfolio optimization
3. **Backend API** (`backend/`) - FastAPI server exposing REST endpoints
4. **Frontend** (`frontend/`) - Next.js 14 web application
5. **Database** (`database/`) - PostgreSQL schema and SQL scripts
6. **Portfolio Management** (`portfolio/`) - Portfolio construction and rebalancing logic
7. **Scripts** (`scripts/`) - Automation, training orchestration, and utilities

### Data Flow
```
Market Data (Schwab/AlphaVantage)
  → Database (PostgreSQL)
  → ML Models (XGBoost screening: 2000+ → 100 candidates)
  → RL Agent (PPO optimization: 100 → 50 positions)
  → Portfolio Manager (construct target portfolio)
  → Trade Execution (Schwab API)
```

## Key Technologies
- **Python 3.11+** - Primary backend language
- **XGBoost** - Gradient boosting for stock prediction (Spearman IC: ~0.08-0.10)
- **Stable-Baselines3** - RL training framework (PPO algorithm)
- **FastAPI** - REST API framework
- **PostgreSQL** - Primary database (47 tables)
- **Next.js 14** - React framework with App Router
- **TypeScript** - Frontend type safety

## Database
- **Connection**: `postgresql://postgres:$@nJose420@localhost/acis-ai`
- **47 Tables** organized into:
  - Reference data (tickers, sectors, market cap)
  - Market data (daily_bars, splits, dividends)
  - Fundamentals (income_statements, balance_sheets, cash_flow_statements, ratios)
  - Technical indicators (ema, macd, rsi, bollinger_bands)
  - ML features (ml_training_features materialized view)
  - Portfolio data (portfolios, holdings, rebalances)
  - Trading (trade_executions, paper_accounts)
  - Client management (clients, brokerage_accounts, autonomous_settings)

## Strategies
The platform supports multiple investment strategies:
- **Growth**: High revenue/earnings growth potential (3 market cap segments)
- **Value**: Undervalued based on fundamentals (3 market cap segments)
- **Dividend**: High dividend yield with stability
- **Momentum**: Strong price trends and relative strength

Market cap segments: `small` (<$2B), `mid` ($2-10B), `large` (>$10B)

## Model Training
Models are strategy and market-cap specific:
- `ml_models/train_growth_strategy.py` → `models/growth_midcap/`
- `rl_trading/train_hybrid_ppo.py` → `rl_models/ppo_growth_mid/`

Feature importance files stored in: `ml_models/feature_importance/`

## Environment Setup
```bash
# Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start backend (port 8000)
cd backend && uvicorn api.main:app --reload

# Start frontend (port 3000)
cd frontend && npm run dev
```

## Important Conventions
- **Date Format**: ISO format strings (`YYYY-MM-DD`)
- **Model Naming**: `{strategy}_{market_cap}cap` (e.g., `growth_midcap`)
- **API Prefix**: All endpoints under `/api/`
- **Database Password**: `$@nJose420` (stored in env vars for production)

## File Organization
```
acis-ai-platform/
├── ml_models/           # XGBoost training scripts
│   ├── models/          # Trained ML models (XGBoost .json)
│   └── feature_importance/  # Feature importance CSVs
├── rl_trading/          # RL training and environments
│   └── rl_models/       # Trained RL models (PPO .zip)
├── backend/             # FastAPI application
│   └── api/             # REST endpoints
├── frontend/            # Next.js application
│   └── src/
│       ├── app/         # App Router pages
│       └── components/  # React components
├── portfolio/           # Portfolio logic
├── scripts/             # Automation and utilities
├── database/            # SQL schemas and migrations
├── data_ingestion/      # Market data fetchers
├── backtesting/         # Backtesting framework
└── utils/               # Shared utilities (DB config, logging)
```

## Common Tasks

### Train a New Model
```bash
# ML Model (XGBoost)
python ml_models/train_growth_strategy.py --market-cap mid --gpu 0

# RL Model (PPO)
python rl_trading/train_hybrid_ppo.py --strategy growth --market-cap mid --device cuda
```

### Generate Portfolio Recommendations
```bash
curl -X POST http://localhost:8000/api/trading/recommendations \
  -H "Content-Type: application/json" \
  -d '{"client_id": 1, "strategy": "growth", "market_cap_segment": "mid"}'
```

### Run End-of-Day Pipeline
```bash
./scripts/run_eod_pipeline.sh
```

## Development Notes
- All Python scripts use absolute imports via `sys.path.insert(0, PROJECT_ROOT)`
- Frontend uses TypeScript strict mode
- Database uses materialized views for ML features (refresh required after data updates)
- Paper trading accounts simulate real trades without executing via Schwab
- Feature engineering includes 100+ features: fundamentals, technicals, sector-relative metrics

## Security
- Schwab OAuth tokens stored encrypted in database
- Database passwords in environment variables
- API authentication via NextAuth (not yet fully implemented)
- Never commit `.env` files or credentials

## Monitoring & Logs
- Training logs: `logs/` directory
- API logs: Console output (structured logging)
- Database logs: PostgreSQL standard logging
- Model performance tracked in `model_versions` table

## Next Steps for New Features
1. Check existing similar functionality in respective directory
2. Update database schema if needed (`database/` → apply SQL)
3. Add backend endpoint (`backend/api/`)
4. Update frontend components (`frontend/src/`)
5. Test with paper trading before live execution
6. Update documentation (`frontend/src/app/docs/`)

## Related Documentation
- Technical database schema: `frontend/src/app/docs/technical/database/page.tsx`
- Getting started guides: `frontend/src/app/docs/getting-started/`
- API documentation: Available at `http://localhost:8000/docs` (FastAPI auto-generated)
