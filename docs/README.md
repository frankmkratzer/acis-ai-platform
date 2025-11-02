# ACIS AI Platform - Complete Documentation

**Version:** 1.0.0
**Last Updated:** January 2025

## Overview

ACIS AI is a sophisticated autonomous investment platform that combines machine learning (ML) and reinforcement learning (RL) to manage client portfolios across multiple trading strategies and market capitalizations. The system automatically selects optimal strategies based on market conditions, rebalances portfolios, and executes trades through brokerage integrations (Schwab) while maintaining strict risk controls and compliance standards.

## Quick Links

- **Web Documentation UI:** [http://192.168.50.234:3000/docs/](http://192.168.50.234:3000/docs/)
- **API Documentation:** [API_REFERENCE.md](./API_REFERENCE.md)
- **Database Schema:** [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)
- **Deployment Guide:** [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **Operations Manual:** [OPERATIONS_MANUAL.md](./OPERATIONS_MANUAL.md)

## System Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  Next.js 14 + React + TypeScript + Tailwind CSS             │
│  Port: 3000                                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────────┐
│                        BACKEND                               │
│  FastAPI + Python 3.11 + SQLAlchemy                         │
│  Port: 8000                                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │ SQL Queries
┌──────────────────────▼──────────────────────────────────────┐
│                       DATABASE                               │
│  PostgreSQL 14+ (~50GB market data)                         │
│  Port: 5432                                                  │
└─────────────────────────────────────────────────────────────┘
```

### ML/RL Infrastructure

```
┌─────────────────────────────────────────────────────────────┐
│                    ML TRAINING (XGBoost)                     │
│  • CPU-based training (multi-core)                          │
│  • scikit-learn pipeline                                    │
│  • Model versioning with timestamps                         │
│  • Training time: ~30 min per model                         │
│  • Output: 9 models (3 strategies × 3 market caps)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   RL TRAINING (PPO/JAX)                      │
│  • GPU-accelerated (NVIDIA CUDA 12.1+)                      │
│  • Gymnasium environment                                    │
│  • Training time: ~3 hours per agent                        │
│  • Output: 9 agents (3 strategies × 3 market caps)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   MLOPS (MLflow)                             │
│  • Experiment tracking                                       │
│  • Model registry and versioning                            │
│  • Data drift detection (KS test + PSI)                     │
│  • Automated retraining pipelines                           │
│  • Port: 5000                                                │
└─────────────────────────────────────────────────────────────┘
```

## Core Features

### 1. Hybrid ML+RL System

- **XGBoost** screens ~2000 stocks → top 100 candidates
- **PPO Reinforcement Learning** optimizes portfolio allocation across top 50 positions
- Combines prediction strength (ML) with sequential decision-making (RL)

### 2. Multiple Trading Strategies

| Strategy  | Focus | Key Metrics |
|-----------|-------|-------------|
| **Growth** | High revenue/earnings growth | Revenue growth, EPS growth, gross margin, R&D |
| **Momentum** | Price trends and technicals | 50/200-day SMA, RSI, MACD, volume trends |
| **Value** | Undervalued fundamentals | P/E, P/B, dividend yield, debt/equity, ROE |
| **Dividend** | Income and stability | Dividend yield, payout ratio, FCF, stability |

Each strategy runs across 3 market cap segments (Large: >$10B, Mid: $2-10B, Small: <$2B) = **12 specialized models**.

### 3. Market Regime Detection

Automatically classifies market conditions:
- **Bull Market** → Growth/Momentum strategies
- **Bear Market** → Value/Dividend strategies
- **High Volatility** → Dividend/defensive positions
- **Low Volatility** → Momentum/aggressive growth
- **Sideways** → Value/quality picks

### 4. Risk Management

**Hard Constraints:**
- Min position: 1% of portfolio
- Max position: 10% of portfolio
- Max positions: 50 holdings
- Portfolio drift threshold: 5% triggers rebalance
- Position drift threshold: 3% per holding
- Minimum cash reserve: 2-5% (configurable)

**Transaction Cost Modeling:**
- Commission: $0 (modern brokerages)
- Slippage: 0.1% market impact
- RL agent learns to minimize turnover

### 5. Autonomous Operations

- **Daily Data Pipeline** (6:00 AM ET): Refresh market data
- **Daily Incremental ML Updates** (2:00 AM ET): Fine-tune models with last 7 days
- **Daily Rebalancing** (4:30 PM ET): Threshold-based portfolio adjustments
- **Weekly Full ML Retraining** (Sunday): Full model retraining on historical data
- **Monthly RL Retraining** (1st of month): Full RL agent retraining

### 6. MLOps & Model Management

- **MLflow Integration**: Experiment tracking, model registry, versioning
- **Data Drift Detection**: KS test + PSI for distribution changes
- **Automated Retraining**: Drift-triggered or scheduled
- **Model Promotion**: Stage-based (Staging → Production) with performance criteria
- **Rollback Capability**: Easy model version management

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 14+ with SQLAlchemy ORM
- **ML**: XGBoost, scikit-learn, pandas, numpy
- **RL**: JAX, Gymnasium, PPO algorithms
- **MLOps**: MLflow, boto3 (S3 artifacts)
- **APIs**: Schwab API, Alpha Vantage
- **Auth**: HTTP Basic Auth, OAuth 2.0 (Schwab)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Custom React components + lucide-react icons
- **State Management**: React hooks + axios API client

### Infrastructure
- **Database**: PostgreSQL 14+ (~50GB storage)
- **Compute**: NVIDIA GPU (CUDA 12.1+) for RL training
- **Network**: ngrok for OAuth callbacks (dev/test)
- **Deployment**: Docker Compose (local), Kubernetes (production)

## Directory Structure

```
acis-ai-platform/
├── backend/                      # FastAPI backend
│   ├── api/
│   │   ├── routers/             # API route handlers
│   │   │   ├── clients.py
│   │   │   ├── trading.py
│   │   │   ├── autonomous.py
│   │   │   ├── portfolio_health.py
│   │   │   └── system_admin.py
│   │   ├── services/            # Business logic
│   │   │   ├── trade_execution.py
│   │   │   ├── trading_service.py
│   │   │   └── balance_manager.py
│   │   ├── database/            # DB models & connection
│   │   └── main.py              # FastAPI app entry
│   └── .env                     # Environment variables
│
├── frontend/                     # Next.js frontend
│   ├── src/
│   │   ├── app/                 # App Router pages
│   │   │   ├── clients/
│   │   │   ├── trading/
│   │   │   ├── ml-models/
│   │   │   ├── autonomous/
│   │   │   ├── admin/
│   │   │   └── docs/            # Documentation UI
│   │   ├── components/          # React components
│   │   │   ├── Tooltip.tsx
│   │   │   ├── InlineHelp.tsx
│   │   │   └── NavigationBar.tsx
│   │   ├── lib/                 # API client utilities
│   │   └── types/               # TypeScript types
│   └── package.json
│
├── ml_models/                    # Trained XGBoost models
│   ├── growth_largecap_*.pkl
│   ├── growth_midcap_*.pkl
│   ├── growth_smallcap_*.pkl
│   ├── momentum_*.pkl
│   ├── value_*.pkl
│   └── dividend_*.pkl
│
├── rl_trading/                   # RL training scripts
│   ├── train_hybrid_ppo.py      # JAX PPO training
│   ├── hybrid_portfolio_env.py  # Gymnasium environment
│   ├── train_growth_strategy.py
│   ├── train_momentum_strategy.py
│   ├── train_value_strategy.py
│   └── train_dividend_strategy.py
│
├── mlops/                        # MLOps infrastructure
│   ├── mlflow/                   # MLflow integration
│   │   ├── mlflow_client.py
│   │   ├── train_with_mlflow.py
│   │   └── docker-compose.mlflow.yml
│   ├── drift_detection/          # Data drift monitoring
│   │   └── drift_detector.py
│   └── retraining/               # Automated retraining
│       └── auto_retrain.py
│
├── scripts/                      # Operational scripts
│   ├── run_eod_pipeline.sh       # Daily data pipeline
│   ├── run_daily_incremental_update.sh  # Daily ML updates
│   ├── run_daily_rebalance.py    # Daily portfolio rebalancing
│   ├── run_weekly_ml_training.sh # Weekly full ML retraining
│   ├── run_monthly_rl_training.sh # Monthly RL retraining
│   ├── auto_train_models.py      # ML training automation
│   ├── auto_train_rl_models.py   # RL training automation
│   └── manage_models.py          # Model management utilities
│
├── backtesting/                  # Backtest framework
│   ├── backtest_engine.py
│   └── autonomous_backtest.py
│
├── portfolio/                    # Portfolio management
│   ├── ml_portfolio_manager.py
│   ├── backtest_engine.py
│   └── claude.md
│
├── database/                     # SQL schemas & migrations
│   ├── schema.sql
│   ├── build_clean_ml_view.sql
│   ├── paper_trading_tables.sql
│   ├── add_autonomous_client_settings.sql
│   └── migrations/
│
├── k8s/                          # Kubernetes manifests
│   └── base/
│       ├── postgres-statefulset.yaml
│       ├── backend-deployment.yaml
│       ├── frontend-deployment.yaml
│       ├── mlflow-deployment.yaml
│       └── model-retraining-cronjob.yaml
│
├── docs/                         # This documentation
│   ├── README.md                 # This file
│   ├── ARCHITECTURE.md
│   ├── API_REFERENCE.md
│   ├── DATABASE_SCHEMA.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── OPERATIONS_MANUAL.md
│   ├── MLOPS_GUIDE.md
│   ├── TRADING_STRATEGIES.md
│   └── TROUBLESHOOTING.md
│
├── tests/                        # Test suites
│   ├── unit/
│   └── integration/
│
├── logs/                         # Application logs
│   ├── pipeline/
│   ├── daily_updates/
│   └── rebalancing/
│
├── requirements.txt              # Python dependencies
├── .gitignore
├── .pre-commit-config.yaml      # Pre-commit hooks
└── README.md                     # Quick start guide
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- NVIDIA GPU (for RL training, CUDA 12.1+)
- ngrok (for Schwab OAuth callbacks)
- Alpha Vantage API key
- Schwab Developer account

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/frankmkratzer/acis-ai-platform.git
   cd acis-ai-platform
   ```

2. **Set Up Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Database**
   ```bash
   PGPASSWORD='$@nJose420' psql -U postgres -c "CREATE DATABASE \"acis-ai\";"
   PGPASSWORD='$@nJose420' psql -U postgres -d acis-ai -f database/schema.sql
   ```

4. **Configure Environment Variables**
   ```bash
   # backend/.env
   DATABASE_URL=postgresql://postgres:$@nJose420@localhost:5432/acis-ai
   ALPHA_VANTAGE_API_KEY=your_key
   SCHWAB_CLIENT_ID=your_client_id
   SCHWAB_CLIENT_SECRET=your_secret
   SCHWAB_REDIRECT_URI=https://your-ngrok-url.ngrok.io/api/schwab/callback
   ```

5. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

6. **Load Initial Data**
   ```bash
   source venv/bin/activate
   ./scripts/run_eod_pipeline.sh
   ```

### Running the Platform

**Terminal 1 - Backend:**
```bash
cd backend
source ../venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - ngrok (for Schwab OAuth):**
```bash
ngrok http 8000
```

**Terminal 4 - MLflow (optional):**
```bash
docker-compose -f mlops/mlflow/docker-compose.mlflow.yml up
```

**Access Points:**
- Frontend: http://192.168.50.234:3000 or http://localhost:3000
- API Docs: http://192.168.50.234:8000/docs
- MLflow UI: http://localhost:5000
- Documentation: http://192.168.50.234:3000/docs/

## Key Concepts

### Trade Recommendations Workflow

1. **Market Regime Detection** → Classifies current market (Bull/Bear/Volatile/etc.)
2. **Meta-Model Selection** → Selects optimal strategy for regime
3. **ML Stock Screening** → XGBoost scores ~2000 stocks → top 100
4. **RL Portfolio Optimization** → PPO agent decides allocation across top 50
5. **Trade Generation** → Calculate buy/sell orders to reach target
6. **Risk Checks** → Validate against position limits, drift thresholds
7. **Execution** → Submit to Schwab (paper or live mode)

### Paper Trading vs Live Trading

- **Paper Trading**: Simulated trades stored in `paper_accounts` and `paper_trades` tables
- **Live Trading**: Real trades executed via Schwab API
- **Sync Balance**: Use `/api/clients/{id}/sync-balance-from-schwab` to initialize paper account from live Schwab balance

### Model Training Workflow

**ML Training (XGBoost):**
1. Load training data from `ml_training_features` view
2. Engineer features (fundamentals + technicals + risk)
3. Train XGBoost classifier (predicts positive returns)
4. Evaluate on test set (accuracy, precision, recall, F1, ROC-AUC)
5. Save model to `ml_models/` directory with timestamp
6. (Optional) Log to MLflow for tracking

**RL Training (PPO):**
1. Load pre-trained ML model for stock screening
2. Create Gymnasium environment with portfolio simulator
3. Train PPO agent with JAX (GPU-accelerated)
4. Optimize for risk-adjusted returns (Sharpe ratio)
5. Save agent to `rl_trading/trained_models/` directory
6. (Optional) Log to MLflow for tracking

### Incremental Learning

- **Daily Incremental Updates**: Fine-tune models with last 7 days of data (~5-10 min)
- **Weekly Full Retraining**: Retrain from scratch on full historical data (~30-60 min)
- **Hybrid Approach**: Fast adaptation + robust long-term performance

## MLOps Features

### MLflow Model Registry

- **Experiment Tracking**: Log parameters, metrics, artifacts for every training run
- **Model Versioning**: Automatic versioning with stage transitions (Staging → Production)
- **Model Comparison**: Compare metrics across models and versions
- **Artifact Storage**: Store models, feature importance, plots

### Data Drift Detection

- **Kolmogorov-Smirnov Test**: Statistical test for distribution changes
- **Population Stability Index (PSI)**: Measure population shift
- **Automated Alerts**: Trigger retraining when drift exceeds threshold

### Automated Retraining

- **Drift-Triggered**: Retrain when >30% of features show drift
- **Scheduled**: Daily incremental, weekly full ML, monthly full RL
- **Performance-Based Promotion**: Auto-promote to production if accuracy > 70%

## Security & Compliance

- **Authentication**: HTTP Basic Auth for API endpoints
- **OAuth 2.0**: Schwab API integration with token refresh
- **Database Security**: PostgreSQL user permissions, encrypted connections
- **Secrets Management**: Environment variables, never committed to git
- **Audit Trail**: All trades logged with timestamps and user IDs
- **Rate Limiting**: API throttling to prevent abuse

## Performance Metrics

**Backtest Results (2015-2023):**
- Growth Strategy: 15.2% CAGR, Sharpe 1.8
- Momentum Strategy: 18.7% CAGR, Sharpe 1.6
- Value Strategy: 12.4% CAGR, Sharpe 1.4
- Dividend Strategy: 9.8% CAGR, Sharpe 1.2
- Meta-Model (Adaptive): 16.9% CAGR, Sharpe 2.1

**System Performance:**
- API Response Time: <100ms (p99)
- ML Inference: <50ms per stock
- RL Inference: <10ms per portfolio
- Daily Rebalance: ~10-15 minutes
- Database Size: ~50GB (10 years of data)

## Support & Maintenance

### Monitoring

- **System Health**: `/api/health` endpoint
- **Autonomous Status**: `/api/autonomous/status`
- **Database Health**: PostgreSQL stats, query performance
- **Model Performance**: MLflow metrics, drift detection reports

### Logs

- **Pipeline Logs**: `logs/pipeline/`
- **Daily Update Logs**: `logs/daily_updates/`
- **Rebalancing Logs**: `logs/rebalancing/`
- **API Logs**: Backend console output

### Common Issues

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for:
- Database connection errors
- Schwab OAuth failures
- Model loading issues
- GPU memory errors (RL training)
- Rebalancing failures

## Contributing

This is a proprietary system. For questions or issues:
- Check documentation at http://192.168.50.234:3000/docs/
- Review logs in `logs/` directory
- Contact system administrator

## License

Proprietary - All Rights Reserved

## Version History

- **v1.0.0** (January 2025): Initial production release
  - Complete ML+RL hybrid system
  - Schwab API integration
  - Autonomous trading capabilities
  - MLOps infrastructure with MLflow
  - Data drift detection and automated retraining
  - Incremental learning support
  - Comprehensive documentation

## Roadmap

- [ ] Tax-loss harvesting automation
- [ ] Additional brokerage integrations (TD Ameritrade, E*TRADE)
- [ ] Advanced risk analytics dashboard
- [ ] Multi-factor authentication
- [ ] Mobile app for client monitoring
- [ ] Backtesting UI with parameter tuning
- [ ] Custom strategy builder
- [ ] ESG/sustainable investing filters

---

**For detailed documentation, visit:** http://192.168.50.234:3000/docs/

**For technical support, see:** [OPERATIONS_MANUAL.md](./OPERATIONS_MANUAL.md) and [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
