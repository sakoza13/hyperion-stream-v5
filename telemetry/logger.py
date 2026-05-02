"""
Project Hyperion  ·  Structured Telemetry Logger
══════════════════════════════════════════════════════
Structured logging abstraction that wraps Python's
`logging` module with JSON-line output and automatic
context injection (lane_id, trace_id, span_id).

All log output is synthetic; no business identifiers
are embedded.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional


class TelemetryLogger:
    """Structured JSON-line logger for high-concurrency telemetry.

    Each log line is a standalone JSON object carrying:
      - timestamp (ISO-8601)
      - level
      - message
      - lane_id / trace_id / span_id (if set)
      - arbitrary context keys

    Designed for ingestion by Prometheus, Grafana Loki,
    and OpenTelemetry collectors.
    """

    def __init__(self, name: str = "hyperion.telemetry",
                 lane_id: Optional[int] = None,
                 trace_id: Optional[str] = None):
        self._logger   = logging.getLogger(name)
        self.lane_id   = lane_id
        self.trace_id  = trace_id or uuid.uuid4().hex[:16]
        self.span_id   = uuid.uuid4().hex[:8]
        self._sequence = 0

    # ── Context management ────────────────────────────────────────

    def with_lane(self, lane_id: int) -> "TelemetryLogger":
        """Return a child logger scoped to a specific lane."""
        child = TelemetryLogger(
            name=self._logger.name,
            lane_id=lane_id,
            trace_id=self.trace_id,
        )
        child.span_id = uuid.uuid4().hex[:8]
        return child

    def new_trace(self) -> "TelemetryLogger":
        """Start a fresh trace context."""
        return TelemetryLogger(
            name=self._logger.name,
            lane_id=self.lane_id,
        )

    # ── Emit ──────────────────────────────────────────────────────

    def _emit(self, level: int, message: str, **kwargs: Any) -> None:
        self._sequence += 1
        record = {
            "ts":       time.time(),
            "level":    logging.getLevelName(level),
            "msg":      message,
            "seq":      self._sequence,
            "lane_id":  self.lane_id,
            "trace_id": self.trace_id,
            "span_id":  self.span_id,
            **kwargs,
        }
        self._logger.log(level, json.dumps(record, sort_keys=True))

    def info(self, message: str, **kwargs) -> None:
        self._emit(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._emit(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._emit(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        self._emit(logging.DEBUG, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        self._emit(logging.CRITICAL, message, **kwargs)
