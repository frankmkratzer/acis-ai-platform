# Backend Directory - FastAPI REST API

## Purpose
FastAPI-based REST API server that exposes all platform functionality: client management, trading operations, model training/management, and portfolio generation.

## Structure
```
backend/
├── api/                    # API endpoints
│   ├── main.py            # FastAPI app entry point
│   ├── clients.py         # Client CRUD, OAuth, autonomous settings
│   ├── trading.py         # Trade recommendations, execution
│   ├── ml_models.py       # Model training, versioning, deployment
│   ├── ml_portfolio.py    # Portfolio generation (ML-based)
│   ├── brokerages.py      # Schwab OAuth integration
│   └── data_management.py # Data ingestion triggers
└── run_server.sh          # Server startup script
