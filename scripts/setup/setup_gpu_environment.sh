#!/bin/bash
# GPU Environment Setup for NVIDIA DGX Spark
# Sets up all GPU-accelerated libraries for ACIS ML training

set -e

echo "=========================================="
echo "ACIS AI Platform - GPU Environment Setup"
echo "=========================================="

# Check CUDA availability
echo ""
echo "Checking CUDA installation..."
if ! command -v nvcc &> /dev/null; then
    echo "ERROR: CUDA not found. Please install CUDA Toolkit 11.8 or 12.x first."
    exit 1
fi

nvcc --version
nvidia-smi

# Create conda environment (if not exists)
echo ""
echo "Setting up conda environment..."
if ! conda env list | grep -q "acis-gpu"; then
    conda create -n acis-gpu python=3.10 -y
fi

# Activate environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate acis-gpu

# Install PyTorch with CUDA support
echo ""
echo "Installing PyTorch with CUDA 11.8..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install RAPIDS AI (cuDF, cuML for GPU-accelerated data processing)
echo ""
echo "Installing RAPIDS AI..."
conda install -c rapidsai -c conda-forge -c nvidia \
    cudf=23.10 cuml=23.10 cugraph=23.10 \
    cudatoolkit=11.8 -y

# Install XGBoost with GPU support
echo ""
echo "Installing GPU XGBoost..."
pip install xgboost[gpu]

# Install LightGBM with GPU support
echo ""
echo "Installing GPU LightGBM..."
pip install lightgbm --install-option=--gpu

# Install Ray for distributed computing
echo ""
echo "Installing Ray..."
pip install "ray[default,tune,rllib]"

# Install MLflow for experiment tracking
echo ""
echo "Installing MLflow..."
pip install mlflow

# Install Optuna for hyperparameter optimization
echo ""
echo "Installing Optuna..."
pip install optuna optuna-integration[pytorch,xgboost]

# Install additional ML libraries
echo ""
echo "Installing additional ML libraries..."
pip install scikit-learn pandas numpy scipy
pip install transformers datasets accelerate  # For FinBERT
pip install ta-lib  # Technical analysis library
pip install cvxpy  # Portfolio optimization

# Install existing project dependencies
echo ""
echo "Installing project dependencies..."
pip install -r ../requirements.txt 2>/dev/null || echo "requirements.txt not found, skipping"

# Verify GPU access
echo ""
echo "=========================================="
echo "Verifying GPU Setup"
echo "=========================================="

python -c "
import torch
import cudf
import cuml
import xgboost as xgb

print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA devices: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')

print(f'\ncuDF version: {cudf.__version__}')
print(f'cuML version: {cuml.__version__}')
print(f'XGBoost GPU support: {xgb.get_config()[\"use_gpu\"]}')
"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  conda activate acis-gpu"
echo ""
echo "To verify GPU access:"
echo "  python -c 'import torch; print(torch.cuda.device_count())'"
echo ""
