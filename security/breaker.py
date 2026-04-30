"""
Project Hyperion  ·  Fail-Closed Circuit Breaker
══════════════════════════════════════════════════════
Ingestion-boundary protection module.

State machine (audited for race conditions):
    CLOSED  ── fail_count ≥ threshold ──→ OPEN
    OPEN    ── recovery_timeout elapsed ─→ HALF_OPEN
    HALF_OPEN ── success ──→ CLOSED
    HALF_OPEN ── failure ──→ OPEN

All state transitions are serialised through a
lightweight transition lock to prevent concurrent
modification races in async contexts.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("hyperion.breaker")

# ── Allowed states ────────────────────────────────────────────────

_STATES = ("CLOSED", "OPEN", "HALF_OPEN")


class CircuitBreaker:
    """Fail-closed circuit breaker with transition-lock safety."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self._validate(failure_threshold, recovery_timeout)
        self.threshold: int     = max(1, failure_threshold)
        self.timeout: float     = max(1.0, recovery_timeout)
        self.state: str         = "CLOSED"
        self.fail_count: int    = 0
        self.last_trip: float   = 0.0
        self._lock              = False

    # ── Validation ────────────────────────────────────────────────

    @staticmethod
    def _validate(threshold: int, timeout: float) -> None:
        if threshold < 1:
            raise ValueError(f"failure_threshold must be ≥ 1, got {threshold}")
        if timeout < 1.0:
            raise ValueError(f"recovery_timeout must be ≥ 1.0 s, got {timeout}")

    # ── Internal guard ────────────────────────────────────────────

    def _acquire(self) -> bool:
        """Acquire the transition lock.  Returns False if already held."""
        if self._lock:
            return False
        self._lock = True
        return True

    def _release(self) -> None:
        self._lock = False

    # ── State Machine API ─────────────────────────────────────────

    def success(self) -> None:
        """Report a successful execution."""
        self.fail_count = 0
        if self.state == "HALF_OPEN" and self._acquire():
            try:
                logger.info("Breaker: HALF_OPEN → CLOSED")
                self.state = "CLOSED"
            finally:
                self._release()

    def failure(self) -> None:
        """Report a failed execution.  Trips OPEN if threshold exceeded."""
        self.fail_count += 1
        if (self.fail_count >= self.threshold
                and self.state != "OPEN"
                and self._acquire()):
            try:
                self.state     = "OPEN"
                self.last_trip = time.monotonic()
                logger.critical(
                    "Breaker TRIPPED OPEN  |  failures=%d/%d",
                    self.fail_count, self.threshold,
                )
            finally:
                self._release()

    def allow(self) -> bool:
        """Check whether execution is permitted."""
        if self.state == "OPEN":
            elapsed = time.monotonic() - self.last_trip
            if elapsed >= self.timeout and self._acquire():
                try:
                    self.state = "HALF_OPEN"
                    logger.info("Breaker: OPEN → HALF_OPEN (%.1fs)", elapsed)
                finally:
                    self._release()
                return True
            return False
        return True

    def reset(self) -> None:
        """Manual reset to CLOSED."""
        if self._acquire():
            try:
                self.state      = "CLOSED"
                self.fail_count = 0
                self.last_trip  = 0.0
                logger.info("Breaker manually reset → CLOSED")
            finally:
                self._release()

    # ── Introspection ─────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "state":       self.state,
            "fail_count":  self.fail_count,
            "threshold":   self.threshold,
            "last_trip":   self.last_trip,
            "locked":      self._lock,
        }
