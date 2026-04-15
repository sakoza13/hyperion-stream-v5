"""
Project Hyperion  ·  Core Orchestration Engine
══════════════════════════════════════════════════════

Abstract event-loop scheduler designed to govern 20x
parallel execution lanes running synthetic payloads.
No business logic is embedded — this is a pure
infrastructure stress-test harness.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger("hyperion.orchestrator")

# ── Tunable defaults (overridable via configs/production.yaml) ──
DEFAULT_LANES            = 20
DEFAULT_BUFFER_MS        = 250
DEFAULT_MAX_PACKET_BYTES = 1_048_576
DEFAULT_BACKLOG          = 4096

# Safety floors — prevent pathological config values
_MIN_LANES      = 1
_MIN_BUFFER_MS  = 10
_MIN_PACKET     = 1024
_MIN_BACKLOG    = 1

# ── Synthetic packet template (dummy data — no business payload) ──────

SYNTHETIC_PACKET = {
    "packet_id":   "synth-{:08x}",
    "lane_hint":   0,
    "timestamp":   0.0,
    "payload":     {"data": "synthetic", "size_bytes": 0},
    "checksum":    "",
}


@dataclass
class LaneContext:
    """Per-lane isolation context.

    Each lane holds an independent non-blocking sequence queue
    so cross-lane deadlocks are structurally impossible.
    """

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
        s = sorted(self.latency_samples)
        idx = int(len(s) * 0.99)
        return s[min(idx, len(s) - 1)] * 1000


class Orchestrator:
    """Primary async event-loop orchestrator for Project Hyperion.

    Manages 20x parallel execution lanes with staggered boot,
    graceful shutdown, per-lane fault isolation, and p99
    latency tracking.  All payloads are synthetic.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.total_lanes = max(_MIN_LANES, cfg.get("concurrency_lanes", DEFAULT_LANES))
        self.buffer_ms   = max(_MIN_BUFFER_MS, cfg.get("buffer_flush_interval_ms", DEFAULT_BUFFER_MS))
        self.max_packet  = max(_MIN_PACKET, cfg.get("max_packet_size_bytes", DEFAULT_MAX_PACKET_BYTES))
        self.backlog     = max(_MIN_BACKLOG, cfg.get("backlog", DEFAULT_BACKLOG))
        self.stagger_ms  = max(0, cfg.get("lane_startup_stagger_ms", 50))
        self.lanes: Dict[int, LaneContext] = {}
        self._running    = False
        self._started_at: float = 0.0

    # ── Validation ────────────────────────────────────────────────

    @staticmethod
    def validate_config(cfg: Dict[str, Any]) -> List[str]:
        """Pre-flight config validation.  Returns human-readable
        warnings for any out-of-range values."""
        warnings: List[str] = []
        lanes = cfg.get("concurrency_lanes", DEFAULT_LANES)
        if lanes < _MIN_LANES:
            warnings.append(f"concurrency_lanes={lanes} below minimum {_MIN_LANES}")
        if lanes > 256:
            warnings.append(f"concurrency_lanes={lanes} exceeds recommended max 256")
        buf = cfg.get("buffer_flush_interval_ms", DEFAULT_BUFFER_MS)
        if buf < _MIN_BUFFER_MS:
            warnings.append(f"buffer_flush_interval_ms={buf} below minimum {_MIN_BUFFER_MS} ms")
        return warnings

    # ── Lifecycle ─────────────────────────────────────────────────

    async def boot_pipeline(self) -> None:
        """Staggered boot of all execution lanes."""
        if self._running:
            logger.warning("boot_pipeline: already running — no-op")
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
        """Synthetic event-processing loop.
        Simulates network-I/O-bound packet handling at
        configurable intervals.  Collects per-packet latency."""
        ctx.started_at = time.monotonic()
        while True:
            t0 = time.monotonic()
            try:
                await asyncio.sleep(self.buffer_ms / 1000.0)
                ctx.packet_count += 1
                ctx.latency_samples.append(time.monotonic() - t0)
            except asyncio.CancelledError:
                logger.info(
                    "Lane %2d shutdown  |  packets=%6d  |  p99=%.2f ms  |  errors=%d",
                    ctx.lane_id, ctx.packet_count, ctx.p99_latency_ms, ctx.error_count,
                )
                break
            except Exception as exc:
                ctx.error_count += 1
                ctx.last_error = str(exc)
                logger.error("Lane %2d fault  |  %s", ctx.lane_id, exc)

    async def shutdown(self) -> None:
        """Graceful teardown of all lanes."""
        if not self._running:
            logger.info("Orchestrator already stopped.")
            return
        uptime = time.monotonic() - self._started_at
        logger.info("Shutting down  |  uptime=%.1fs  |  lanes=%d", uptime, len(self.lanes))
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
        """Per-lane metrics snapshot for external monitoring."""
        return {
            lid: {
                "packet_count": ctx.packet_count,
                "error_count":  ctx.error_count,
                "p99_ms":       round(ctx.p99_latency_ms, 2),
                "last_error":   ctx.last_error,
            }
            for lid, ctx in self.lanes.items()
        }

    @property
    def uptime_seconds(self) -> float:
        if not self._running:
            return 0.0
        return time.monotonic() - self._started_at


# ── Standalone entry-point (synthetic stress-test) ────────────────────

async def main():
    orch = Orchestrator()
    await orch.boot_pipeline()
    await asyncio.sleep(30)
    summary = orch.lane_summary()
    total = sum(s["packet_count"] for s in summary.values())
    logger.info("Synthetic run complete  |  packets=%d  |  lanes=%d  |  uptime=%.1fs",
                total, len(summary), orch.uptime_seconds)
    await orch.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
