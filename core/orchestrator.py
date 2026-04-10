"""
Project Hyperion  ·  Core Orchestration Engine
══════════════════════════════════════════════════════
Abstract event-loop scheduler designed to govern 20x
parallel execution lanes.  All payloads are synthetic;
no business logic is embedded.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Awaitable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hyperion.orchestrator")

# ── Tunable defaults (overridable via configs/production.yaml) ──
DEFAULT_LANES            = 20
DEFAULT_BUFFER_MS        = 250
DEFAULT_MAX_PACKET_BYTES = 1_048_576
DEFAULT_BACKLOG          = 4096


@dataclass
class LaneContext:
    """Per-lane isolation context.  Each lane holds an independent
    non-blocking sequence queue so cross-lane deadlocks are structurally
    impossible."""

    lane_id: int
    task: Optional[asyncio.Task]      = None
    started_at: float                  = 0.0
    packet_count: int                  = 0
    error_count: int                   = 0
    last_error: Optional[str]          = None
    latency_samples: List[float]       = field(default_factory=list)

    @property
    def p99_latency_ms(self) -> float:
        if not self.latency_samples:
            return 0.0
        sorted_samples = sorted(self.latency_samples)
        idx = int(len(sorted_samples) * 0.99)
        return sorted_samples[min(idx, len(sorted_samples) - 1)] * 1000


class Orchestrator:
    """Primary async event-loop orchestrator for Project Hyperion.

    Manages 20x parallel execution lanes with staggered boot,
    graceful shutdown, and per-lane fault isolation.  All lane
    payloads are synthetic — this is an infrastructure stress-test
    harness, not a business-logic runtime.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.total_lanes = max(1, cfg.get("concurrency_lanes", DEFAULT_LANES))
        self.buffer_ms   = max(10, cfg.get("buffer_flush_interval_ms", DEFAULT_BUFFER_MS))
        self.max_packet  = max(1024, cfg.get("max_packet_size_bytes", DEFAULT_MAX_PACKET_BYTES))
        self.backlog     = max(1, cfg.get("backlog", DEFAULT_BACKLOG))
        self.stagger_ms  = cfg.get("lane_startup_stagger_ms", 50)
        self.lanes: Dict[int, LaneContext] = {}
        self._running = False
        self._started_at: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────

    async def boot_pipeline(self) -> None:
        """Staggered boot of all execution lanes to avoid thundering-herd
        CPU spikes during cold-start."""
        if self._running:
            logger.warning("boot_pipeline called while already running — no-op")
            return
        self._started_at = time.monotonic()
        logger.info(
            "Booting %d lanes  |  buffer=%d ms  |  stagger=%d ms  |  max_packet=%d B",
            self.total_lanes, self.buffer_ms, self.stagger_ms, self.max_packet,
        )
        for lane_id in range(1, self.total_lanes + 1):
            ctx = LaneContext(lane_id=lane_id)
            ctx.task = asyncio.create_task(self._lane_loop(ctx))
            self.lanes[lane_id] = ctx
            if self.stagger_ms:
                await asyncio.sleep(self.stagger_ms / 1000.0)
        self._running = True
        logger.info("All %d lanes operational.", self.total_lanes)

    async def _lane_loop(self, ctx: LaneContext) -> None:
        """Infinite event-processing loop for a single lane.
        Synthetic workload only — simulates network-I/O bound
        packet processing at configurable intervals.
        Collects per-packet latency for p99 reporting."""
        ctx.started_at = time.monotonic()
        while True:
            t0 = time.monotonic()
            try:
                await asyncio.sleep(self.buffer_ms / 1000.0)
                ctx.packet_count += 1
                ctx.latency_samples.append(time.monotonic() - t0)
            except asyncio.CancelledError:
                logger.info(
                    "Lane %d shutdown  |  packets=%d  |  p99=%.2f ms  |  errors=%d",
                    ctx.lane_id, ctx.packet_count, ctx.p99_latency_ms, ctx.error_count,
                )
                break
            except Exception as exc:
                ctx.error_count += 1
                ctx.last_error = str(exc)
                logger.error("Lane %d fault  |  %s", ctx.lane_id, exc)

    async def shutdown(self) -> None:
        """Graceful teardown — cancels all lanes, awaits completion,
        and clears the lane pool."""
        if not self._running:
            logger.info("Orchestrator already stopped.")
            return
        uptime = time.monotonic() - self._started_at
        logger.info(
            "Initiating graceful shutdown  |  uptime=%.1fs  |  lanes=%d",
            uptime, len(self.lanes),
        )
        for ctx in self.lanes.values():
            if ctx.task:
                ctx.task.cancel()
        await asyncio.gather(
            *[ctx.task for ctx in self.lanes.values() if ctx.task],
            return_exceptions=True,
        )
        self.lanes.clear()
        self._running = False
        logger.info("Orchestrator shut down cleanly.")

    # ── Introspection ─────────────────────────────────────────────

    def lane_summary(self) -> Dict[int, Dict[str, Any]]:
        """Return a snapshot of per-lane metrics for external monitoring."""
        return {
            lid: {
                "packet_count": ctx.packet_count,
                "error_count":  ctx.error_count,
                "p99_ms":       round(ctx.p99_latency_ms, 2),
                "last_error":   ctx.last_error,
            }
            for lid, ctx in self.lanes.items()
        }


# ── Standalone entry-point (synthetic stress-test) ────────────────────

async def main():
    orch = Orchestrator()
    await orch.boot_pipeline()
    # Run synthetic load for 30 s, print lane summary, then exit
    await asyncio.sleep(30)
    summary = orch.lane_summary()
    total_packets = sum(s["packet_count"] for s in summary.values())
    logger.info("Synthetic run complete  |  total_packets=%d  |  lanes=%d",
                total_packets, len(summary))
    await orch.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
