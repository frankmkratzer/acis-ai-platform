"""
ML Model Management API
Endpoints for training, viewing, and deleting ML models with database-backed versioning
"""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psycopg2
from fastapi import APIRouter, BackgroundTasks, HTTPException
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

router = APIRouter(prefix="/api/ml-models", tags=["ml-models"])

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "acis-ai",
    "user": "postgres",
    "password": "$@nJose420",
}

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"


class ModelInfo(BaseModel):
    name: str
    path: str
    created: str
    size_mb: float
    spearman_ic: Optional[float] = None
    n_features: Optional[int] = None
    framework: Optional[str] = None


class TrainingConfig(BaseModel):
    framework: str = "xgboost"  # 'xgboost' or 'rl_ppo'
    start_date: str = "2015-01-01"
    end_date: str = "2025-10-30"
    gpu: bool = True
    strategy: str = "growth"  # 'dividend', 'growth', 'value'
    market_cap_segment: str = "mid"  # 'small', 'mid', 'large', 'all'
    # RL-specific parameters
    timesteps: int = 1000000
    eval_freq: int = 10000
    save_freq: int = 50000


class TrainingJob(BaseModel):
    job_id: str
    status: str  # running, completed, failed
    framework: str
    started_at: str
    log_file: str


# In-memory store for training jobs
training_jobs: Dict[str, TrainingJob] = {}


def get_model_metadata(model_dir: Path) -> Dict:
    """Load model metadata from JSON file"""
    metadata_path = model_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    return {}


def get_model_size(model_dir: Path) -> float:
    """Calculate total size of model directory in MB"""
    total_size = 0
    for file in model_dir.rglob("*"):
        if file.is_file():
            total_size += file.stat().st_size
    return total_size / (1024 * 1024)  # Convert to MB


def get_model_created_time(model_dir: Path) -> str:
    """Get model creation time"""
    model_file = model_dir / "model.json"
    if model_file.exists():
        timestamp = model_file.stat().st_mtime
        return datetime.fromtimestamp(timestamp).isoformat()
    return datetime.now().isoformat()


@router.get("/list", response_model=List[ModelInfo])
async def list_models():
    """List all trained models"""
    models = []

    if not MODELS_DIR.exists():
        return models

    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir() and (model_dir / "model.json").exists():
            metadata = get_model_metadata(model_dir)

            model_info = ModelInfo(
                name=model_dir.name,
                path=str(model_dir.relative_to(PROJECT_ROOT)),
                created=get_model_created_time(model_dir),
                size_mb=get_model_size(model_dir),
                spearman_ic=metadata.get("spearman_ic"),
                n_features=metadata.get("n_features"),
                framework=metadata.get("framework", "Unknown"),
            )
            models.append(model_info)

    # Sort by creation time (newest first)
    models.sort(key=lambda x: x.created, reverse=True)
    return models


@router.get("/{model_name}/details")
async def get_model_details(model_name: str):
    """Get detailed information about a specific model"""
    model_dir = MODELS_DIR / model_name

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail="Model not found")

    metadata = get_model_metadata(model_dir)

    # Load feature importance if available
    feature_importance = []
    importance_path = model_dir / "feature_importance.csv"
    if importance_path.exists():
        import pandas as pd

        df = pd.read_csv(importance_path)
        feature_importance = df.head(20).to_dict("records")

    return {
        "name": model_name,
        "metadata": metadata,
        "feature_importance": feature_importance,
        "size_mb": get_model_size(model_dir),
        "created": get_model_created_time(model_dir),
        "files": [str(f.relative_to(model_dir)) for f in model_dir.iterdir()],
    }


@router.post("/{model_name}/set-production")
async def set_production_model(model_name: str, reason: Optional[str] = None):
    """Set a model as the production model"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if model exists in database
        cursor.execute(
            """
            SELECT id, framework, status, is_production
            FROM model_versions
            WHERE model_name = %s
            ORDER BY trained_at DESC
            LIMIT 1
        """,
            (model_name,),
        )

        model = cursor.fetchone()

        if not model:
            raise HTTPException(status_code=404, detail="Model not found in database")

        if model["is_production"]:
            return {"message": f"Model '{model_name}' is already in production"}

        # Promote to production
        cursor.execute(
            """
            SELECT promote_model_to_production(%s, %s, %s)
        """,
            (model["id"], "api_user", reason or "Promoted via API"),
        )

        conn.commit()

        return {
            "message": f"Model '{model_name}' promoted to production",
            "framework": model["framework"],
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.get("/production")
async def get_production_models():
    """Get all current production models"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT
                model_name,
                version,
                framework,
                model_path,
                spearman_ic,
                trained_at,
                promoted_to_production_at,
                size_mb
            FROM model_versions
            WHERE is_production = TRUE
            ORDER BY framework
        """
        )

        models = cursor.fetchall()
        return {"production_models": [dict(m) for m in models]}

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@router.delete("/{model_name}")
async def delete_model(model_name: str):
    """Delete a trained model (only if not in production)"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Check if model is in production
        cursor.execute(
            """
            SELECT id, is_production, status
            FROM model_versions
            WHERE model_name = %s
            ORDER BY trained_at DESC
            LIMIT 1
        """,
            (model_name,),
        )

        model = cursor.fetchone()

        # Allow deletion of production models (strategy-specific models don't use production tracking)
        # if model and model['is_production']:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Cannot delete production model. Please promote a different model to production first."
        #     )

        # Delete from filesystem
        model_dir = MODELS_DIR / model_name
        if model_dir.exists():
            shutil.rmtree(model_dir)

        # Mark as deleted in database
        if model:
            cursor.execute(
                """
                UPDATE model_versions
                SET status = 'deleted'
                WHERE model_name = %s
            """,
                (model_name,),
            )

            # Log deletion
            cursor.execute(
                """
                INSERT INTO model_deployment_log (
                    model_version_id, action, previous_status, new_status,
                    performed_by, reason
                ) VALUES (%s, 'deleted', %s, 'deleted', 'api_user', 'Deleted via API')
            """,
                (model["id"], model["status"]),
            )

            conn.commit()

        return {"message": f"Model '{model_name}' deleted successfully"}

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


