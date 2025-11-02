# Autonomous Trading System

Complete end-to-end autonomous fund management system powered by ML (XGBoost) and RL (PPO) models.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS TRADING SYSTEM                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│ Market Regime    │  Classifies market conditions
│ Detector         │  - Volatility: low/medium/high/extreme
└────────┬─────────┘  - Trend: bull/bear/sideways
         │            - Breadth: advance/decline ratio
         ▼
┌──────────────────┐
│ Meta-Strategy    │  Selects optimal strategy based on regime
│ Selector         │  - 7 strategies: growth/value × 3 market caps + dividend
└────────┬─────────┘  - Rule-based selection with confidence scores
         │
         ▼
┌──────────────────┐
│ Hybrid Portfolio │  Generates portfolio using ML+RL models
│ Generator        │  Step 1: XGBoost → select top N stocks (IC: 10.14%)
└────────┬─────────┘  Step 2: PPO → optimize portfolio weights
         │
         ▼
┌──────────────────┐
│ Risk Manager     │  Enforces constraints
│                  │  - Max position: 10%
└────────┬─────────┘  - Max concentration: 40% in top 3
         │            - Max turnover: 30% daily
         │            - Max drawdown: 15%
         ▼
┌──────────────────┐
│ Trade Executor   │  Executes via Schwab API
│ (Schwab API)     │  - Dry run: just logs
└──────────────────┘  - Paper trading: simulated in DB
                      - Live trading: REAL money 🚨
```

## Components

### 1. Market Regime Detection
**File**: `market_regime_detector.py`

Analyzes SPY and market breadth to classify current market conditions:
- **Volatility**: Realized vol vs historical percentiles
- **Trend**: Price vs SMA(50) vs SMA(200)
- **Breadth**: Advance/decline ratio, new highs/lows
- **Sectors**: Leading/lagging sector momentum

**Output**: Regime label like "bull_low_vol" with confidence score

### 2. Meta-Strategy Selector
**File**: `meta_strategy_selector.py`

Rule-based system to select optimal strategy for current regime:
- High vol → Value strategies (defensive)
- Low vol + Bull → Growth strategies (aggressive)
- Sideways → Dividend strategy (income)
- Bear → Small-cap value (contrarian)

**Output**: Strategy name + confidence score

### 3. Hybrid Portfolio Generator
**File**: `hybrid_portfolio_generator.py`

Two-stage ML+RL portfolio construction:

**Stage 1 - Stock Selection (XGBoost)**:
- Loads trained XGBoost model for strategy
- Generates return predictions for universe
- Selects top N stocks with positive predicted returns
- Information Coefficient: 10.14% on test set

**Stage 2 - Weight Optimization (PPO RL Agent)**:
- Loads trained PPO agent
- Takes ML predictions + market features as state
- Outputs optimal portfolio weights
- Falls back to equal weights if RL model unavailable

**Output**: `{ticker: weight}` dict summing to 1.0

### 4. Autonomous Rebalancer
**File**: `autonomous_rebalancer.py`

Main orchestration layer:

```python
def rebalance(force=False):
    # 1. Detect market regime
    regime = regime_detector.detect_current_regime()

    # 2. Select strategy
    strategy = meta_selector.select_strategy(regime)

    # 3. Get current positions
    current = get_current_positions()

    # 4. Generate target portfolio
    target = portfolio_generator.generate_portfolio(strategy, total_value)

    # 5. Calculate trades
    trades = calculate_trades(current, target)

    # 6. Risk checks
    if risk_manager.approve_rebalance(trades):
        # 7. Execute trades
        executed = execute_trades(trades)

        # 8. Log everything
        log_rebalance(...)
```

### 5. Schwab Connector
**File**: `../trading/schwab_connector.py`

Brokerage integration for trade execution:
- OAuth 2.0 authentication
- Account info queries
- Order placement (market/limit)
- Position tracking
- Paper trading simulation

**Modes**:
- **Paper Trading**: Simulated execution in PostgreSQL
- **Live Trading**: Real API calls to Schwab

### 6. Backtesting Framework
**File**: `../backtesting/autonomous_backtest.py`

Historical validation system:
- Simulates full autonomous system on past data
- Compares ML models vs mock portfolios
- Tracks performance metrics over time

**10-Year Results (2015-2025)**:
- ML Models: $1,980,543 (31.84% CAGR, 1.19 Sharpe)
- Mock: $1,816,310 (30.79% CAGR, 1.15 Sharpe)
- **Outperformance**: +9.0% ($164k)

## Usage

### Dry Run (No Trades)
```bash
# Just analyze, don't execute
python scripts/run_daily_rebalance.py --dry-run
```

### Paper Trading (Simulated)
```bash
# Execute simulated trades in database
python scripts/run_daily_rebalance.py --paper-trading
```

### Live Trading (REAL MONEY 🚨)
```bash
# Execute REAL trades - BE CAREFUL!
python scripts/run_daily_rebalance.py --live --account-id YOUR_ACCOUNT_ID
```

### Options
```bash
--account-id ID      # Account to rebalance (default: PAPER_AUTONOMOUS_FUND)
--use-mock           # Use mock portfolios instead of ML/RL models
--force              # Force rebalance even if drift is low
```

## Automated Scheduling

### Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add this line to run daily at 4:30 PM ET (after market close)
30 16 * * 1-5 /home/fkratzer/acis-ai-platform/scripts/run_daily_rebalance.sh
```

