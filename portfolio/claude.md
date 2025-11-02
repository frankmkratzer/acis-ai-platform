# Portfolio Directory - Portfolio Construction & Management

## Purpose
Core portfolio management logic: constructing target portfolios, calculating drift, generating rebalance recommendations.

## Key Files
- **`ml_portfolio_manager.py`** - ML-based portfolio generation (XGBoost + optimization)
- **`rl_portfolio_manager.py`** - RL-based portfolio generation (PPO agent)
- **`portfolio_drift.py`** - Calculate portfolio drift from target
- **`rebalance_engine.py`** - Generate buy/sell orders to reach target

## Workflow
1. **ML Stage**: Screen 2000+ stocks → Top 100 by predicted return
2. **RL Stage**: Optimize Top 100 → Final 50 positions with weights
3. **Drift Check**: Compare current vs target portfolio
4. **Rebalance**: Generate orders if drift > threshold

## Usage
```python
from portfolio.ml_portfolio_manager import MLPortfolioManager

manager = MLPortfolioManager(strategy='growth', market_cap_segment='mid')
result = manager.execute_rebalance(
    tickers=None,  # None = use all tickers
    current_portfolio={},
    cash_available=100000,
    top_n=50
)
# Returns: target_portfolio DataFrame, predictions, stats
```
