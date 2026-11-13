"""Benchmarks API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import asyncio
import time
import random

from app.core.database import get_db
from app.api.deps import require_operator, require_admin, require_viewer, get_client_ip, get_user_agent
from app.models import Benchmark, Model, AuditLog, log_audit
from app.core.auth import SessionData

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


class BenchmarkCreate(BaseModel):
    model_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=255)
    workload_type: str = Field(..., pattern="^(synthetic|custom)$")
    config_json: str = Field(..., min_length=2)  # JSON string

    model_config = {'protected_namespaces': ()}


class BenchmarkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, pattern="^(pending|running|completed|failed)$")
    results_json: Optional[str] = None
    error_message: Optional[str] = None


class BenchmarkResponse(BaseModel):
    id: int
    model_id: int
    name: str
    status: str
    workload_type: str
    config_json: str
    results_json: Optional[str]
    error_message: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str

    model_config = {'protected_namespaces': (), 'from_attributes': True}
class BenchmarkListResponse(BaseModel):
    items: List[BenchmarkResponse]
    total: int
    page: int
    limit: int


# In-memory benchmark runner (for demo; production would use job queue)
_benchmark_tasks: dict = {}


async def run_synthetic_benchmark(benchmark_id: int, config: dict) -> dict:
    """Run a deterministic synthetic benchmark."""
    # Simulate benchmark execution with deterministic results
    batch_size = config.get("batch_size", 8)
    seq_len = config.get("seq_len", 2048)
    num_steps = config.get("num_steps", 100)

    # Deterministic "measurements" based on config
    # In reality, this would run actual inference kernels
    base_throughput = 1000 * batch_size / (seq_len / 1024)  # tokens/sec estimate
    tokens_per_step = batch_size * seq_len
    total_tokens = tokens_per_step * num_steps

    # Simulate some variance
    random.seed(benchmark_id)
    throughput = base_throughput * random.uniform(0.9, 1.1)
    ttft = random.uniform(10, 50)  # ms
    tpot = random.uniform(5, 20)   # ms
    peak_memory = random.uniform(2, 8) * batch_size  # GB

    # Simulate execution time
    await asyncio.sleep(0.1)  # Brief delay

    return {
        "throughput_tokens_per_sec": round(throughput, 2),
        "ttft_ms": round(ttft, 2),
        "tpot_ms": round(tpot, 2),
        "peak_memory_gb": round(peak_memory, 2),
        "total_tokens": total_tokens,
        "num_steps": num_steps,
        "batch_size": batch_size,
        "seq_len": seq_len,
    }


async def run_benchmark_task(benchmark_id: int):
    """Background task to run benchmark."""
    from app.core.database import get_db_context
    from datetime import datetime, timezone

    async with get_db_context() as db:
        result = await db.execute(select(Benchmark).where(Benchmark.id == benchmark_id))
        benchmark = result.scalar_one_or_none()
        if not benchmark:
            return

        benchmark.status = "running"
        benchmark.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            config = json.loads(benchmark.config_json)
            results = await run_synthetic_benchmark(benchmark_id, config)

            benchmark.status = "completed"
            benchmark.results_json = json.dumps(results)
            benchmark.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            benchmark.status = "failed"
            benchmark.error_message = str(e)
            benchmark.completed_at = datetime.now(timezone.utc)

        await db.commit()


@router.get("", response_model=BenchmarkListResponse)
async def list_benchmarks(
    model_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """List benchmarks with pagination and filters."""
    query = select(Benchmark).options(selectinload(Benchmark.model))

    if model_id:
        query = query.where(Benchmark.model_id == model_id)
    if status:
        query = query.where(Benchmark.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.order_by(Benchmark.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    benchmarks = result.scalars().all()

    return BenchmarkListResponse(
        items=[BenchmarkResponse.model_validate(b) for b in benchmarks],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{benchmark_id}", response_model=BenchmarkResponse)
async def get_benchmark(
    benchmark_id: int,
    session: SessionData = Depends(require_viewer),
    db: AsyncSession = Depends(get_db),
):
    """Get benchmark by ID."""
    result = await db.execute(select(Benchmark).where(Benchmark.id == benchmark_id))
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return BenchmarkResponse.model_validate(benchmark)


@router.post("", response_model=BenchmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_benchmark(
    benchmark_data: BenchmarkCreate,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new benchmark."""
    # Validate model exists
    model = await db.scalar(select(Model).where(Model.id == benchmark_data.model_id))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Validate config_json is valid JSON
    try:
        json.loads(benchmark_data.config_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="config_json must be valid JSON")

    benchmark = Benchmark(**benchmark_data.model_dump())
    db.add(benchmark)
    await db.flush()

    await log_audit(
        db, action="create_benchmark", user_id=session.user_id,
        resource_type="benchmark", resource_id=str(benchmark.id),
        details=benchmark_data.model_dump(), ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()
    await db.refresh(benchmark)
    return BenchmarkResponse.model_validate(benchmark)


@router.post("/{benchmark_id}/run", response_model=BenchmarkResponse)
async def run_benchmark(
    benchmark_id: int,
    request: Request,
    session: SessionData = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Start benchmark execution (async background)."""
    result = await db.execute(select(Benchmark).where(Benchmark.id == benchmark_id))
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    if benchmark.status == "running":
        raise HTTPException(status_code=409, detail="Benchmark already running")

    # Reset status
    benchmark.status = "pending"
    benchmark.results_json = None
    benchmark.error_message = None
    benchmark.started_at = None
    benchmark.completed_at = None
    await db.commit()

    # Start background task
    asyncio.create_task(run_benchmark_task(benchmark_id))

    await log_audit(
        db, action="run_benchmark", user_id=session.user_id,
        resource_type="benchmark", resource_id=str(benchmark_id),
        details={}, ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.commit()

    return BenchmarkResponse.model_validate(benchmark)


@router.delete("/{benchmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_benchmark(
    benchmark_id: int,
    request: Request,
    session: SessionData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a benchmark (admin only)."""
    result = await db.execute(select(Benchmark).where(Benchmark.id == benchmark_id))
    benchmark = result.scalar_one_or_none()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    await log_audit(
        db, action="delete_benchmark", user_id=session.user_id,
        resource_type="benchmark", resource_id=str(benchmark_id),
        details={"name": benchmark.name}, ip_address=get_client_ip(request), user_agent=get_user_agent(request)
    )
    await db.delete(benchmark)
    await db.commit()