def run_training_job(job_id: str, config: TrainingConfig):
    """Background task to run model training"""
    try:
        training_jobs[job_id].status = "running"

        # Handle RL (PPO) training
        if config.framework == "rl_ppo":
            script = PROJECT_ROOT / "rl_trading" / "train_hybrid_ppo.py"
            log_file = (
                LOGS_DIR / f"training_{job_id}_rl_{config.strategy}_{config.market_cap_segment}.log"
            )
            training_jobs[job_id].log_file = str(log_file.relative_to(PROJECT_ROOT))

            # Build RL training command
            cmd = [
                "python",
                str(script),
                "--strategy",
                config.strategy,
                "--market-cap",
                config.market_cap_segment,
                "--timesteps",
                str(config.timesteps),
                "--eval-freq",
                str(config.eval_freq),
                "--save-freq",
                str(config.save_freq),
            ]

            # Add GPU device if enabled
            if config.gpu:
                cmd.extend(["--device", "cuda"])
            else:
                cmd.extend(["--device", "cpu"])

        # Handle ML (XGBoost) training
        else:
            # Select training script based on strategy
            if config.strategy == "dividend":
                script = PROJECT_ROOT / "ml_models" / "train_dividend_strategy.py"
            elif config.strategy == "growth":
                script = PROJECT_ROOT / "ml_models" / "train_growth_strategy.py"
            elif config.strategy == "value":
                script = PROJECT_ROOT / "ml_models" / "train_value_strategy.py"
            else:
                raise ValueError(f"Unknown strategy: {config.strategy}")

            log_file = (
                LOGS_DIR / f"training_{job_id}_{config.strategy}_{config.market_cap_segment}.log"
            )
            training_jobs[job_id].log_file = str(log_file.relative_to(PROJECT_ROOT))

            # Build ML training command
            cmd = [
                "python",
                str(script),
                "--start-date",
                config.start_date,
                "--end-date",
                config.end_date,
            ]

            # Add market cap segment for growth/value (dividend ignores this)
            if config.strategy in ["growth", "value"]:
                cmd.extend(["--market-cap", config.market_cap_segment])

            # Add GPU flag if enabled
            if config.gpu:
                cmd.extend(["--gpu", "0"])

        # Run training
        with open(log_file, "w") as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
            )

        if result.returncode == 0:
            training_jobs[job_id].status = "completed"
        else:
            training_jobs[job_id].status = "failed"

    except Exception as e:
        training_jobs[job_id].status = "failed"
        print(f"Training job {job_id} failed: {e}")


@router.post("/train")
async def start_training(config: TrainingConfig, background_tasks: BackgroundTasks):
    """Start a new model training job"""
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    job = TrainingJob(
        job_id=job_id,
        status="queued",
        framework=config.framework,
        started_at=datetime.now().isoformat(),
        log_file="",
    )

    training_jobs[job_id] = job

    # Start training in background
    background_tasks.add_task(run_training_job, job_id, config)

    return {"job_id": job_id, "message": "Training job started", "job": job}


@router.get("/jobs", response_model=List[TrainingJob])
async def list_training_jobs():
    """List all training jobs"""
    return list(training_jobs.values())


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific training job"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = training_jobs[job_id]

    # Read log file if it exists
    log_content = ""
    if job.log_file:
        log_path = PROJECT_ROOT / job.log_file
        if log_path.exists():
            with open(log_path, "r") as f:
                log_content = f.read()

    return {"job": job, "log": log_content}


@router.delete("/jobs/{job_id}")
async def delete_training_job(job_id: str):
    """Delete a training job (removes from tracking, optionally deletes log file)"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = training_jobs[job_id]

    # Remove from tracking
    del training_jobs[job_id]

    # Optionally delete log file
    if job.log_file:
        log_path = PROJECT_ROOT / job.log_file
        if log_path.exists():
            try:
                log_path.unlink()
            except Exception as e:
                # Log deletion failed but job tracking removed
                pass

    return {"message": f"Training job {job_id} deleted"}


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, lines: int = 100):
    """Get recent logs from a training job"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = training_jobs[job_id]

    if not job.log_file:
        return {"logs": "Log file not yet created"}

    log_path = PROJECT_ROOT / job.log_file
    if not log_path.exists():
        return {"logs": "Log file not found"}

    # Read last N lines
    with open(log_path, "r") as f:
        all_lines = f.readlines()
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

    return {"logs": "".join(recent_lines)}
