# Issue #009 — SOC 2 Type II Pre-Audit Checklist

**Reported:** 2026-05-25 09:00 &nbsp;|&nbsp; **Status:** Open &nbsp;|&nbsp; **Labels:** `security`, `compliance`

## Summary
Prepare the telemetry storage layer and access control patterns for a future
SOC 2 Type II compliance audit.  This is a prerequisite for enterprise cloud
credit programs that require evidence of security controls.

## Pre-Audit Checklist
- [x] Append-only telemetry ledger with cryptographic verification
- [x] Non-root container runtime
- [x] Secrets blacklist in `.gitignore`
- [ ] Access control lists (ACLs) on vault storage directory
- [ ] Audit log for all manual breaker resets
- [ ] Data retention policy (vault log rotation)
- [ ] Penetration test report (external firm, Phase 3)
- [ ] Incident response runbook

## Notes
SOC 2 audit is targeted for Q4 2026 (Phase 3).  The cryptographic vault
design already satisfies the immutability and verification requirements
of SOC 2 CC6.1 and CC6.7.
