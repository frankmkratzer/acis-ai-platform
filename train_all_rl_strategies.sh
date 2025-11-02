#!/bin/bash
set -e

echo "================================================================"
echo "Training ALL Hybrid ML+RL Portfolio Strategies"
echo "================================================================"
echo ""

# Set GPU if available
GPU_FLAG=""
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected - using CUDA"
    GPU_FLAG="--device cuda"
else
    echo "No GPU detected - using CPU"
    GPU_FLAG="--device cpu"
fi

# Training parameters
TIMESTEPS=1000000
EVAL_FREQ=10000
SAVE_FREQ=50000

echo ""
echo "================================================================"
echo "1. Dividend Strategy (Mid Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy dividend \
    --market-cap mid \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "2. Growth Strategy (Small Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy growth \
    --market-cap small \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "3. Growth Strategy (Mid Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy growth \
    --market-cap mid \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "4. Growth Strategy (Large Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy growth \
    --market-cap large \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "5. Value Strategy (Small Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy value \
    --market-cap small \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "6. Value Strategy (Mid Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy value \
    --market-cap mid \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "7. Value Strategy (Large Cap)"
echo "================================================================"
python rl_trading/train_hybrid_ppo.py \
    --strategy value \
    --market-cap large \
    --timesteps $TIMESTEPS \
    --eval-freq $EVAL_FREQ \
    --save-freq $SAVE_FREQ \
    $GPU_FLAG

echo ""
echo "================================================================"
echo "✅ ALL RL STRATEGIES TRAINED SUCCESSFULLY!"
echo "================================================================"
echo ""
echo "Models saved to:"
echo "  models/ppo_hybrid_dividend_midcap/"
echo "  models/ppo_hybrid_growth_smallcap/"
echo "  models/ppo_hybrid_growth_midcap/"
echo "  models/ppo_hybrid_growth_largecap/"
echo "  models/ppo_hybrid_value_smallcap/"
echo "  models/ppo_hybrid_value_midcap/"
echo "  models/ppo_hybrid_value_largecap/"
echo ""
echo "View training logs with:"
echo "  tensorboard --logdir models/"
echo "================================================================"
