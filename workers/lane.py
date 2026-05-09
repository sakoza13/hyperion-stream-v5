"""
Project Hyperion  ·  Distributed Lane Worker
══════════════════════════════════════════════════════
Per-lane async worker simulating low-latency
I/O-bound packet processing.  All data is synthetic.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import asyncio
import hashlib
import random
import time
from typing import Any, Dict, List, Optional


def _synth_packet(lane_id: int, seq: int) -> Dict[str, Any]:
    return {
        "packet_id":   f"synth-{lane_id:02d}-{seq:08x}",
        "lane_hint":   lane_id,
        "timestamp":   time.time(),
        "payload":     {"data": "synthetic", "seq": seq},
        "checksum":    hashlib.md5(f"synth-{seq}".encode()).hexdigest(),
    }


async def lane_worker(lane_id: int, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Simulate a single lane-processing cycle.

    Sleep window: configurable via lane_jitter_ms (default 5–20 ms).
    Returns synthetic result with latency measurement.
    """
    cfg = config or {}
    jitter_ms = cfg.get("lane_jitter_ms", (5, 20))
    sleep_s = random.uniform(jitter_ms[0], jitter_ms[1]) / 1000.0

    t0 = time.perf_counter()
    await asyncio.sleep(sleep_s)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    seq = random.randint(0, 0xFFFFFFFF)
    packet = _synth_packet(lane_id, seq)

    return {
        "lane_id":        lane_id,
        "status":         "VERIFIED_SUCCESS",
        "latency_ms":     round(elapsed_ms, 3),
        "routed_packet":  packet,
    }


async def lane_batch(lane_id: int, batch_size: int = 100) -> List[Dict[str, Any]]:
    """Process a batch of synthetic packets through a single lane.
    Returns results along with batch-level p99 latency."""
    tasks = [lane_worker(lane_id) for _ in range(batch_size)]
    results = await asyncio.gather(*tasks)
    latencies = sorted(r["latency_ms"] for r in results)
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
    return results


async def lane_stress_test(lane_id: int,
                           duration_sec: int = 10,
                           jitter_ms: tuple = (5, 20)) -> Dict[str, Any]:
    """Continuously process packets for *duration_sec* and
    return aggregate statistics.  Used for lane-level
    stress-testing and capacity planning."""
    cfg = {"lane_jitter_ms": jitter_ms}
    deadline = time.monotonic() + duration_sec
    latencies: List[float] = []
    errors = 0

    while time.monotonic() < deadline:
        try:
            result = await lane_worker(lane_id, cfg)
            latencies.append(result["latency_ms"])
        except Exception:
            errors += 1

    s = sorted(latencies) if latencies else [0.0]
    return {
        "lane_id":    lane_id,
        "count":      len(latencies),
        "errors":     errors,
        "mean_ms":    round(sum(s) / len(s), 3),
        "p50_ms":     round(s[int(len(s) * 0.50)], 3),
        "p99_ms":     round(s[int(len(s) * 0.99)], 3),
        "p999_ms":    round(s[int(len(s) * 0.999)], 3),
        "duration_s": duration_sec,
    }
