# Issue #007 — Per-Lane Stress-Test Harness

**Reported:** 2026-05-20 13:00 &nbsp;|&nbsp; **Closed:** 2026-05-26 15:00 &nbsp;|&nbsp; **Labels:** `performance-engineering`, `testing`

## Summary
Create a standalone stress-test harness that can saturate a single lane for
a configurable duration and return p50/p99/p999 latency histograms.

## Acceptance Criteria
- [x] `lane_stress_test()` runs packets continuously for N seconds
- [x] Returns `count`, `mean_ms`, `p50_ms`, `p99_ms`, `p999_ms`
- [x] Configurable jitter window
- [x] CLI entry-point with `--lanes` and `--duration` arguments

## Resolution
`lane_stress_test()` added to `workers/lane.py`.  CLI harness in
`tests/stress_benchmarks.py`.
