# ACIS Trading Platform - Dagster Orchestration

Production-ready workflow orchestration for daily data pipelines and portfolio management.

## Overview

Dagster manages your entire data pipeline:
- **Daily Market Data**: Price bars, news, dividends, splits (6:00pm PT / 9:00pm ET)
- **Technical Indicators**: SMA, EMA, RSI, MACD (after daily data)
- **Weekly Fundamentals**: Quarterly/annual financials (Sundays 10am PT)
- **Quarterly Rebalancing**: Growth & Value portfolios (first Monday of quarter, 6pm PT)
- **Annual Rebalancing**: Dividend portfolios (first Monday of January, 6pm PT)

## Installation

### 1. Install Dagster (Windows-native)

```bash
cd C:\Users\frank\PycharmProjects\PythonProject\acis-ai-platform

# Install Dagster
pip install dagster dagster-webserver dagster-postgres

# Verify installation
dagster --version
```

### 2. Set Environment Variables

Ensure `.env` file has:
```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=acis
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$@nJose420
POLYGON_API_KEY=your_api_key_here
```

## Running Dagster

### Development Mode (Local UI)

```bash
# Start Dagster web UI
cd orchestration
dagster dev -f repository.py

# Open browser to: http://localhost:3000
```

This starts:
- **Dagster UI** at `http://localhost:3000`
- **Asset catalog** (view all assets and their dependencies)
- **Job scheduler** (manual or automatic runs)
- **Run history** (logs, metadata, errors)

### Production Mode (Daemon + Webserver)

For production, run Dagster as a service:

```bash
# 1. Start Dagster Daemon (runs schedules in background)
dagster-daemon run

# 2. Start Webserver (UI for monitoring)
dagster-webserver -f repository.py -h 0.0.0.0 -p 3000
```

## Asset Dependency Graph

```
Market Data (Parallel)
├── daily_bars
├── dividends
├── splits
├── news
├── short_interest
└── fundamentals

Technical Indicators (Sequential - depends on daily_bars)
├── sma (depends on: daily_bars)
├── ema (depends on: daily_bars)
├── rsi (depends on: daily_bars)
└── macd (depends on: ema)

Portfolios (depends on: fundamentals, sma, ema, rsi, macd)
└── portfolios_snapshot (8 portfolios)
    ├── Dividend - Large Cap
    ├── Dividend - Mid Cap
    ├── Growth - Large Cap
    ├── Growth - Mid Cap
    ├── Growth - Small Cap
    ├── Value - Large Cap
    ├── Value - Mid Cap
    └── Value - Small Cap
```

## Jobs & Schedules

### 1. Daily Market Data Job
**Schedule**: Mon-Fri at 6:00 PM PT (9:00 PM ET)
**Assets**: daily_bars, dividends, splits, news, short_interest, sma, ema, rsi, macd
**Purpose**: Update all market data after market close (5hr buffer for data availability)

```bash
# Manual run
dagster job execute -f repository.py -j daily_market_data
```

### 2. Weekly Fundamentals Job
**Schedule**: Sunday at 10:00 AM PT
**Assets**: fundamentals
**Purpose**: Check for new quarterly/annual reports

```bash
# Manual run
dagster job execute -f repository.py -j weekly_fundamentals
```

### 3. Quarterly Portfolio Rebalance
**Schedule**: First Monday of Jan/Apr/Jul/Oct at 6:00 PM PT
**Assets**: portfolios_snapshot
**Purpose**: Rebalance Growth & Value portfolios

```bash
# Manual run
dagster job execute -f repository.py -j quarterly_portfolio_rebalance
```

### 4. Annual Dividend Rebalance
**Schedule**: First Monday of January at 6:00 PM PT
**Assets**: portfolios_snapshot
**Purpose**: Rebalance Dividend portfolios

```bash
# Manual run
dagster job execute -f repository.py -j annual_dividend_rebalance
```

## Usage Examples

### View All Assets
```bash
cd orchestration
dagster asset list -f repository.py
```

