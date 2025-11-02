---
description: Quick model training with sensible defaults
---

Train a model with minimal input required.

Ask the user:
1. Model type: XGBoost or RL
2. Strategy: growth, value, dividend, momentum
3. Market cap: small, mid, large

Then use sensible defaults:
- Date range: 2015-01-01 to today
- GPU: Auto-detect (use if available)
- Standard hyperparameters

Execute training:

**For XGBoost:**
```bash
python ml_models/train_xgboost.py \
  --strategy {strategy} \
  --market-cap {marketcap} \
  --start-date 2015-01-01 \
  --end-date {today} \
  {--gpu 0 if available}
```

**For RL:**
```bash
python rl_trading/train_hybrid_ppo.py \
  --strategy {strategy} \
  --market-cap {marketcap} \
  --timesteps 100000
```

Monitor training and report results when complete.
