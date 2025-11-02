"""
System Administration Router

Endpoints for system administration tasks including:
- Pipeline execution (daily data, weekly ML, monthly RL)
- Pipeline status monitoring
- System health checks
- Log file access
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional

import psutil
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["System Administration"])

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Pipeline status storage (in-memory, would be better in database for production)
pipeline_jobs: Dict[str, dict] = {}


class PipelineJob(BaseModel):
    """Pipeline job status"""

    job_id: str
    pipeline_type: Literal["daily", "weekly_ml", "monthly_rl"]
    status: Literal["pending", "running", "completed", "failed"]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    log_file: Optional[str] = None
    error_message: Optional[str] = None


class PipelineResponse(BaseModel):
    """Response for pipeline execution"""

    success: bool
    message: str
    job_id: Optional[str] = None
    job: Optional[PipelineJob] = None


class SystemStatus(BaseModel):
    """System health and status"""

    status: str
    database_connected: bool
    disk_usage_percent: float
    memory_usage_percent: float
    cpu_usage_percent: float
    active_pipelines: int
    recent_logs: List[str]


def run_pipeline_script(pipeline_type: str, script_path: str) -> dict:
    """
    Execute a pipeline script in the background

    Args:
        pipeline_type: Type of pipeline (daily, weekly_ml, monthly_rl)
        script_path: Path to the shell script

    Returns:
        dict with job information
    """
    job_id = f"{pipeline_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Create job entry
    job = {
        "job_id": job_id,
        "pipeline_type": pipeline_type,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "log_file": None,
        "error_message": None,
        "process": None,
    }

    try:
        # Execute script in background
        process = subprocess.Popen(
            [script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            shell=True,
        )

        job["process"] = process
        pipeline_jobs[job_id] = job

        return job

    except Exception as e:
        job["status"] = "failed"
        job["error_message"] = str(e)
        job["completed_at"] = datetime.now().isoformat()
        pipeline_jobs[job_id] = job
        raise


@router.post("/pipelines/daily", response_model=PipelineResponse)
async def run_daily_pipeline(background_tasks: BackgroundTasks):
    """
    Execute the daily data pipeline

    This pipeline:
    - Validates database connectivity
    - Refreshes materialized views
    - Performs database maintenance
    - Generates summary report

    Duration: ~5 minutes
    """
    script_path = PROJECT_ROOT / "scripts" / "run_daily_data_pipeline.sh"

    if not script_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Daily pipeline script not found at {script_path}"
        )

    try:
        job = run_pipeline_script("daily", str(script_path))

        return PipelineResponse(
            success=True,
            message="Daily data pipeline started",
            job_id=job["job_id"],
            job=PipelineJob(**{k: v for k, v in job.items() if k != "process"}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/weekly-ml", response_model=PipelineResponse)
async def run_weekly_ml_pipeline(background_tasks: BackgroundTasks):
    """
    Execute the weekly ML training pipeline

    This pipeline:
    - Validates ml_training_features view
    - Trains all XGBoost models (12 total)
    - Saves models to models/ml directory

    Duration: ~30-60 minutes
    """
    script_path = PROJECT_ROOT / "scripts" / "run_weekly_ml_training.sh"

    if not script_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Weekly ML pipeline script not found at {script_path}"
        )

    try:
        job = run_pipeline_script("weekly_ml", str(script_path))

        return PipelineResponse(
            success=True,
            message="Weekly ML training pipeline started",
            job_id=job["job_id"],
            job=PipelineJob(**{k: v for k, v in job.items() if k != "process"}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipelines/monthly-rl", response_model=PipelineResponse)
async def run_monthly_rl_pipeline(background_tasks: BackgroundTasks):
    """
    Execute the monthly RL training pipeline

    This pipeline:
    - Validates ML models exist
    - Checks GPU availability
    - Trains all PPO agents (12 total)
    - Saves agents to models/rl directory

    Duration: ~2-4 hours
    """
    script_path = PROJECT_ROOT / "scripts" / "run_monthly_rl_training.sh"

    if not script_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Monthly RL pipeline script not found at {script_path}"
        )

    try:
        job = run_pipeline_script("monthly_rl", str(script_path))

        return PipelineResponse(
            success=True,
            message="Monthly RL training pipeline started",
            job_id=job["job_id"],
            job=PipelineJob(**{k: v for k, v in job.items() if k != "process"}),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/status/{job_id}", response_model=PipelineJob)
async def get_pipeline_status(job_id: str):
    """
    Get the status of a pipeline job
    """
    if job_id not in pipeline_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = pipeline_jobs[job_id]

    # Check if process is still running
    if job["process"] is not None:
        poll = job["process"].poll()
        if poll is not None:
            # Process finished
            if poll == 0:
                job["status"] = "completed"
            else:
                job["status"] = "failed"
                stderr = job["process"].stderr.read().decode() if job["process"].stderr else ""
                job["error_message"] = stderr[:500]  # First 500 chars

            job["completed_at"] = datetime.now().isoformat()
            job["process"] = None  # Clear process reference

    # Return job without process object (not serializable)
    return PipelineJob(**{k: v for k, v in job.items() if k != "process"})


@router.get("/pipelines/list", response_model=List[PipelineJob])
async def list_pipeline_jobs(limit: int = 50):
    """
    List recent pipeline jobs
    """
    jobs = []
    for job_id, job in sorted(
        pipeline_jobs.items(), key=lambda x: x[1]["started_at"], reverse=True
    )[:limit]:
        # Update status if process is still running
        if job["process"] is not None:
            poll = job["process"].poll()
            if poll is not None:
                if poll == 0:
                    job["status"] = "completed"
                else:
                    job["status"] = "failed"
                job["completed_at"] = datetime.now().isoformat()
                job["process"] = None

        jobs.append(PipelineJob(**{k: v for k, v in job.items() if k != "process"}))

    return jobs


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get overall system health and status
    """
    # Check database connection
    db_connected = True
    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = "$@nJose420"
        result = subprocess.run(
            ["psql", "-U", "postgres", "-d", "acis-ai", "-h", "localhost", "-c", "SELECT 1"],
            capture_output=True,
            timeout=5,
            env=env,
        )
        db_connected = result.returncode == 0
    except:
        db_connected = False

    # Get system metrics
    disk = psutil.disk_usage("/")
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)

    # Count active pipelines
    active = sum(1 for job in pipeline_jobs.values() if job["status"] == "running")

    # Get recent log files
    log_dir = PROJECT_ROOT / "logs" / "pipeline"
    recent_logs = []
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.log"), key=os.path.getmtime, reverse=True)[:10]
        recent_logs = [str(f.relative_to(PROJECT_ROOT)) for f in log_files]

    return SystemStatus(
        status="healthy" if db_connected else "degraded",
        database_connected=db_connected,
        disk_usage_percent=disk.percent,
        memory_usage_percent=memory.percent,
        cpu_usage_percent=cpu,
        active_pipelines=active,
        recent_logs=recent_logs,
    )


@router.get("/logs/{log_type}/{filename}")
async def get_log_file(log_type: str, filename: str):
    """
    Retrieve contents of a log file

    Args:
        log_type: Type of log (pipeline, training, etc.)
        filename: Name of the log file
    """
    log_path = PROJECT_ROOT / "logs" / log_type / filename

    # Security: ensure path is within logs directory
    try:
        log_path = log_path.resolve()
        if not str(log_path).startswith(str(PROJECT_ROOT / "logs")):
            raise HTTPException(status_code=403, detail="Access denied")
    except:
        raise HTTPException(status_code=400, detail="Invalid log path")

    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    try:
        with open(log_path, "r") as f:
            content = f.read()

        return {
            "filename": filename,
            "content": content,
            "size": len(content),
            "modified": datetime.fromtimestamp(os.path.getmtime(log_path)).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
