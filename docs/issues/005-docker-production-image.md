# Issue #005 — Docker Production Container Spec

**Reported:** 2026-05-09 10:00 &nbsp;|&nbsp; **Closed:** 2026-05-14 12:30 &nbsp;|&nbsp; **Labels:** `infrastructure-scaling`, `docker`

## Summary
Package Project Hyperion as a minimal, secure production Docker image targeting
`python:3.11-slim`.  Image must run as non-root and include a healthcheck.

## Acceptance Criteria
- [x] Multi-layer build with dependency caching
- [x] Non-root `hyperion` user with nologin shell
- [x] HEALTHCHECK directive with 30 s interval
- [x] EXPOSE 8080 (app) + 9090 (metrics)
- [x] Pinned apt package versions for reproducible builds

## Resolution
Implemented in `docker/Dockerfile`.  Security hardening applied May 14.
