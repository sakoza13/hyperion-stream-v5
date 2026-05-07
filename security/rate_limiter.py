"""
Project Hyperion  ·  Token-Bucket Rate Limiter
══════════════════════════════════════════════════════
Ingestion-gate rate limiter using the token-bucket
algorithm.  Prevents downstream saturation during
traffic bursts while allowing short-term bursts
via a configurable burst multiplier.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import logging
import time
from typing import Optional

logger = logging.getLogger("hyperion.rate_limiter")


class TokenBucket:
    """Classic token-bucket rate limiter.

    Tokens refill at a fixed rate (refill_rate/sec) up to
    a configurable capacity.  A burst multiplier allows
    short-term overage for legitimate traffic spikes while
    the steady-state rate remains bounded.
    """

    def __init__(self,
                 capacity: int        = 10_000,
                 refill_rate: float   = 500.0,
                 burst_mult: float    = 1.5):
        self._validate(capacity, refill_rate, burst_mult)
        self.capacity     = capacity
        self.burst_cap    = int(capacity * burst_mult)
        self.refill_rate  = refill_rate
        self.burst_mult   = burst_mult
        self._tokens: float      = float(self.burst_cap)
        self._last_refill: float = time.monotonic()
        self._total_consumed: int = 0
        self._total_rejected: int = 0

    # ── Validation ────────────────────────────────────────────────

    @staticmethod
    def _validate(cap: int, rate: float, burst: float) -> None:
        if cap < 1:
            raise ValueError(f"capacity must be ≥ 1, got {cap}")
        if rate < 1.0:
            raise ValueError(f"refill_rate must be ≥ 1.0, got {rate}")
        if burst < 1.0:
            raise ValueError(f"burst_mult must be ≥ 1.0, got {burst}")

    # ── Core ──────────────────────────────────────────────────────

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self.burst_cap),
            self._tokens + elapsed * self.refill_rate,
        )
        self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Attempt to consume *tokens* from the bucket.
        Returns True if allowed, False if rate-limited."""
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            self._total_consumed += tokens
            return True
        self._total_rejected += tokens
        logger.debug("Rate-limit REJECT  |  needed=%d  |  available=%.1f", tokens, self._tokens)
        return False

    def try_consume(self, tokens: int = 1) -> bool:
        """Alias for consume — used by ingestion gates."""
        return self.consume(tokens)

    # ── Introspection ─────────────────────────────────────────────

    @property
    def available_tokens(self) -> float:
        self._refill()
        return self._tokens

    @property
    def stats(self) -> dict:
        return {
            "consumed": self._total_consumed,
            "rejected": self._total_rejected,
            "available": round(self._tokens, 1),
            "capacity":  self.capacity,
            "burst_cap": self.burst_cap,
            "rate":      self.refill_rate,
        }
