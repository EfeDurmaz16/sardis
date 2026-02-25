# P0/P1 Hardening Priorities

Date: 2026-02-25  
Owner: Platform / Security

## P0

### Immutable hard-limit layer for NL policy parser
- Goal: Ensure natural-language parsing can never relax non-negotiable risk constraints.
- Requirements:
  - Hard-coded absolute caps enforced after parser output.
  - Parser output cannot override immutable caps.
  - Fail-closed behavior on parser uncertainty/error.
- Validation:
  - Fuzz tests for adversarial prompts.
  - Property tests for cap invariants and monotonic safety.
- Status: Planned

## P1

### Agent-level sliding window limiter on payment endpoints
- Goal: Bound request/decision volume per agent to reduce abuse and failure amplification.
- Requirements:
  - Sliding window limits at payment execution endpoints.
  - Per-org overrides and burst handling.
  - Explicit telemetry for rate-limit denials.
- Status: Planned

### Mainnet gas profiling + optimization pass
- Goal: Keep margin-safe execution costs for production on-chain flows.
- Requirements:
  - Baseline gas report for critical contract and user-op paths.
  - Optimization pass with before/after benchmark artifacts.
  - Regression checks in CI for gas ceiling drift.
- Status: Planned

### Turnkey outage runbook + DR playbook (RTO/RPO + failover mode)
- Goal: Define deterministic degraded/failover behavior during MPC dependency outage.
- Requirements:
  - Incident decision tree with explicit RTO/RPO targets.
  - Operator runbook for failover and recovery.
  - Customer-facing status communication template.
- Status: Planned
