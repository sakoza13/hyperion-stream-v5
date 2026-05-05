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
from typing import Any, Dict

# ── Synthetic payload template ────────────────────────────────────

def _synth_packet(lane_id: int, seq: int) -> Dict[str, Any]:
    return {
        "packet_id":   f"synth-{lane_id:02d}-{seq:08x}",
        "lane_hint":   lane_id,
        "timestamp":   time.time(),
        "payload":     {"data": "synthetic", "seq": seq},
        "checksum":    hashlib.md5(f"synth-{seq}".encode()).hexdigest(),
    }


async def lane_worker(lane_id: int, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Simulate a single lane-processing cycle.

    Sleeps for a randomised interval (5–20 ms by default)
    to emulate network-I/O latency, then returns a
    synthetic result packet with lane routing metadata.
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


async def lane_batch(lane_id: int, batch_size: int = 100) -> list[Dict[str, Any]]:
    """Process a batch of synthetic packets through a single lane."""
    tasks = [lane_worker(lane_id) for _ in range(batch_size)]
    return await asyncio.gather(*tasks)
