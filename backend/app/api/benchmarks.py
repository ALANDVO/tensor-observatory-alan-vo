"""Benchmarks API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional, List

from pydantic import BaseModel, Field

from app.core.auth import SessionData
from app.core.benchmark_engine import run_synthetic_benchmark

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


class BenchmarkCreate(BaseModel):
    model_id: int = Field(..., gt=0)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict] = Field(None)


class BenchmarkUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[dict] = Field(None)
    error_message: Optional[str] = Field(None)


class BenchmarkResponse(BaseModel):
    id: int
    model_id: int
    name: str
    status: str
    created_at: str
    result_json: Optional[dict] = None

    model_config = {"protected_namespaces": (), "from_attributes": True}


class BenchmarkListResponse(BaseModel):
    items: List[BenchmarkResponse]
    total: int

    model_config = {"protected_namespaces": (), "from_attributes": True}


# In-memory benchmark runner (for demo; production would use job queue)
_benchmark_tasks: dict = {}


async def run_synthetic_benchmark(
    benchmark_id: int,
    config: dict,
) -> dict:
    """Run a deterministic synthetic benchmark and return results.

    Parameters
    ----------
    benchmark_id : int
        Database benchmark ID.
    config : dict
        Must contain: model_id, num_tokens, ttft_ms, tpot_ms, memory_mb (all optional
        with sensible defaults).

    Returns
    -------
    dict
        Benchmark result with token throughput, latency (TTFT, TPOT), memory tracking.
    """
    # Extract config with defaults
    num_tokens = config.get("num_tokens", 100)
    ttft_ms = config.get("ttft_ms", 200)
    tpot_ms = config.get("tpot_ms", 50)
    memory_mb = config.get("memory_mb", 500.0)

    # Clamp values
    num_tokens = max(1, min(num_tokens, 10000))
    ttft_ms = max(1, min(ttft_ms, 5000))
    tpot_ms = max(0.1, min(tpot_ms, 2000))
    memory_mb = max(10, min(memory_mb, 10000))

    # Import and run the synthetic token stream
    from app.core.benchmark_engine import _synthetic_token_stream

    # Run the synthetic token stream (CPU-bound, deterministic)
    result = _synthetic_token_stream(
        num_tokens,
        ttft_ms,
        tpot_ms,
        memory_mb,
    )

    # Attach benchmark ID for DB persistence
    result["benchmark_id"] = benchmark_id
    result["config"] = config

    return result


async def run_benchmark_task(benchmark_id: int, db_session) -> None:
    """Background task: run benchmark and store results in DB.

    Parameters
    ----------
    benchmark_id : int
        Database benchmark ID.
    db_session : AsyncSession
        SQLAlchemy async session for persisting results.
    """
    from app.core.database import get_async_session
    from app.models.benchmarks import Benchmark

    async with get_async_session() as session:
        result = await session.get(Benchmark, benchmark_id)
        if not result:
            return

        config = result.config_json or {}
        # Override with task-specific config if needed
        config["benchmark_id"] = benchmark_id

        # Run synthetic benchmark
        benchmark_result = await run_synthetic_benchmark(benchmark_id, config)

        # Store results as JSON
        result.status = "completed"
        result.result_json = benchmark_result
        result.error_message = None
        await session.commit()


@router.get("", response_model=BenchmarkListResponse)
async def list_benchmarks(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
) -> BenchmarkListResponse:
    """List benchmarks with pagination and filters."""
    ...


@router.get("/{benchmark_id}", response_model=BenchmarkResponse)
async def get_benchmark(
    benchmark_id: int,
) -> BenchmarkResponse:
    """Get benchmark by ID."""
    ...


@router.post("", response_model=BenchmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_benchmark(
    benchmark_create: BenchmarkCreate,
) -> BenchmarkResponse:
    """Create a new benchmark."""
    ...


@router.post("/{benchmark_id}/run", response_model=BenchmarkResponse)
async def run_benchmark(
    benchmark_id: int,
) -> BenchmarkResponse:
    """Start benchmark execution (async background)."""
    ...


@router.delete("/{benchmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_benchmark(
    benchmark_id: int,
) -> None:
    """Delete a benchmark (admin only)."""
    await db.commit()
