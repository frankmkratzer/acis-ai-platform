# ACIS AI Platform - System Architecture

**Last Updated:** January 2025

## Table of Contents

- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [Database Architecture](#database-architecture)
- [ML/RL Architecture](#mlrl-architecture)
- [MLOps Architecture](#mlops-architecture)
- [Data Flow](#data-flow)
- [Trading Pipeline](#trading-pipeline)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)

## Overview

ACIS AI follows a modern three-tier architecture with clear separation of concerns:

1. **Presentation Layer** (Frontend): Next.js 14 + React + TypeScript
2. **Business Logic Layer** (Backend): FastAPI + Python 3.11
3. **Data Layer** (Database): PostgreSQL 14+

Additionally, ML/RL infrastructure and MLOps tooling provide AI capabilities and model lifecycle management.

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                              │
│                      (Web Interface)                              │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────▼─────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐    │
│  │  Client Mgmt │  │  Trading UI   │  │  ML Models UI      │    │
│  └──────────────┘  └───────────────┘  └────────────────────┘    │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐    │
│  │  Autonomous  │  │  Admin Panel  │  │  Documentation     │    │
│  └──────────────┘  └───────────────┘  └────────────────────┘    │
│                         Port: 3000                                │
└────────────────────────┬─────────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼─────────────────────────────────────────┐
│                    BACKEND (FastAPI)                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     API ROUTERS                             │  │
│  │  Clients │ Trading │ Autonomous │ Portfolio │ System Admin │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   BUSINESS SERVICES                         │  │
│  │  Trade Execution │ Trading Service │ Balance Manager      │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   EXTERNAL APIs                             │  │
│  │  Schwab API │ Alpha Vantage │ OAuth 2.0                    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                         Port: 8000                                │
└────────────────────────┬─────────────────────────────────────────┘
                         │ SQL Queries
┌────────────────────────▼─────────────────────────────────────────┐
│                    DATABASE (PostgreSQL 14)                       │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │  Market Data │  │  Client Data   │  │  Trading Data        │ │
│  │  (~50GB)     │  │  (Accounts)    │  │  (Executions/Rec's)  │ │
│  └──────────────┘  └────────────────┘  └──────────────────────┘ │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │  ML Features │  │  Paper Trading │  │  Autonomous Settings │ │
│  │  (Views)     │  │  (Simulations) │  │  (Configs)           │ │
│  └──────────────┘  └────────────────┘  └──────────────────────┘ │
│                         Port: 5432                                │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   ML/RL INFRASTRUCTURE                             │
│  ┌──────────────────┐    ┌───────────────────┐                   │
│  │  XGBoost Models  │    │  PPO RL Agents    │                   │
│  │  (Stock Screen)  │    │  (Portfolio Opt)  │                   │
│  │  ml_models/      │    │  rl_trading/      │                   │
│  │  ~30 min train   │    │  ~3 hrs train     │                   │
│  └──────────────────┘    └───────────────────┘                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              MLOps (MLflow)                               │    │
│  │  Tracking │ Registry │ Drift Detection │ Auto Retraining │    │
│  │                      Port: 5000                           │    │
│  └──────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

### Technology Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript 5.x
- **Styling**: Tailwind CSS 3.x
- **State Management**: React hooks (useState, useEffect)
- **HTTP Client**: axios
- **Icons**: lucide-react
- **UI Components**: Custom components (Tooltip, InlineHelp, NavigationBar)

### Directory Structure

```
frontend/src/
├── app/                          # App Router pages
│   ├── layout.tsx               # Root layout with navigation
│   ├── page.tsx                 # Home/dashboard
│   ├── clients/
│   │   ├── page.tsx             # Client list
│   │   └── [id]/
│   │       ├── page.tsx         # Client detail
│   │       └── portfolio-health/
│   │           └── page.tsx     # Portfolio health analysis
│   ├── trading/
│   │   ├── page.tsx             # Trading dashboard
│   │   └── history/
│   │       └── page.tsx         # Trade history
│   ├── ml-models/
│   │   └── page.tsx             # ML model management
│   ├── autonomous/
│   │   └── page.tsx             # Autonomous fund dashboard
│   ├── admin/
│   │   └── page.tsx             # System administration
│   ├── backtest/
│   │   └── page.tsx             # Backtesting interface
│   └── docs/                    # Documentation UI
│       ├── layout.tsx           # Docs layout with sidebar
│       ├── page.tsx             # Docs home
│       ├── getting-started/
│       ├── methodology/
│       ├── operations/
│       └── technical/
├── components/                   # Reusable React components
│   ├── Tooltip.tsx              # Tooltip component with help icons
│   ├── InlineHelp.tsx           # Expandable help boxes
│   ├── NavigationBar.tsx        # Top navigation
│   ├── ClientFormModal.tsx      # Client create/edit modal
│   └── AutonomousSettingsPanel.tsx
├── lib/                          # Utilities and helpers
│   └── api.ts                   # API client configuration
└── types/                        # TypeScript type definitions
    └── index.ts                 # Shared types (Client, Trade, etc.)
```

### Key Design Patterns

**1. Server Components vs Client Components:**
```typescript
// Server component (default) - good for static content
export default function DocsPage() {
  return <div>Documentation</div>
}

// Client component - needed for interactivity
'use client'
export default function TradingPage() {
  const [trades, setTrades] = useState([])
  // ... interactive logic
}
```

**2. API Client Pattern:**
```typescript
// lib/api.ts
const api = axios.create({
  baseURL: 'http://192.168.50.234:8000/api',
  auth: { username: 'admin', password: 'password' }
})

// Usage in components
const response = await api.get('/clients')
```

**3. Tooltip Pattern for Inline Help:**
```typescript
<Tooltip
  content="This shows your portfolio's health score"
  learnMoreLink="/docs/operations/portfolio-health"
/>
```

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI 0.104+
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Database Driver**: psycopg2-binary
- **Validation**: Pydantic 2.x
- **Server**: Uvicorn (ASGI)
- **Auth**: HTTP Basic Auth + OAuth 2.0

### Directory Structure

```
backend/api/
├── main.py                       # FastAPI app entry point
├── routers/                      # API route handlers
│   ├── clients.py               # Client CRUD operations
│   ├── trading.py               # Trade recommendations & execution
│   ├── autonomous.py            # Autonomous fund operations
│   ├── portfolio_health.py      # Portfolio health scoring
│   └── system_admin.py          # System administration
├── services/                     # Business logic layer
│   ├── trade_execution.py       # Trade execution engine
│   ├── trading_service.py       # Trading business logic
│   └── balance_manager.py       # Account balance management
├── database/                     # Database layer
│   ├── connection.py            # PostgreSQL connection pool
│   ├── models.py                # SQLAlchemy models
│   └── queries.py               # Complex SQL queries
└── .env                          # Environment configuration
```

### API Router Pattern

```python
# routers/clients.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..database import get_db_connection

router = APIRouter(prefix="/api/clients", tags=["clients"])

@router.get("/", response_model=List[Client])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    conn = Depends(get_db_connection)
):
    """List all clients with pagination"""
    # Business logic here
    return clients

@router.post("/", response_model=Client)
async def create_client(
    client: ClientCreate,
    conn = Depends(get_db_connection)
):
    """Create new client"""
    # Validation & creation logic
    return new_client
```

### Service Layer Pattern

```python
# services/trade_execution.py
class TradeExecutionService:
    def __init__(self, schwab_api, db_conn):
        self.schwab = schwab_api
        self.db = db_conn

    def execute_trades(self, client_id: int, recommendations: List[Trade]):
        """Execute trades for a client"""
        # 1. Validate recommendations
        # 2. Check account balance
        # 3. Submit to Schwab API
        # 4. Record execution in database
        # 5. Update paper trading account
        pass
```

## Database Architecture

### Schema Design

**Core Principles:**
- **Normalization**: 3NF for data integrity
- **Time-Series Optimization**: Indexed on (ticker, date) for market data
- **Partitioning**: Large tables partitioned by date ranges
- **Materialized Views**: Pre-computed ML features for fast inference

### Key Tables

```sql
-- Client Management
clients (
    client_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    risk_tolerance VARCHAR(20),
    created_at TIMESTAMP
)

client_brokerage_accounts (
    id SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(client_id),
    brokerage_id INT REFERENCES brokerages(brokerage_id),
    account_hash VARCHAR(255),  -- Encrypted account number
    oauth_access_token TEXT,
    oauth_refresh_token TEXT,
    token_expires_at TIMESTAMP
)

-- Market Data
daily_bars (
    ticker VARCHAR(10),
    date DATE,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    PRIMARY KEY (ticker, date)
)

ticker_overview (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    market_cap BIGINT,
    sector VARCHAR(100),
    industry VARCHAR(100),
    updated_at TIMESTAMP
)

-- Trading
trade_recommendations (
    id SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(client_id),
    ticker VARCHAR(10),
    action VARCHAR(10),  -- BUY/SELL
    quantity INT,
    recommended_price DECIMAL(12,4),
    strategy VARCHAR(50),
    ml_score DECIMAL(5,4),
    rl_weight DECIMAL(5,4),
    created_at TIMESTAMP
)

trade_executions (
    id SERIAL PRIMARY KEY,
    recommendation_id INT REFERENCES trade_recommendations(id),
    executed_at TIMESTAMP,
    executed_price DECIMAL(12,4),
    status VARCHAR(20),  -- FILLED/PARTIAL/FAILED
    schwab_order_id VARCHAR(100)
)

-- Paper Trading
paper_accounts (
    account_id SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(client_id),
    cash_balance DECIMAL(15,2),
    total_value DECIMAL(15,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)

paper_trades (
    trade_id SERIAL PRIMARY KEY,
    account_id INT REFERENCES paper_accounts(account_id),
    ticker VARCHAR(10),
    action VARCHAR(10),
    quantity INT,
    price DECIMAL(12,4),
    trade_date TIMESTAMP
)

-- Autonomous Fund
autonomous_client_settings (
    id SERIAL PRIMARY KEY,
    client_id INT REFERENCES clients(client_id),
    auto_trading_enabled BOOLEAN DEFAULT FALSE,
    preferred_strategy VARCHAR(50),
    drift_threshold DECIMAL(5,4) DEFAULT 0.05,
    min_cash_balance DECIMAL(15,2),
    max_position_size DECIMAL(5,4) DEFAULT 0.10,
    updated_at TIMESTAMP
)
```

### Materialized View for ML Features

```sql
CREATE MATERIALIZED VIEW ml_training_features AS
SELECT
    db.ticker,
    db.date,
    -- Price features
    db.close,
    db.volume,
    -- Technical indicators
    (db.close - LAG(db.close, 50) OVER w) / LAG(db.close, 50) OVER w AS momentum_50d,
    (db.close - LAG(db.close, 200) OVER w) / LAG(db.close, 200) OVER w AS momentum_200d,
    -- Fundamental features
    r.pe_ratio,
    r.pb_ratio,
    r.dividend_yield,
    r.debt_to_equity,
    r.roe,
    -- Target variable
    (LEAD(db.close, 30) OVER w - db.close) / db.close AS target_return
FROM daily_bars db
LEFT JOIN ratios r ON db.ticker = r.ticker AND db.date = r.date
WINDOW w AS (PARTITION BY db.ticker ORDER BY db.date)
WHERE db.date >= '2015-01-01';

-- Refresh daily
REFRESH MATERIALIZED VIEW ml_training_features;
```

### Indexes for Performance

```sql
-- Time-series queries
CREATE INDEX idx_daily_bars_ticker_date ON daily_bars(ticker, date DESC);
CREATE INDEX idx_daily_bars_date ON daily_bars(date DESC);

-- Client lookups
CREATE INDEX idx_clients_email ON clients(email);
CREATE INDEX idx_client_brokerage_accounts_client_id ON client_brokerage_accounts(client_id);

-- Trading queries
CREATE INDEX idx_trade_recommendations_client_date ON trade_recommendations(client_id, created_at DESC);
CREATE INDEX idx_trade_executions_recommendation ON trade_executions(recommendation_id);

-- Paper trading
CREATE INDEX idx_paper_trades_account_date ON paper_trades(account_id, trade_date DESC);
```

## ML/RL Architecture

### Four-Layer AI System

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Market Regime Detection                                │
│ ───────────────────────────────────────────────────────────────│
│ Input: VIX, Treasury yields, sector rotation, market breadth    │
│ Model: Classification (Random Forest or Rules-Based)            │
│ Output: Regime (Bull/Bear/High Vol/Low Vol/Sideways)           │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Meta-Model Strategy Selection                          │
│ ───────────────────────────────────────────────────────────────│
│ Input: Market regime + recent strategy performance             │
│ Logic: Rule-based or ML-based strategy selector                │
│ Output: Selected strategy (e.g., growth_largecap)              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: ML Stock Screening (XGBoost)                           │
│ ───────────────────────────────────────────────────────────────│
│ Input: ~2000 stocks with fundamentals + technicals             │
│ Model: XGBoost binary classifier (will outperform Y/N)         │
│ Features: 50+ engineered features per stock                    │
│ Output: Top 100 stocks ranked by ML score (0-1)                │
│ Training: 2015-2023 data, ~30 min per model                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: RL Portfolio Optimization (PPO)                        │
│ ───────────────────────────────────────────────────────────────│
│ Input: Top 50 stocks from ML layer + current portfolio         │
│ Agent: PPO (Proximal Policy Optimization) with JAX             │
│ State: Stock features, current positions, cash, market context │
│ Action: Portfolio weights (allocation percentages)              │
│ Reward: Risk-adjusted returns (Sharpe ratio)                   │
│ Output: Target portfolio (50 positions with weights)           │
│ Training: 2015-2023 data, ~3 hours per agent on GPU            │
└─────────────────────────────────────────────────────────────────┘
```

### XGBoost Model Architecture

```python
# ml_models/train_xgboost_optimized.py
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

# Model parameters
params = {
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'random_state': 42
}

# Training
model = XGBClassifier(**params)
model.fit(X_train, y_train,
          eval_set=[(X_test, y_test)],
          verbose=False)

# Inference
ml_scores = model.predict_proba(X_new)[:, 1]  # Probability of positive return
top_100 = X_new.nlargest(100, 'ml_score')
```

### PPO RL Agent Architecture

```python
# rl_trading/train_hybrid_ppo.py
import jax
from stable_baselines3 import PPO

# Environment: Portfolio management gym
env = HybridPortfolioEnv(
    ml_model=xgboost_model,
    tickers=sp500_tickers,
    start_date='2015-01-01',
    end_date='2023-12-31',
    initial_balance=100000
)

# PPO Agent
agent = PPO(
    'MlpPolicy',
    env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    device='cuda'  # GPU acceleration
)

# Train
agent.learn(total_timesteps=1_000_000)

# Inference
observation = env.reset()
action, _states = agent.predict(observation, deterministic=True)
# action = portfolio weights for top 50 stocks
```

## MLOps Architecture

### MLflow Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                         MLflow Server                            │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐  │
│  │  Tracking      │  │  Model         │  │  Artifact        │  │
│  │  Server        │  │  Registry      │  │  Store           │  │
│  │                │  │                │  │                  │  │
│  │  • Experiments │  │  • Versions    │  │  • Models (.pkl) │  │
│  │  • Runs        │  │  • Stages      │  │  • Plots (.png)  │  │
│  │  • Metrics     │  │  • Transitions │  │  • Data (.csv)   │  │
│  │  • Parameters  │  │                │  │                  │  │
│  └────────────────┘  └────────────────┘  └──────────────────┘  │
│                                                                  │
│  Backend Store: PostgreSQL (metadata)                           │
│  Artifact Store: S3 or local filesystem                         │
│  Port: 5000                                                     │
└─────────────────────────────────────────────────────────────────┘
                           ▲
                           │ mlflow.log_*
┌──────────────────────────┴──────────────────────────────────────┐
│                   Training Scripts                               │
│  • train_with_mlflow.py                                         │
│  • auto_retrain.py                                              │
│  • train_hybrid_ppo.py                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Data Drift Detection Pipeline

```python
# mlops/drift_detection/drift_detector.py
class DataDriftDetector:
    def detect_drift_ks(self, reference_data, current_data):
        """Kolmogorov-Smirnov test for each feature"""
        for feature in self.features:
            statistic, p_value = ks_2samp(
                reference_data[feature],
                current_data[feature]
            )
            if p_value < 0.05:  # Drift detected
                return True
        return False

    def detect_drift_psi(self, reference_data, current_data):
        """Population Stability Index"""
        psi = calculate_psi(reference_data, current_data)
        return psi >= 0.2  # Significant change
```

### Automated Retraining Pipeline

```python
# mlops/retraining/auto_retrain.py
class AutoRetrainingPipeline:
    def run_pipeline(self):
        for strategy in ['growth', 'value', 'dividend', 'momentum']:
            # 1. Check drift
            drift_detected = monitor_drift_and_alert(strategy)

            if drift_detected:
                # 2. Retrain model
                run_id, model_name = train_model_with_mlflow(strategy)

                # 3. Evaluate and promote if meets criteria
                if model_accuracy > 0.7:
                    promote_model_to_production(model_name)
```

## Data Flow

### Daily Data Pipeline

```
6:00 AM ET - Daily Data Pipeline
────────────────────────────────
┌─────────────────┐
│ Alpha Vantage   │
│ API             │
└────────┬────────┘
         │ Fetch EOD prices
         ▼
┌─────────────────┐
│ Database        │
│ • daily_bars    │
│ • ticker_events │
│ • ratios        │
└────────┬────────┘
         │ Refresh
         ▼
┌─────────────────────────────┐
│ Materialized Views          │
│ • ml_training_features      │
│ • portfolio_health_metrics  │
└─────────────────────────────┘
```

### Trading Pipeline

```
4:30 PM ET - Daily Rebalancing
───────────────────────────────
┌──────────────────┐
│ Market Regime    │
│ Detection        │
└────────┬─────────┘
         │ Regime classification
         ▼
┌──────────────────┐
│ Strategy         │
│ Selection        │
└────────┬─────────┘
         │ Selected strategy
         ▼
┌──────────────────┐
│ ML Screening     │
│ (XGBoost)        │
└────────┬─────────┘
         │ Top 100 stocks
         ▼
┌──────────────────┐
│ RL Optimization  │
│ (PPO Agent)      │
└────────┬─────────┘
         │ Target portfolio
         ▼
┌──────────────────┐
│ Trade Generation │
│ (Buy/Sell orders)│
└────────┬─────────┘
         │ Recommendations
         ▼
┌──────────────────┐
│ Risk Validation  │
│ • Position limits│
│ • Drift check    │
└────────┬─────────┘
         │ Approved trades
         ▼
┌──────────────────┐
│ Execution        │
│ • Schwab API     │
│ • Paper Trading  │
└──────────────────┘
```

## Security Architecture

### Authentication Flow

```
┌──────────────┐
│ User Browser │
└──────┬───────┘
       │ HTTP Basic Auth
       │ (username/password)
       ▼
┌──────────────────┐
│ FastAPI Backend  │
│ • Validates creds│
│ • Returns JWT    │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Database         │
│ • users table    │
│ • hashed passwords│
└──────────────────┘
```

### Schwab OAuth 2.0 Flow

```
┌───────────┐                 ┌──────────┐                ┌────────────┐
│  Browser  │                 │ Backend  │                │ Schwab API │
└─────┬─────┘                 └────┬─────┘                └─────┬──────┘
      │                            │                            │
      │ 1. Click "Link Schwab"     │                            │
      ├───────────────────────────>│                            │
      │                            │                            │
      │ 2. Redirect to Schwab      │                            │
      │<───────────────────────────┤                            │
      │                            │                            │
      │ 3. Login & Authorize       │                            │
      ├────────────────────────────┼───────────────────────────>│
      │                            │                            │
      │ 4. Callback with code      │                            │
      ├───────────────────────────>│                            │
      │                            │                            │
      │                            │ 5. Exchange code for token │
      │                            ├───────────────────────────>│
      │                            │                            │
      │                            │ 6. Access + Refresh tokens │
      │                            │<───────────────────────────┤
      │                            │                            │
      │                            │ 7. Store tokens (encrypted)│
      │                            ├─────────┐                  │
      │                            │         │                  │
      │                            │<────────┘                  │
      │ 8. Success message         │                            │
      │<───────────────────────────┤                            │
```

## Deployment Architecture

### Local/Development

```
┌─────────────────────────────────────────┐
│         Developer Workstation            │
│  ┌───────────┐  ┌──────────────────┐    │
│  │ Frontend  │  │ Backend          │    │
│  │ npm run   │  │ uvicorn --reload │    │
│  │ dev       │  │                  │    │
│  │ :3000     │  │ :8000            │    │
│  └───────────┘  └──────────────────┘    │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │ PostgreSQL (local)                │  │
│  │ :5432                             │  │
│  └───────────────────────────────────┘  │
│                                          │
│  ┌───────────────────────────────────┐  │
│  │ ngrok http 8000                   │  │
│  │ (for Schwab OAuth callbacks)     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Production (Kubernetes)

```
┌──────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Ingress Controller                     │  │
│  │  (NGINX) - SSL/TLS Termination                     │  │
│  └─────────┬──────────────────────────────────────────┘  │
│            │                                              │
│  ┌─────────▼──────────┐    ┌──────────────────────────┐ │
│  │ Frontend Deployment│    │ Backend Deployment       │ │
│  │ • Replicas: 2      │    │ • Replicas: 3            │ │
│  │ • Port: 3000       │    │ • Port: 8000             │ │
│  │ • Resources:       │    │ • Resources:             │ │
│  │   CPU: 500m        │    │   CPU: 1000m             │ │
│  │   Mem: 512Mi       │    │   Mem: 2Gi               │ │
│  └────────────────────┘    └──────────────────────────┘ │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ PostgreSQL StatefulSet                             │  │
│  │ • Replicas: 1 (primary) + 1 (replica)             │  │
│  │ • Persistent Volume: 100Gi SSD                     │  │
│  │ • Backup CronJob: Daily @ 2 AM                     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ MLflow Deployment                                  │  │
│  │ • Replicas: 1                                      │  │
│  │ • Persistent Volume: 50Gi (artifacts)             │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │ CronJobs                                           │  │
│  │ • daily-data-pipeline (6:00 AM)                   │  │
│  │ • daily-incremental-update (2:00 AM)              │  │
│  │ • daily-rebalance (4:30 PM)                       │  │
│  │ • weekly-ml-training (Sun 2:00 AM)                │  │
│  │ • monthly-rl-training (1st @ 3:00 AM)             │  │
│  │ • model-drift-check (Daily 3:00 AM)               │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Performance Considerations

### Database Optimization

- **Connection Pooling**: SQLAlchemy pool size = 20
- **Query Optimization**: Explain analyze on slow queries
- **Indexes**: All foreign keys and date columns indexed
- **Partitioning**: Large tables partitioned by month/year
- **Vacuum**: Auto-vacuum enabled, manual VACUUM ANALYZE weekly

### API Performance

- **Async Endpoints**: FastAPI with async/await for I/O-bound operations
- **Caching**: Redis cache for frequently accessed data (portfolio snapshots)
- **Rate Limiting**: 100 requests/minute per client
- **Pagination**: All list endpoints use skip/limit pagination

### ML/RL Inference Optimization

- **Model Caching**: Load models once into memory, reuse across requests
- **Batch Inference**: Process multiple stocks in single XGBoost call
- **GPU Utilization**: RL inference on GPU when available
- **Feature Precomputation**: Materialized views for ML features

## Disaster Recovery

### Backup Strategy

- **Database**: Daily pg_dump to S3, retain 30 days
- **Models**: All trained models versioned and backed up to S3
- **Code**: Git repository with main + develop branches
- **Logs**: 7-day retention in logs/, archived to S3 monthly

### Recovery Procedures

1. **Database Failure**: Restore from latest backup, replay WAL logs
2. **Model Corruption**: Roll back to previous model version from MLflow
3. **API Outage**: Kubernetes auto-restart, health check every 30s
4. **Data Pipeline Failure**: Manual trigger from System Admin page

---

**For more details, see:**
- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - Complete database documentation
- [API_REFERENCE.md](./API_REFERENCE.md) - API endpoint reference
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Deployment procedures
- [MLOPS_GUIDE.md](./MLOPS_GUIDE.md) - MLOps infrastructure details
