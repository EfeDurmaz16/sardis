# Compliance Execution Track (Q1 2026)

Date: 2026-02-26  
Owner: Sardis Compliance + Platform + Security

## 1) PCI Scope Boundary (Target State)

### In scope
- PAN execution lane only (restricted/break-glass path).
- PAN reveal and entry worker runtime (ephemeral secrets, isolated runner).
- Access controls for PAN-lane operators and service principals.
- Audit log chain for card execution decisions and override events.

### Out of scope (must remain out)
- LLM runtime and prompt logs.
- Generic API services that never process PAN/CVV.
- Analytics/dashboard stores with redacted metadata only.

### Non-negotiable controls
1. PAN/CVV never stored in Sardis application DB.
2. Production uses PostgreSQL with strict role split and encrypted backups.
3. PAN lane requires explicit allowlist + approval + policy gates.
4. Any policy bypass attempt generates critical alert + evidence record.

## 2) SOC2 Evidence Automation

### Evidence sources
- Policy enforcement: hard-limit tests and attestation tests.
- Auditability: compliance audit API tests and audit store integrity tests.
- Operational controls: incident drill and ops readiness gates.

### Automation path
1. Run `bash scripts/release/compliance_execution_check.sh` in CI/nightly.
2. Persist test artifacts and release-gate output in immutable build logs.
3. Link build/run IDs into evidence package for control owners.
4. Generate hash-based evidence manifest:
   - `python3 scripts/release/generate_soc2_evidence_manifest.py --output artifacts/compliance/soc2-evidence-manifest.json`
5. Validate measured DR targets:
   - `bash scripts/release/drill_metrics_check.sh`

### Required evidence outputs
- Test command and timestamp.
- Commit SHA + branch.
- Pass/fail outcome and failure root cause if any.
- Control mapping reference (see cadence file).
- Evidence manifest with SHA256 digests (`artifacts/compliance/soc2-evidence-manifest.json`).

## 3) Control Testing Cadence

See: `docs/audits/control-testing-cadence-q1-2026.md`

- Weekly: high-risk preventive controls (policy hard-limits, approval gates, replay/idempotency).
- Monthly: full compliance suite + runbook walkthrough.
- Quarterly: incident simulation + rollback proof + control-owner signoff.

## 4) Gate For GA

GA requires all of the following:
1. PCI boundary decision documented with acquirer/sponsor + QSA path.
2. Compliance release check green on main branch.
3. No critical open control gaps in cadence tracker.
4. Incident drill and rollback evidence refreshed in current quarter.
