# Issue #004 — Token-Bucket Ingestion Rate Limiter

**Reported:** 2026-05-05 14:30 &nbsp;|&nbsp; **Closed:** 2026-05-07 16:45 &nbsp;|&nbsp; **Labels:** `performance-engineering`, `security`

## Summary
Implement a token-bucket rate limiter at the ingestion boundary to prevent
downstream saturation during traffic bursts.  Must support a configurable
burst multiplier for short-term overage.

## Parameters
| Parameter | Default | Description |
|---|---|---|
| `capacity` | 10,000 | Maximum tokens in bucket |
| `refill_rate` | 500/s | Steady-state refill rate |
| `burst_mult` | 1.5× | Short-term burst ceiling (15,000 tokens) |

## Resolution
Implemented in `security/rate_limiter.py`.  Exposes `consume()`, `try_consume()`,
and `stats` introspection.
