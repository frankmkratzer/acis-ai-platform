# Strategy Configuration Files

This directory contains configuration files for each investment strategy combining ML and RL.

## Available Strategies

### 1. Dividend Strategy
- **Config**: `dividend_strategy.json`
- **Market Cap**: Mid/Large cap only (>$2B)
- **Focus**: High dividend yield + sustainable fundamentals
- **Characteristics**:
  - Lower volatility, stable allocation
  - 40 max positions (concentrated)
  - Lower turnover (quarterly rebalancing)
  - 10 bps transaction costs
  - Min 1% dividend yield required

### 2. Growth Strategies
#### Small Cap (`growth_small_strategy.json`)
- **Market Cap**: $300M-$2B
- **Price Filter**: >$5 (higher quality)
- **Focus**: High momentum, aggressive appreciation
- **Characteristics**:
  - Higher volatility, 50 positions
  - Higher turnover, momentum-driven
  - 20 bps transaction costs (less liquid)
  - Aggressive exploration (ent_coef=0.02)

#### Mid Cap (`growth_mid_strategy.json`)
- **Market Cap**: $2B-$10B
- **Focus**: Balanced growth
- **Characteristics**:
  - Medium-high volatility, 50 positions
  - 15 bps transaction costs
  - Strong momentum focus

#### Large Cap (`growth_large_strategy.json`)
- **Market Cap**: >$10B
- **Focus**: Quality growth
- **Characteristics**:
  - Medium volatility, 40 positions
  - 10 bps transaction costs (most liquid)
  - Can hold larger positions (up to 12%)

### 3. Value Strategies
#### Small Cap (`value_small_strategy.json`)
- **Market Cap**: $300M-$2B
- **Price Filter**: >$5
- **Focus**: Undervalued + mean reversion
- **Characteristics**:
  - Medium volatility, 50 positions
  - Lower turnover (value reversion)
  - 20 bps transaction costs
  - PE < 20, PB < 3 filters

#### Mid Cap (`value_mid_strategy.json`)
- **Market Cap**: $2B-$10B
- **Focus**: Quality value stocks
- **Characteristics**:
  - Medium volatility, 50 positions
  - 15 bps transaction costs
  - Valuation filters applied

#### Large Cap (`value_large_strategy.json`)
- **Market Cap**: >$10B
- **Focus**: Blue-chip value
- **Characteristics**:
  - Low-medium volatility, 40 positions
  - Lowest turnover (buy and hold)
  - 10 bps transaction costs

## Configuration Structure

Each config contains:

```json
{
  "strategy": "growth|value|dividend",
  "market_cap_segment": "small|mid|large",
  "description": "...",

  "environment": {
    "ml_top_n": 100,           // ML selects top N candidates
    "rl_max_positions": 50,    // RL allocates to max N positions
    "rebalance_frequency": 20, // Days between rebalances
    "transaction_cost": 0.001, // Per-trade cost (10 bps = 0.001)
    "position_limits": [0.01, 0.10],  // Min/max position size
    "min_ml_score": 0.01,      // Min predicted return threshold
    "initial_capital": 100000
  },

  "ml_filters": {
    "min_market_cap": 2000000000,
    "max_market_cap": 10000000000,
    "min_price": 5.0,
    "max_pe_ratio": 20,        // Value strategies only
    "max_pb_ratio": 3.0        // Value strategies only
  },

  "ppo_hyperparams": {
    "learning_rate": 0.0003,
    "gamma": 0.99,             // Discount factor (higher = more long-term)
    "ent_coef": 0.01,          // Exploration (higher = more exploration)
    // ... other PPO params
  },

  "portfolio_characteristics": {
    "target_volatility": "low|medium|high",
    "expected_turnover": "low|medium|high",
    "focus": "income_generation|capital_appreciation|mean_reversion"
  }
}
```

## Key Parameter Differences

### Transaction Costs
- **Large Cap**: 10 bps (0.001) - most liquid
- **Mid Cap**: 15 bps (0.0015)
- **Small Cap**: 20 bps (0.002) - less liquid

### Position Limits
- **Conservative** (dividend, value large): [1.5%, 8-12%]
- **Balanced** (growth/value mid): [1%, 10%]
- **Aggressive** (growth/value small): [1%, 10%]

### Exploration (ent_coef)
- **Dividend/Value**: 0.005-0.01 (less exploration, stable)
- **Growth**: 0.015-0.02 (more exploration, momentum)

### Discount Factor (gamma)
- **Dividend**: 0.98 (more near-term focused on income)
- **Value**: 0.99 (standard)
- **Growth**: 0.995 (more long-term focused)

## Usage

Load a config in Python:
```python
import json

with open('rl_trading/configs/growth_mid_strategy.json') as f:
    config = json.load(f)

# Use in environment
env = HybridPortfolioEnv(
    strategy=config['strategy'],
    market_cap_segment=config['market_cap_segment'],
    **config['environment']
)
```

Or use in training:
```bash
python rl_trading/train_hybrid_ppo.py \
    --strategy growth \
    --market-cap mid
```

The training script will automatically load the appropriate config.
