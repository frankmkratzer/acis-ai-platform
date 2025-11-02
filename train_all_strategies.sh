#!/bin/bash
#
# Train all strategy models
# Usage: ./train_all_strategies.sh [--gpu GPU_ID]
#

set -e  # Exit on error

GPU_FLAG=""
if [ "$1" == "--gpu" ] && [ -n "$2" ]; then
    GPU_FLAG="--gpu $2"
    echo "Using GPU: $2"
fi

echo "========================================"
echo "Training All Strategy Models"
echo "========================================"
echo ""

# 1. Dividend Strategy (Mid/Large cap only)
echo "1/7: Training Dividend Strategy (Mid/Large cap)"
echo "----------------------------------------"
python ml_models/train_dividend_strategy.py $GPU_FLAG
echo ""

# 2. Growth Strategies (by market cap)
echo "2/7: Training Growth Strategy - Small Cap"
echo "----------------------------------------"
python ml_models/train_growth_strategy.py --market-cap small $GPU_FLAG
echo ""

echo "3/7: Training Growth Strategy - Mid Cap"
echo "----------------------------------------"
python ml_models/train_growth_strategy.py --market-cap mid $GPU_FLAG
echo ""

echo "4/7: Training Growth Strategy - Large Cap"
echo "----------------------------------------"
python ml_models/train_growth_strategy.py --market-cap large $GPU_FLAG
echo ""

# 3. Value Strategies (by market cap)
echo "5/7: Training Value Strategy - Small Cap"
echo "----------------------------------------"
python ml_models/train_value_strategy.py --market-cap small $GPU_FLAG
echo ""

echo "6/7: Training Value Strategy - Mid Cap"
echo "----------------------------------------"
python ml_models/train_value_strategy.py --market-cap mid $GPU_FLAG
echo ""

echo "7/7: Training Value Strategy - Large Cap"
echo "----------------------------------------"
python ml_models/train_value_strategy.py --market-cap large $GPU_FLAG
echo ""

echo "========================================"
echo "✅ ALL STRATEGY MODELS TRAINED!"
echo "========================================"
echo ""
echo "Models saved to:"
echo "  - models/dividend_strategy/"
echo "  - models/growth_smallcap/"
echo "  - models/growth_midcap/"
echo "  - models/growth_largecap/"
echo "  - models/value_smallcap/"
echo "  - models/value_midcap/"
echo "  - models/value_largecap/"
echo ""
echo "Use these models in the ML Portfolio Manager by specifying:"
echo "  strategy='dividend|growth|value'"
echo "  market_cap_segment='small|mid|large'"
echo "========================================"
