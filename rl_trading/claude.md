# RL Trading Directory - Reinforcement Learning Portfolio Optimization

## Purpose
This directory contains Proximal Policy Optimization (PPO) reinforcement learning agents for portfolio optimization. RL agents form the second stage of the two-stage ML+RL pipeline, taking the top 100 stocks from XGBoost and optimizing allocation to create the final 50-position portfolio.

## Key Files

### Training Scripts
- **`train_hybrid_ppo.py`** - Main PPO training script (Stable-Baselines3)
- **`train_jax_ppo.py`** - Experimental JAX-based PPO implementation
- **`train_ppo_agent.py`** - Alternative PPO training approach

### Environment & Agent
- **`portfolio_env.py`** - Gym environment for portfolio management
- **`rl_agent.py`** - RL agent wrapper for inference

### Evaluation
- **`evaluate_rl_agent.py`** - Evaluate trained RL models

## RL Framework

### Algorithm: Proximal Policy Optimization (PPO)
- **Type**: On-policy actor-critic method
- **Advantages**:
  - Stable training (clipped objective prevents large updates)
  - Sample efficient (reuses data within epoch)
  - Works well with continuous action spaces
- **Library**: Stable-Baselines3

### Why PPO for Portfolio Optimization?
1. **Continuous Action Space**: Portfolio weights (0-1 per position)
2. **Risk-Reward Tradeoff**: PPO learns to balance returns vs drawdowns
3. **Temporal Dependencies**: Handles market regime changes
4. **Constraint Handling**: Naturally learns position limits, diversification

## Environment Design

### State Space (Observation)
For each of the top 100 candidate stocks:
- **ML Prediction**: XGBoost predicted return (normalized)
- **Price Features**: Current price, returns (1d, 5d, 20d)
- **Volatility**: Historical volatility, beta
- **Fundamentals**: P/E, market cap, sector encoding
- **Technical**: RSI, MACD, moving average crossovers
- **Position Status**: Current weight in portfolio (if any)

**Total Dimensions**: ~600-800 (depends on feature set)

### Action Space
- **Type**: Continuous, Box[-1, 1]
- **Dimensions**: 50 (one per position in final portfolio)
- **Interpretation**:
  - Action value represents target weight for that position
  - Actions normalized to sum to 1.0 (weights)
  - Negative actions = reduce/close position
  - Positive actions = increase/open position

### Reward Function
```python
reward = sharpe_ratio_improvement
         - 0.1 * turnover_penalty
         - 0.2 * drawdown_penalty
         + 0.05 * diversification_bonus
```

**Components**:
- **Sharpe Ratio**: Risk-adjusted returns (target: > 1.5)
- **Turnover Penalty**: Discourage excessive trading
- **Drawdown Penalty**: Minimize peak-to-trough losses
- **Diversification Bonus**: Encourage spread across sectors/stocks

## Training Process

### Command Line Usage
```bash
# Train PPO agent for growth mid-cap strategy
python train_hybrid_ppo.py \
  --strategy growth \
  --market-cap mid \
  --timesteps 1000000 \
  --eval-freq 10000 \
  --save-freq 50000 \
  --device cuda

# CPU training
python train_hybrid_ppo.py --strategy growth --market-cap mid --device cpu --timesteps 500000
```

### Training Pipeline
1. **Load ML Predictions**: Get top 100 stocks from XGBoost model
2. **Initialize Environment**: Portfolio gym environment with historical data
3. **Train PPO Agent**:
   - Episode length: 60 trading days (3 months)
   - Batch size: 2048 steps
   - Learning rate: 3e-4 (annealed)
   - Entropy coefficient: 0.01 (exploration)
4. **Evaluation**: Test on held-out time periods
5. **Save Model**: `.zip` file with policy network weights

### Hyperparameters
```python
PPO_PARAMS = {
    'learning_rate': 3e-4,
    'n_steps': 2048,           # Steps per rollout
    'batch_size': 64,
    'n_epochs': 10,            # Gradient updates per rollout
    'gamma': 0.99,             # Discount factor
    'gae_lambda': 0.95,        # GAE parameter
    'clip_range': 0.2,         # PPO clip epsilon
    'ent_coef': 0.01,          # Entropy bonus (exploration)
    'vf_coef': 0.5,            # Value function loss coefficient
    'max_grad_norm': 0.5       # Gradient clipping
}
```

## Model Performance

### Target Metrics
- **Sharpe Ratio**: > 1.5 (vs benchmark ~1.0)
- **Max Drawdown**: < 25%
- **Annual Return**: > 15%
- **Win Rate**: > 55% of trades profitable
- **Portfolio Concentration**: Max 5% per position

### Expected Training Time
- **CPU**: 8-12 hours (1M timesteps)
- **GPU**: 2-4 hours (1M timesteps)

## Output Structure

### Trained Models Directory
```
rl_models/
├── ppo_growth_small/
│   └── best_model.zip          # Stable-Baselines3 model
├── ppo_growth_mid/
│   └── best_model.zip
├── ppo_growth_large/
│   └── best_model.zip
├── ppo_value_small/
├── ppo_value_mid/
├── ppo_value_large/
└── ppo_dividend/
```

