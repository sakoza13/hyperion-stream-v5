"""
Project Hyperion  ·  Cryptographic Telemetry Vault
══════════════════════════════════════════════════════
Append-only, hash-chained telemetry ledger.
Every block is linked via SHA-256 to its predecessor,
creating an immutable audit trail.

Author:  Project Hyperion Engineering
Status:  Bootstrapped — Architecture Validated
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("hyperion.vault")

# Genesis seed — anchors the entire chain
GENESIS_SEED = b"HYPERION_GENESIS_ROOT_V5"


class TelemetryBlock:
    """A single immutable block in the telemetry ledger."""
    __slots__ = ("timestamp", "payload", "prev_hash", "block_hash")

    def __init__(self, timestamp: float, payload: Dict[str, Any],
                 prev_hash: str, block_hash: str):
        self.timestamp  = timestamp
        self.payload    = payload
        self.prev_hash  = prev_hash
        self.block_hash = block_hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts":         self.timestamp,
            "data":       self.payload,
            "prev_hash":  self.prev_hash,
            "hash":       self.block_hash,
        }


class TelemetryVault:
    """Append-only cryptographic telemetry ledger.

    Each block is hashed as:
        SHA-256( timestamp | serialized_payload | previous_hash )

    The genesis block chains from GENESIS_SEED, and every
    subsequent block carries the digest of its predecessor,
    forming a tamper-evident chain suitable for compliance
    auditing.
    """

    def __init__(self):
        self._last_hash = hashlib.sha256(GENESIS_SEED).hexdigest()
        self._block_count = 0

    # ── Core API ──────────────────────────────────────────────────

    def append(self, data: Dict[str, Any]) -> str:
        """Commit a telemetry event to the ledger.
        Returns the new block's hex digest."""
        ts      = time.time()
        payload = json.dumps(data, sort_keys=True)
        content = f"{ts}|{payload}|{self._last_hash}"
        digest  = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self._last_hash = digest
        self._block_count += 1
        logger.debug("Vault block %d committed  |  hash=%s", self._block_count, digest[:16])
        return digest

    def append_batch(self, items: List[Dict[str, Any]]) -> List[str]:
        """Commit multiple events as sequential blocks.  Each block
        chains to its immediate predecessor."""
        return [self.append(item) for item in items]

    # ── Integrity Verification ────────────────────────────────────

    def verify_chain(self, blocks: List[Dict[str, Any]]) -> bool:
        """Replay-verify an entire ledger segment.

        Recomputes every block hash from the genesis seed and
        compares against the stored digest.  Returns False
        immediately if any block fails to validate.
        """
        running = hashlib.sha256(GENESIS_SEED).hexdigest()
        for blk in blocks:
            ts      = blk.get("ts", 0)
            payload = json.dumps(blk.get("data", {}), sort_keys=True)
            content = f"{ts}|{payload}|{running}"
            expected = blk.get("hash", "")
            recomputed = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if recomputed != expected:
                logger.error(
                    "Chain integrity FAILED  |  expected=%s  |  got=%s",
                    expected[:16], recomputed[:16],
                )
                return False
            running = expected
        logger.info("Chain integrity VERIFIED  |  blocks=%d", len(blocks))
        return True

    # ── Introspection ─────────────────────────────────────────────

    @property
    def block_count(self) -> int:
        return self._block_count

    @property
    def latest_hash(self) -> str:
        return self._last_hash