The shell script:
- Activates virtual environment
- Runs in paper trading mode by default
- Logs to `logs/rebalancing/rebalance_YYYYMMDD_HHMMSS.log`

### Manual Test
```bash
# Test the shell script
./scripts/run_daily_rebalance.sh
```

## Database Schema

### Key Tables

**`market_regime`**: Daily market regime classification
```sql
date, vix, realized_volatility_20d, volatility_regime,
spy_sma_50, spy_sma_200, trend_regime,
advance_decline_ratio, new_highs_lows_ratio,
sector_momentum, regime_label, regime_confidence
```

**`strategy_performance`**: Historical strategy returns by regime
```sql
strategy, regime, period_start, period_end,
total_return, sharpe_ratio, max_drawdown
```

**`rebalancing_log`**: Audit trail of all rebalances
```sql
rebalance_date, account_id, strategy_selected,
meta_model_confidence, market_regime,
pre_rebalance_value, post_rebalance_value,
num_buys, num_sells, total_turnover,
trades (JSONB), status
```

**`paper_accounts`**: Simulated trading accounts
```sql
account_id, cash_balance, buying_power, total_value
```

**`paper_positions`**: Simulated holdings
```sql
account_id, ticker, quantity, avg_price, market_value
```

**`trade_executions`**: Trade execution log
```sql
order_id, account_id, ticker, quantity, order_type,
side, price, status, created_at, filled_at
```

## Risk Management

### Position Limits
- **Max Position Size**: 10% per stock
- **Max Concentration**: 40% in top 3 positions
- **Min Cash Reserve**: 2%

### Trading Limits
- **Max Daily Turnover**: 30% of portfolio
- **Max Drawdown**: 15% from peak
- **Rebalance Threshold**: 5% drift from target

### Safety Features
- Risk checks before every rebalance
- Automatic rejection if limits breached
- Full audit trail in database
- Confirmation prompt for live trading

## Model Training

### XGBoost (Stock Selection)
```bash
# Train growth mid-cap model
python scripts/auto_train_models.py \
    --models growth_midcap \
    --start-date 2015-01-01 \
    --end-date 2025-10-30
```

### PPO (Weight Optimization)
```bash
# Train RL agent
python rl_trading/train_hybrid_ppo.py \
    --strategy growth \
    --market-cap mid \
    --timesteps 100000
```

## Monitoring

### Check Rebalancing Logs
```sql
SELECT
    rebalance_date,
    strategy_selected,
    market_regime,
    pre_rebalance_value,
    post_rebalance_value,
    num_buys,
    num_sells,
    status
FROM rebalancing_log
ORDER BY rebalance_date DESC
LIMIT 10;
```

### View Current Positions
```sql
SELECT ticker, quantity, avg_price, market_value
FROM paper_positions
WHERE account_id = 'PAPER_AUTONOMOUS_FUND'
ORDER BY market_value DESC;
```

### Check Recent Trades
```sql
SELECT
    created_at,
    ticker,
    side,
    quantity,
    price,
    status
FROM trade_executions
WHERE account_id = 'PAPER_AUTONOMOUS_FUND'
ORDER BY created_at DESC
LIMIT 20;
```

## Testing

### Run Backtest
```bash
# Test ML models on historical data
python backtesting/autonomous_backtest.py \
    --start-date 2015-01-01 \
    --end-date 2025-10-30 \
    --capital 100000
```

### Test Components Individually
```bash
# Test market regime detection
python autonomous/market_regime_detector.py

# Test portfolio generation
python autonomous/hybrid_portfolio_generator.py --strategy growth_largecap

# Test Schwab connector
python trading/schwab_connector.py --paper
```

## Transition to Live Trading

### Phase 1: Paper Trading (Current)
- ✅ All trades simulated in database
- ✅ Full functionality without risk
- ✅ Build confidence over weeks/months

### Phase 2: Small Live Deployment
1. Fund real Schwab account with small amount ($1,000)
2. Update account credentials in database
3. Run with `--live --account-id REAL_ACCOUNT`
4. Monitor closely for 2-4 weeks

### Phase 3: Full Production
1. Verify paper trading performance matches expectations
2. Fund production account
3. Update cron job to use `--live` flag
4. Set up monitoring alerts
5. Review performance weekly

## Architecture Decisions

### Why Two-Stage ML+RL?
- **XGBoost excels at stock selection**: Binary classification (will it outperform?)
- **RL excels at portfolio optimization**: Sequential decision making under constraints
- Combining both leverages strengths of each approach

### Why Rule-Based Meta-Strategy?
- Market regimes change slowly (weeks/months)
- Simple rules are interpretable and robust
- Can be upgraded to ML meta-model later

### Why Paper Trading by Default?
- Safety first: never risk real money accidentally
- Build confidence through extended testing
- Identical code path to live trading

## Next Steps

1. **Monitor Paper Trading**: Run daily for 30 days, verify performance
2. **RL Model Training**: Complete training of all 7 strategy RL agents
3. **Meta-Model Enhancement**: Consider ML-based strategy selection
4. **Risk Model Refinement**: Add sector exposure limits
5. **Live Deployment**: Transition to small live account

## Support

For issues or questions:
- Check logs in `logs/rebalancing/`
- Review database audit trail
- Examine backtest results
- Test components individually

## Safety Warnings

⚠️ **NEVER run with `--live` flag without thoroughly testing in paper trading first**

⚠️ **Always verify account_id before running live trades**

⚠️ **Keep API credentials secure and never commit to git**

⚠️ **Monitor positions daily when running live**

⚠️ **Have a manual override plan ready**