## Usage in Portfolio Generation

### Two-Stage Pipeline
```python
# Stage 1: ML screening (2000+ → 100)
ml_manager = MLPortfolioManager(strategy='growth', market_cap_segment='mid')
top_100_predictions = ml_manager.generate_predictions(features_df)

# Stage 2: RL optimization (100 → 50)
rl_agent = RLTradingAgent(strategy='growth', market_cap='mid')
rl_agent.load_model('rl_models/ppo_growth_mid/best_model.zip')

# Get top 100 stock data
top_100_data = get_stock_data_for_tickers(top_100_predictions['ticker'].tolist())

# RL agent decides allocation
target_portfolio = rl_agent.predict_portfolio(top_100_data, top_100_predictions)
# Returns: 50 positions with optimized weights
```

### Real-Time Inference
```python
# During trading hours
observation = construct_observation(top_100_stocks, current_portfolio)
action = rl_agent.predict(observation)
target_weights = normalize_actions_to_weights(action)
```

## Strategy-Specific Tuning

### Growth Strategy
- Higher entropy coefficient (more exploration)
- Lower turnover penalty (growth stocks = more volatile)
- Sharpe ratio weight: 0.7

### Value Strategy
- Lower entropy coefficient (more conservative)
- Higher diversification bonus
- Drawdown penalty weight: 0.3

### Dividend Strategy
- Stability-focused reward
- Higher turnover penalty (buy and hold)
- Dividend yield bonus in reward

## Common Issues

### Training Instability
- **Symptom**: Reward oscillates wildly
- **Fix**: Reduce learning rate, increase clip_range, reduce batch size

### Overfitting
- **Symptom**: Train reward high, eval reward low
- **Fix**: Increase entropy coefficient, use train/val time split, reduce timesteps

### Poor Sharpe Ratio
- **Symptom**: Returns decent but volatility too high
- **Fix**: Increase drawdown penalty, add volatility term to reward, adjust position limits

### GPU Out of Memory
- **Fix**: Reduce n_steps, use CPU, reduce observation dimensions

## Hyperparameter Tuning

### Key Parameters to Tune
1. **Learning Rate** (3e-5 to 3e-3): Lower = stable but slow
2. **Clip Range** (0.1 to 0.3): Higher = more policy updates
3. **Entropy Coefficient** (0.0 to 0.1): Higher = more exploration
4. **N Steps** (1024 to 4096): Higher = more data per update
5. **Gamma** (0.95 to 0.999): Higher = more future-focused

### Tuning Strategy
```bash
# Use Optuna for hyperparameter optimization
python tune_ppo_hyperparams.py --strategy growth --market-cap mid --trials 50
```

## Backtesting

### Evaluate Trained Agent
```bash
# Backtest on historical data
python evaluate_rl_agent.py \
  --model rl_models/ppo_growth_mid/best_model.zip \
  --start-date 2023-01-01 \
  --end-date 2024-12-31
```

### Metrics Reported
- Cumulative returns
- Sharpe ratio
- Max drawdown
- Win rate
- Average turnover
- Sector diversification

## Model Versioning

### Database Tracking
All trained RL models logged to `model_versions` table:
- `model_name`: e.g., "ppo_growth_mid"
- `framework`: "rl_ppo"
- `training_timesteps`: e.g., 1000000
- `sharpe_ratio`: Model performance
- `trained_at`: Training timestamp
- `is_production`: Production status flag

## Advanced Features

### Multi-Strategy Ensemble
Train multiple RL agents and ensemble predictions:
```python
agents = [
    RLTradingAgent('growth', 'mid'),
    RLTradingAgent('value', 'mid'),
    RLTradingAgent('momentum', 'mid')
]
# Weighted average of portfolios
ensemble_portfolio = weighted_ensemble(agents, weights=[0.4, 0.4, 0.2])
```

### Online Learning
Continuously update RL agent with new market data:
```python
# Load existing model
agent.load('rl_models/ppo_growth_mid/best_model.zip')
# Continue training on recent data
agent.learn(total_timesteps=100000, reset_num_timesteps=False)
```

## Dependencies
- `stable-baselines3>=2.0.0` - RL framework
- `gymnasium>=0.28.0` - Environment interface
- `torch>=2.0.0` - Neural networks (policy/value functions)
- `numpy>=1.24.0` - Numerical operations
- `pandas>=2.0.0` - Data handling

## Related Files
- ML models: `../ml_models/`
- Portfolio manager: `../portfolio/rl_portfolio_manager.py`
- Database schema: `../database/create_tables.sql`
- API endpoints: `../backend/api/trading.py`
- Backtesting: `../backtesting/autonomous_backtest.py`

## Best Practices

1. **Train on diverse market conditions** (bull, bear, sideways markets)
2. **Use appropriate observation normalization** (z-score, min-max)
3. **Monitor training curves** (reward, policy loss, value loss)
4. **Validate on out-of-sample data** before production
5. **Start with conservative hyperparameters** (low learning rate, high clip range)
6. **Log all training runs** for reproducibility
7. **Test in paper trading** for 30+ days before live trading
