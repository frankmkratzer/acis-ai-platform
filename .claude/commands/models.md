---
description: List all trained models with performance metrics and status
---

List all trained models in the ACIS AI Platform with detailed information:

1. **XGBoost Models**
   For each model in `models/` directory:
   - Model name (strategy_marketcap)
   - Training date
   - Spearman IC
   - Sharpe ratio
   - Production status (🏆 if production)
   - File size
   - Last modified

2. **RL Models**
   For each model in `rl_models/` directory:
   - Model name (ppo_strategy_marketcap)
   - Training date
   - Final Sharpe ratio
   - Episode count
   - Production status
   - File size

3. **Performance Comparison**
   - Best Spearman IC
   - Best Sharpe ratio
   - Which models are production-ready

Format as a table with clear indicators for production models and performance rankings.
