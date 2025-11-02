# ACIS AI Platform Skills

This directory contains reusable automation workflows (skills) for common platform tasks.

## Available Skills

### Model Training
- **`train-growth-model`** - Train growth strategy XGBoost model with GPU/CPU option
  ```
  Usage: "train a growth model for mid cap"
  ```

- **`train-rl-agent`** - Train PPO reinforcement learning agent for portfolio optimization
  ```
  Usage: "train a RL agent for growth mid cap strategy"
  ```

### Testing & Validation
- **`run-backtest`** - Execute strategy backtest on historical data
  ```
  Usage: "run a backtest from 2020 to 2024"
  ```

- **`compare-models`** - Side-by-side comparison of model performance metrics
  ```
  Usage: "compare growth_mid and value_mid models"
  ```

### Deployment
- **`deploy-model`** - Safely promote model to production with validation
  ```
  Usage: "deploy the growth_midcap model to production"
  ```

- **`rollback-model`** - Revert to previous model version safely
  ```
  Usage: "rollback the growth_mid model to previous version"
  ```

### Data Management
- **`refresh-ml-features`** - Refresh materialized view after data updates
  ```
  Usage: "refresh the ML features view"
  ```

- **`sync-market-data`** - Run end-of-day market data pipeline
  ```
  Usage: "sync market data for today"
  ```

### Client Operations
- **`generate-recommendations`** - Create personalized trade recommendations for client
  ```
  Usage: "generate recommendations for client 1"
  ```

### System Maintenance
- **`health-check`** - Comprehensive platform health check
  ```
  Usage: "run a health check"
  ```

- **`analyze-logs`** - Parse and summarize platform logs for errors and patterns
  ```
  Usage: "analyze logs for the past day"
  ```

## How to Use Skills

Skills can be invoked in two ways:

### 1. Direct Invocation (Recommended)
```
train a growth model for mid cap
```

### 2. Explicit Skill Command
```
/skill train-growth-model
```

## Creating New Skills

1. Create a new YAML file in `.claude/skills/`
2. Define name, description, and prompt
3. Test the skill

Example structure:
```yaml
name: my-skill
description: What this skill does
prompt: |
  Step-by-step instructions for Claude to follow...

  1. First step
  2. Second step
  3. Report results
```

## Skill Best Practices

- **Be Specific**: Include exact commands and paths
- **Add Safety Checks**: Validate inputs before executing
- **Provide Context**: Explain what each step does
- **Handle Errors**: Include troubleshooting steps
- **Ask for Confirmation**: For destructive operations

## Potential Future Skills

Consider adding additional skills for:
- `optimize-hyperparameters` - Automated hyperparameter tuning with Optuna
- `generate-client-report` - Monthly performance report for clients
- `rebalance-portfolio` - Execute portfolio rebalancing workflow
- `validate-data-quality` - Check for data gaps, outliers, and anomalies
- `train-ensemble` - Train ensemble of multiple strategies
- `stress-test-portfolio` - Simulate portfolio under market stress scenarios

## Documentation

For more information on skills, see:
- https://docs.claude.com/claude-code/skills
