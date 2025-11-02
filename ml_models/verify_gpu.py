#!/usr/bin/env python3
"""Verify GPU access on DGX Spark"""

import torch
import xgboost as xgb

print("=" * 60)
print("DGX Spark - GPU Verification")
print("=" * 60)

# PyTorch GPU check
print(f"\nPyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")

if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\nGPU {i}:")
        print(f"  Name: {torch.cuda.get_device_name(i)}")
        print(f"  Memory: {props.total_memory / 1024**3:.2f} GB")
        print(f"  Compute Capability: {props.major}.{props.minor}")
else:
    print("\nWARNING: CUDA not available in PyTorch!")
    print("This may be normal for ARM-based systems.")

# XGBoost GPU check
print(f"\n{'=' * 60}")
print(f"XGBoost version: {xgb.__version__}")
build_info = xgb.build_info()
print(f"XGBoost GPU support: {build_info.get('USE_CUDA', 'Unknown')}")

# Test GPU computation
if torch.cuda.is_available():
    print(f"\n{'=' * 60}")
    print("Testing GPU computation...")
    try:
        x = torch.randn(1000, 1000).cuda()
        y = torch.matmul(x, x.T)
        print("✓ GPU computation successful!")
    except Exception as e:
        print(f"✗ GPU computation failed: {e}")
else:
    print("\nSkipping GPU computation test (CUDA not available)")

print(f"\n{'=' * 60}")
print("Verification complete!")
print("=" * 60)
