"""
ACIS AI Platform - FastAPI Backend

Main application entry point for the web platform API.
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api import backtest, ml_models, ml_portfolio
from backend.api.routers import (
    auth,
    autonomous,
    brokerages,
    clients,
    portfolio_health,
    rl_monitoring,
    rl_trading,
    schwab,
    system_admin,
    trading,
)

# Create FastAPI app
app = FastAPI(
    title="ACIS AI Platform API",
    description="AI-powered wealth management platform with RL portfolio optimization and natural language querying",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://192.168.50.234:3000",
        "http://192.168.50.94:3000",  # User's machine
        "http://localhost:8000",
        "http://192.168.50.234:8000",
        "http://192.168.50.94:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(brokerages.router)
app.include_router(schwab.router)
app.include_router(trading.router)
app.include_router(rl_monitoring.router)
app.include_router(rl_trading.router)
app.include_router(ml_portfolio.router)
app.include_router(ml_models.router)
app.include_router(backtest.router)
app.include_router(autonomous.router)  # Autonomous trading system
app.include_router(portfolio_health.router)  # Portfolio health & rebalancing
app.include_router(system_admin.router)  # System administration & pipelines


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "ACIS AI Platform API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "endpoints": {
            "auth": "/api/auth",
            "clients": "/api/clients",
            "brokerages": "/api/brokerages",
            "schwab": "/api/schwab",
            "trading": "/api/trading",
            "rl": "/api/rl",
            "admin": "/api/admin",
        },
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "acis-ai-platform", "database": "connected"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # Auto-reload on code changes