### Materialize Single Asset
```bash
dagster asset materialize -f repository.py --select daily_bars
```

### Materialize Asset Group
```bash
dagster asset materialize -f repository.py --select market_data
```

### View Asset Lineage
```bash
# Open UI and navigate to: Assets > portfolios_snapshot
# See full dependency graph from source data to portfolios
```

### Check Schedule Status
```bash
# View in UI: Automation > Schedules
# Or via CLI:
dagster schedule list -f repository.py
```

## Monitoring & Alerts

### Dagster UI Features
- **Asset Catalog**: View all assets, descriptions, metadata
- **Runs**: See execution history, logs, timing
- **Schedules**: Manage automated runs
- **Asset Lineage**: Visualize data dependencies
- **Sensors**: Trigger jobs based on external events (future)

### Logging
All asset executions log to:
- Dagster UI (realtime)
- `logs/` directory (if configured)
- Database runs table (execution metadata)

## Production Deployment

### Option 1: Windows Service
Use NSSM (Non-Sucking Service Manager) to run Dagster as Windows Service:

```powershell
# Install NSSM
choco install nssm

# Create Dagster Daemon service
nssm install DagsterDaemon "C:\Path\To\Python\Scripts\dagster-daemon.exe" "run"

# Create Dagster Webserver service
nssm install DagsterWebserver "C:\Path\To\Python\Scripts\dagster-webserver.exe" "-f repository.py"

# Start services
nssm start DagsterDaemon
nssm start DagsterWebserver
```

### Option 2: Docker (Recommended for Cloud)
```yaml
# docker-compose.yml
version: "3.8"
services:
  dagster:
    image: dagster/dagster-docker:latest
    volumes:
      - ./orchestration:/opt/dagster/app
      - ..:/opt/dagster/acis-platform
    ports:
      - "3000:3000"
    environment:
      DAGSTER_POSTGRES_HOST: postgres
      DAGSTER_POSTGRES_DB: dagster
```

### Option 3: Dagster Cloud (Managed)
Deploy to Dagster Cloud for zero-ops:
- https://dagster.cloud
- Push-button deployment
- Built-in monitoring & alerts
- Free tier available

## Troubleshooting

### Asset Failed to Materialize
```bash
# Check logs in UI: Runs > [failed run] > View logs
# Or check specific asset:
dagster asset materialize -f repository.py --select failing_asset
```

### Schedule Not Running
```bash
# Ensure daemon is running
dagster-daemon run

# Check schedule status
dagster schedule list -f repository.py

# Turn on schedule if off
dagster schedule start -f repository.py daily_market_data_schedule
```

### Database Connection Issues
```bash
# Test connection
python -c "from utils import get_psycopg2_connection; get_psycopg2_connection()"

# Check .env file has correct credentials
```

## Next Steps

1. **Start Dagster UI**: `dagster dev -f repository.py`
2. **Explore Assets**: Navigate to Assets tab, click on assets to see code
3. **Test Manual Run**: Click "Materialize" on `daily_bars` asset
4. **Enable Schedules**: Turn on schedules in Automation tab
5. **Monitor**: Check Runs tab daily to ensure jobs succeed

## Support

- **Dagster Docs**: https://docs.dagster.io
- **Dagster Slack**: https://dagster.io/slack
- **GitHub Issues**: https://github.com/dagster-io/dagster/issues

## Architecture Benefits

**vs. Manual Scripts**:
- ✅ Automatic dependency resolution
- ✅ Built-in retry logic
- ✅ Web UI for monitoring
- ✅ Scheduling with cron
- ✅ Historical run tracking

**vs. Airflow**:
- ✅ Native Windows support
- ✅ Simpler setup (no Docker required)
- ✅ Asset-based (vs task-based)
- ✅ Better for ML/data pipelines
- ✅ Modern Python-first API

**vs. Custom Scheduler**:
- ✅ Production-tested framework
- ✅ Rich monitoring & alerting
- ✅ Asset versioning & lineage
- ✅ Easy cloud deployment
- ✅ Active community support
