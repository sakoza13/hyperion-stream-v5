# Issue #006 — Structured JSON-Line Logger with Trace Context

**Reported:** 2026-04-28 08:45 &nbsp;|&nbsp; **Closed:** 2026-05-02 11:30 &nbsp;|&nbsp; **Labels:** `telemetry`, `infrastructure-scaling`

## Summary
Build a structured logging abstraction that emits JSON-line output compatible
with Grafana Loki and OpenTelemetry collectors.  Each log line must carry
trace_id, span_id, and optional lane_id for distributed tracing.

## Acceptance Criteria
- [x] JSON-line output (one JSON object per line)
- [x] Automatic trace_id / span_id generation
- [x] `with_lane()` scoping for per-lane log contexts
- [x] `new_trace()` for fresh trace initialisation
- [x] Sequence counter for causal ordering

## Resolution
Implemented in `telemetry/logger.py`.  Ready for Loki ingestion.
