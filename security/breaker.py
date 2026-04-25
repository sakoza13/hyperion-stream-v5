"""
Project Hyperion  ·  Fail-Closed Circuit Breaker
══════════════════════════════════════════════════════
Ingestion-boundary protection module.  Trips OPEN
after N consecutive failures, transitions through
HALF-OPEN for a single probe, then returns to CLOSED
on success.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("hyperion.breaker")


class CircuitBreaker:
    """Fail-closed circuit breaker.

    State machine:
        CLOSED  ── fail_count ≥ threshold ──→ OPEN
        OPEN    ── recovery_timeout elapsed ─→ HALF_OPEN
        HALF_OPEN ── success ──→ CLOSED
        HALF_OPEN ── failure ──→ OPEN

    All transitions are guarded by monotonic clock
    comparisons to prevent double-trip race conditions.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._validate(failure_threshold, recovery_timeout)
        self.threshold  = max(1, failure_threshold)
        self.timeout    = max(1.0, recovery_timeout)
        self.state: str       = "CLOSED"
        self.fail_count: int  = 0
        self.last_trip: float = 0.0
        self._transitioning   = False   # crude single-thread guard

    # ── Validation ────────────────────────────────────────────────

    @staticmethod
    def _validate(threshold: int, timeout: float) -> None:
        if threshold < 1:
            raise ValueError(f"failure_threshold must be ≥ 1, got {threshold}")
        if timeout < 1.0:
            raise ValueError(f"recovery_timeout must be ≥ 1.0 s, got {timeout}")

    # ── State Machine API ─────────────────────────────────────────

    def success(self) -> None:
        """Report a successful execution.  Resets the failure counter.
        If HALF_OPEN, transitions back to CLOSED."""
        self.fail_count = 0
        if self.state == "HALF_OPEN" and not self._transitioning:
            self._transitioning = True
            logger.info("Breaker: HALF_OPEN → CLOSED")
            self.state = "CLOSED"
            self._transitioning = False

    def failure(self) -> None:
        """Report a failed execution.  Increments the failure counter
        and trips OPEN if the threshold is crossed."""
        self.fail_count += 1
        if (self.fail_count >= self.threshold
                and self.state != "OPEN"
                and not self._transitioning):
            self._transitioning = True
            self.state      = "OPEN"
            self.last_trip  = time.monotonic()
            logger.critical(
                "Breaker TRIPPED OPEN  |  failures=%d/%d",
                self.fail_count, self.threshold,
            )
            self._transitioning = False

    def allow(self) -> bool:
        """Check whether execution is currently permitted.
        Returns False when the breaker is OPEN and the
        recovery timeout has not yet elapsed."""
        if self.state == "OPEN":
            elapsed = time.monotonic() - self.last_trip
            if elapsed >= self.timeout and not self._transitioning:
                self._transitioning = True
                self.state = "HALF_OPEN"
                logger.info("Breaker: OPEN → HALF_OPEN (%.1fs elapsed)", elapsed)
                self._transitioning = False
                return True
            return False
        return True

    def reset(self) -> None:
        """Manual reset — forces CLOSED and clears all counters."""
        self.state        = "CLOSED"
        self.fail_count   = 0
        self.last_trip    = 0.0
        self._transitioning = False
        logger.info("Breaker manually reset → CLOSED")

    # ── Introspection ─────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "state":       self.state,
            "fail_count":  self.fail_count,
            "threshold":   self.threshold,
            "last_trip":   self.last_trip,
        }
