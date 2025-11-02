#!/bin/bash
# Simplified GPU Environment Setup for DGX Spark
# Uses system Python 3.12 and pip (no conda required)

set -e

echo "=========================================="
echo "ACIS AI Platform - GPU Environment Setup"
echo "=========================================="

# Check CUDA availability via nvidia-smi
echo ""
echo "Checking CUDA installation..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "ERROR: nvidia-smi not found. GPU not available."
    exit 1
fi

echo "GPU Information:"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

# Use system Python
PYTHON_CMD=python3

echo ""
echo "Python version:"
$PYTHON_CMD --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
$PYTHON_CMD -m venv ~/acis-gpu-env

# Activate virtual environment
source ~/acis-gpu-env/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.x support (matches CUDA 13.0 on DGX)
echo ""
echo "Installing PyTorch with CUDA 12.x support..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install XGBoost with GPU support
echo ""
echo "Installing GPU XGBoost..."
pip install xgboost

# Install Ray for distributed computing
echo ""
echo "Installing Ray..."
pip install "ray[default,tune]"

# Install MLflow for experiment tracking
echo ""
echo "Installing MLflow..."
pip install mlflow

# Install Optuna for hyperparameter optimization
echo ""
echo "Installing Optuna..."
pip install optuna optuna-integration[xgboost]

# Install ML libraries
echo ""
echo "Installing ML libraries..."
pip install scikit-learn pandas numpy scipy matplotlib seaborn

# Install database libraries
echo ""
echo "Installing database libraries..."
pip install psycopg2-binary sqlalchemy python-dotenv

# Verify GPU access
echo ""
echo "=========================================="
echo "Verifying GPU Setup"
echo "=========================================="

python -c "
import torch
import xgboost as xgb

print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA devices: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
    print(f'CUDA version (PyTorch): {torch.version.cuda}')
else:
    print('WARNING: CUDA not available in PyTorch')

print(f'\nXGBoost version: {xgb.__version__}')
print(f'XGBoost built with GPU support: {xgb.build_info()[\"USE_CUDA\"]}')
"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To activate the environment:"
echo "  source ~/acis-gpu-env/bin/activate"
echo ""
echo "To verify GPU access:"
echo "  python -c 'import torch; print(torch.cuda.device_count())'"
echo ""
echo "Add this to your ~/.bashrc for auto-activation:"
echo "  alias acis-gpu='source ~/acis-gpu-env/bin/activate'"
echo ""
