"""Deterministic synthetic benchmark engine for inference throughput and latency."""

import time
import random
import asyncio
from typing import Dict, Any


# ---------------------------------------------------------------------------
# Synthetic token-generation simulation (no LLM key required)
# ---------------------------------------------------------------------------

def _synthetic_token_stream(
    num_tokens: int,
    ttft_ms: int = 200,
    tpot_ms: int = 50,
    memory_mb: float = 500.0,
) -> Dict[str, Any]:
    """Generate a deterministic synthetic token stream.

    Returns per-token timing and cumulative metrics.
    """
    ttft_s = ttft_ms / 1000.0
    tpot_s = tpot_ms / 1000.0

    # TTFT: time to first token
    first_token_time = ttft_s

    # Simulate token generation times (normally distributed around tpot)
    rng = random.Random(42)  # deterministic seed
    generation_times = [
        max(0.1, rng.gauss(tpot_s, tpot_s * 0.2)) for _ in range(num_tokens)
    ]

    # TTFT latency
    ttft_latency = first_token_time

    # TPOT (time per output token) = mean of generation times
    tpot_latency = sum(generation_times) / len(generation_times) if generation_times else 0.0

    # Total time = TTFT + TPOT * N
    total_time = first_token_time + sum(generation_times)

    # Memory tracking (peak during generation)
    peak_memory_mb = memory_mb

    # Token throughput (tokens / total_time)
    token_throughput = num_tokens / total_time if total_time > 0 else 0.0

    return {
        "num_tokens": num_tokens,
        "ttft_ms": ttft_ms,
        "tpot_ms": tpot_ms,
        "ttft_latency_s": first_token_time,
        "tpot_latency_s": tpot_latency,
        "total_latency_s": total_time,
        "token_throughput_tokens_s": token_throughput,
        "peak_memory_mb": peak_memory_mb,
        "generation_times_ms": [t * 1000 for t in generation_times],
    }


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

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

    # Run the synthetic token stream (CPU-bound, deterministic)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        _synthetic_token_stream,
        num_tokens,
        ttft_ms,
        tpot_ms,
        memory_mb,
    )

    # Attach benchmark ID for DB persistence
    result["benchmark_id"] = benchmark_id
    result["config"] = config

    return result